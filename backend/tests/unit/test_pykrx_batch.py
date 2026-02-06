"""Unit tests for pykrx batch loading with PostgreSQL ON CONFLICT"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import patch, MagicMock
import pandas as pd

from app.services.pykrx_loader import PyKrxDataLoader
from app.models.real_data import StocksDailyPrice


@pytest.mark.unit
class TestPyKrxBatchLoading:
    """PyKrxDataLoader 배치 로딩 테스트"""

    @pytest.fixture
    def loader(self):
        """PyKrxDataLoader 인스턴스 생성"""
        return PyKrxDataLoader()

    @pytest.fixture
    def sample_ohlcv_data(self):
        """샘플 OHLCV 데이터"""
        return pd.DataFrame({
            '시가': [100.0, 101.0, 102.0, 103.0, 104.0],
            '고가': [105.0, 106.0, 107.0, 108.0, 109.0],
            '저가': [95.0, 96.0, 97.0, 98.0, 99.0],
            '종가': [102.0, 103.0, 104.0, 105.0, 106.0],
            '거래량': [1000000, 1100000, 1200000, 1300000, 1400000],
            '등락률': [0.5, 1.0, 1.5, 2.0, 2.5]
        }, index=pd.date_range('2025-01-01', periods=5, freq='D'))

    def test_load_daily_prices_batch_basic_success(self, db, loader, sample_ohlcv_data):
        """배치 모드 기본 적재 성공"""
        with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name, \
             patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_ohlcv:
            mock_name.return_value = '삼성전자'
            mock_ohlcv.return_value = sample_ohlcv_data

            result = loader.load_daily_prices_batch(
                db, '005930', '20250101', '20250105', '삼성전자'
            )

        assert result['success'] is True
        assert result['inserted'] == 5
        assert '5건' in result['message']
        assert '삼성전자' in result['message']

    def test_load_daily_prices_batch_empty_data(self, db, loader):
        """배치 모드 빈 데이터 처리"""
        with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name, \
             patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_ohlcv:
            mock_name.return_value = '테스트'
            mock_ohlcv.return_value = pd.DataFrame()

            result = loader.load_daily_prices_batch(
                db, '999999', '20250101', '20250105', '테스트'
            )

        assert result['success'] is True
        assert result['inserted'] == 0
        assert '데이터 없음' in result['message']

    def test_load_daily_prices_batch_upsert_idempotent(self, db, loader, sample_ohlcv_data):
        """배치 모드 upsert는 중복 실행해도 안전"""
        with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name, \
             patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_ohlcv:
            mock_name.return_value = '삼성전자'
            mock_ohlcv.return_value = sample_ohlcv_data

            # 1차 적재
            result1 = loader.load_daily_prices_batch(
                db, '005930', '20250101', '20250105', '삼성전자'
            )

            assert result1['success'] is True
            assert result1['inserted'] == 5

            # DB에 저장된 레코드 수 확인
            count_after_first = db.query(StocksDailyPrice).filter(
                StocksDailyPrice.code == '005930'
            ).count()
            assert count_after_first == 5

            # 2차 적재 (동일 데이터)
            result2 = loader.load_daily_prices_batch(
                db, '005930', '20250101', '20250105', '삼성전자'
            )

            assert result2['success'] is True
            assert result2['inserted'] == 5

            # DB에 저장된 레코드 수 확인 (증가하지 않아야 함)
            count_after_second = db.query(StocksDailyPrice).filter(
                StocksDailyPrice.code == '005930'
            ).count()
            assert count_after_second == 5  # 중복 없이 유지

    def test_load_daily_prices_batch_large_dataset_chunking(self, db, loader):
        """배치 모드 대용량 데이터 (1000건) 분할 처리"""
        # 1000건 샘플 데이터 생성
        large_data = pd.DataFrame({
            '시가': [100.0 + i*0.1 for i in range(1000)],
            '고가': [105.0 + i*0.1 for i in range(1000)],
            '저가': [95.0 + i*0.1 for i in range(1000)],
            '종가': [102.0 + i*0.1 for i in range(1000)],
            '거래량': [1000000 + i*100 for i in range(1000)],
            '등락률': [0.5 + i*0.01 for i in range(1000)]
        }, index=pd.date_range('2024-01-01', periods=1000, freq='D'))

        with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name, \
             patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_ohlcv:
            mock_name.return_value = '테스트'
            mock_ohlcv.return_value = large_data

            result = loader.load_daily_prices_batch(
                db, '999999', '20240101', '20261231', '테스트', batch_size=500
            )

        assert result['success'] is True
        assert result['inserted'] == 1000

        # DB에 저장된 레코드 수 확인
        count = db.query(StocksDailyPrice).filter(
            StocksDailyPrice.code == '999999'
        ).count()
        assert count == 1000

    def test_load_daily_prices_batch_with_null_values(self, db, loader):
        """배치 모드 NULL 값 처리"""
        data_with_nulls = pd.DataFrame({
            '시가': [100.0, None, 102.0, 103.0, 104.0],
            '고가': [105.0, 106.0, None, 108.0, 109.0],
            '저가': [95.0, 96.0, 97.0, None, 99.0],
            '종가': [102.0, 103.0, 104.0, 105.0, None],
            '거래량': [1000000, None, 1200000, 1300000, 1400000],
            '등락률': [0.5, 1.0, None, 2.0, 2.5]
        }, index=pd.date_range('2025-01-01', periods=5, freq='D'))

        with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name, \
             patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_ohlcv:
            mock_name.return_value = '테스트'
            mock_ohlcv.return_value = data_with_nulls

            result = loader.load_daily_prices_batch(
                db, '999999', '20250101', '20250105', '테스트'
            )

        assert result['success'] is True
        assert result['inserted'] == 5

        # DB에서 NULL 값이 제대로 저장되었는지 확인
        records = db.query(StocksDailyPrice).filter(
            StocksDailyPrice.code == '999999'
        ).all()

        assert len(records) == 5

        # 일부 NULL 값 확인
        assert records[1].high_price == Decimal('106.0')  # high_price는 값 있음
        assert records[1].open_price is None  # open_price는 NULL
        assert records[2].high_price is None  # high_price는 NULL

    def test_load_daily_prices_batch_exception_handling(self, db, loader):
        """배치 모드 예외 처리"""
        with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name, \
             patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_ohlcv:
            mock_name.return_value = '테스트'
            mock_ohlcv.side_effect = Exception("API Error")

            result = loader.load_daily_prices_batch(
                db, '999999', '20250101', '20250105', '테스트'
            )

        assert result['success'] is False
        assert 'API Error' in result['message']
        assert result['inserted'] == 0

    def test_load_daily_prices_batch_records_structure(self, db, loader, sample_ohlcv_data):
        """배치 모드 레코드 구조 확인"""
        with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name, \
             patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_ohlcv:
            mock_name.return_value = '삼성전자'
            mock_ohlcv.return_value = sample_ohlcv_data

            result = loader.load_daily_prices_batch(
                db, '005930', '20250101', '20250105', '삼성전자'
            )

        assert result['success'] is True

        # DB에서 저장된 데이터 확인
        records = db.query(StocksDailyPrice).filter(
            StocksDailyPrice.code == '005930'
        ).order_by(StocksDailyPrice.date).all()

        assert len(records) == 5
        # 첫 번째 레코드 확인
        assert records[0].code == '005930'
        assert records[0].date == date(2025, 1, 1)
        assert records[0].open_price == Decimal('100.0')
        assert records[0].close_price == Decimal('102.0')
        assert records[0].volume == 1000000

    def test_load_daily_prices_batch_default_name(self, db, loader, sample_ohlcv_data):
        """배치 모드 기본 종목명 (ticker로 폴백)"""
        with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name, \
             patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_ohlcv:
            mock_name.return_value = None  # 종목명 조회 실패
            mock_ohlcv.return_value = sample_ohlcv_data

            result = loader.load_daily_prices_batch(
                db, '005930', '20250101', '20250105'
            )

        assert result['success'] is True
        assert '005930' in result['message']  # ticker로 폴백됨


@pytest.mark.integration
class TestPyKrxBatchIntegration:
    """배치 로딩 통합 테스트"""

    def test_batch_mode_with_multiple_stocks_sequential(self, db):
        """여러 종목 배치 모드 순차 처리 (병렬 아님)"""
        loader = PyKrxDataLoader()

        sample_data = pd.DataFrame({
            '시가': [100.0] * 5,
            '고가': [105.0] * 5,
            '저가': [95.0] * 5,
            '종가': [102.0] * 5,
            '거래량': [1000000] * 5,
            '등락률': [0.5] * 5
        }, index=pd.date_range('2025-01-01', periods=5, freq='D'))

        with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name, \
             patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_ohlcv:

            mock_name.side_effect = lambda x: {
                '005930': '삼성전자',
                '000660': 'SK하이닉스'
            }.get(x, x)
            mock_ohlcv.return_value = sample_data

            # 2개 종목 순차 적재
            result1 = loader.load_daily_prices_batch(
                db, '005930', '20250101', '20250105'
            )
            result2 = loader.load_daily_prices_batch(
                db, '000660', '20250101', '20250105'
            )

        assert result1['success'] is True
        assert result2['success'] is True
        assert result1['inserted'] == 5
        assert result2['inserted'] == 5

        # DB에서 실제 데이터 확인
        count = db.query(StocksDailyPrice).filter(
            StocksDailyPrice.code.in_(['005930', '000660'])
        ).count()
        assert count == 10

    def test_batch_mode_data_integrity(self, db):
        """배치 모드 데이터 무결성 확인"""
        loader = PyKrxDataLoader()

        # 정확한 OHLCV 데이터
        open_prices = [100.0, 101.5, 102.0, 103.5, 104.0]
        sample_data = pd.DataFrame({
            '시가': open_prices,
            '고가': [105.5, 106.0, 107.5, 108.0, 109.5],
            '저가': [95.5, 96.0, 97.5, 98.0, 99.5],
            '종가': [102.5, 103.0, 104.5, 105.0, 106.5],
            '거래량': [1000000, 1100000, 1200000, 1300000, 1400000],
            '등락률': [0.5, 1.0, 1.5, 2.0, 2.5]
        }, index=pd.date_range('2025-01-01', periods=5, freq='D'))

        with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name, \
             patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_ohlcv:

            mock_name.return_value = '삼성전자'
            mock_ohlcv.return_value = sample_data

            result = loader.load_daily_prices_batch(
                db, '005930', '20250101', '20250105'
            )

        assert result['success'] is True

        # DB에서 데이터 검증
        records = db.query(StocksDailyPrice).filter(
            StocksDailyPrice.code == '005930'
        ).order_by(StocksDailyPrice.date).all()

        assert len(records) == 5

        # 각 레코드의 값 확인
        for i, record in enumerate(records):
            assert record.code == '005930'
            assert record.open_price == Decimal(str(open_prices[i]))
            assert record.volume == 1000000 + (i * 100000)
