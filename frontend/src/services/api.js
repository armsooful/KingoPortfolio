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
    if (error.response?.status === 401) {
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
 * 로그인 (OAuth2 형식)
 */
export const login = (data) => {
  // OAuth2 형식으로 변환 (form-urlencoded)
  const formData = new URLSearchParams();
  // email을 username으로 매핑 (OAuth2 표준)
  formData.append('username', data.email || data.username);
  formData.append('password', data.password);

  return api.post('/token', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
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
