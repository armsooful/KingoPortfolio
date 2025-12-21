#!/bin/bash

DB_PATH="/Users/changrim/KingoPortfolio/backend/kingo.db"

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================="
echo "  KingoPortfolio 데이터베이스 조회"
echo -e "==========================================${NC}"
echo ""

# 메뉴 표시
if [ -z "$1" ]; then
    echo "사용법: ./view_db.sh [옵션]"
    echo ""
    echo "옵션:"
    echo "  all        - 모든 테이블 확인"
    echo "  stocks     - 주식 데이터"
    echo "  etfs       - ETF 데이터"
    echo "  bonds      - 채권 데이터"
    echo "  deposits   - 예적금 데이터"
    echo "  users      - 사용자 목록"
    echo "  schema     - 테이블 구조"
    echo "  count      - 데이터 개수"
    echo ""
    echo "예시: ./view_db.sh stocks"
    exit 0
fi

case "$1" in
    all)
        echo -e "${BLUE}📊 전체 데이터 현황${NC}"
        sqlite3 $DB_PATH << 'EOF'
.mode column
.headers on
SELECT
  (SELECT COUNT(*) FROM stocks) as 주식,
  (SELECT COUNT(*) FROM etfs) as ETF,
  (SELECT COUNT(*) FROM bonds) as 채권,
  (SELECT COUNT(*) FROM deposit_products) as 예적금,
  (SELECT COUNT(*) FROM users) as 사용자;
EOF
        echo ""
        echo -e "${BLUE}📈 주식${NC}"
        sqlite3 $DB_PATH << 'EOF'
.mode box
.headers on
SELECT ticker as 티커, name as 종목명, CAST(current_price as INT) as 현재가,
       CAST(market_cap/1000000000000 as INT) as '시총(조)', category as 카테고리
FROM stocks ORDER BY market_cap DESC LIMIT 5;
EOF
        echo ""
        echo -e "${BLUE}📊 ETF${NC}"
        sqlite3 $DB_PATH << 'EOF'
.mode box
.headers on
SELECT ticker as 티커, name as ETF명, CAST(current_price as INT) as 현재가
FROM etfs LIMIT 5;
EOF
        ;;

    stocks)
        echo -e "${BLUE}📈 주식 데이터 (13개)${NC}"
        echo ""
        sqlite3 $DB_PATH << 'EOF'
.mode box
.headers on
SELECT
  ticker as 티커,
  name as 종목명,
  CAST(current_price as INT) as 현재가,
  CAST(market_cap/1000000000000 as INT) as '시총(조)',
  pe_ratio as PER,
  dividend_yield as '배당(%)',
  risk_level as 위험도,
  category as 카테고리
FROM stocks
ORDER BY market_cap DESC;
EOF
        ;;

    etfs)
        echo -e "${BLUE}📊 ETF 데이터 (5개)${NC}"
        echo ""
        sqlite3 $DB_PATH << 'EOF'
.mode box
.headers on
SELECT
  ticker as 티커,
  name as ETF명,
  CAST(current_price as INT) as 현재가,
  etf_type as 유형,
  ROUND(ytd_return, 2) as '연초수익률(%)',
  risk_level as 위험도
FROM etfs;
EOF
        ;;

    bonds)
        echo -e "${BLUE}💰 채권 데이터 (3개)${NC}"
        echo ""
        sqlite3 $DB_PATH << 'EOF'
.mode box
.headers on
SELECT
  name as 채권명,
  bond_type as 유형,
  interest_rate as '금리(%)',
  maturity_years as '만기(년)',
  credit_rating as 신용등급,
  risk_level as 위험도
FROM bonds;
EOF
        ;;

    deposits)
        echo -e "${BLUE}💵 예적금 데이터 (3개)${NC}"
        echo ""
        sqlite3 $DB_PATH << 'EOF'
.mode box
.headers on
SELECT
  name as 상품명,
  bank as 은행,
  product_type as 유형,
  interest_rate as '금리(%)',
  CAST(minimum_investment as INT) as 최소가입액
FROM deposit_products;
EOF
        ;;

    users)
        echo -e "${BLUE}👥 사용자 목록${NC}"
        echo ""
        sqlite3 $DB_PATH << 'EOF'
.mode box
.headers on
SELECT
  id,
  email,
  name,
  created_at as 가입일
FROM users;
EOF
        ;;

    schema)
        echo -e "${BLUE}🏗️  테이블 구조${NC}"
        echo ""
        sqlite3 $DB_PATH << 'EOF'
.tables

.schema stocks
EOF
        ;;

    count)
        echo -e "${BLUE}📊 데이터 개수${NC}"
        echo ""
        sqlite3 $DB_PATH << 'EOF'
.mode box
.headers on
SELECT
  '주식' as 카테고리, (SELECT COUNT(*) FROM stocks) as 개수
UNION ALL
SELECT 'ETF', (SELECT COUNT(*) FROM etfs)
UNION ALL
SELECT '채권', (SELECT COUNT(*) FROM bonds)
UNION ALL
SELECT '예적금', (SELECT COUNT(*) FROM deposit_products)
UNION ALL
SELECT '사용자', (SELECT COUNT(*) FROM users)
UNION ALL
SELECT '진단기록', (SELECT COUNT(*) FROM diagnoses);
EOF
        ;;

    *)
        echo "알 수 없는 옵션: $1"
        echo "사용법: ./view_db.sh [all|stocks|etfs|bonds|deposits|users|schema|count]"
        exit 1
        ;;
esac

echo ""
