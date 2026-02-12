import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  explainDirect,
  explainPortfolio,
  downloadExplanationPDF,
  downloadPremiumReportPDF,
  saveExplanationHistory
} from '../services/api';
import '../styles/PortfolioExplanation.css';

/**
 * Phase 3-A: 포트폴리오 성과 해석 페이지
 *
 * 설명 중심 포트폴리오 해석 서비스
 * - 종목 추천 X
 * - 투자 판단 유도 X
 * - 결과 해석 및 맥락 제공 O
 */
function PortfolioExplanationPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [explanation, setExplanation] = useState(null);

  // 입력 폼 상태
  const [formData, setFormData] = useState({
    cagr: '',
    volatility: '',
    mdd: '',
    sharpe: '',
    start_date: '',
    end_date: '',
    rf_annual: '0.035',
    benchmark_name: '',
    benchmark_return: '',
  });

  // location.state에서 데이터 받기 (다른 페이지에서 전달받은 경우)
  useEffect(() => {
    if (location.state?.metrics) {
      const { metrics } = location.state;
      setFormData(prev => ({
        ...prev,
        cagr: metrics.cagr?.toString() || '',
        volatility: metrics.volatility?.toString() || '',
        mdd: metrics.mdd?.toString() || '',
        sharpe: metrics.sharpe?.toString() || '',
        start_date: metrics.period_start || '',
        end_date: metrics.period_end || '',
      }));
    }
  }, [location.state]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const requestData = {
        cagr: parseFloat(formData.cagr),
        volatility: parseFloat(formData.volatility),
        mdd: parseFloat(formData.mdd),
        sharpe: formData.sharpe ? parseFloat(formData.sharpe) : null,
        start_date: formData.start_date,
        end_date: formData.end_date,
        rf_annual: parseFloat(formData.rf_annual) || 0,
        benchmark_name: formData.benchmark_name || null,
        benchmark_return: formData.benchmark_return ? parseFloat(formData.benchmark_return) : null,
      };

      const response = await explainDirect(requestData);
      setExplanation(response.data);
    } catch (err) {
      console.error('Analysis error:', err);
      setError(err.response?.data?.detail || '분석 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  // 예시 데이터로 채우기
  const fillExampleData = () => {
    setFormData({
      cagr: '0.085',
      volatility: '0.15',
      mdd: '-0.12',
      sharpe: '0.62',
      start_date: '2023-01-01',
      end_date: '2024-01-01',
      rf_annual: '0.035',
      benchmark_name: 'KOSPI 200',
      benchmark_return: '0.065',
    });
  };

  return (
    <div className="explanation-container">
      <div className="explanation-header">
        <h1 className="explanation-title">📊 포트폴리오 성과 해석</h1>
        <p className="explanation-subtitle">
          성과 지표를 입력하면 이해하기 쉬운 설명을 제공합니다
        </p>
        <div className="explanation-notice">
          <span className="explanation-notice-icon">📖</span>
          <span>
            본 서비스는 <strong>정보 제공 목적</strong>으로만 운영됩니다.
            투자 권유나 추천이 아닙니다.
          </span>
        </div>
      </div>

      {/* 입력 폼 */}
      {!explanation && (
        <div className="explanation-input-section">
          <div className="explanation-form-header">
            <h2 className="explanation-section-title">성과 지표 입력</h2>
            <button
              type="button"
              onClick={fillExampleData}
              className="explanation-example-button"
            >
              예시 데이터
            </button>
          </div>

          <form onSubmit={handleSubmit} className="explanation-form">
            <div className="explanation-form-grid">
              {/* 기간 설정 */}
              <div className="explanation-form-group">
                <label className="explanation-label">시작일 *</label>
                <input
                  type="date"
                  name="start_date"
                  value={formData.start_date}
                  onChange={handleInputChange}
                  required
                  className="explanation-input"
                />
              </div>
              <div className="explanation-form-group">
                <label className="explanation-label">종료일 *</label>
                <input
                  type="date"
                  name="end_date"
                  value={formData.end_date}
                  onChange={handleInputChange}
                  required
                  className="explanation-input"
                />
              </div>

              {/* 수익률 지표 */}
              <div className="explanation-form-group">
                <label className="explanation-label">
                  CAGR (연복리수익률) *
                  <span className="explanation-hint">예: 0.085 = 8.5%</span>
                </label>
                <input
                  type="number"
                  name="cagr"
                  value={formData.cagr}
                  onChange={handleInputChange}
                  step="0.001"
                  required
                  placeholder="0.085"
                  className="explanation-input"
                />
              </div>
              <div className="explanation-form-group">
                <label className="explanation-label">
                  변동성 *
                  <span className="explanation-hint">예: 0.15 = 15%</span>
                </label>
                <input
                  type="number"
                  name="volatility"
                  value={formData.volatility}
                  onChange={handleInputChange}
                  step="0.001"
                  min="0"
                  required
                  placeholder="0.15"
                  className="explanation-input"
                />
              </div>

              {/* 위험 지표 */}
              <div className="explanation-form-group">
                <label className="explanation-label">
                  MDD (최대 낙폭) *
                  <span className="explanation-hint">예: -0.12 = -12%</span>
                </label>
                <input
                  type="number"
                  name="mdd"
                  value={formData.mdd}
                  onChange={handleInputChange}
                  step="0.001"
                  max="0"
                  required
                  placeholder="-0.12"
                  className="explanation-input"
                />
              </div>
              <div className="explanation-form-group">
                <label className="explanation-label">
                  샤프 비율
                  <span className="explanation-hint">선택사항</span>
                </label>
                <input
                  type="number"
                  name="sharpe"
                  value={formData.sharpe}
                  onChange={handleInputChange}
                  step="0.01"
                  placeholder="0.62"
                  className="explanation-input"
                />
              </div>

              {/* 기준 수익률 */}
              <div className="explanation-form-group">
                <label className="explanation-label">
                  무위험 수익률
                  <span className="explanation-hint">예: 0.035 = 3.5%</span>
                </label>
                <input
                  type="number"
                  name="rf_annual"
                  value={formData.rf_annual}
                  onChange={handleInputChange}
                  step="0.001"
                  placeholder="0.035"
                  className="explanation-input"
                />
              </div>

              {/* 벤치마크 비교 */}
              <div className="explanation-form-group">
                <label className="explanation-label">
                  벤치마크 이름
                  <span className="explanation-hint">선택사항</span>
                </label>
                <input
                  type="text"
                  name="benchmark_name"
                  value={formData.benchmark_name}
                  onChange={handleInputChange}
                  placeholder="KOSPI 200"
                  className="explanation-input"
                />
              </div>
              <div className="explanation-form-group">
                <label className="explanation-label">
                  벤치마크 수익률
                  <span className="explanation-hint">선택사항</span>
                </label>
                <input
                  type="number"
                  name="benchmark_return"
                  value={formData.benchmark_return}
                  onChange={handleInputChange}
                  step="0.001"
                  placeholder="0.065"
                  className="explanation-input"
                />
              </div>
            </div>

            {error && (
              <div className="explanation-error-message">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="explanation-submit-button"
            >
              {isLoading ? '분석 중...' : '해석 요청'}
            </button>
          </form>
        </div>
      )}

      {/* 결과 표시 */}
      {explanation && (
        <ExplanationResult
          data={explanation}
          onReset={() => setExplanation(null)}
          formData={formData}
        />
      )}
    </div>
  );
}

/**
 * 해석 결과 컴포넌트
 */
function ExplanationResult({ data, onReset, formData }) {
  const navigate = useNavigate();
  const {
    summary,
    performance_explanation,
    risk_explanation,
    risk_periods,
    comparison,
    disclaimer
  } = data;

  const [isDownloading, setIsDownloading] = useState(false);
  const [isPremiumDownloading, setIsPremiumDownloading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [downloadError, setDownloadError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // 요청 데이터 생성 헬퍼
  const getRequestData = () => ({
    cagr: parseFloat(formData.cagr),
    volatility: parseFloat(formData.volatility),
    mdd: parseFloat(formData.mdd),
    sharpe: formData.sharpe ? parseFloat(formData.sharpe) : null,
    start_date: formData.start_date,
    end_date: formData.end_date,
    rf_annual: parseFloat(formData.rf_annual) || 0,
    benchmark_name: formData.benchmark_name || null,
    benchmark_return: formData.benchmark_return ? parseFloat(formData.benchmark_return) : null,
  });

  // 기본 PDF 다운로드 핸들러
  const handleDownloadPDF = async () => {
    setIsDownloading(true);
    setDownloadError(null);

    try {
      await downloadExplanationPDF(getRequestData());
    } catch (err) {
      console.error('PDF download error:', err);
      setDownloadError('PDF 다운로드 중 오류가 발생했습니다.');
    } finally {
      setIsDownloading(false);
    }
  };

  // 프리미엄 PDF 다운로드 핸들러
  const handleDownloadPremiumPDF = async () => {
    setIsPremiumDownloading(true);
    setDownloadError(null);

    try {
      const requestData = {
        ...getRequestData(),
        report_title: '나의 포트폴리오 해석 리포트',
        total_return: null, // 누적 수익률 (선택)
      };

      await downloadPremiumReportPDF(requestData);
    } catch (err) {
      console.error('Premium PDF download error:', err);
      setDownloadError('프리미엄 PDF 다운로드 중 오류가 발생했습니다.');
    } finally {
      setIsPremiumDownloading(false);
    }
  };

  // 히스토리 저장 핸들러
  const handleSaveToHistory = async () => {
    setIsSaving(true);
    setDownloadError(null);
    setSaveSuccess(false);

    try {
      const requestData = {
        ...getRequestData(),
        report_title: `분석 리포트 (${formData.start_date} ~ ${formData.end_date})`,
      };

      await saveExplanationHistory(requestData);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error('Save history error:', err);
      setDownloadError('히스토리 저장 중 오류가 발생했습니다.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="explanation-result-section">
      {/* 요약 카드 */}
      <div className="explanation-summary-card">
        <h2 className="explanation-summary-title">요약</h2>
        <p className="explanation-summary-text">{summary}</p>
      </div>

      {/* 성과 해석 */}
      <div className="explanation-section">
        <h2 className="explanation-section-title">성과 지표 해석</h2>
        <div className="explanation-metrics-grid">
          {performance_explanation.map((item, index) => (
            <MetricCard key={index} metric={item} />
          ))}
        </div>
      </div>

      {/* 위험 설명 */}
      <div className="explanation-section">
        <h2 className="explanation-section-title">위험 분석</h2>
        <div className="explanation-risk-card">
          <p className="explanation-risk-text">{risk_explanation}</p>
        </div>

        {risk_periods && risk_periods.length > 0 && (
          <div className="explanation-risk-periods-section">
            <h3 className="explanation-sub-title">주요 위험 구간</h3>
            {risk_periods.map((period, index) => (
              <div
                key={index}
                className="explanation-risk-period-item"
                style={{ borderLeft: `4px solid ${getSeverityColor(period.severity)}` }}
              >
                <div className="explanation-risk-period-header">
                  <span
                    className="explanation-severity-badge"
                    style={{ backgroundColor: getSeverityColor(period.severity) }}
                  >
                    {getSeverityLabel(period.severity)}
                  </span>
                  {period.start_date && period.end_date && (
                    <span className="explanation-period-date">
                      {period.start_date} ~ {period.end_date}
                    </span>
                  )}
                </div>
                <p className="explanation-risk-period-desc">{period.description}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 비교 맥락 */}
      {comparison && (
        <div className="explanation-section">
          <h2 className="explanation-section-title">벤치마크 비교</h2>
          <div className="explanation-comparison-card">
            <div className="explanation-comparison-header">
              <span className="explanation-benchmark-name">{comparison.benchmark_name}</span>
              {comparison.benchmark_return !== null && (
                <span className="explanation-benchmark-return">
                  {(comparison.benchmark_return * 100).toFixed(1)}%
                </span>
              )}
            </div>
            <p className="explanation-comparison-text">{comparison.relative_performance}</p>
            <p className="explanation-comparison-note">{comparison.note}</p>
          </div>
        </div>
      )}

      {/* 면책 조항 */}
      <div className="explanation-disclaimer-section">
        <p className="explanation-disclaimer-text">{disclaimer}</p>
      </div>

      {/* 버튼 섹션 */}
      <div className="explanation-button-section">
        <button onClick={onReset} className="explanation-reset-button">
          새로운 분석
        </button>
        <button
          onClick={handleSaveToHistory}
          disabled={isSaving}
          className="explanation-save-button"
        >
          {isSaving ? '저장 중...' : '히스토리 저장'}
        </button>
      </div>

      {/* PDF 다운로드 섹션 */}
      <div className="explanation-pdf-section">
        <h3 className="explanation-pdf-section-title">PDF 리포트 다운로드</h3>
        <div className="explanation-pdf-button-group">
          <button
            onClick={handleDownloadPDF}
            disabled={isDownloading}
            className="explanation-download-button"
          >
            {isDownloading ? '생성 중...' : '기본 PDF'}
          </button>
          <button
            onClick={handleDownloadPremiumPDF}
            disabled={isPremiumDownloading}
            className="explanation-premium-button"
          >
            {isPremiumDownloading ? '생성 중...' : '프리미엄 PDF'}
          </button>
        </div>
        <p className="explanation-pdf-hint">
          프리미엄 PDF: 표지, 요약, 종합해석 포함
        </p>
      </div>

      {/* 알림 메시지 */}
      {saveSuccess && (
        <div className="explanation-success-message">
          히스토리에 저장되었습니다.
          <button
            onClick={() => navigate('/report-history')}
            className="explanation-inline-link"
          >
            리포트 히스토리 보기 →
          </button>
        </div>
      )}

      {downloadError && (
        <div className="explanation-download-error">
          {downloadError}
        </div>
      )}
    </div>
  );
}

/**
 * 개별 지표 카드 컴포넌트
 * UI 원칙: 숫자보다 설명 우선 - 사용자의 불안을 낮추는 정보 구조
 */
function MetricCard({ metric }) {
  const { metric: name, formatted_value, description, context, level } = metric;

  return (
    <div
      className="explanation-metric-card"
      style={{ borderLeft: `4px solid ${getLevelColor(level)}` }}
    >
      {/* 지표 이름 - 작게 */}
      <div className="explanation-metric-label-row">
        <span className="explanation-metric-label">{getMetricLabel(name)}</span>
        <span
          className="explanation-metric-value-small"
          style={{ color: getLevelColor(level) }}
        >
          {formatted_value}
        </span>
      </div>

      {/* 설명 - 가장 크고 눈에 띄게 (숫자보다 설명 우선) */}
      <p className="explanation-metric-description-main">{description}</p>

      {/* 맥락 설명 - 이해를 돕는 추가 정보 */}
      {context && (
        <div className="explanation-metric-context-box">
          <span className="explanation-context-icon">💡</span>
          <p className="explanation-metric-context-text">{context}</p>
        </div>
      )}
    </div>
  );
}

// 헬퍼 함수들
function getMetricLabel(metric) {
  const labels = {
    'CAGR': '연복리수익률 (CAGR)',
    'Volatility': '변동성',
    'MDD': '최대 낙폭 (MDD)',
    'Sharpe Ratio': '샤프 비율',
  };
  return labels[metric] || metric;
}

function getLevelColor(level) {
  const colors = {
    'very_low': '#e53935',
    'low': '#ff9800',
    'moderate': '#2196f3',
    'high': '#4caf50',
    'very_high': '#9c27b0',
  };
  return colors[level] || '#666';
}

function getSeverityColor(severity) {
  const colors = {
    'mild': '#ffc107',
    'moderate': '#ff9800',
    'severe': '#f44336',
  };
  return colors[severity] || '#666';
}

function getSeverityLabel(severity) {
  const labels = {
    'mild': '경미',
    'moderate': '보통',
    'severe': '심각',
  };
  return labels[severity] || severity;
}

export default PortfolioExplanationPage;
