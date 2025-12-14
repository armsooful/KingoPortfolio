import axios from 'axios';

// API 기본 설정
const API_BASE_URL = 'http://localhost:8000';

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
      // 토큰 만료 시 로컬스토리지 초기화
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
 * @param {Object} data - { email, password, name }
 * @returns {Promise}
 */
export const signUp = (data) => {
  return api.post('/api/auth/signup', data);
};

/**
 * 로그인
 * @param {Object} data - { email, password }
 * @returns {Promise}
 */
export const login = (data) => {
  return api.post('/api/auth/login', data);
};

/**
 * 현재 사용자 정보 조회
 * @returns {Promise}
 */
export const getCurrentUser = () => {
  return api.get('/api/auth/me');
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
 * @returns {Promise}
 */
export const getSurveyQuestions = () => {
  return api.get('/api/survey/questions');
};

/**
 * 특정 설문 문항 조회
 * @param {number} questionId - 문항 ID
 * @returns {Promise}
 */
export const getSurveyQuestion = (questionId) => {
  return api.get(`/api/survey/questions/${questionId}`);
};

// ============================================================
// Diagnosis API
// ============================================================

/**
 * 설문 제출 및 진단 실행
 * @param {Object} data - { answers: [{question_id, answer_value}, ...], monthly_investment }
 * @returns {Promise}
 */
export const submitDiagnosis = (data) => {
  return api.post('/api/diagnosis/submit', data);
};

/**
 * 최근 진단 결과 조회
 * @returns {Promise}
 */
export const getMyLatestDiagnosis = () => {
  return api.get('/api/diagnosis/me');
};

/**
 * 특정 진단 결과 조회
 * @param {string} diagnosisId - 진단 ID
 * @returns {Promise}
 */
export const getDiagnosis = (diagnosisId) => {
  return api.get(`/api/diagnosis/${diagnosisId}`);
};

/**
 * 진단 이력 조회
 * @param {number} limit - 조회 개수 (기본값: 10)
 * @returns {Promise}
 */
export const getDiagnosisHistory = (limit = 10) => {
  return api.get(`/api/diagnosis/history/all?limit=${limit}`);
};

// ============================================================
// Health Check
// ============================================================

/**
 * 백엔드 헬스 체크
 * @returns {Promise}
 */
export const healthCheck = () => {
  return axios.get(`${API_BASE_URL}/health`);
};

export default api;