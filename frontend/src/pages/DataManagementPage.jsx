// frontend/src/pages/DataManagementPage.jsx

import { useState, useEffect } from 'react';
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
    const typeNames = { all: '모든', stocks: '주식', etfs: 'ETF' };
    if (!window.confirm(`${typeNames[type]} 데이터를 수집하시겠습니까? (1-2분 소요)`)) {
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
      if (type === 'all') response = await api.loadAllData();
      else if (type === 'stocks') response = await api.loadStocks();
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

  const handleProgressComplete = async (progressData) => {
    await fetchDataStatus();
  };

  const handleCloseModal = () => {
    setCurrentTaskId(null);
  };

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
                  <div className="score-label">🏦 예적금</div>
                  <div className="score-value" style={{ color: '#FF9800' }}>
                    {dataStatus.deposits}개
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* yfinance Data Collection Section */}
          <div className="description-section">
            <h2>🔄 yfinance 데이터 수집</h2>
            <div className="info-box" style={{ marginTop: '15px', padding: '15px', background: '#f0f7ff', borderRadius: '8px', borderLeft: '4px solid #2196F3' }}>
              <p style={{ margin: 0, color: '#333' }}>
                💡 yfinance API로 실시간 종목 정보를 수집합니다. 전체 데이터 수집은 약 1-2분이 소요됩니다.
              </p>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginTop: '20px' }}>
              <button
                onClick={() => handleLoadData('all')}
                disabled={loading}
                className="btn btn-primary"
                style={{ padding: '20px', fontSize: '1rem', fontWeight: 'bold' }}
              >
                {loading ? '🔄 수집 중...' : '📦 전체 데이터'}
              </button>
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

          {/* pykrx Section */}
          <div className="description-section" style={{ marginTop: '40px', borderTop: '2px solid #e0e0e0', paddingTop: '30px' }}>
            <h2>🇰🇷 pykrx - 한국 주식 데이터</h2>
            <div className="info-box" style={{ marginTop: '15px', padding: '15px', background: '#e8f5e9', borderRadius: '8px', borderLeft: '4px solid #4CAF50' }}>
              <p style={{ margin: 0, color: '#333', fontSize: '0.9rem' }}>
                📊 pykrx 라이브러리를 통해 한국 증권시장 실시간 데이터를 수집합니다.<br />
                ✅ KRX (한국거래소) 공식 데이터 - API 제한 없음
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '15px', marginTop: '20px' }}>
              <button
                onClick={async () => {
                  if (!window.confirm('인기 한국 주식 전체를 수집하시겠습니까? (약 1-2분 소요)')) return;

                  setLoading(true);
                  setError(null);

                  try {
                    const response = await api.loadAllPykrxStocks();

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
                disabled={loading}
                className="btn btn-primary"
                style={{ padding: '20px', fontSize: '1rem', fontWeight: 'bold' }}
              >
                {loading ? '🔄 수집 중...' : '🇰🇷 한국 주식 전체 수집'}
              </button>

              <button
                onClick={async () => {
                  if (!window.confirm('인기 한국 ETF 전체를 수집하시겠습니까?')) return;

                  setLoading(true);
                  setError(null);

                  try {
                    const response = await api.loadAllPykrxETFs();

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
                disabled={loading}
                className="btn btn-primary"
                style={{ padding: '20px', fontSize: '1rem', fontWeight: 'bold' }}
              >
                {loading ? '🔄 수집 중...' : '📊 한국 ETF 전체 수집'}
              </button>
            </div>

            <div style={{ marginTop: '20px', padding: '20px', background: '#f5f5f5', borderRadius: '8px' }}>
              <h3 style={{ marginBottom: '15px', fontSize: '1.1rem' }}>🔍 특정 종목 검색 & 적재</h3>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <input
                  type="text"
                  placeholder="종목 코드 입력 (예: 005930, 035420)"
                  value={symbolInput}
                  onChange={(e) => setSymbolInput(e.target.value.replace(/[^0-9]/g, ''))}
                  maxLength={6}
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
                    const ticker = symbolInput.trim();
                    if (!ticker) {
                      alert('종목 코드를 입력하세요');
                      return;
                    }
                    if (ticker.length !== 6) {
                      alert('6자리 종목 코드를 입력하세요');
                      return;
                    }

                    setLoading(true);
                    setError(null);

                    try {
                      const response = await api.loadPykrxStock(ticker);

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
                  disabled={loading}
                  className="btn btn-primary"
                  style={{ padding: '12px 24px' }}
                >
                  📈 주식 수집
                </button>
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

                    setLoading(true);
                    setError(null);

                    try {
                      const response = await api.loadPykrxETF(ticker);

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
                  disabled={loading}
                  className="btn btn-secondary"
                  style={{ padding: '12px 24px' }}
                >
                  📊 ETF 수집
                </button>
              </div>
              <div style={{ marginTop: '10px', fontSize: '0.85rem', color: '#666' }}>
                💡 인기 종목: 삼성전자(005930), NAVER(035420), 카카오(035720), SK하이닉스(000660) 등<br />
                💡 인기 ETF: KODEX 200(069500), KODEX 레버리지(122630), KODEX 인버스(114800) 등
              </div>
            </div>

            <div style={{ marginTop: '20px', padding: '20px', background: '#fff3e0', borderRadius: '8px', border: '1px solid #ffb74d' }}>
              <h3 style={{ marginBottom: '15px', fontSize: '1.1rem' }}>📊 재무 지표 데이터 수집</h3>
              <div style={{ marginBottom: '10px', fontSize: '0.85rem', color: '#666', background: '#fff', padding: '10px', borderRadius: '5px' }}>
                ⚠️ pykrx는 상세 재무제표를 제공하지 않습니다. PER, PBR, EPS, BPS 지표를 기반으로 재무 정보를 추정합니다.
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '10px' }}>
                <button
                  onClick={async () => {
                    if (!window.confirm('인기 한국 주식 전체 재무 지표를 수집하시겠습니까? (약 1-2분 소요)')) return;

                    setLoading(true);
                    setError(null);

                    try {
                      const response = await api.loadAllPykrxFinancials();

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
                  disabled={loading}
                  className="btn btn-success"
                  style={{ padding: '15px', fontSize: '0.95rem', fontWeight: 'bold' }}
                >
                  {loading ? '🔄 수집 중...' : '📈 재무 지표 전체 수집'}
                </button>

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

                    setLoading(true);
                    setError(null);

                    try {
                      const response = await api.loadPykrxFinancials(ticker);

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
                  disabled={loading}
                  className="btn btn-success"
                  style={{ padding: '15px', fontSize: '0.95rem' }}
                >
                  📊 개별종목 재무 지표 수집
                </button>
              </div>
              <div style={{ marginTop: '10px', fontSize: '0.85rem', color: '#666' }}>
                💡 최근 거래일 기준 PER, PBR, EPS, BPS, 배당수익률 등을 수집하여 ROE, ROA, 부채비율 등을 추정합니다.
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
