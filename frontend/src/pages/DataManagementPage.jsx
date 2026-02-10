// frontend/src/pages/DataManagementPage.jsx

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../services/api';
import ProgressModal from '../components/ProgressModal';
import DataTable from '../components/DataTable';

export default function DataManagementPage() {
  const [loading, setLoading] = useState(false);
  const [dataStatus, setDataStatus] = useState(null);
  const [loadResult, setLoadResult] = useState(null);
  const [error, setError] = useState(null);
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [activeTab, setActiveTab] = useState('stocks');
  const [symbolInput, setSymbolInput] = useState('');
  const [dividendTickers, setDividendTickers] = useState('');
  const [dividendBasDt, setDividendBasDt] = useState('');
  const [dividendAsOf, setDividendAsOf] = useState(new Date().toISOString().split('T')[0]);
  const [actionStart, setActionStart] = useState('');
  const [actionEnd, setActionEnd] = useState('');
  const [actionAsOf, setActionAsOf] = useState(new Date().toISOString().split('T')[0]);
  const [dartFiscalYear, setDartFiscalYear] = useState(2024);
  const [dartReportType, setDartReportType] = useState('ANNUAL');
  const [dartFinLimit, setDartFinLimit] = useState('');
  const [fdrMarket, setFdrMarket] = useState('KRX');
  const [fdrAsOf, setFdrAsOf] = useState(new Date().toISOString().split('T')[0]);
  const [bondQualityFilter, setBondQualityFilter] = useState('all');
  const navigate = useNavigate();

  useEffect(() => {
    fetchDataStatus();
  }, []);

  const fetchDataStatus = async () => {
    try {
      const response = await api.getDataStatus();
      setDataStatus(response.data);
    } catch (err) {
      console.error('Failed to fetch data status:', err);
      if (err.response?.status === 401) {
        navigate('/login');
      }
    }
  };

  const handleLoadData = async (type) => {
    const typeNames = { stocks: '주식', etfs: 'ETF' };
    if (!window.confirm(`${typeNames[type]} 데이터를 수집하시겠습니까?`)) {
      return;
    }

    setLoading(true);
    setError(null);
    setLoadResult(null);

    // 임시 task_id로 즉시 모달 표시
    const tempTaskId = `temp_${type}_${Date.now()}`;
    setCurrentTaskId(tempTaskId);

    try {
      let response;
      if (type === 'stocks') response = await api.loadStocks();
      else response = await api.loadETFs();

      setLoadResult(response.data);

      // 실제 task_id로 업데이트
      if (response.data.task_id) {
        setCurrentTaskId(response.data.task_id);
      }

      await fetchDataStatus();
    } catch (err) {
      setError(err.response?.data?.detail || '데이터 수집 실패');
      setCurrentTaskId(null); // 에러 시 모달 닫기
    } finally {
      setLoading(false);
    }
  };

  const handleLoadBonds = async () => {
    const filterLabels = {
      all: '전체 채권',
      investment_grade: '투자적격등급 (AAA~BBB) 채권',
      high_quality: '최우량 (AAA~A) 채권',
    };
    const label = filterLabels[bondQualityFilter] || '전체 채권';

    if (!window.confirm(`${label}을 조회하시겠습니까?`)) {
      return;
    }

    setLoading(true);
    setError(null);
    setLoadResult(null);

    // 임시 task_id로 즉시 모달 표시
    const tempTaskId = `temp_bonds_${Date.now()}`;
    setCurrentTaskId(tempTaskId);

    try {
      const response = await api.loadBonds(bondQualityFilter);

      setLoadResult(response.data);

      // 실제 task_id로 업데이트
      if (response.data.task_id) {
        setCurrentTaskId(response.data.task_id);
      }

      await fetchDataStatus();
    } catch (err) {
      setError(err.response?.data?.detail || '채권 데이터 조회 실패');
      setCurrentTaskId(null); // 에러 시 모달 닫기
    } finally {
      setLoading(false);
    }
  };

  const handleProgressComplete = useCallback(async (progressData) => {
    await fetchDataStatus();
  }, []);

  const handleCloseModal = useCallback(() => {
    setCurrentTaskId(null);
  }, []);

  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card" style={{ maxWidth: '1200px' }}>
          {/* Header */}
          <div className="result-header">
            <div className="result-icon" style={{ fontSize: '3rem' }}>
              🗄️
            </div>
            <h1 className="result-type" style={{ color: '#667eea' }}>
              데이터 관리
            </h1>
            <p className="result-subtitle">종목 정보 수집 및 데이터베이스 관리</p>
          </div>

          {/* Data Status Cards */}
          {dataStatus && (
            <div className="description-section">
              <h2>📊 현재 데이터 현황</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginTop: '20px' }}>
                <div className="score-card">
                  <div className="score-label">📈 주식</div>
                  <div className="score-value" style={{ color: '#2196F3' }}>
                    {dataStatus.stocks}개
                  </div>
                </div>
                <div className="score-card">
                  <div className="score-label">📊 ETF</div>
                  <div className="score-value" style={{ color: '#9C27B0' }}>
                    {dataStatus.etfs}개
                  </div>
                </div>
                <div className="score-card">
                  <div className="score-label">💰 채권</div>
                  <div className="score-value" style={{ color: '#4CAF50' }}>
                    {dataStatus.bonds}개
                  </div>
                </div>
                <div className="score-card">
                  <div className="score-label">🏦 예금</div>
                  <div className="score-value" style={{ color: '#FF9800' }}>
                    {dataStatus.deposits}개
                  </div>
                </div>
                <div className="score-card">
                  <div className="score-label">🏦 적금</div>
                  <div className="score-value" style={{ color: '#E91E63' }}>
                    {dataStatus.savings || 0}개
                  </div>
                </div>
                <div className="score-card">
                  <div className="score-label">🏛️ 연금저축</div>
                  <div className="score-value" style={{ color: '#673AB7' }}>
                    {dataStatus.annuity_savings || 0}개
                  </div>
                </div>
                <div className="score-card">
                  <div className="score-label">🏠 주담대</div>
                  <div className="score-value" style={{ color: '#795548' }}>
                    {dataStatus.mortgage_loans || 0}개
                  </div>
                </div>
                <div className="score-card">
                  <div className="score-label">🏠 전세대출</div>
                  <div className="score-value" style={{ color: '#607D8B' }}>
                    {dataStatus.rent_house_loans || 0}개
                  </div>
                </div>
                <div className="score-card">
                  <div className="score-label">💳 신용대출</div>
                  <div className="score-value" style={{ color: '#E91E63' }}>
                    {dataStatus.credit_loans || 0}개
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* yfinance Data Collection Section */}
          <div className="description-section">
            <h2>🔄 데이터 수집</h2>
            <div className="info-box" style={{ marginTop: '15px', padding: '15px', background: '#f0f7ff', borderRadius: '8px', borderLeft: '4px solid #2196F3' }}>
              <p style={{ margin: 0, color: '#333' }}>
                💡 KRX(pykrx)로 실시간 종목 정보를 수집합니다.
              </p>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginTop: '20px' }}>
              <button
                onClick={() => handleLoadData('stocks')}
                disabled={loading}
                className="btn btn-primary"
                style={{ padding: '20px', fontSize: '1rem', fontWeight: 'bold' }}
              >
                📈 주식 데이터
              </button>
              <button
                onClick={() => handleLoadData('etfs')}
                disabled={loading}
                className="btn btn-primary"
                style={{ padding: '20px', fontSize: '1rem', fontWeight: 'bold' }}
              >
                📊 ETF 데이터
              </button>
            </div>
          </div>

          {/* Progress Modal */}
          {currentTaskId && (
            <ProgressModal
              taskId={currentTaskId}
              onComplete={handleProgressComplete}
              onClose={handleCloseModal}
            />
          )}

          {/* Loading */}
          {loading && !currentTaskId && (
            <div className="loading-container">
              <div className="spinner"></div>
              <p>데이터 수집 중...</p>
              <p style={{ fontSize: '0.9rem', color: '#666' }}>잠시만 기다려주세요</p>
            </div>
          )}

          {/* Success Message */}
          {loadResult && (
            <div className="ai-card" style={{ background: '#f0fdf4', borderLeft: '4px solid #4CAF50' }}>
              <h3 style={{ color: '#4CAF50', marginBottom: '15px' }}>✅ {loadResult.message}</h3>
              {loadResult.results && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {Object.entries(loadResult.results).map(([key, val]) => (
                    <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', background: 'white', borderRadius: '6px', border: '1px solid #e0e0e0' }}>
                      <span style={{ fontWeight: 'bold' }}>{key}</span>
                      <div style={{ display: 'flex', gap: '20px', fontSize: '0.9rem' }}>
                        <span style={{ color: '#4CAF50' }}>✓ {val.success}</span>
                        <span style={{ color: '#2196F3' }}>↻ {val.updated}</span>
                        <span style={{ color: '#f44336' }}>✗ {val.failed || 0}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="ai-card risk-warning">
              <h3>❌ 오류 발생</h3>
              <p className="ai-content">{error}</p>
            </div>
          )}

          {/* Alpha Vantage Section */}
          <div className="description-section" style={{ marginTop: '40px', borderTop: '2px solid #e0e0e0', paddingTop: '30px' }}>
            <h2>🌍 Alpha Vantage - 미국 주식 데이터</h2>
            <div className="info-box" style={{ marginTop: '15px', padding: '15px', background: '#fff8e1', borderRadius: '8px', borderLeft: '4px solid #FFC107' }}>
              <p style={{ margin: 0, color: '#333', fontSize: '0.9rem' }}>
                📊 Alpha Vantage API를 통해 미국 주식 시세 및 재무제표를 수집합니다.<br />
                ⚠️ 무료 플랜: 25 requests/day, 5 requests/minute (약 12초 간격)
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '15px', marginTop: '20px' }}>
              <button
                onClick={async () => {
                  if (!window.confirm('인기 미국 주식 전체를 수집하시겠습니까? (약 5-10분 소요, API Rate Limit 주의)')) return;

                  setLoading(true);
                  setError(null);
                  setLoadResult(null);

                  try {
                    const response = await api.loadAllAlphaVantageStocks();
                    setLoadResult(response.data);

                    // task_id로 모달 표시
                    if (response.data.task_id || response.data.result?.task_id) {
                      setCurrentTaskId(response.data.task_id || response.data.result.task_id);
                    }

                    await fetchDataStatus();
                  } catch (err) {
                    setError(err.response?.data?.detail || '미국 주식 데이터 수집 실패');
                    setCurrentTaskId(null);
                  } finally {
                    setLoading(false);
                  }
                }}
                className="btn btn-primary"
                style={{ padding: '20px', fontSize: '1rem', fontWeight: 'bold' }}
              >
                🇺🇸 미국 주식 전체 수집
              </button>

              <button
                onClick={async () => {
                  if (!window.confirm('인기 미국 ETF 전체를 수집하시겠습니까?')) return;

                  setLoading(true);
                  setError(null);
                  setLoadResult(null);

                  try {
                    const response = await api.loadAllAlphaVantageETFs();
                    setLoadResult(response.data);

                    // task_id로 모달 표시
                    if (response.data.task_id || response.data.result?.task_id) {
                      setCurrentTaskId(response.data.task_id || response.data.result.task_id);
                    }

                    await fetchDataStatus();
                  } catch (err) {
                    setError(err.response?.data?.detail || '미국 ETF 데이터 수집 실패');
                    setCurrentTaskId(null);
                  } finally {
                    setLoading(false);
                  }
                }}
                className="btn btn-primary"
                style={{ padding: '20px', fontSize: '1rem', fontWeight: 'bold' }}
              >
                📊 미국 ETF 전체 수집
              </button>

              <button
                disabled={loading}
                onClick={async () => {
                  if (!window.confirm('미국 주식/ETF 시계열 데이터(최근 100일)를 수집하시겠습니까?\n\nAPI 호출 제한으로 인해 시간이 걸릴 수 있습니다.')) {
                    return;
                  }

                  setLoading(true);
                  setError(null);

                  try {
                    const response = await api.loadAllAlphaVantageTimeSeries('compact');
                    setLoadResult(response.data);

                    // task_id로 모달 표시
                    if (response.data.task_id || response.data.result?.task_id) {
                      setCurrentTaskId(response.data.task_id || response.data.result.task_id);
                    }

                    await fetchDataStatus();
                  } catch (err) {
                    setError(err.response?.data?.detail || '시계열 데이터 수집 실패');
                    setCurrentTaskId(null);
                  } finally {
                    setLoading(false);
                  }
                }}
                className="btn btn-primary"
                style={{ padding: '20px', fontSize: '1rem', fontWeight: 'bold' }}
              >
                📈 시계열 데이터 수집 (Compact)
              </button>
            </div>

            <div style={{ marginTop: '20px', padding: '20px', background: '#f5f5f5', borderRadius: '8px' }}>
              <h3 style={{ marginBottom: '15px', fontSize: '1.1rem' }}>🔍 특정 종목 검색 & 적재</h3>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <input
                  type="text"
                  placeholder="종목 심볼 입력 (예: AAPL, TSLA)"
                  value={symbolInput}
                  onChange={(e) => setSymbolInput(e.target.value.toUpperCase())}
                  style={{
                    flex: '1',
                    minWidth: '200px',
                    padding: '12px',
                    fontSize: '1rem',
                    border: '2px solid #ddd',
                    borderRadius: '6px'
                  }}
                />
                <button
                  onClick={async () => {
                    const symbol = symbolInput.trim();
                    if (!symbol) {
                      alert('종목 심볼을 입력하세요');
                      return;
                    }

                    setLoading(true);
                    setError(null);

                    try {
                      const response = await api.loadAlphaVantageStock(symbol);

                      // task_id가 있으면 진행상황 모달 표시
                      if (response.data.task_id) {
                        setCurrentTaskId(response.data.task_id);
                      } else {
                        alert('✅ ' + response.data.message);
                        await fetchDataStatus();
                      }
                    } catch (err) {
                      alert('❌ ' + (err.response?.data?.detail || '실패'));
                      setCurrentTaskId(null);
                    } finally {
                      setLoading(false);
                    }
                  }}
                  className="btn btn-primary"
                  style={{ padding: '12px 24px' }}
                  disabled={loading}
                >
                  📈 시세 수집
                </button>
                <button
                  onClick={async () => {
                    const symbol = symbolInput.trim();
                    if (!symbol) {
                      alert('종목 심볼을 입력하세요');
                      return;
                    }

                    setLoading(true);
                    setError(null);

                    try {
                      const response = await api.loadAlphaVantageFinancials(symbol);

                      // task_id가 있으면 진행상황 모달 표시
                      if (response.data.task_id) {
                        setCurrentTaskId(response.data.task_id);
                      } else {
                        alert('✅ ' + response.data.message);
                        await fetchDataStatus();
                      }
                    } catch (err) {
                      alert('❌ ' + (err.response?.data?.detail || '실패'));
                      setCurrentTaskId(null);
                    } finally {
                      setLoading(false);
                    }
                  }}
                  className="btn btn-secondary"
                  style={{ padding: '12px 24px' }}
                  disabled={loading}
                >
                  📊 재무제표 수집
                </button>
              </div>
              <div style={{ marginTop: '10px', fontSize: '0.85rem', color: '#666' }}>
                💡 인기 종목: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, JPM, JNJ, KO 등
              </div>
            </div>
          </div>

          {/* pykrx Timeseries Section */}
          <div className="description-section" style={{ marginTop: '40px', borderTop: '2px solid #e0e0e0', paddingTop: '30px' }}>
            <h2>📈 pykrx - 한국 주식 시계열 데이터</h2>
            <div className="info-box" style={{ marginTop: '15px', padding: '15px', background: '#e3f2fd', borderRadius: '8px', borderLeft: '4px solid #2196F3' }}>
              <p style={{ margin: 0, color: '#333', fontSize: '0.9rem' }}>
                📊 한국 주식의 과거 가격 데이터(OHLCV)를 수집하여 백테스팅에 활용합니다.<br />
                ✅ KRX (한국거래소) 공식 데이터 - API 제한 없음
              </p>
            </div>

            <div style={{ marginTop: '20px', padding: '20px', background: '#f5f5f5', borderRadius: '8px' }}>
              <h3 style={{ marginBottom: '15px', fontSize: '1.1rem' }}>📥 단일 종목 시계열 데이터 수집</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9rem', fontWeight: '600' }}>
                    종목 코드 (6자리)
                  </label>
                  <input
                    type="text"
                    placeholder="005930 (삼성전자)"
                    maxLength={6}
                    value={symbolInput}
                    onChange={(e) => setSymbolInput(e.target.value.replace(/[^0-9]/g, ''))}
                    style={{
                      width: '100%',
                      padding: '10px',
                      fontSize: '1rem',
                      border: '2px solid #ddd',
                      borderRadius: '6px'
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9rem', fontWeight: '600' }}>
                    수집 기간
                  </label>
                  <select
                    id="krx-timeseries-days"
                    style={{
                      width: '100%',
                      padding: '10px',
                      fontSize: '1rem',
                      border: '2px solid #ddd',
                      borderRadius: '6px'
                    }}
                  >
                    <option value="90">3개월 (90일)</option>
                    <option value="180">6개월 (180일)</option>
                    <option value="365">1년 (365일)</option>
                    <option value="730">2년 (730일)</option>
                    <option value="1825">5년 (1825일)</option>
                    <option value="3650">10년 (3650일)</option>
                  </select>
                </div>
              </div>
              <button
                onClick={async () => {
                  const ticker = symbolInput.trim();
                  if (!ticker) {
                    alert('종목 코드를 입력하세요');
                    return;
                  }
                  if (ticker.length !== 6) {
                    alert('6자리 종목 코드를 입력하세요');
                    return;
                  }

                  const days = document.getElementById('krx-timeseries-days').value;

                  setLoading(true);
                  setError(null);

                  try {
                    const token = localStorage.getItem('access_token');
                    const response = await fetch(
                      `${import.meta.env.VITE_API_URL}/admin/krx-timeseries/load-stock/${ticker}?days=${days}`,
                      {
                        method: 'POST',
                        headers: { Authorization: `Bearer ${token}` }
                      }
                    );

                    if (!response.ok) {
                      const errorData = await response.json();
                      throw new Error(errorData.detail || '데이터 수집 실패');
                    }

                    const data = await response.json();
                    alert(`✅ ${ticker} 종목 데이터 ${data.records_added}건 수집 완료`);
                    await fetchDataStatus();
                  } catch (err) {
                    alert('❌ ' + err.message);
                  } finally {
                    setLoading(false);
                  }
                }}
                disabled={loading}
                className="btn btn-primary"
                style={{ width: '100%', padding: '12px', fontSize: '1rem', fontWeight: 'bold' }}
              >
                📊 시계열 데이터 수집
              </button>
              <div style={{ marginTop: '10px', fontSize: '0.85rem', color: '#666' }}>
                💡 예: 005930 (삼성전자), 000660 (SK하이닉스), 035420 (NAVER)
              </div>
            </div>

            <div style={{ marginTop: '20px', padding: '20px', background: '#fff3e0', borderRadius: '8px', border: '1px solid #ffb74d' }}>
              <h3 style={{ marginBottom: '15px', fontSize: '1.1rem' }}>📦 전체 종목 시계열 데이터 일괄 수집</h3>
              <div style={{ marginBottom: '10px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9rem', fontWeight: '600' }}>
                  처리할 종목 수 (최대 200개)
                </label>
                <input
                  type="number"
                  id="krx-timeseries-limit"
                  min="1"
                  max="200"
                  defaultValue="50"
                  style={{
                    width: '100%',
                    padding: '10px',
                    fontSize: '1rem',
                    border: '2px solid #ddd',
                    borderRadius: '6px'
                  }}
                />
              </div>
              <button
                onClick={async () => {
                  const limit = document.getElementById('krx-timeseries-limit').value;
                  const days = document.getElementById('krx-timeseries-days').value;

                  if (!window.confirm(`${limit}개 종목의 시계열 데이터를 수집하시겠습니까? (백그라운드 처리, 약 ${Math.ceil(limit / 10)}분 예상)`)) {
                    return;
                  }

                  setLoading(true);
                  setError(null);

                  try {
                    const token = localStorage.getItem('access_token');
                    const response = await fetch(
                      `${import.meta.env.VITE_API_URL}/admin/krx-timeseries/load-all-stocks?days=${days}&limit=${limit}`,
                      {
                        method: 'POST',
                        headers: { Authorization: `Bearer ${token}` }
                      }
                    );

                    if (!response.ok) {
                      const errorData = await response.json();
                      throw new Error(errorData.detail || '데이터 수집 실패');
                    }

                    const data = await response.json();
                    alert(`✅ ${data.total_count}개 종목 데이터 수집 시작 (백그라운드)`);

                    // 30초 후 상태 새로고침
                    setTimeout(() => {
                      fetchDataStatus();
                    }, 30000);
                  } catch (err) {
                    alert('❌ ' + err.message);
                  } finally {
                    setLoading(false);
                  }
                }}
                disabled={loading}
                className="btn btn-success"
                style={{ width: '100%', padding: '15px', fontSize: '1rem', fontWeight: 'bold' }}
              >
                {loading ? '🔄 시작 중...' : '🚀 일괄 수집 시작'}
              </button>
              <div style={{ marginTop: '10px', fontSize: '0.85rem', color: '#666', padding: '10px', background: '#fff', borderRadius: '5px' }}>
                ⚠️ 백그라운드에서 실행되며 시간이 걸릴 수 있습니다. 약 {Math.ceil(document.getElementById('krx-timeseries-limit')?.value / 10 || 5)}분 예상됩니다.
              </div>
            </div>

            <div style={{ marginTop: '20px', padding: '20px', background: '#e8f5e9', borderRadius: '8px', border: '1px solid #66bb6a' }}>
              <h3 style={{ marginBottom: '15px', fontSize: '1.1rem' }}>📦 전체 종목 5년치 증분 적재 (stocks 테이블 기준)</h3>
              <p style={{ margin: '0 0 15px 0', fontSize: '0.85rem', color: '#555' }}>
                stocks 테이블에 등록된 전 종목을 대상으로 시계열 데이터를 적재합니다.<br />
                이미 적재된 종목은 마지막 적재일 이후부터만 수집하여 부하를 줄입니다.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9rem', fontWeight: '600' }}>
                    시장 선택
                  </label>
                  <select
                    id="incremental-market"
                    style={{
                      width: '100%',
                      padding: '10px',
                      fontSize: '1rem',
                      border: '2px solid #ddd',
                      borderRadius: '6px'
                    }}
                  >
                    <option value="">KRX 전체</option>
                    <option value="KOSPI">KOSPI</option>
                    <option value="KOSDAQ">KOSDAQ</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.9rem', fontWeight: '600' }}>
                    스레드 수
                  </label>
                  <select
                    id="incremental-workers"
                    style={{
                      width: '100%',
                      padding: '10px',
                      fontSize: '1rem',
                      border: '2px solid #ddd',
                      borderRadius: '6px'
                    }}
                  >
                    <option value="2">2 (저부하)</option>
                    <option value="4" selected>4 (권장)</option>
                    <option value="6">6</option>
                    <option value="8">8 (고성능)</option>
                  </select>
                </div>
              </div>
              <button
                onClick={async () => {
                  const market = document.getElementById('incremental-market').value || null;
                  const numWorkers = Number(document.getElementById('incremental-workers').value) || 4;
                  const marketLabel = market || 'KRX 전체';

                  if (!window.confirm(
                    `[${marketLabel}] stocks 테이블 전 종목의 5년치 시계열 데이터를 증분 적재하시겠습니까?\n\n` +
                    `- 신규 종목: 5년치 수집\n` +
                    `- 기존 종목: 마지막 적재일 이후만 수집\n` +
                    `- 스레드: ${numWorkers}개\n\n` +
                    `⚠️ 첫 실행 시 4-6시간 소요될 수 있습니다.`
                  )) {
                    return;
                  }

                  setLoading(true);
                  setError(null);
                  const tempTaskId = `temp_incremental_${Date.now()}`;
                  setCurrentTaskId(tempTaskId);

                  try {
                    const res = await api.loadStocksIncremental({
                      default_days: 1825,
                      num_workers: numWorkers,
                      market: market,
                    });
                    if (res.data.task_id) {
                      setCurrentTaskId(res.data.task_id);
                    }
                    const stats = res.data.stats || {};
                    alert(
                      `✅ 증분 적재 시작\n` +
                      `대상: ${stats.total_stocks || '?'}종목\n` +
                      `신규 추정: ${stats.new_stocks_estimate || '?'}종목\n` +
                      `task_id: ${res.data.task_id}`
                    );
                    await fetchDataStatus();
                  } catch (err) {
                    alert('❌ ' + (err.response?.data?.detail || '증분 적재 시작 실패'));
                    setCurrentTaskId(null);
                  } finally {
                    setLoading(false);
                  }
                }}
                disabled={loading}
                className="btn btn-success"
                style={{ width: '100%', padding: '15px', fontSize: '1rem', fontWeight: 'bold', background: '#2e7d32' }}
              >
                {loading ? '🔄 시작 중...' : '📦 전체 종목 5년치 증분 적재'}
              </button>
              <div style={{ marginTop: '10px', fontSize: '0.85rem', color: '#555', padding: '10px', background: '#fff', borderRadius: '5px' }}>
                💡 첫 실행: 약 4-6시간 (야간 실행 권장) / 매일 재실행: 약 10-30분 (증분만 수집)
              </div>
            </div>
          </div>

          <div className="description-section" style={{ marginTop: '40px', borderTop: '2px solid #e0e0e0', paddingTop: '30px' }}>
            <h2>📦 배당/기업액션/채권/재무제표 적재</h2>

            <div style={{ marginTop: '15px', padding: '15px', background: '#e3f2fd', borderRadius: '8px', borderLeft: '4px solid #2196f3' }}>
              <p style={{ margin: 0, color: '#333', fontSize: '0.9rem' }}>
                🔑 배당·채권: 금융위원회 OpenAPI 키가 필요합니다. 기업액션·재무제표: DART API Key가 필요합니다.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '15px', marginTop: '20px' }}>
              <div style={{ padding: '15px', border: '1px solid #e5e7eb', borderRadius: '8px', background: '#ffffff' }}>
                <h3 style={{ marginBottom: '10px', fontSize: '1rem' }}>배당 이력 (금융위원회 OpenAPI)</h3>
                <input
                  type="text"
                  value={dividendTickers}
                  onChange={(e) => setDividendTickers(e.target.value)}
                  placeholder="종목 코드 (쉼표로 구분) 예: 005930,000660"
                  style={{ width: '100%', padding: '10px', fontSize: '0.9rem', border: '1px solid #ddd', borderRadius: '6px', marginBottom: '8px' }}
                />
                <input
                  type="date"
                  value={dividendAsOf}
                  onChange={(e) => setDividendAsOf(e.target.value)}
                  style={{ width: '100%', padding: '10px', fontSize: '0.9rem', border: '1px solid #ddd', borderRadius: '6px', marginBottom: '10px' }}
                />
                <input
                  type="text"
                  value={dividendBasDt}
                  onChange={(e) => setDividendBasDt(e.target.value.replace(/[^0-9]/g, '').slice(0, 8))}
                  placeholder="기준일자 (YYYYMMDD) - 비워두면 회사명으로 전체 조회"
                  style={{ width: '100%', padding: '10px', fontSize: '0.9rem', border: '1px solid #ddd', borderRadius: '6px', marginBottom: '10px' }}
                />
                <button
                  onClick={async () => {
                    const tickers = dividendTickers.split(',').map((t) => t.trim()).filter(Boolean);
                    if (tickers.length === 0) {
                      alert('종목 코드를 입력하세요');
                      return;
                    }
                    setLoading(true);
                    setError(null);
                    try {
                      const response = await api.loadFscDividends({
                        tickers,
                        bas_dt: dividendBasDt || null,
                        as_of_date: dividendAsOf,
                      });
                      alert('✅ ' + response.data.message);
                    } catch (err) {
                      alert('❌ ' + (err.response?.data?.detail || '배당 이력 적재 실패'));
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading}
                  className="btn btn-primary"
                  style={{ width: '100%', padding: '10px', fontSize: '0.95rem' }}
                >
                  배당 이력 적재 (FSC)
                </button>
              </div>

              <div style={{ padding: '15px', border: '1px solid #e5e7eb', borderRadius: '8px', background: '#ffffff' }}>
                <h3 style={{ marginBottom: '10px', fontSize: '1rem' }}>기업 액션 (DART 공시)</h3>
                <input
                  type="date"
                  value={actionStart}
                  onChange={(e) => setActionStart(e.target.value)}
                  style={{ width: '100%', padding: '10px', fontSize: '0.9rem', border: '1px solid #ddd', borderRadius: '6px', marginBottom: '8px' }}
                />
                <input
                  type="date"
                  value={actionEnd}
                  onChange={(e) => setActionEnd(e.target.value)}
                  style={{ width: '100%', padding: '10px', fontSize: '0.9rem', border: '1px solid #ddd', borderRadius: '6px', marginBottom: '8px' }}
                />
                <input
                  type="date"
                  value={actionAsOf}
                  onChange={(e) => setActionAsOf(e.target.value)}
                  style={{ width: '100%', padding: '10px', fontSize: '0.9rem', border: '1px solid #ddd', borderRadius: '6px', marginBottom: '10px' }}
                />
                <button
                  onClick={async () => {
                    if (!actionStart || !actionEnd) {
                      alert('시작일/종료일을 입력하세요');
                      return;
                    }
                    setLoading(true);
                    setError(null);
                    try {
                      const response = await api.loadDartCorporateActions({
                        start_date: actionStart,
                        end_date: actionEnd,
                        as_of_date: actionAsOf,
                      });
                      alert('✅ ' + response.data.message);
                    } catch (err) {
                      alert('❌ ' + (err.response?.data?.detail || '기업 액션 적재 실패'));
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading}
                  className="btn btn-primary"
                  style={{ width: '100%', padding: '10px', fontSize: '0.95rem' }}
                >
                  기업 액션 적재
                </button>
              </div>

              <div style={{ padding: '15px', border: '1px solid #e5e7eb', borderRadius: '8px', background: '#ffffff' }}>
                <h3 style={{ marginBottom: '10px', fontSize: '1rem' }}>채권 기본정보 (금융위원회 OpenAPI)</h3>
                <label style={{ fontSize: '0.82rem', color: '#555' }}>등급 필터</label>
                <select
                  value={bondQualityFilter}
                  onChange={(e) => setBondQualityFilter(e.target.value)}
                  style={{ width: '100%', padding: '8px', fontSize: '0.9rem', border: '1px solid #ddd', borderRadius: '6px', marginBottom: '10px', boxSizing: 'border-box' }}
                >
                  <option value="all">전체 채권</option>
                  <option value="investment_grade">투자적격등급 (AAA~BBB)</option>
                  <option value="high_quality">최우량 (AAA~A)</option>
                </select>
                <button
                  onClick={handleLoadBonds}
                  disabled={loading}
                  className="btn btn-primary"
                  style={{ width: '100%', padding: '15px', fontSize: '1rem', fontWeight: 'bold' }}
                >
                  📊 채권 데이터 조회
                </button>
                <div style={{ marginTop: '8px', fontSize: '0.8rem', color: '#666' }}>
                  💡 오늘 기준일로 선택한 등급의 채권을 조회합니다
                </div>
              </div>

              {/* DART 재무제표 카드 */}
              <div style={{ background: '#fff', borderRadius: '8px', padding: '20px', border: '1px solid #e0e0e0' }}>
                <h3 style={{ marginBottom: '10px', fontSize: '1rem' }}>재무제표 + PER/PBR (DART)</h3>
                <p style={{ fontSize: '0.82rem', color: '#666', margin: '0 0 12px' }}>
                  DART 사업보고서에서 당기순이익·자기자본을 수집하고,
                  시가총액 기준 PER/PBR을 계산하여 stocks에 저장합니다. (백그라운드 실행)
                </p>

                <label style={{ fontSize: '0.82rem', color: '#555' }}>회계연도</label>
                <input
                  type="number"
                  value={dartFiscalYear}
                  onChange={(e) => setDartFiscalYear(Number(e.target.value))}
                  style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #ccc', marginBottom: '8px', boxSizing: 'border-box' }}
                />

                <label style={{ fontSize: '0.82rem', color: '#555' }}>보고서 종류</label>
                <select
                  value={dartReportType}
                  onChange={(e) => setDartReportType(e.target.value)}
                  style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #ccc', marginBottom: '8px', boxSizing: 'border-box' }}
                >
                  <option value="ANNUAL">ANNUAL (사업보고서)</option>
                  <option value="Q3">Q3 (3분기보고서)</option>
                  <option value="Q2">Q2 (반기보고서)</option>
                  <option value="Q1">Q1 (1분기보고서)</option>
                </select>

                <label style={{ fontSize: '0.82rem', color: '#555' }}>종목 수 제한 (테스트용)</label>
                <input
                  type="number"
                  value={dartFinLimit}
                  onChange={(e) => setDartFinLimit(e.target.value)}
                  placeholder="빈 칸이면 전체"
                  min={1}
                  max={5000}
                  style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #ccc', marginBottom: '12px', boxSizing: 'border-box' }}
                />

                <button
                  onClick={async () => {
                    if (!window.confirm(`FY${dartFiscalYear} ${dartReportType} 재무제표를 수집할지 확인합니다.`)) return;
                    setLoading(true);
                    try {
                      const params = { fiscal_year: dartFiscalYear, report_type: dartReportType };
                      if (dartFinLimit) params.limit = Number(dartFinLimit);
                      const res = await api.loadDartFinancials(params);
                      setCurrentTaskId(res.data.task_id);
                      alert('✅ DART 재무제표 수집 시작됨\ntask_id: ' + res.data.task_id + '\n진행 상황은 아래 ProgressModal에서 확인 가능합니다.');
                      await fetchDataStatus();
                    } catch (err) {
                      alert('❌ ' + (err.response?.data?.detail || 'DART 재무제표 적재 실패'));
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading}
                  className="btn btn-primary"
                  style={{ width: '100%', padding: '10px', fontSize: '0.95rem' }}
                >
                  재무제표 적재 (DART)
                </button>
                <div style={{ marginTop: '8px', fontSize: '0.8rem', color: '#666' }}>
                  💡 종목당 ~1초 소요 (DART rate limit). 전체 종목은 백그라운드로 실행됩니다.
                </div>
              </div>

            </div>
          </div>

          {/* 금융감독원 금융상품 한 눈에 Section */}
          <div className="description-section" style={{ marginTop: '40px', borderTop: '2px solid #e0e0e0', paddingTop: '30px' }}>
            <h2>🏛️ 금융감독원 - 금융상품 한 눈에</h2>
            <div style={{ marginTop: '15px', padding: '15px', background: '#f3e5f5', borderRadius: '8px', borderLeft: '4px solid #9C27B0' }}>
              <p style={{ margin: 0, color: '#333', fontSize: '0.9rem' }}>
                🔑 금융감독원 금융상품통합비교공시 API를 통해 예금·적금·연금·대출 상품을 수집합니다.<br />
                📋 FSS API Key가 필요합니다. (finlife.fss.or.kr)
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '15px', marginTop: '20px' }}>
              {/* FSS 정기예금 카드 */}
              <div style={{ padding: '15px', border: '1px solid #e5e7eb', borderRadius: '8px', background: '#ffffff' }}>
                <h3 style={{ marginBottom: '10px', fontSize: '1rem' }}>🏦 정기예금 상품</h3>
                <p style={{ fontSize: '0.82rem', color: '#666', margin: '0 0 12px' }}>
                  은행 정기예금 상품 및 기간별 금리 옵션을 수집합니다.
                </p>
                <button
                  onClick={async () => {
                    if (!window.confirm('FSS 정기예금 상품을 조회하시겠습니까?')) return;
                    setLoading(true);
                    setError(null);
                    const tempTaskId = `temp_deposits_${Date.now()}`;
                    setCurrentTaskId(tempTaskId);
                    try {
                      const res = await api.loadDeposits();
                      if (res.data.task_id) setCurrentTaskId(res.data.task_id);
                      await fetchDataStatus();
                    } catch (err) {
                      alert('❌ ' + (err.response?.data?.detail || '정기예금 적재 실패'));
                      setCurrentTaskId(null);
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading}
                  className="btn btn-primary"
                  style={{ width: '100%', padding: '10px', fontSize: '0.95rem' }}
                >
                  정기예금 조회
                </button>
              </div>

              {/* FSS 적금 카드 */}
              <div style={{ padding: '15px', border: '1px solid #e5e7eb', borderRadius: '8px', background: '#ffffff' }}>
                <h3 style={{ marginBottom: '10px', fontSize: '1rem' }}>🏦 적금 상품</h3>
                <p style={{ fontSize: '0.82rem', color: '#666', margin: '0 0 12px' }}>
                  은행 적금 상품 및 기간별 금리 옵션을 수집합니다.
                </p>
                <button
                  onClick={async () => {
                    if (!window.confirm('FSS 적금 상품을 조회하시겠습니까?')) return;
                    setLoading(true);
                    setError(null);
                    const tempTaskId = `temp_savings_${Date.now()}`;
                    setCurrentTaskId(tempTaskId);
                    try {
                      const res = await api.loadSavings();
                      if (res.data.task_id) setCurrentTaskId(res.data.task_id);
                      await fetchDataStatus();
                    } catch (err) {
                      alert('❌ ' + (err.response?.data?.detail || '적금 적재 실패'));
                      setCurrentTaskId(null);
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading}
                  className="btn btn-primary"
                  style={{ width: '100%', padding: '10px', fontSize: '0.95rem' }}
                >
                  적금 조회
                </button>
              </div>

              {/* FSS 연금저축 카드 */}
              <div style={{ padding: '15px', border: '1px solid #e5e7eb', borderRadius: '8px', background: '#ffffff' }}>
                <h3 style={{ marginBottom: '10px', fontSize: '1rem' }}>🏛️ 연금저축 상품</h3>
                <p style={{ fontSize: '0.82rem', color: '#666', margin: '0 0 12px' }}>
                  연금저축 상품 및 수익률 정보를 수집합니다.
                </p>
                <button
                  onClick={async () => {
                    if (!window.confirm('FSS 연금저축 상품을 조회하시겠습니까?')) return;
                    setLoading(true);
                    setError(null);
                    const tempTaskId = `temp_annuity_${Date.now()}`;
                    setCurrentTaskId(tempTaskId);
                    try {
                      const res = await api.loadAnnuitySavings();
                      if (res.data.task_id) setCurrentTaskId(res.data.task_id);
                      await fetchDataStatus();
                    } catch (err) {
                      alert('❌ ' + (err.response?.data?.detail || '연금저축 적재 실패'));
                      setCurrentTaskId(null);
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading}
                  className="btn btn-primary"
                  style={{ width: '100%', padding: '10px', fontSize: '0.95rem' }}
                >
                  연금저축 조회
                </button>
              </div>

              {/* FSS 주택담보대출 카드 */}
              <div style={{ padding: '15px', border: '1px solid #e5e7eb', borderRadius: '8px', background: '#ffffff' }}>
                <h3 style={{ marginBottom: '10px', fontSize: '1rem' }}>🏠 주택담보대출 상품</h3>
                <p style={{ fontSize: '0.82rem', color: '#666', margin: '0 0 12px' }}>
                  은행 주택담보대출 상품 및 금리 옵션을 수집합니다.
                </p>
                <button
                  onClick={async () => {
                    if (!window.confirm('FSS 주택담보대출 상품을 조회하시겠습니까?')) return;
                    setLoading(true);
                    setError(null);
                    const tempTaskId = `temp_mortgage_${Date.now()}`;
                    setCurrentTaskId(tempTaskId);
                    try {
                      const res = await api.loadMortgageLoans();
                      if (res.data.task_id) setCurrentTaskId(res.data.task_id);
                      await fetchDataStatus();
                    } catch (err) {
                      alert('❌ ' + (err.response?.data?.detail || '주택담보대출 적재 실패'));
                      setCurrentTaskId(null);
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading}
                  className="btn btn-primary"
                  style={{ width: '100%', padding: '10px', fontSize: '0.95rem' }}
                >
                  주택담보대출 조회
                </button>
              </div>

              {/* FSS 전세자금대출 카드 */}
              <div style={{ padding: '15px', border: '1px solid #e5e7eb', borderRadius: '8px', background: '#ffffff' }}>
                <h3 style={{ marginBottom: '10px', fontSize: '1rem' }}>🏠 전세자금대출 상품</h3>
                <p style={{ fontSize: '0.82rem', color: '#666', margin: '0 0 12px' }}>
                  은행 전세자금대출 상품 및 금리 옵션을 수집합니다.
                </p>
                <button
                  onClick={async () => {
                    if (!window.confirm('FSS 전세자금대출 상품을 조회하시겠습니까?')) return;
                    setLoading(true);
                    setError(null);
                    const tempTaskId = `temp_rentloan_${Date.now()}`;
                    setCurrentTaskId(tempTaskId);
                    try {
                      const res = await api.loadRentHouseLoans();
                      if (res.data.task_id) setCurrentTaskId(res.data.task_id);
                      await fetchDataStatus();
                    } catch (err) {
                      alert('❌ ' + (err.response?.data?.detail || '전세자금대출 적재 실패'));
                      setCurrentTaskId(null);
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading}
                  className="btn btn-primary"
                  style={{ width: '100%', padding: '10px', fontSize: '0.95rem' }}
                >
                  전세자금대출 조회
                </button>
              </div>

              {/* FSS 개인신용대출 카드 */}
              <div style={{ padding: '15px', border: '1px solid #e5e7eb', borderRadius: '8px', background: '#ffffff' }}>
                <h3 style={{ marginBottom: '10px', fontSize: '1rem' }}>💳 개인신용대출 상품</h3>
                <p style={{ fontSize: '0.82rem', color: '#666', margin: '0 0 12px' }}>
                  은행·저축은행·여신전문 개인신용대출 상품 및 신용등급별 금리를 수집합니다.
                </p>
                <button
                  onClick={async () => {
                    if (!window.confirm('FSS 개인신용대출 상품을 조회하시겠습니까?')) return;
                    setLoading(true);
                    setError(null);
                    const tempTaskId = `temp_creditloan_${Date.now()}`;
                    setCurrentTaskId(tempTaskId);
                    try {
                      const res = await api.loadCreditLoans();
                      if (res.data.task_id) setCurrentTaskId(res.data.task_id);
                      await fetchDataStatus();
                    } catch (err) {
                      alert('❌ ' + (err.response?.data?.detail || '개인신용대출 적재 실패'));
                      setCurrentTaskId(null);
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading}
                  className="btn btn-primary"
                  style={{ width: '100%', padding: '10px', fontSize: '0.95rem' }}
                >
                  개인신용대출 조회
                </button>
              </div>
            </div>
          </div>

          <div className="description-section" style={{ marginTop: '40px', borderTop: '2px solid #e0e0e0', paddingTop: '30px' }}>
            <h2>📘 FinanceDataReader 종목 마스터</h2>
            <div style={{ marginTop: '15px', padding: '15px', background: '#f1f5f9', borderRadius: '8px', borderLeft: '4px solid #64748b' }}>
              <p style={{ margin: 0, color: '#333', fontSize: '0.9rem' }}>
                📌 종목 마스터를 적재합니다. 주식 데이터 수집의 사전 단계(Stage 1)입니다. Marcap·발행주식수 포함.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '15px', marginTop: '20px' }}>
              <div style={{ padding: '15px', border: '1px solid #e5e7eb', borderRadius: '8px', background: '#ffffff' }}>
                <h3 style={{ marginBottom: '10px', fontSize: '1rem' }}>FDR 종목 마스터 적재</h3>
                <select
                  value={fdrMarket}
                  onChange={(e) => setFdrMarket(e.target.value)}
                  style={{ width: '100%', padding: '10px', fontSize: '0.9rem', border: '1px solid #ddd', borderRadius: '6px', marginBottom: '8px' }}
                >
                  <option value="KRX">KRX</option>
                  <option value="KOSPI">KOSPI</option>
                  <option value="KOSDAQ">KOSDAQ</option>
                  <option value="KONEX">KONEX</option>
                </select>
                <input
                  type="date"
                  value={fdrAsOf}
                  onChange={(e) => setFdrAsOf(e.target.value)}
                  style={{ width: '100%', padding: '10px', fontSize: '0.9rem', border: '1px solid #ddd', borderRadius: '6px', marginBottom: '10px' }}
                />
                <button
                  onClick={async () => {
                    setLoading(true);
                    setError(null);
                    try {
                      const response = await api.loadFdrStockListing({
                        market: fdrMarket,
                        as_of_date: fdrAsOf,
                      });
                      alert('✅ ' + response.data.message);
                    } catch (err) {
                      alert('❌ ' + (err.response?.data?.detail || 'FDR 종목 마스터 적재 실패'));
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading}
                  className="btn btn-secondary"
                  style={{ width: '100%', padding: '10px', fontSize: '0.95rem' }}
                >
                  FDR 종목 마스터 적재
                </button>
              </div>
            </div>
          </div>

          {/* Data View Section */}
          {dataStatus && dataStatus.total > 0 && (
            <div className="description-section" style={{ marginTop: '40px', borderTop: '2px solid #e0e0e0', paddingTop: '30px' }}>
              <h2>📋 적재된 데이터 조회</h2>

              <div style={{ display: 'flex', gap: '10px', marginTop: '20px', flexWrap: 'wrap' }}>
                {dataStatus.stocks > 0 && (
                  <button
                    onClick={() => setActiveTab('stocks')}
                    className={activeTab === 'stocks' ? 'btn btn-primary' : 'btn btn-secondary'}
                    style={{ flex: '1', minWidth: '150px' }}
                  >
                    📈 주식 ({dataStatus.stocks})
                  </button>
                )}
                {dataStatus.etfs > 0 && (
                  <button
                    onClick={() => setActiveTab('etfs')}
                    className={activeTab === 'etfs' ? 'btn btn-primary' : 'btn btn-secondary'}
                    style={{ flex: '1', minWidth: '150px' }}
                  >
                    📊 ETF ({dataStatus.etfs})
                  </button>
                )}
                {dataStatus.bonds > 0 && (
                  <button
                    onClick={() => setActiveTab('bonds')}
                    className={activeTab === 'bonds' ? 'btn btn-primary' : 'btn btn-secondary'}
                    style={{ flex: '1', minWidth: '150px' }}
                  >
                    💰 채권 ({dataStatus.bonds})
                  </button>
                )}
                {dataStatus.deposits > 0 && (
                  <button
                    onClick={() => setActiveTab('deposits')}
                    className={activeTab === 'deposits' ? 'btn btn-primary' : 'btn btn-secondary'}
                    style={{ flex: '1', minWidth: '150px' }}
                  >
                    🏦 예적금 ({dataStatus.deposits})
                  </button>
                )}
              </div>

              <div style={{ marginTop: '20px' }}>
                {activeTab === 'stocks' && dataStatus.stocks > 0 && (
                  <DataTable type="stocks" fetchData={() => api.getStocks(0, 100)} />
                )}
                {activeTab === 'etfs' && dataStatus.etfs > 0 && (
                  <DataTable type="etfs" fetchData={() => api.getETFs(0, 100)} />
                )}
                {activeTab === 'bonds' && dataStatus.bonds > 0 && (
                  <DataTable type="bonds" fetchData={() => api.getBonds(0, 100)} />
                )}
                {activeTab === 'deposits' && dataStatus.deposits > 0 && (
                  <DataTable type="deposits" fetchData={() => api.getDeposits(0, 100)} />
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
