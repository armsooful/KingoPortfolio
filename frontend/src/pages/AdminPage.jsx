// frontend/src/pages/AdminPage.jsx

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../services/api';
import ProgressBar from '../components/ProgressBar';
import DataTable from '../components/DataTable';

export default function AdminPage() {
  const [loading, setLoading] = useState(false);
  const [dataStatus, setDataStatus] = useState(null);
  const [loadResult, setLoadResult] = useState(null);
  const [error, setError] = useState(null);
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [activeTab, setActiveTab] = useState('stocks');
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
    setCurrentTaskId(null);

    try {
      let response;
      if (type === 'all') response = await api.loadAllData();
      else if (type === 'stocks') response = await api.loadStocks();
      else response = await api.loadETFs();

      setLoadResult(response.data);

      // task_id가 있으면 진행 상황 추적 시작
      if (response.data.task_id) {
        setCurrentTaskId(response.data.task_id);
      }

      await fetchDataStatus();
    } catch (err) {
      setError(err.response?.data?.detail || '데이터 수집 실패');
    } finally {
      setLoading(false);
    }
  };

  const handleProgressComplete = async (progressData) => {
    // 진행 완료 후 데이터 현황 새로고침
    await fetchDataStatus();
    setCurrentTaskId(null);
  };

  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card" style={{ maxWidth: '1200px' }}>
          {/* Header */}
          <div className="result-header">
            <div className="result-icon" style={{ fontSize: '3rem' }}>
              🔧
            </div>
            <h1 className="result-type" style={{ color: '#667eea' }}>
              관리자 콘솔
            </h1>
            <p className="result-subtitle">종목 정보 수집 및 데이터 관리 시스템</p>
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

          {/* Data Collection Section */}
          <div className="description-section">
            <h2>🔄 데이터 수집</h2>
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
            <div className="info-box" style={{ marginTop: '15px', padding: '15px', background: '#f0f7ff', borderRadius: '8px', borderLeft: '4px solid #2196F3' }}>
              <p style={{ margin: 0, color: '#333' }}>
                💡 yfinance API로 실시간 종목 정보를 수집합니다. 전체 데이터 수집은 약 1-2분이 소요됩니다.
              </p>
            </div>
          </div>

          {/* Progress Section */}
          {currentTaskId && (
            <div className="description-section">
              <h2>⏳ 데이터 수집 진행 상황</h2>
              <ProgressBar taskId={currentTaskId} onComplete={handleProgressComplete} />
            </div>
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

          {/* Data View Section - 탭 형태 */}
          {dataStatus && dataStatus.total > 0 && (
            <div className="description-section">
              <h2>📋 적재된 데이터 조회</h2>

              {/* 탭 버튼 */}
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

              {/* 탭 컨텐츠 */}
              <div style={{ marginTop: '20px' }}>
                {activeTab === 'stocks' && dataStatus.stocks > 0 && (
                  <DataTable
                    type="stocks"
                    fetchData={() => api.getStocks(0, 100)}
                  />
                )}
                {activeTab === 'etfs' && dataStatus.etfs > 0 && (
                  <DataTable
                    type="etfs"
                    fetchData={() => api.getETFs(0, 100)}
                  />
                )}
                {activeTab === 'bonds' && dataStatus.bonds > 0 && (
                  <DataTable
                    type="bonds"
                    fetchData={() => api.getBonds(0, 100)}
                  />
                )}
                {activeTab === 'deposits' && dataStatus.deposits > 0 && (
                  <DataTable
                    type="deposits"
                    fetchData={() => api.getDeposits(0, 100)}
                  />
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
