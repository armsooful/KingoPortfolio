"""
FDR + pykrx 기반 한국 주식 마스터/일별 데이터 적재 스크립트

사용 예시:
  python -m scripts.load_market_data --meta
  python -m scripts.load_market_data --prices --factors --days 5
  python -m scripts.load_market_data --prices --start-date 2025-01-01 --end-date 2025-01-31
"""

import argparse
import os
import time
from datetime import datetime, timedelta
from typing import Iterable, List, Optional

import pandas as pd
import FinanceDataReader as fdr
from pykrx import stock as pykrx_stock
from sqlalchemy import create_engine, Table, MetaData, text
from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import insert as pg_insert


def _get_engine():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    return create_engine(db_url)


def _normalize_date_str(value: str) -> Optional[datetime.date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        try:
            return datetime.strptime(value, "%Y%m%d").date()
        except Exception:
            return None


def update_stocks_meta(engine):
    print("[FDR] Updating stocks_meta...")

    active = fdr.StockListing("KRX")
    active = active.rename(
        columns={
            "Code": "code",
            "Name": "name",
            "Market": "market",
            "Sector": "sector",
            "Industry": "industry",
            "ListingDate": "listing_date",
        }
    )
    active["is_active"] = True

    try:
        delisted = fdr.StockListing("KRX-DELISTING")
        delisted = delisted.rename(
            columns={
                "Symbol": "code",
                "Name": "name",
                "Market": "market",
                "Sector": "sector",
                "Industry": "industry",
                "ListingDate": "listing_date",
                "DelistingDate": "delisting_date",
            }
        )
        delisted["is_active"] = False
    except Exception:
        delisted = pd.DataFrame(columns=active.columns.tolist() + ["delisting_date", "is_active"])

    meta_df = pd.concat([active, delisted], ignore_index=True)
    meta_df = meta_df.drop_duplicates("code", keep="last")

    # normalize
    for col in ["sector", "industry"]:
        if col not in meta_df.columns:
            meta_df[col] = None

    meta_df["listing_date"] = meta_df["listing_date"].apply(
        lambda x: _normalize_date_str(str(x)) if pd.notna(x) else None
    )
    if "delisting_date" in meta_df.columns:
        meta_df["delisting_date"] = meta_df["delisting_date"].apply(
            lambda x: _normalize_date_str(str(x)) if pd.notna(x) else None
        )
    else:
        meta_df["delisting_date"] = None

    meta_df["updated_at"] = datetime.utcnow()

    cols = [
        "code",
        "name",
        "market",
        "sector",
        "industry",
        "listing_date",
        "delisting_date",
        "is_active",
        "updated_at",
    ]
    meta_df = meta_df[cols]

    # upsert
    meta = MetaData()
    table = Table("stocks_meta", meta, autoload_with=engine)
    rows = meta_df.to_dict(orient="records")
    if not rows:
        print("No rows to upsert")
        return

    stmt = pg_insert(table).values(rows)
    update_cols = {c: stmt.excluded[c] for c in cols if c != "code"}
    stmt = stmt.on_conflict_do_update(index_elements=["code"], set_=update_cols)

    with engine.begin() as conn:
        conn.execute(stmt)

    print(f"[FDR] stocks_meta upserted: {len(rows)} rows")


def _daterange(start: datetime, end: datetime) -> Iterable[datetime]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _load_tickers(engine, market: Optional[str], limit: Optional[int]) -> List[str]:
    query = "SELECT code FROM stocks_meta WHERE is_active IS TRUE"
    params = {}
    if market:
        query += " AND market = :market"
        params["market"] = market
    query += " ORDER BY code"
    if limit:
        query += " LIMIT :limit"
        params["limit"] = limit
    with engine.begin() as conn:
        rows = conn.execute(text(query), params).fetchall()
    return [row[0] for row in rows]


def _fetch_by_ticker(target_date: str, tickers: List[str]) -> pd.DataFrame:
    date_str = target_date.replace("-", "")
    price_rows = []
    fund_rows = []
    cap_rows = []

    for ticker in tickers:
        try:
            df_price = pykrx_stock.get_market_ohlcv_by_date(date_str, date_str, ticker)
            if df_price is not None and not df_price.empty:
                row = df_price.iloc[-1].to_dict()
                row["code"] = ticker
                price_rows.append(row)
        except Exception as e:
            print(f"[PYKRX] ticker={ticker} price fetch failed: {e}")

        try:
            df_fund = pykrx_stock.get_market_fundamental_by_date(date_str, date_str, ticker)
            if df_fund is not None and not df_fund.empty:
                row = df_fund.iloc[-1].to_dict()
                row["code"] = ticker
                fund_rows.append(row)
        except Exception as e:
            print(f"[PYKRX] ticker={ticker} fund fetch failed: {e}")

        try:
            df_cap = pykrx_stock.get_market_cap_by_date(date_str, date_str, ticker)
            if df_cap is not None and not df_cap.empty:
                row = df_cap.iloc[-1].to_dict()
                row["code"] = ticker
                cap_rows.append(row)
        except Exception as e:
            print(f"[PYKRX] ticker={ticker} cap fetch failed: {e}")

    if not price_rows:
        return pd.DataFrame()

    df_price = pd.DataFrame(price_rows).set_index("code")
    df_fund = pd.DataFrame(fund_rows).set_index("code") if fund_rows else pd.DataFrame()
    df_cap = pd.DataFrame(cap_rows).set_index("code") if cap_rows else pd.DataFrame()

    df_daily = df_price.join(df_fund, how="left").join(df_cap[["시가총액"]] if "시가총액" in df_cap.columns else df_cap, how="left")
    df_daily.index.name = "code"
    df_daily = df_daily.reset_index()
    df_daily["date"] = target_date
    return df_daily


def insert_daily_data(
    engine,
    target_date: str,
    sleep_sec: float = 0.0,
    fallback_by_ticker: bool = False,
    market: Optional[str] = None,
    ticker_limit: Optional[int] = None,
):
    date_str = target_date.replace("-", "")
    print(f"[PYKRX] Processing {target_date}...")

    def _fetch_all_markets(fn, label: str):
        frames = []
        for mkt in ["KOSPI", "KOSDAQ", "KONEX"]:
            try:
                df = fn(date_str, market=mkt)
                if df is not None and not df.empty:
                    if label == "price":
                        print(f"[PYKRX] {mkt} columns={list(df.columns)} rows={len(df)}")
                    frames.append(df)
                else:
                    print(f"[PYKRX] {mkt} empty for {label}")
            except Exception as e:
                print(f"[PYKRX] {mkt} fetch failed for {label}: {e}")
        if frames:
            return pd.concat(frames)
        return pd.DataFrame()

    try:
        df_price = _fetch_all_markets(pykrx_stock.get_market_ohlcv_by_ticker, "price")
    except Exception as e:
        print(f"[PYKRX] Failed to fetch price data for {target_date}: {e}")
        return

    if df_price.empty or not set(["시가", "고가", "저가", "종가"]).issubset(df_price.columns):
        print(f"[PYKRX] No valid price data for {target_date}")
        # Fallback: single ticker sanity check
        try:
            df_single = pykrx_stock.get_market_ohlcv_by_date(date_str, date_str, "005930")
            if df_single is not None:
                print(f"[PYKRX] single ticker cols={list(df_single.columns)} rows={len(df_single)}")
        except Exception as e:
            print(f"[PYKRX] single ticker fetch failed: {e}")

        if not fallback_by_ticker:
            return

        tickers = _load_tickers(engine, market, ticker_limit)
        if not tickers:
            print("[PYKRX] No tickers found for fallback fetch")
            return
        print(f"[PYKRX] Fallback per-ticker fetch start (count={len(tickers)})")
        df_daily = _fetch_by_ticker(target_date, tickers)
        if df_daily.empty or not set(["시가", "고가", "저가", "종가"]).issubset(df_daily.columns):
            print(f"[PYKRX] Fallback per-ticker yielded no valid price data for {target_date}")
            return
        df_price = df_daily.set_index("code")
        df_fund = pd.DataFrame()
        df_cap = pd.DataFrame()
    else:
        df_fund = _fetch_all_markets(pykrx_stock.get_market_fundamental_by_ticker, "fund")
        df_cap = _fetch_all_markets(pykrx_stock.get_market_cap_by_ticker, "cap")
    if "date" not in df_price.columns:
        df_daily = df_price.join(df_fund, how="left").join(df_cap[["시가총액"]] if "시가총액" in df_cap.columns else df_cap, how="left")
        df_daily.index.name = "code"
        df_daily = df_daily.reset_index()
        df_daily["date"] = target_date
    else:
        df_daily = df_price
    prices = df_daily[["code", "date", "시가", "고가", "저가", "종가", "거래량", "등락률"]].copy()
    prices.columns = [
        "code",
        "date",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
        "change_rate",
    ]

    factors = df_daily[["code", "date", "시가총액", "PER", "PBR", "배당수익률"]].copy()
    factors.columns = [
        "code",
        "date",
        "market_cap",
        "per",
        "pbr",
        "dividend_yield",
    ]

    meta = MetaData()
    prices_table = Table("stock_price_daily", meta, autoload_with=engine)
    factors_table = Table("stocks_daily_factors", meta, autoload_with=engine)

    with engine.begin() as conn:
        if not prices.empty:
            stmt = pg_insert(prices_table).values(prices.to_dict(orient="records"))
            stmt = stmt.on_conflict_do_nothing(constraint='uq_stock_price_daily')
            conn.execute(stmt)
        if not factors.empty:
            stmt = pg_insert(factors_table).values(factors.to_dict(orient="records"))
            stmt = stmt.on_conflict_do_nothing(index_elements=["code", "date"])
            conn.execute(stmt)

    print(f"[PYKRX] Inserted daily data for {target_date} (prices={len(prices)} factors={len(factors)})")
    if sleep_sec > 0:
        time.sleep(sleep_sec)


def main():
    parser = argparse.ArgumentParser(description="Load market data into PostgreSQL")
    parser.add_argument("--meta", action="store_true", help="Update stocks_meta")
    parser.add_argument("--prices", action="store_true", help="Insert daily prices")
    parser.add_argument("--factors", action="store_true", help="Insert daily factors")
    parser.add_argument("--start-date", help="Start date YYYY-MM-DD")
    parser.add_argument("--end-date", help="End date YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=0, help="Number of recent days to load")
    parser.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds between days")
    parser.add_argument("--fallback-by-ticker", action="store_true", help="Fallback to per-ticker fetch when market fetch fails")
    parser.add_argument("--market", help="Market filter for fallback (KOSPI/KOSDAQ/KONEX)")
    parser.add_argument("--ticker-limit", type=int, help="Limit tickers for fallback fetch")
    args = parser.parse_args()

    engine = _get_engine()

    if not (args.meta or args.prices or args.factors):
        args.meta = True
        args.prices = True
        args.factors = True

    if args.meta:
        update_stocks_meta(engine)

    if args.prices or args.factors:
        if args.days and args.days > 0:
            end = datetime.now().date()
            start = end - timedelta(days=args.days - 1)
        elif args.start_date and args.end_date:
            start = datetime.fromisoformat(args.start_date).date()
            end = datetime.fromisoformat(args.end_date).date()
        else:
            # default: last 5 days
            end = datetime.now().date()
            start = end - timedelta(days=4)

        for d in _daterange(start, end):
            insert_daily_data(
                engine,
                d.strftime("%Y-%m-%d"),
                sleep_sec=args.sleep,
                fallback_by_ticker=args.fallback_by_ticker,
                market=args.market,
                ticker_limit=args.ticker_limit,
            )


if __name__ == "__main__":
    main()
