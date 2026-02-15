import axios from 'axios';

// API 기본 설정
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// UUID generator for idempotency keys
const generateUUID = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

// 요청 인터셉터 - 토큰 자동 추가
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Add idempotency key for write requests
    if (config.method && ['post', 'put', 'patch', 'delete'].includes(config.method.toLowerCase())) {
      if (!config.headers['x-idempotency-key']) {
        config.headers['x-idempotency-key'] = generateUUID();
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 응답 인터셉터 - 에러 처리
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // 로그인/회원가입 요청의 401 에러는 정상적인 실패이므로 리다이렉트하지 않음
    const isAuthEndpoint = error.config?.url === '/auth/login' ||
                          error.config?.url === '/auth/signup';

    if (error.response?.status === 401 && !isAuthEndpoint) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ============================================================
// Auth API
// ============================================================

/**
 * 회원가입
 */
export const signUp = (data) => {
  return api.post('/auth/signup', data);
};

/**
 * 로그인
 */
export const login = (data) => {
  return api.post('/auth/login', {
    email: data.email,
    password: data.password
  });
};

/**
 * 현재 사용자 정보 조회
 */
export const getCurrentUser = () => {
  return api.get('/auth/me');
};

/**
 * 로그아웃
 */
export const logout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user');
};

/**
 * 비밀번호 변경
 */
export const changePassword = (data) => {
  return api.put('/auth/change-password', data);
};

/**
 * 프로필 완성도 조회
 */
export const getProfileCompletionStatus = () => {
  return api.get('/auth/profile/completion-status');
};

/**
 * 프로필 업데이트
 */
export const updateProfile = (data) => {
  return api.put('/auth/profile', data);
};

// ============================================================
// Survey API
// ============================================================

/**
 * 모든 설문 문항 조회
 */
export const getSurveyQuestions = () => {
  return api.get('/survey/questions');
};

/**
 * 특정 설문 문항 조회
 */
export const getSurveyQuestion = (questionId) => {
  return api.get(`/survey/questions/${questionId}`);
};

/**
 * 유의사항 동의 기록
 */
export const recordConsent = (data) => {
  return api.post('/api/v1/consents', data);
};

export const listConsents = (limit = 50, offset = 0) => {
  const params = new URLSearchParams({ limit, offset });
  return api.get(`/api/v1/consents?${params.toString()}`);
};

export const listAdminConsents = (params = {}) => {
  const query = new URLSearchParams(params);
  return api.get(`/admin/consents?${query.toString()}`);
};

// ============================================================
// Diagnosis API
// ============================================================

/**
 * 설문 제출 및 진단 실행
 */
export const submitDiagnosis = (data) => {
  return api.post('/diagnosis/submit', data);
};

/**
 * 최근 진단 결과 조회
 */
export const getMyLatestDiagnosis = () => {
  return api.get('/diagnosis/me');
};

/**
 * 특정 진단 결과 조회
 */
export const getDiagnosis = (diagnosisId) => {
  return api.get(`/diagnosis/${diagnosisId}`);
};

/**
 * 진단 이력 조회
 */
export const getDiagnosisHistory = (limit = 10) => {
  return api.get(`/diagnosis/history/all?limit=${limit}`);
};

// ============================================================
// Health Check
// ============================================================

const getKSTDateString = () => {
  const now = new Date();
  const kstOffset = 9 * 60 * 60 * 1000;
  const kstDate = new Date(now.getTime() + kstOffset);
  return kstDate.toISOString().split('T')[0];
}

/**
 * 백엔드 헬스 체크
 */
export const healthCheck = () => {
  return axios.get(`${API_BASE_URL}/health`);
};

// ============================================================
// PDF Report API
// ============================================================

/**
 * 포트폴리오 PDF 리포트 다운로드
 */
export const downloadPortfolioPDF = async (investmentAmount = 10000000) => {
  const token = localStorage.getItem('access_token');
  const response = await fetch(`${API_BASE_URL}/reports/portfolio-pdf?investment_amount=${investmentAmount}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  if (!response.ok) {
    throw new Error('Failed to download PDF report');
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `portfolio_report_${getKSTDateString()}.pdf`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};

/**
 * 특정 진단 결과 PDF 리포트 다운로드
 */
export const downloadDiagnosisPDF = async (diagnosisId) => {
  const token = localStorage.getItem('access_token');
  const response = await fetch(`${API_BASE_URL}/reports/diagnosis-pdf/${diagnosisId}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  if (!response.ok) {
    throw new Error('Failed to download PDF report');
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `diagnosis_report_${diagnosisId}_${getKSTDateString()}.pdf`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};

// ============================================================
// Phase 7 Evaluation API
// ============================================================

export const createPhase7Portfolio = (data) => {
  return api.post('/api/v1/phase7/portfolios', data);
};

export const listPhase7Portfolios = () => {
  return api.get('/api/v1/phase7/portfolios');
};

export const evaluatePhase7Portfolio = (data) => {
  return api.post('/api/v1/phase7/evaluations', data);
};

export const listPhase7Evaluations = (portfolioId, limit = 50, offset = 0) => {
  const params = new URLSearchParams();
  if (portfolioId) {
    params.append('portfolio_id', portfolioId);
  }
  params.append('limit', limit);
  params.append('offset', offset);
  return api.get(`/api/v1/phase7/evaluations?${params.toString()}`);
};

export const getPhase7EvaluationDetail = (evaluationId) => {
  return api.get(`/api/v1/phase7/evaluations/${evaluationId}`);
};

export const getPhase7AvailablePeriod = (portfolioId) => {
  return api.get(`/api/v1/phase7/evaluations/available-period?portfolio_id=${portfolioId}`);
};

export const comparePhase7Portfolios = (data) => {
  return api.post('/api/v1/phase7/comparisons', data);
};

/**
 * PDF 리포트 데이터 미리보기
 */
export const previewReportData = (investmentAmount = 10000000) => {
  return api.get(`/reports/preview?investment_amount=${investmentAmount}`);
};

export default api;
// ============================================================
// Admin API
// ============================================================

/**
 * 주식 데이터만 수집
 */
export const loadStocks = () => {
  return api.post('/admin/load-stocks');
};

/**
 * ETF 데이터만 수집
 */
export const loadETFs = () => {
  return api.post('/admin/load-etfs');
};

export const loadDartDividends = (payload) => {
  return api.post('/admin/dart/load-dividends', payload);
};

export const loadFscDividends = (payload) => {
  return api.post('/admin/fsc/load-dividends', payload);
};

export const loadFdrStockListing = (payload) => {
  return api.post('/admin/fdr/load-stock-listing', payload);
};

export const loadDartCorporateActions = (payload) => {
  return api.post('/admin/dart/load-corporate-actions', payload);
};

export const loadFscBonds = (payload) => {
  return api.post('/admin/fsc/load-bonds', payload);
};

/**
 * 채권 데이터 전체 조회 (기준일자: 오늘)
 * @param {string} qualityFilter - 'all' | 'investment_grade' | 'high_quality'
 */
export const loadBonds = (qualityFilter = 'all') => {
  return api.post('/admin/load-bonds', null, { params: { quality_filter: qualityFilter } });
};

export const loadDartFinancials = (params = {}) => {
  return api.post('/admin/dart/load-financials', null, { params });
};

/**
 * FSS 정기예금 상품 조회
 */
export const loadDeposits = () => {
  return api.post('/admin/load-deposits');
};

/**
 * FSS 적금 상품 조회
 */
export const loadSavings = () => {
  return api.post('/admin/load-savings');
};

/**
 * FSS 연금저축 상품 조회
 */
export const loadAnnuitySavings = () => {
  return api.post('/admin/load-annuity-savings');
};

/**
 * FSS 주택담보대출 상품 조회
 */
export const loadMortgageLoans = () => {
  return api.post('/admin/load-mortgage-loans');
};

/**
 * FSS 전세자금대출 상품 조회
 */
export const loadRentHouseLoans = () => {
  return api.post('/admin/load-rent-house-loans');
};

/**
 * FSS 개인신용대출 상품 조회
 */
export const loadCreditLoans = () => {
  return api.post('/admin/load-credit-loans');
};

/**
 * DB 데이터 현황 조회
 */
export const getDataStatus = () => {
  return api.get('/admin/data-status');
};

/**
 * 진행 상황 조회 (특정 task)
 */
export const getProgress = (taskId) => {
  return api.get(`/admin/progress/${taskId}`);
};

/**
 * 모든 진행 상황 조회
 */
export const getAllProgress = () => {
  return api.get('/admin/progress');
};

/**
 * 적재된 주식 데이터 조회
 */
export const getStocks = (skip = 0, limit = 100) => {
  return api.get(`/admin/stocks?skip=${skip}&limit=${limit}`);
};

/**
 * 적재된 ETF 데이터 조회
 */
export const getETFs = (skip = 0, limit = 100) => {
  return api.get(`/admin/etfs?skip=${skip}&limit=${limit}`);
};

/**
 * 적재된 채권 데이터 조회
 */
export const getBonds = (skip = 0, limit = 100) => {
  return api.get(`/admin/bonds?skip=${skip}&limit=${limit}`);
};

/**
 * 적재된 예적금 데이터 조회
 */
export const getDeposits = (skip = 0, limit = 100) => {
  return api.get(`/admin/deposits?skip=${skip}&limit=${limit}`);
};

// ============================================================
// Alpha Vantage API
// ============================================================

/**
 * Alpha Vantage: 인기 미국 주식 전체 적재
 */
export const loadAllAlphaVantageStocks = () => {
  return api.post('/admin/alpha-vantage/load-all-stocks');
};

/**
 * Alpha Vantage: 특정 주식 적재
 */
export const loadAlphaVantageStock = (symbol) => {
  return api.post(`/admin/alpha-vantage/load-stock/${symbol}`);
};

/**
 * Alpha Vantage: 특정 주식의 재무제표 적재
 */
export const loadAlphaVantageFinancials = (symbol) => {
  return api.post(`/admin/alpha-vantage/load-financials/${symbol}`);
};

/**
 * Alpha Vantage: 인기 미국 ETF 전체 적재
 */
export const loadAllAlphaVantageETFs = () => {
  return api.post('/admin/alpha-vantage/load-all-etfs');
};

/**
 * Alpha Vantage: 적재된 미국 주식 데이터 조회
 */
export const getAlphaVantageStocks = (skip = 0, limit = 100) => {
  return api.get(`/admin/alpha-vantage/stocks?skip=${skip}&limit=${limit}`);
};

/**
 * Alpha Vantage: 특정 주식의 재무제표 조회
 */
export const getAlphaVantageFinancials = (symbol) => {
  return api.get(`/admin/alpha-vantage/financials/${symbol}`);
};

/**
 * Alpha Vantage: DB 통계
 */
export const getAlphaVantageDataStatus = () => {
  return api.get('/admin/alpha-vantage/data-status');
};

/**
 * Alpha Vantage: 모든 인기 주식/ETF 시계열 데이터 적재
 * @param {string} outputsize - 'compact' (최근 100일) or 'full' (최대 20년)
 */
export const loadAllAlphaVantageTimeSeries = (outputsize = 'compact') => {
  return api.post(`/admin/alpha-vantage/load-all-timeseries?outputsize=${outputsize}`);
};

/**
 * Alpha Vantage: 특정 종목의 시계열 데이터 적재
 * @param {string} symbol - 주식 심볼
 * @param {string} outputsize - 'compact' (최근 100일) or 'full' (최대 20년)
 */
export const loadAlphaVantageTimeSeries = (symbol, outputsize = 'compact') => {
  return api.post(`/admin/alpha-vantage/load-timeseries/${symbol}?outputsize=${outputsize}`);
};

// ============================================================
// pykrx (한국 주식) API
// ============================================================

/**
 * pykrx: 인기 한국 주식 전체 재무제표 적재
 */
export const loadAllPykrxFinancials = () => {
  return api.post('/admin/pykrx/load-all-financials');
};

/**
 * pykrx: 특정 한국 주식 재무제표 적재
 */
export const loadPykrxFinancials = (ticker) => {
  return api.post(`/admin/pykrx/load-financials/${ticker}`);
};

/**
 * pykrx: stocks 테이블 전체 종목 증분 시계열 적재
 */
export const loadStocksIncremental = (payload) => {
  return api.post('/admin/pykrx/load-stocks-incremental', payload);
};

// ============================================================
// Financial Analysis API
// ============================================================

/**
 * 재무 분석 조회
 */
export const getFinancialAnalysis = (symbol) => {
  return api.get(`/admin/financial-analysis/${symbol}`);
};

/**
 * 재무 건전성 점수 조회 (V1 - 보수적)
 */
export const getFinancialScore = (symbol) => {
  return api.get(`/admin/financial-score/${symbol}`);
};

/**
 * 재무 건전성 점수 조회 (V2 - 성장주 친화적)
 */
export const getFinancialScoreV2 = (symbol) => {
  return api.get(`/admin/financial-score-v2/${symbol}`);
};

/**
 * 종목 비교 분석
 */
export const compareFinancials = (symbols) => {
  return api.post('/admin/financial-analysis/compare', symbols);
};

// ============================================================
// Valuation API
// ============================================================

/**
 * 멀티플 비교 분석
 */
export const getValuationMultiples = (symbol) => {
  return api.get(`/admin/valuation/multiples/${symbol}`);
};

/**
 * DCF 밸류에이션
 */
export const getDCFValuation = (symbol) => {
  return api.get(`/admin/valuation/dcf/${symbol}`);
};

/**
 * 배당할인모형 (DDM)
 */
export const getDDMValuation = (symbol) => {
  return api.get(`/admin/valuation/ddm/${symbol}`);
};

/**
 * 종합 밸류에이션 분석
 */
export const getComprehensiveValuation = (symbol) => {
  return api.get(`/admin/valuation/comprehensive/${symbol}`);
};

// ============================================================
// Quant Analysis API
// ============================================================

/**
 * 종합 퀀트 분석
 */
export const getComprehensiveQuant = (symbol, marketSymbol = 'SPY', days = 252) => {
  return api.get(`/admin/quant/comprehensive/${symbol}`, {
    params: { market_symbol: marketSymbol, days }
  });
};

/**
 * 기술적 지표 분석
 */
export const getTechnicalIndicators = (symbol, days = 252) => {
  return api.get(`/admin/quant/technical/${symbol}`, { params: { days } });
};

/**
 * 리스크 지표 분석
 */
export const getRiskMetrics = (symbol, marketSymbol = 'SPY', days = 252) => {
  return api.get(`/admin/quant/risk/${symbol}`, {
    params: { market_symbol: marketSymbol, days }
  });
};

// ============================================================
// Report Generation API
// ============================================================

/**
 * 종합 투자 리포트 생성
 */
export const getComprehensiveReport = (symbol, marketSymbol = 'SPY', days = 252) => {
  return api.get(`/admin/report/comprehensive/${symbol}`, {
    params: { market_symbol: marketSymbol, days }
  });
};

/**
 * 여러 종목 비교 리포트
 */
export const getComparisonReport = (symbols) => {
  return api.post('/admin/report/comparison', symbols);
};

/**
 * ============================================================
 * 정성적 분석 (Qualitative Analysis - AI)
 * ============================================================
 */
export const getNewsSentiment = (symbol) => {
  return api.get(`/admin/qualitative/news-sentiment/${symbol}`);
};

// ============================================================
// Portfolio API
// ============================================================

/**
 * 포트폴리오 생성
 */
export const generatePortfolio = (data) => {
  return api.post('/portfolio/generate', data);
};

/**
 * 포트폴리오 리밸런싱
 */
export const rebalancePortfolio = (diagnosisId, investmentAmount) => {
  return api.post(`/portfolio/rebalance/${diagnosisId}?investment_amount=${investmentAmount}`);
};

/**
 * 자산 배분 전략 조회
 */
export const getAssetAllocation = (investmentType) => {
  return api.get(`/portfolio/asset-allocation/${investmentType}`);
};

/**
 * 선택 가능한 섹터 목록
 */
export const getAvailableSectors = () => {
  return api.get('/portfolio/available-sectors');
};

/**
 * 포트폴리오 수익률 시뮬레이션
 */
export const simulatePortfolio = (investmentType, investmentAmount, years = 10) => {
  return api.post(`/portfolio/simulate?investment_type=${investmentType}&investment_amount=${investmentAmount}&years=${years}`);
};

// ============================================================
// Backtesting API
// ============================================================

/**
 * 백테스트 실행
 */
export const runBacktest = (data) => {
  return api.post('/backtest/run', data);
};

/**
 * 포트폴리오 비교 백테스트
 */
export const comparePortfolios = (data) => {
  return api.post('/backtest/compare', data);
};

/**
 * 투자 성향별 과거 성과 지표 조회
 */
export const getBacktestMetrics = (investmentType, periodYears = 1) => {
  return api.get(`/backtest/metrics/${investmentType}?period_years=${periodYears}`);
};

// ============================================================
// Scenarios API
// ============================================================

/**
 * 관리형 시나리오 목록 조회
 */
export const getScenarios = () => {
  return api.get('/scenarios');
};

/**
 * 시나리오 상세 조회
 */
export const getScenarioDetail = (scenarioId) => {
  return api.get(`/scenarios/${scenarioId}`);
};

// ============================================================
// Analysis API (Phase 3-A)
// ============================================================

/**
 * 포트폴리오 성과 해석
 */
export const explainPortfolio = (data) => {
  return api.post('/api/v1/analysis/explain', data);
};

/**
 * 직접 지표 해석 (포트폴리오 ID 없이)
 */
export const explainDirect = (data) => {
  return api.post('/api/v1/analysis/explain/direct', data);
};

/**
 * 면책 조항 조회
 */
export const getAnalysisDisclaimer = () => {
  return api.get('/api/v1/analysis/disclaimer');
};

/**
 * 성과 해석 PDF 다운로드 (직접 지표 입력)
 */
export const downloadExplanationPDF = async (data) => {
  const token = localStorage.getItem('access_token');
  const response = await fetch(`${API_BASE_URL}/api/v1/analysis/explain/pdf`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    throw new Error('Failed to download PDF report');
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `performance_report_${getKSTDateString()}.pdf`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};

/**
 * 포트폴리오 성과 해석 PDF 다운로드
 */
export const downloadPortfolioExplanationPDF = async (data) => {
  const token = localStorage.getItem('access_token');
  const response = await fetch(`${API_BASE_URL}/api/v1/analysis/explain/portfolio/pdf`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    throw new Error('Failed to download PDF report');
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `portfolio_report_${data.portfolio_id}_${getKSTDateString()}.pdf`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};

// ============================================================
// Phase 3-B: 리포트 히스토리 API
// ============================================================

/**
 * 성과 해석 히스토리 저장
 */
export const saveExplanationHistory = (data) => {
  return api.post('/api/v1/analysis/history', data);
};

/**
 * 성과 해석 히스토리 목록 조회
 */
export const getExplanationHistory = (skip = 0, limit = 20) => {
  return api.get(`/api/v1/analysis/history?skip=${skip}&limit=${limit}`);
};

/**
 * 성과 해석 히스토리 상세 조회
 */
export const getExplanationHistoryDetail = (historyId) => {
  return api.get(`/api/v1/analysis/history/${historyId}`);
};

/**
 * 성과 해석 히스토리 삭제
 */
export const deleteExplanationHistory = (historyId) => {
  return api.delete(`/api/v1/analysis/history/${historyId}`);
};

/**
 * 기간별 비교 리포트
 */
export const comparePeriods = (data) => {
  return api.post('/api/v1/analysis/compare-periods', data);
};

/**
 * 프리미엄 성과 해석 리포트 PDF 다운로드
 */
export const downloadPremiumReportPDF = async (data) => {
  const token = localStorage.getItem('access_token');
  const response = await fetch(`${API_BASE_URL}/api/v1/analysis/premium-report/pdf`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    throw new Error('Failed to download premium PDF report');
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const title = (data.report_title || 'premium_report').replace(/\s+/g, '_').slice(0, 30);
  a.download = `${title}_${getKSTDateString()}.pdf`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};

// ============================================================
// Securities API - 종목/섹터 조회
// ============================================================

/**
 * 주식 종목 목록 조회
 */
export const listStocks = (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.search) queryParams.append('search', params.search);
  if (params.sector) queryParams.append('sector', params.sector);
  if (params.market) queryParams.append('market', params.market);
  if (params.riskLevel) queryParams.append('risk_level', params.riskLevel);
  if (params.category) queryParams.append('category', params.category);
  if (params.sortBy) queryParams.append('sort_by', params.sortBy);
  if (params.sortOrder) queryParams.append('sort_order', params.sortOrder);
  if (params.limit) queryParams.append('limit', params.limit);
  if (params.offset) queryParams.append('offset', params.offset);
  return api.get(`/api/v1/securities/stocks?${queryParams.toString()}`);
};

/**
 * 주식 종목 상세 조회
 */
export const getStock = (ticker) => {
  return api.get(`/api/v1/securities/stocks/${ticker}`);
};

/**
 * ETF 목록 조회
 */
export const listETFs = (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.search) queryParams.append('search', params.search);
  if (params.etfType) queryParams.append('etf_type', params.etfType);
  if (params.riskLevel) queryParams.append('risk_level', params.riskLevel);
  if (params.sortBy) queryParams.append('sort_by', params.sortBy);
  if (params.sortOrder) queryParams.append('sort_order', params.sortOrder);
  if (params.limit) queryParams.append('limit', params.limit);
  if (params.offset) queryParams.append('offset', params.offset);
  return api.get(`/api/v1/securities/etfs?${queryParams.toString()}`);
};

/**
 * ETF 상세 조회
 */
export const getETF = (ticker) => {
  return api.get(`/api/v1/securities/etfs/${ticker}`);
};

/**
 * 섹터 목록 조회
 */
export const listSectors = (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.market) queryParams.append('market', params.market);
  return api.get(`/api/v1/securities/sectors?${queryParams.toString()}`);
};

/**
 * 시장 목록 조회
 */
export const listMarkets = () => {
  return api.get('/api/v1/securities/markets');
};

/**
 * 카테고리 목록 조회
 */
export const listCategories = () => {
  return api.get('/api/v1/securities/categories');
};

// ============================================================
// Market Subscription API
// ============================================================

export const getMarketSubscriptionStatus = () => {
  return api.get('/api/v1/market-subscription/status');
};

export const subscribeMarketEmail = () => {
  return api.post('/api/v1/market-subscription/subscribe');
};

export const unsubscribeMarketEmail = () => {
  return api.post('/api/v1/market-subscription/unsubscribe');
};

// ============================================================
// Screener API
// ============================================================

export const searchStocks = (query, limit = 10) => {
  return api.get(`/api/v1/screener/search?q=${encodeURIComponent(query)}&limit=${limit}`);
};

export const compareStocks = (tickers) => {
  return api.get(`/api/v1/screener/compare?tickers=${tickers.join(',')}`);
};

export const screenerStocks = (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.search) queryParams.append('search', params.search);
  if (params.sector) queryParams.append('sector', params.sector);
  if (params.market) queryParams.append('market', params.market);
  if (params.minScore != null) queryParams.append('min_score', params.minScore);
  if (params.maxScore != null) queryParams.append('max_score', params.maxScore);
  if (params.grade) queryParams.append('grade', params.grade);
  if (params.sortBy) queryParams.append('sort_by', params.sortBy);
  if (params.sortOrder) queryParams.append('sort_order', params.sortOrder);
  if (params.limit) queryParams.append('limit', params.limit);
  if (params.offset != null) queryParams.append('offset', params.offset);
  return api.get(`/api/v1/screener/stocks?${queryParams.toString()}`);
};

// ============================================================
// Watchlist API
// ============================================================

export const getWatchlist = () => {
  return api.get('/api/v1/watchlist');
};

export const addToWatchlist = (ticker) => {
  return api.post('/api/v1/watchlist', { ticker });
};

export const removeFromWatchlist = (ticker) => {
  return api.delete(`/api/v1/watchlist/${ticker}`);
};

export const getWatchlistStatus = (ticker) => {
  return api.get(`/api/v1/watchlist/status/${ticker}`);
};

export const getWatchlistAlertStatus = () => {
  return api.get('/api/v1/market-subscription/watchlist-alerts/status');
};

export const toggleWatchlistAlerts = () => {
  return api.post('/api/v1/market-subscription/watchlist-alerts/toggle');
};

export const getAiCommentary = (ticker) => {
  return api.post(`/admin/stock-detail/${ticker}/ai-commentary`);
};

export const batchComputeCompassScores = (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.market) queryParams.append('market', params.market);
  if (params.limit) queryParams.append('limit', params.limit);
  return api.post(`/admin/scoring/batch-compute?${queryParams.toString()}`);
};

// ── Phase 3: 수집 이력 모니터링 ──
export const getCollectionLogs = (params = {}) => {
  return api.get('/admin/collection-logs', { params });
};

export const getCollectionSummary = () => {
  return api.get('/admin/collection-logs/summary');
};

export const getCollectionLogDetail = (logId) => {
  return api.get(`/admin/collection-logs/${logId}`);
};

export const getSchedulerStatus = () => {
  return api.get('/admin/scheduler/status');
};
