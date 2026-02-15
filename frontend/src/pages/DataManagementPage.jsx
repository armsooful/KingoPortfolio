// frontend/src/pages/DataManagementPage.jsx

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../services/api';
import ProgressModal from '../components/ProgressModal';
import DataTable from '../components/DataTable';
import '../styles/DataManagement.css';

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
  const [actionYear, setActionYear] = useState(new Date().getFullYear());
  const [actionQuarter, setActionQuarter] = useState('Q1');
  const [dartFiscalYear, setDartFiscalYear] = useState(2024);
  const [dartReportType, setDartReportType] = useState('ANNUAL');
  const [dartFinLimit, setDartFinLimit] = useState('');
  const [fdrMarket, setFdrMarket] = useState('KRX');
  const [fdrAsOf, setFdrAsOf] = useState(new Date().toISOString().split('T')[0]);
  const [bondQualityFilter, setBondQualityFilter] = useState('all');
  // Phase 3: 수집 스케줄 탭 상태
  const [scheduleView, setScheduleView] = useState('status'); // 'status' | 'logs'
  const [schedulerStatus, setSchedulerStatus] = useState(null);
  const [collectionLogs, setCollectionLogs] = useState([]);
  const [collectionSummary, setCollectionSummary] = useState(null);
  const [logJobFilter, setLogJobFilter] = useState('');
  const [logDetailModal, setLogDetailModal] = useState(null);
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

  const fetchSchedulerData = useCallback(async () => {
    try {
      const [statusRes, summaryRes, logsRes] = await Promise.all([
        api.getSchedulerStatus(),
        api.getCollectionSummary(),
        api.getCollectionLogs({ limit: 50, job_name: logJobFilter || undefined }),
      ]);
      setSchedulerStatus(statusRes.data.data);
      setCollectionSummary(summaryRes.data.data);
      setCollectionLogs(logsRes.data.data.items || []);
    } catch (err) {
      console.error('Failed to fetch scheduler data:', err);
    }
  }, [logJobFilter]);

  useEffect(() => {
    if (activeTab === 'schedule') {
      fetchSchedulerData();
    }
  }, [activeTab, fetchSchedulerData]);

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

  const stepBadge = (num, color) => (
    <span className="dm-step-badge" style={{ background: color }}>Step {num}</span>
  );

  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card" style={{ maxWidth: '1200px' }}>
          <button className="admin-back-btn" onClick={() => navigate('/admin')}>
            ← 관리자 홈
          </button>
          {/* Header */}
          <div className="result-header">
            <div className="result-icon" style={{ fontSize: '3rem' }}>
              ⚙️
            </div>
            <h1 className="result-type">
              데이터 관리
            </h1>
            <p className="result-subtitle">데이터 수집 파이프라인 및 현황 관리</p>
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
            </div>
          )}

          {/* Success Message */}
          {loadResult && (
            <div className="ai-card dm-success-card">
              <h3>{loadResult.message}</h3>
              {loadResult.results && (
                <div className="dm-success-results">
                  {Object.entries(loadResult.results).map(([key, val]) => (
                    <div key={key} className="dm-success-row">
                      <span className="dm-success-row-key">{key}</span>
                      <div className="dm-success-row-vals">
                        <span style={{ color: 'var(--stock-up)' }}>+ {val.success}</span>
                        <span style={{ color: '#2196F3' }}>~ {val.updated}</span>
                        <span style={{ color: 'var(--stock-down)' }}>x {val.failed || 0}</span>
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
              <h3>오류 발생</h3>
              <p className="ai-content">{error}</p>
            </div>
          )}

          {/* ─── Data Status Cards ─── */}
          {dataStatus && (
            <div className="description-section">
              <h2>현재 데이터 현황</h2>
              <div className="dm-status-grid">
                {[
                  { label: '주식', count: dataStatus.stocks, color: '#2196F3' },
                  { label: 'ETF', count: dataStatus.etfs, color: '#9C27B0' },
                  { label: '채권', count: dataStatus.bonds, color: '#4CAF50' },
                  { label: '예금', count: dataStatus.deposits, color: '#FF9800' },
                  { label: '적금', count: dataStatus.savings || 0, color: '#E91E63' },
                  { label: '연금저축', count: dataStatus.annuity_savings || 0, color: '#673AB7' },
                  { label: '주담대', count: dataStatus.mortgage_loans || 0, color: '#795548' },
                  { label: '전세대출', count: dataStatus.rent_house_loans || 0, color: '#607D8B' },
                  { label: '신용대출', count: dataStatus.credit_loans || 0, color: '#E91E63' },
                ].map(({ label, count, color }) => (
                  <div key={label} className="score-card">
                    <div className="score-label">{label}</div>
                    <div className="score-value" style={{ color }}>{count}건</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ─── Step 1: FDR 종목 마스터 ─── */}
          <div className="description-section dm-section">
            <h2>{stepBadge(1, '#64748b')} FDR 종목 마스터</h2>
            <p className="dm-section-subtitle">
              종목 마스터 적재 (Stage 1). Marcap/발행주식수 포함. 이후 모든 수집의 기초 데이터입니다.
            </p>
            <div className="dm-grid">
              <div className="dm-card">
                <label className="dm-label">시장</label>
                <select
                  value={fdrMarket}
                  onChange={(e) => setFdrMarket(e.target.value)}
                  className="dm-input dm-input-mb"
                >
                  <option value="KRX">KRX 전체</option>
                  <option value="KOSPI">KOSPI</option>
                  <option value="KOSDAQ">KOSDAQ</option>
                  <option value="KONEX">KONEX</option>
                </select>
                <label className="dm-label">기준일</label>
                <input
                  type="date"
                  value={fdrAsOf}
                  onChange={(e) => setFdrAsOf(e.target.value)}
                  className="dm-input dm-input-mb-lg"
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
                      alert(response.data.message);
                    } catch (err) {
                      alert(err.response?.data?.detail || 'FDR 종목 마스터 적재 실패');
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading}
                  className="btn btn-secondary dm-btn-full"
                >
                  FDR 종목 마스터 적재
                </button>
              </div>
            </div>
          </div>

          {/* ─── Step 2: 주식/ETF 수집 (yfinance) ─── */}
          <div className="description-section dm-section">
            <h2>{stepBadge(2, '#2196F3')} 주식 / ETF 수집</h2>
            <p className="dm-section-subtitle">
              FDR 종목 마스터 기반으로 yfinance에서 시가총액, 섹터, 상장일 등을 수집합니다.
            </p>
            <div className="dm-grid-2col">
              <button
                onClick={() => handleLoadData('stocks')}
                disabled={loading}
                className="btn btn-primary dm-btn-action"
              >
                주식 데이터 수집
              </button>
              <button
                onClick={() => handleLoadData('etfs')}
                disabled={loading}
                className="btn btn-primary dm-btn-action"
              >
                ETF 데이터 수집
              </button>
            </div>
          </div>

          {/* ─── Step 3: pykrx 시계열 ─── */}
          <div className="description-section dm-section">
            <h2>{stepBadge(3, '#1565c0')} pykrx 시계열 데이터</h2>
            <p className="dm-section-subtitle">
              KRX 공식 데이터로 과거 가격(OHLCV)을 수집합니다. API 제한 없음.
            </p>

            {/* 단일 종목 */}
            <div className="dm-panel">
              <h3>단일 종목 시계열</h3>
              <div className="dm-grid-2col-sm">
                <div>
                  <label className="dm-label">종목 코드 (6자리)</label>
                  <input
                    type="text"
                    placeholder="005930"
                    maxLength={6}
                    value={symbolInput}
                    onChange={(e) => setSymbolInput(e.target.value.replace(/[^0-9]/g, ''))}
                    className="dm-input"
                  />
                </div>
                <div>
                  <label className="dm-label">수집 기간</label>
                  <select id="krx-timeseries-days" className="dm-input">
                    <option value="90">3개월</option>
                    <option value="180">6개월</option>
                    <option value="365">1년</option>
                    <option value="730">2년</option>
                    <option value="1825">5년</option>
                    <option value="3650">10년</option>
                  </select>
                </div>
              </div>
              <button
                onClick={async () => {
                  const ticker = symbolInput.trim();
                  if (!ticker || ticker.length !== 6) {
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
                    alert(`${ticker} 시계열 ${data.records_added}건 수집 완료`);
                    await fetchDataStatus();
                  } catch (err) {
                    alert(err.message);
                  } finally {
                    setLoading(false);
                  }
                }}
                disabled={loading}
                className="btn btn-primary dm-btn-full-bold"
              >
                시계열 데이터 수집
              </button>
              <p className="dm-hint">
                예: 005930 (삼성전자), 000660 (SK하이닉스), 035420 (NAVER)
              </p>
            </div>

            {/* 전체 종목 증분 적재 */}
            <div className="dm-panel-green">
              <h3>전체 종목 5년치 증분 적재</h3>
              <p className="dm-panel-green-desc">
                stocks 테이블 기준 전 종목 대상. 기존 종목은 마지막 적재일 이후만 수집합니다.
              </p>
              <div className="dm-grid-2col-sm">
                <div>
                  <label className="dm-label">시장</label>
                  <select id="incremental-market" className="dm-input">
                    <option value="">KRX 전체</option>
                    <option value="KOSPI">KOSPI</option>
                    <option value="KOSDAQ">KOSDAQ</option>
                  </select>
                </div>
                <div>
                  <label className="dm-label">스레드 수</label>
                  <select id="incremental-workers" className="dm-input">
                    <option value="2">2 (저부하)</option>
                    <option value="4">4 (권장)</option>
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
                    `[${marketLabel}] 전 종목 5년치 증분 적재를 시작하시겠습니까?\n\n` +
                    `- 신규: 5년치 수집 / 기존: 증분만 수집\n` +
                    `- 스레드: ${numWorkers}개\n` +
                    `- 첫 실행 시 4-6시간 소요될 수 있습니다.`
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
                      `증분 적재 시작\n` +
                      `대상: ${stats.total_stocks || '?'}종목\n` +
                      `task_id: ${res.data.task_id}`
                    );
                    await fetchDataStatus();
                  } catch (err) {
                    alert(err.response?.data?.detail || '증분 적재 시작 실패');
                    setCurrentTaskId(null);
                  } finally {
                    setLoading(false);
                  }
                }}
                disabled={loading}
                className="btn btn-success dm-btn-incremental"
              >
                {loading ? '시작 중...' : '전체 종목 5년치 증분 적재'}
              </button>
              <p className="dm-hint-dark">
                첫 실행: 약 4-6시간 (야간 권장) / 재실행: 약 10-30분 (증분만)
              </p>
            </div>
          </div>

          {/* ─── Step 4: 재무/배당/기업액션/채권 ─── */}
          <div className="description-section dm-section">
            <h2>{stepBadge(4, '#e65100')} 재무 / 배당 / 기업액션 / 채권</h2>
            <p className="dm-section-subtitle">
              DART API, 금융위원회 OpenAPI를 통해 재무제표, 배당, 기업 액션, 채권 데이터를 적재합니다.
            </p>

            <div className="dm-grid">
              {/* 재무제표 + PER/PBR */}
              <div className="dm-card">
                <h3>재무제표 + PER/PBR</h3>
                <p className="dm-card-sub">DART 사업보고서 기반. 백그라운드 실행.</p>
                <label className="dm-label">회계연도</label>
                <input
                  type="number"
                  value={dartFiscalYear}
                  onChange={(e) => setDartFiscalYear(Number(e.target.value))}
                  className="dm-input dm-input-mb"
                />
                <label className="dm-label">보고서 종류</label>
                <select
                  value={dartReportType}
                  onChange={(e) => setDartReportType(e.target.value)}
                  className="dm-input dm-input-mb"
                >
                  <option value="ANNUAL">사업보고서 (ANNUAL)</option>
                  <option value="Q3">3분기보고서</option>
                  <option value="Q2">반기보고서</option>
                  <option value="Q1">1분기보고서</option>
                </select>
                <label className="dm-label">종목 수 제한 (테스트)</label>
                <input
                  type="number"
                  value={dartFinLimit}
                  onChange={(e) => setDartFinLimit(e.target.value)}
                  placeholder="빈 칸 = 전체"
                  min={1}
                  max={5000}
                  className="dm-input dm-input-mb-lg"
                />
                <button
                  onClick={async () => {
                    if (!window.confirm(`FY${dartFiscalYear} ${dartReportType} 재무제표를 수집합니까?`)) return;
                    setLoading(true);
                    try {
                      const params = { fiscal_year: dartFiscalYear, report_type: dartReportType };
                      if (dartFinLimit) params.limit = Number(dartFinLimit);
                      const res = await api.loadDartFinancials(params);
                      setCurrentTaskId(res.data.task_id);
                      alert('DART 재무제표 수집 시작됨\ntask_id: ' + res.data.task_id);
                      await fetchDataStatus();
                    } catch (err) {
                      alert(err.response?.data?.detail || 'DART 재무제표 적재 실패');
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading}
                  className="btn btn-primary dm-btn-full"
                >
                  재무제표 적재 (DART)
                </button>
                <p className="dm-hint-sm">종목당 ~1초 (DART rate limit)</p>
              </div>

              {/* 배당 이력 */}
              <div className="dm-card">
                <h3>배당 이력</h3>
                <p className="dm-card-sub">금융위원회 OpenAPI</p>
                <label className="dm-label">종목 코드 (쉼표 구분)</label>
                <input
                  type="text"
                  value={dividendTickers}
                  onChange={(e) => setDividendTickers(e.target.value)}
                  placeholder="005930,000660"
                  className="dm-input dm-input-mb"
                />
                <label className="dm-label">기준일 (as_of_date)</label>
                <input
                  type="date"
                  value={dividendAsOf}
                  onChange={(e) => setDividendAsOf(e.target.value)}
                  className="dm-input dm-input-mb"
                />
                <label className="dm-label">기준일자 (YYYYMMDD, 선택)</label>
                <input
                  type="text"
                  value={dividendBasDt}
                  onChange={(e) => setDividendBasDt(e.target.value.replace(/[^0-9]/g, '').slice(0, 8))}
                  placeholder="비워두면 전체 조회"
                  className="dm-input dm-input-mb-lg"
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
                      alert(response.data.message);
                    } catch (err) {
                      alert(err.response?.data?.detail || '배당 이력 적재 실패');
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading}
                  className="btn btn-primary dm-btn-full"
                >
                  배당 이력 적재 (FSC)
                </button>
              </div>

              {/* 기업 액션 */}
              <div className="dm-card">
                <h3>기업 액션</h3>
                <p className="dm-card-sub">DART 공시 (분할/합병/감자)</p>
                <label className="dm-label">연도</label>
                <input
                  type="number"
                  value={actionYear}
                  onChange={(e) => setActionYear(Number(e.target.value))}
                  min={2015}
                  max={2030}
                  className="dm-input dm-input-mb"
                />
                <label className="dm-label">분기</label>
                <select
                  value={actionQuarter}
                  onChange={(e) => setActionQuarter(e.target.value)}
                  className="dm-input dm-input-mb-lg"
                >
                  <option value="Q1">Q1 (1~3월)</option>
                  <option value="Q2">Q2 (4~6월)</option>
                  <option value="Q3">Q3 (7~9월)</option>
                  <option value="Q4">Q4 (10~12월)</option>
                  <option value="ALL">전체 (1~12월)</option>
                </select>
                <button
                  onClick={async () => {
                    setLoading(true);
                    setError(null);
                    try {
                      const response = await api.loadDartCorporateActions({
                        year: actionYear,
                        quarter: actionQuarter,
                      });
                      alert(response.data.message);
                    } catch (err) {
                      alert(err.response?.data?.detail || '기업 액션 적재 실패');
                    } finally {
                      setLoading(false);
                    }
                  }}
                  disabled={loading}
                  className="btn btn-primary dm-btn-full"
                >
                  기업 액션 적재
                </button>
              </div>

              {/* 채권 */}
              <div className="dm-card">
                <h3>채권 기본정보</h3>
                <p className="dm-card-sub">금융위원회 OpenAPI</p>
                <label className="dm-label">등급 필터</label>
                <select
                  value={bondQualityFilter}
                  onChange={(e) => setBondQualityFilter(e.target.value)}
                  className="dm-input dm-input-mb-lg"
                >
                  <option value="all">전체 채권</option>
                  <option value="investment_grade">투자적격등급 (AAA~BBB)</option>
                  <option value="high_quality">최우량 (AAA~A)</option>
                </select>
                <button
                  onClick={handleLoadBonds}
                  disabled={loading}
                  className="btn btn-primary dm-btn-full-bold"
                >
                  채권 데이터 조회
                </button>
                <p className="dm-hint-sm">오늘 기준일로 선택 등급 채권을 조회</p>
              </div>
            </div>
          </div>

          {/* ─── Step 5: 금융감독원 금융상품 ─── */}
          <div className="description-section dm-section">
            <h2>{stepBadge(5, '#7b1fa2')} 금융감독원 금융상품</h2>
            <p className="dm-section-subtitle">
              FSS API (finlife.fss.or.kr)를 통해 예금/적금/연금/대출 상품을 수집합니다.
            </p>

            <div className="dm-grid">
              {[
                { title: '정기예금', fn: () => api.loadDeposits(), taskPrefix: 'deposits' },
                { title: '적금', fn: () => api.loadSavings(), taskPrefix: 'savings' },
                { title: '연금저축', fn: () => api.loadAnnuitySavings(), taskPrefix: 'annuity' },
                { title: '주택담보대출', fn: () => api.loadMortgageLoans(), taskPrefix: 'mortgage' },
                { title: '전세자금대출', fn: () => api.loadRentHouseLoans(), taskPrefix: 'rentloan' },
                { title: '개인신용대출', fn: () => api.loadCreditLoans(), taskPrefix: 'creditloan' },
              ].map(({ title, fn, taskPrefix }) => (
                <div key={taskPrefix} className="dm-card">
                  <h3 className="dm-fss-title">{title}</h3>
                  <button
                    onClick={async () => {
                      if (!window.confirm(`FSS ${title} 상품을 조회하시겠습니까?`)) return;
                      setLoading(true);
                      setError(null);
                      const tempId = `temp_${taskPrefix}_${Date.now()}`;
                      setCurrentTaskId(tempId);
                      try {
                        const res = await fn();
                        if (res.data.task_id) setCurrentTaskId(res.data.task_id);
                        await fetchDataStatus();
                      } catch (err) {
                        alert(err.response?.data?.detail || `${title} 적재 실패`);
                        setCurrentTaskId(null);
                      } finally {
                        setLoading(false);
                      }
                    }}
                    disabled={loading}
                    className="btn btn-primary dm-btn-full"
                  >
                    {title} 조회
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* ─── Alpha Vantage (미국 주식) — 준비 중 ─── */}
          <div className="description-section dm-section">
            <div className="dm-placeholder">
              <h2>Alpha Vantage - 미국 주식</h2>
              <p>추후 지원 예정입니다. 현재는 한국 시장 데이터에 집중합니다.</p>
            </div>
          </div>

          {/* ─── Phase 3: 수집 스케줄 모니터링 ─── */}
          <div className="description-section dm-section">
            <h2>{stepBadge(6, '#0d9488')} 수집 스케줄 모니터링</h2>
            <p className="dm-section-subtitle">
              자동 수집 스케줄 상태와 실행 이력을 확인합니다.
            </p>

            <div className="dm-tab-row" style={{ marginTop: '15px' }}>
              <button
                onClick={() => { setScheduleView('status'); if (!schedulerStatus) fetchSchedulerData(); }}
                className={scheduleView === 'status' ? 'btn btn-primary' : 'btn btn-secondary'}
              >
                스케줄 상태
              </button>
              <button
                onClick={() => { setScheduleView('logs'); if (!collectionLogs.length) fetchSchedulerData(); }}
                className={scheduleView === 'logs' ? 'btn btn-primary' : 'btn btn-secondary'}
              >
                실행 이력
              </button>
            </div>

            {/* 요약 통계 */}
            {collectionSummary && (
              <div className="dm-status-grid" style={{ marginTop: '15px' }}>
                <div className="score-card">
                  <div className="score-label">30일 실행</div>
                  <div className="score-value" style={{ color: '#2563eb' }}>
                    {collectionSummary.overall?.total_runs_30d || 0}회
                  </div>
                </div>
                <div className="score-card">
                  <div className="score-label">성공률</div>
                  <div className="score-value" style={{ color: 'var(--stock-up)' }}>
                    {collectionSummary.overall?.success_rate_30d != null
                      ? `${collectionSummary.overall.success_rate_30d}%`
                      : '-'}
                  </div>
                </div>
                <div className="score-card">
                  <div className="score-label">7일 실패</div>
                  <div className="score-value" style={{
                    color: (collectionSummary.overall?.recent_failures_7d || 0) > 0
                      ? 'var(--stock-down)' : 'var(--stock-up)'
                  }}>
                    {collectionSummary.overall?.recent_failures_7d || 0}건
                  </div>
                </div>
              </div>
            )}

            {/* 스케줄 상태 뷰 */}
            {scheduleView === 'status' && schedulerStatus && (
              <div className="dm-grid" style={{ marginTop: '15px' }}>
                {schedulerStatus.jobs.map((job) => (
                  <div key={job.scheduler_id} className="dm-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <h3 style={{ margin: 0, fontSize: '0.9rem' }}>{job.job_label}</h3>
                      {job.is_running ? (
                        <span className="dm-schedule-status dm-schedule-running">실행중</span>
                      ) : job.last_run?.status === 'completed' ? (
                        <span className="dm-schedule-status dm-schedule-completed">성공</span>
                      ) : job.last_run?.status === 'failed' ? (
                        <span className="dm-schedule-status dm-schedule-failed">실패</span>
                      ) : (
                        <span className="dm-schedule-status dm-schedule-pending">대기</span>
                      )}
                    </div>
                    <div className="dm-hint-sm" style={{ marginTop: 0 }}>
                      {job.next_run_time ? (
                        <>다음 실행: {new Date(job.next_run_time).toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</>
                      ) : '스케줄 없음'}
                    </div>
                    {job.last_run && (
                      <div className="dm-hint-sm" style={{ marginTop: '4px' }}>
                        마지막: {new Date(job.last_run.started_at).toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        {job.last_run.duration_seconds != null && ` (${Math.round(job.last_run.duration_seconds)}초)`}
                        {job.last_run.validation_status && (
                          <span className={`dm-validation-badge dm-validation-${job.last_run.validation_status}`}>
                            {job.last_run.validation_status}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* 실행 이력 뷰 */}
            {scheduleView === 'logs' && (
              <div className="dm-panel" style={{ marginTop: '15px' }}>
                <div style={{ display: 'flex', gap: '10px', marginBottom: '12px', alignItems: 'center' }}>
                  <select
                    value={logJobFilter}
                    onChange={(e) => setLogJobFilter(e.target.value)}
                    className="dm-input"
                    style={{ maxWidth: '200px' }}
                  >
                    <option value="">전체 작업</option>
                    <option value="incremental_prices">일별 시세</option>
                    <option value="compass_batch">Compass Score</option>
                    <option value="weekly_stock_refresh">주간 종목 갱신</option>
                    <option value="dart_financials">DART 재무제표</option>
                    <option value="monthly_products">월간 금융상품</option>
                  </select>
                  <button onClick={fetchSchedulerData} className="btn btn-secondary" style={{ padding: '8px 16px' }}>
                    새로고침
                  </button>
                </div>

                <div className="dm-log-table-wrap">
                  <table className="dm-log-table">
                    <thead>
                      <tr>
                        <th>작업명</th>
                        <th>상태</th>
                        <th>시작</th>
                        <th>소요</th>
                        <th>성공/실패</th>
                        <th>검증</th>
                      </tr>
                    </thead>
                    <tbody>
                      {collectionLogs.length === 0 ? (
                        <tr>
                          <td colSpan={6} style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>
                            실행 이력이 없습니다
                          </td>
                        </tr>
                      ) : (
                        collectionLogs.map((log) => (
                          <tr
                            key={log.id}
                            className={`dm-log-row dm-log-row-${log.status}`}
                            onClick={() => setLogDetailModal(log)}
                            style={{ cursor: 'pointer' }}
                          >
                            <td>{log.job_label}</td>
                            <td>
                              <span className={`dm-schedule-status dm-schedule-${log.status}`}>
                                {log.status === 'completed' ? '성공' : log.status === 'failed' ? '실패' : '실행중'}
                              </span>
                            </td>
                            <td className="dm-log-time">
                              {log.started_at
                                ? new Date(log.started_at).toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                                : '-'}
                            </td>
                            <td>{log.duration_seconds != null ? `${Math.round(log.duration_seconds)}초` : '-'}</td>
                            <td>
                              <span style={{ color: 'var(--stock-up)' }}>{log.success_count || 0}</span>
                              {' / '}
                              <span style={{ color: 'var(--stock-down)' }}>{log.failed_count || 0}</span>
                            </td>
                            <td>
                              {log.validation_status && (
                                <span className={`dm-validation-badge dm-validation-${log.validation_status}`}>
                                  {log.validation_status}
                                </span>
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 상세 모달 */}
            {logDetailModal && (
              <div className="dm-log-detail-overlay" onClick={() => setLogDetailModal(null)}>
                <div className="dm-log-detail-modal" onClick={(e) => e.stopPropagation()}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <h3 style={{ margin: 0, color: 'var(--text)' }}>{logDetailModal.job_label}</h3>
                    <button onClick={() => setLogDetailModal(null)} className="btn btn-secondary" style={{ padding: '4px 12px' }}>X</button>
                  </div>
                  <div className="dm-log-detail-grid">
                    <div><span className="dm-label">상태</span><span className={`dm-schedule-status dm-schedule-${logDetailModal.status}`}>{logDetailModal.status}</span></div>
                    <div><span className="dm-label">시작</span>{logDetailModal.started_at ? new Date(logDetailModal.started_at).toLocaleString('ko-KR') : '-'}</div>
                    <div><span className="dm-label">완료</span>{logDetailModal.completed_at ? new Date(logDetailModal.completed_at).toLocaleString('ko-KR') : '-'}</div>
                    <div><span className="dm-label">소요시간</span>{logDetailModal.duration_seconds != null ? `${Math.round(logDetailModal.duration_seconds)}초` : '-'}</div>
                    <div><span className="dm-label">성공</span><span style={{ color: 'var(--stock-up)' }}>{logDetailModal.success_count || 0}</span></div>
                    <div><span className="dm-label">실패</span><span style={{ color: 'var(--stock-down)' }}>{logDetailModal.failed_count || 0}</span></div>
                    <div><span className="dm-label">전체</span>{logDetailModal.total_count || 0}</div>
                    <div><span className="dm-label">검증</span>{logDetailModal.validation_status && <span className={`dm-validation-badge dm-validation-${logDetailModal.validation_status}`}>{logDetailModal.validation_status}</span>}</div>
                  </div>
                  {logDetailModal.error_message && (
                    <div style={{ marginTop: '12px' }}>
                      <span className="dm-label">에러</span>
                      <pre className="dm-log-detail-pre">{logDetailModal.error_message}</pre>
                    </div>
                  )}
                  {logDetailModal.detail && (
                    <div style={{ marginTop: '12px' }}>
                      <span className="dm-label">상세</span>
                      <pre className="dm-log-detail-pre">{JSON.stringify(logDetailModal.detail, null, 2)}</pre>
                    </div>
                  )}
                  {logDetailModal.validation_detail && (
                    <div style={{ marginTop: '12px' }}>
                      <span className="dm-label">검증 상세</span>
                      <pre className="dm-log-detail-pre">{JSON.stringify(logDetailModal.validation_detail, null, 2)}</pre>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* ─── Data View ─── */}
          {dataStatus && dataStatus.total > 0 && (
            <div className="description-section dm-section">
              <h2>적재된 데이터 조회</h2>

              <div className="dm-tab-row">
                {dataStatus.stocks > 0 && (
                  <button
                    onClick={() => setActiveTab('stocks')}
                    className={activeTab === 'stocks' ? 'btn btn-primary' : 'btn btn-secondary'}
                  >
                    주식 ({dataStatus.stocks})
                  </button>
                )}
                {dataStatus.etfs > 0 && (
                  <button
                    onClick={() => setActiveTab('etfs')}
                    className={activeTab === 'etfs' ? 'btn btn-primary' : 'btn btn-secondary'}
                  >
                    ETF ({dataStatus.etfs})
                  </button>
                )}
                {dataStatus.bonds > 0 && (
                  <button
                    onClick={() => setActiveTab('bonds')}
                    className={activeTab === 'bonds' ? 'btn btn-primary' : 'btn btn-secondary'}
                  >
                    채권 ({dataStatus.bonds})
                  </button>
                )}
                {dataStatus.deposits > 0 && (
                  <button
                    onClick={() => setActiveTab('deposits')}
                    className={activeTab === 'deposits' ? 'btn btn-primary' : 'btn btn-secondary'}
                  >
                    예적금 ({dataStatus.deposits})
                  </button>
                )}
              </div>

              <div className="dm-tab-content">
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
