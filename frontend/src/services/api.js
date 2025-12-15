import axios from 'axios';

// API 기본 설정
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
// Auth API (⭐ /api 제거!)
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
  return api.post('/auth/login', data);
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
// Survey API (⭐ /api 제거!)
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
// Diagnosis API (⭐ /api 제거!)
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