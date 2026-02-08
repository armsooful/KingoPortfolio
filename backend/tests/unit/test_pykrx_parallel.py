"""pykrx 병렬 처리 성능 테스트"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock
from app.services.pykrx_loader import PyKrxDataLoader
from app.models.real_data import StocksDailyPrice
from decimal import Decimal
import pandas as pd
from sqlalchemy.orm import Session


@pytest.mark.unit
@pytest.mark.financial
class TestPyKrxParallelLoading:
    """pykrx 병렬 처리 테스트"""

    @pytest.fixture
    def loader(self):
        """PyKrxDataLoader 인스턴스"""
        return PyKrxDataLoader()

    @pytest.fixture
    def sample_ohlcv_data(self):
        """샘플 OHLCV 데이터"""
        dates = pd.date_range('2025-01-01', periods=5, freq='D')
        return pd.DataFrame({
            '시가': [100.0, 101.0, 102.0, 103.0, 104.0],
            '고가': [105.0, 106.0, 107.0, 108.0, 109.0],
            '저가': [95.0, 96.0, 97.0, 98.0, 99.0],
            '종가': [102.0, 103.0, 104.0, 105.0, 106.0],
            '거래량': [1000000, 1100000, 1200000, 1300000, 1400000],
            '등락률': [0.5, 0.4, 0.3, 0.2, 0.1]
        }, index=dates)

    def test_load_daily_prices_basic(self, loader, db, sample_ohlcv_data):
        """기본 일별 시세 적재 테스트"""
        ticker = '005930'

        with patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_get:
            with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name:
                mock_get.return_value = sample_ohlcv_data
                mock_name.return_value = '삼성전자'

                result = loader.load_daily_prices(
                    db,
                    ticker,
                    '20250101',
                    '20250105',
                    '삼성전자'
                )

        assert result['success'] is True
        assert result['inserted'] == 5
        assert result['updated'] == 0

    def test_load_daily_prices_upsert(self, loader, db, sample_ohlcv_data):
        """Upsert 동작 테스트"""
        ticker = '005930'

        # 첫 번째 적재
        with patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_get:
            with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name:
                mock_get.return_value = sample_ohlcv_data
                mock_name.return_value = '삼성전자'

                result1 = loader.load_daily_prices(
                    db,
                    ticker,
                    '20250101',
                    '20250105',
                    '삼성전자'
                )

        assert result1['inserted'] == 5

        # 두 번째 적재 (가격 업데이트)
        updated_data = sample_ohlcv_data.copy()
        updated_data['종가'] = [103.0, 104.0, 105.0, 106.0, 107.0]

        with patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_get:
            with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name:
                mock_get.return_value = updated_data
                mock_name.return_value = '삼성전자'

                result2 = loader.load_daily_prices(
                    db,
                    ticker,
                    '20250101',
                    '20250105',
                    '삼성전자'
                )

        assert result2['inserted'] == 0
        assert result2['updated'] == 5

    @pytest.mark.slow
    def test_load_all_daily_prices_sequential(self, loader, db):
        """순차 처리 성능 테스트 (참고용)"""
        tickers = ['005930', '000660']  # 삼성전자, SK하이닉스

        sample_data = pd.DataFrame({
            '시가': [100.0] * 5,
            '고가': [105.0] * 5,
            '저가': [95.0] * 5,
            '종가': [102.0] * 5,
            '거래량': [1000000] * 5,
            '등락률': [0.5] * 5
        }, index=pd.date_range('2025-01-01', periods=5, freq='D'))

        with patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_get:
            with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name:
                mock_get.return_value = sample_data
                mock_name.side_effect = ['삼성전자', 'SK하이닉스']

                result = loader.load_all_daily_prices(
                    db,
                    '20250101',
                    '20250105',
                    tickers=tickers,
                    task_id='test_sequential'
                )

        assert result['success'] == 2
        assert result['failed'] == 0
        assert result['total_inserted'] == 10

    @pytest.mark.slow
    def test_load_all_daily_prices_parallel(self, loader, db):
        """병렬 처리 성능 테스트"""
        tickers = ['005930', '000660', '005490', '035420']  # 4개 종목

        sample_data = pd.DataFrame({
            '시가': [100.0] * 5,
            '고가': [105.0] * 5,
            '저가': [95.0] * 5,
            '종가': [102.0] * 5,
            '거래량': [1000000] * 5,
            '등락률': [0.5] * 5
        }, index=pd.date_range('2025-01-01', periods=5, freq='D'))

        with patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_get:
            with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name:
                mock_get.return_value = sample_data
                mock_name.side_effect = ['삼성전자', 'SK하이닉스', 'POSCO홀딩스', 'NAVER']

                result = loader.load_all_daily_prices_parallel(
                    db,
                    '20250101',
                    '20250105',
                    tickers=tickers,
                    task_id='test_parallel',
                    num_workers=2
                )

        assert result['success'] == 4
        assert result['failed'] == 0
        assert result['total_inserted'] == 20

    def test_parallel_thread_safety(self, loader, db):
        """병렬 처리 스레드 안전성 테스트"""
        import threading

        tickers = ['005930', '000660']
        results = {'count': 0}
        results_lock = threading.Lock()

        sample_data = pd.DataFrame({
            '시가': [100.0] * 5,
            '고가': [105.0] * 5,
            '저가': [95.0] * 5,
            '종가': [102.0] * 5,
            '거래량': [1000000] * 5,
            '등락률': [0.5] * 5
        }, index=pd.date_range('2025-01-01', periods=5, freq='D'))

        with patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_get:
            with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name:
                mock_get.return_value = sample_data
                mock_name.side_effect = ['삼성전자', 'SK하이닉스']

                result = loader.load_all_daily_prices_parallel(
                    db,
                    '20250101',
                    '20250105',
                    tickers=tickers,
                    task_id='test_thread_safety',
                    num_workers=2
                )

        # 결과 검증
        assert result['success'] + result['failed'] == len(tickers)

    def test_parallel_error_handling(self, loader, db):
        """병렬 처리 에러 처리 테스트"""
        tickers = ['005930', '000660']

        with patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_get:
            with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name:
                # 첫 번째 호출은 성공, 두 번째는 실패
                mock_get.side_effect = [
                    pd.DataFrame({
                        '시가': [100.0] * 5,
                        '고가': [105.0] * 5,
                        '저가': [95.0] * 5,
                        '종가': [102.0] * 5,
                        '거래량': [1000000] * 5,
                        '등락률': [0.5] * 5
                    }, index=pd.date_range('2025-01-01', periods=5, freq='D')),
                    Exception("Network error")
                ]
                mock_name.side_effect = ['삼성전자', 'SK하이닉스']

                result = loader.load_all_daily_prices_parallel(
                    db,
                    '20250101',
                    '20250105',
                    tickers=tickers,
                    task_id='test_error_handling',
                    num_workers=2
                )

        # 실패가 격리됨을 확인
        assert result['success'] == 1
        assert result['failed'] == 1

    def test_parallel_num_workers(self, loader, db):
        """스레드 수 설정 테스트"""
        tickers = ['005930', '000660', '005490', '035420']

        sample_data = pd.DataFrame({
            '시가': [100.0] * 5,
            '고가': [105.0] * 5,
            '저가': [95.0] * 5,
            '종가': [102.0] * 5,
            '거래량': [1000000] * 5,
            '등락률': [0.5] * 5
        }, index=pd.date_range('2025-01-01', periods=5, freq='D'))

        with patch('app.services.pykrx_loader.stock.get_market_ohlcv') as mock_get:
            with patch('app.services.pykrx_loader.stock.get_market_ticker_name') as mock_name:
                mock_get.return_value = sample_data
                mock_name.side_effect = ['삼성전자', 'SK하이닉스', 'POSCO홀딩스', 'NAVER']

                # 최대 4개 종목이므로 8개 스레드로도 가능
                result = loader.load_all_daily_prices_parallel(
                    db,
                    '20250101',
                    '20250105',
                    tickers=tickers,
                    task_id='test_num_workers',
                    num_workers=8
                )

        assert result['num_workers'] == 8
        assert result['success'] == 4
