import axios from 'axios';

// API 기본 설정
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터 - 토큰 자동 추가
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
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
  a.download = `portfolio_report_${new Date().toISOString().split('T')[0]}.pdf`;
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
  a.download = `diagnosis_report_${diagnosisId}_${new Date().toISOString().split('T')[0]}.pdf`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
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
 * 모든 종목 데이터 수집
 */
export const loadAllData = () => {
  return api.post('/admin/load-data');
};

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
 * pykrx: 인기 한국 주식 전체 적재
 */
export const loadAllPykrxStocks = () => {
  return api.post('/admin/pykrx/load-all-stocks');
};

/**
 * pykrx: 특정 한국 주식 적재
 */
export const loadPykrxStock = (ticker) => {
  return api.post(`/admin/pykrx/load-stock/${ticker}`);
};

/**
 * pykrx: 인기 한국 ETF 전체 적재
 */
export const loadAllPykrxETFs = () => {
  return api.post('/admin/pykrx/load-all-etfs');
};

/**
 * pykrx: 특정 한국 ETF 적재
 */
export const loadPykrxETF = (ticker) => {
  return api.post(`/admin/pykrx/load-etf/${ticker}`);
};

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
