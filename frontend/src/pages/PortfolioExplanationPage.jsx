import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  explainDirect,
  explainPortfolio,
  downloadExplanationPDF,
  downloadPremiumReportPDF,
  saveExplanationHistory
} from '../services/api';

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
    <div className="explanation-container" style={styles.container}>
      <div className="explanation-header" style={styles.header}>
        <h1 style={styles.title}>포트폴리오 성과 해석</h1>
        <p style={styles.subtitle}>
          성과 지표를 입력하면 이해하기 쉬운 설명을 제공합니다
        </p>
        <div style={styles.notice}>
          <span style={styles.noticeIcon}>📖</span>
          <span>
            본 서비스는 <strong>정보 제공 목적</strong>으로만 운영됩니다.
            투자 권유나 추천이 아닙니다.
          </span>
        </div>
      </div>

      {/* 입력 폼 */}
      {!explanation && (
        <div className="input-section" style={styles.inputSection}>
          <div style={styles.formHeader}>
            <h2 style={styles.sectionTitle}>성과 지표 입력</h2>
            <button
              type="button"
              onClick={fillExampleData}
              style={styles.exampleButton}
            >
              예시 데이터
            </button>
          </div>

          <form onSubmit={handleSubmit} style={styles.form}>
            <div style={styles.formGrid}>
              {/* 기간 설정 */}
              <div style={styles.formGroup}>
                <label style={styles.label}>시작일 *</label>
                <input
                  type="date"
                  name="start_date"
                  value={formData.start_date}
                  onChange={handleInputChange}
                  required
                  style={styles.input}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>종료일 *</label>
                <input
                  type="date"
                  name="end_date"
                  value={formData.end_date}
                  onChange={handleInputChange}
                  required
                  style={styles.input}
                />
              </div>

              {/* 수익률 지표 */}
              <div style={styles.formGroup}>
                <label style={styles.label}>
                  CAGR (연복리수익률) *
                  <span style={styles.hint}>예: 0.085 = 8.5%</span>
                </label>
                <input
                  type="number"
                  name="cagr"
                  value={formData.cagr}
                  onChange={handleInputChange}
                  step="0.001"
                  required
                  placeholder="0.085"
                  style={styles.input}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>
                  변동성 *
                  <span style={styles.hint}>예: 0.15 = 15%</span>
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
                  style={styles.input}
                />
              </div>

              {/* 위험 지표 */}
              <div style={styles.formGroup}>
                <label style={styles.label}>
                  MDD (최대 낙폭) *
                  <span style={styles.hint}>예: -0.12 = -12%</span>
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
                  style={styles.input}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>
                  샤프 비율
                  <span style={styles.hint}>선택사항</span>
                </label>
                <input
                  type="number"
                  name="sharpe"
                  value={formData.sharpe}
                  onChange={handleInputChange}
                  step="0.01"
                  placeholder="0.62"
                  style={styles.input}
                />
              </div>

              {/* 기준 수익률 */}
              <div style={styles.formGroup}>
                <label style={styles.label}>
                  무위험 수익률
                  <span style={styles.hint}>예: 0.035 = 3.5%</span>
                </label>
                <input
                  type="number"
                  name="rf_annual"
                  value={formData.rf_annual}
                  onChange={handleInputChange}
                  step="0.001"
                  placeholder="0.035"
                  style={styles.input}
                />
              </div>

              {/* 벤치마크 비교 */}
              <div style={styles.formGroup}>
                <label style={styles.label}>
                  벤치마크 이름
                  <span style={styles.hint}>선택사항</span>
                </label>
                <input
                  type="text"
                  name="benchmark_name"
                  value={formData.benchmark_name}
                  onChange={handleInputChange}
                  placeholder="KOSPI 200"
                  style={styles.input}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>
                  벤치마크 수익률
                  <span style={styles.hint}>선택사항</span>
                </label>
                <input
                  type="number"
                  name="benchmark_return"
                  value={formData.benchmark_return}
                  onChange={handleInputChange}
                  step="0.001"
                  placeholder="0.065"
                  style={styles.input}
                />
              </div>
            </div>

            {error && (
              <div style={styles.errorMessage}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              style={{
                ...styles.submitButton,
                opacity: isLoading ? 0.7 : 1,
              }}
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
    <div className="result-section" style={styles.resultSection}>
      {/* 요약 카드 */}
      <div style={styles.summaryCard}>
        <h2 style={styles.summaryTitle}>요약</h2>
        <p style={styles.summaryText}>{summary}</p>
      </div>

      {/* 성과 해석 */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>성과 지표 해석</h2>
        <div style={styles.metricsGrid}>
          {performance_explanation.map((item, index) => (
            <MetricCard key={index} metric={item} />
          ))}
        </div>
      </div>

      {/* 위험 설명 */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>위험 분석</h2>
        <div style={styles.riskCard}>
          <p style={styles.riskText}>{risk_explanation}</p>
        </div>

        {risk_periods && risk_periods.length > 0 && (
          <div style={styles.riskPeriodsSection}>
            <h3 style={styles.subTitle}>주요 위험 구간</h3>
            {risk_periods.map((period, index) => (
              <div key={index} style={{
                ...styles.riskPeriodItem,
                borderLeft: `4px solid ${getSeverityColor(period.severity)}`
              }}>
                <div style={styles.riskPeriodHeader}>
                  <span style={{
                    ...styles.severityBadge,
                    backgroundColor: getSeverityColor(period.severity)
                  }}>
                    {getSeverityLabel(period.severity)}
                  </span>
                  {period.start_date && period.end_date && (
                    <span style={styles.periodDate}>
                      {period.start_date} ~ {period.end_date}
                    </span>
                  )}
                </div>
                <p style={styles.riskPeriodDesc}>{period.description}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 비교 맥락 */}
      {comparison && (
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>벤치마크 비교</h2>
          <div style={styles.comparisonCard}>
            <div style={styles.comparisonHeader}>
              <span style={styles.benchmarkName}>{comparison.benchmark_name}</span>
              {comparison.benchmark_return !== null && (
                <span style={styles.benchmarkReturn}>
                  {(comparison.benchmark_return * 100).toFixed(1)}%
                </span>
              )}
            </div>
            <p style={styles.comparisonText}>{comparison.relative_performance}</p>
            <p style={styles.comparisonNote}>{comparison.note}</p>
          </div>
        </div>
      )}

      {/* 면책 조항 */}
      <div style={styles.disclaimerSection}>
        <p style={styles.disclaimerText}>{disclaimer}</p>
      </div>

      {/* 버튼 섹션 */}
      <div style={styles.buttonSection}>
        <button onClick={onReset} style={styles.resetButton}>
          새로운 분석
        </button>
        <button
          onClick={handleSaveToHistory}
          disabled={isSaving}
          style={{
            ...styles.saveButton,
            opacity: isSaving ? 0.7 : 1,
          }}
        >
          {isSaving ? '저장 중...' : '히스토리 저장'}
        </button>
      </div>

      {/* PDF 다운로드 섹션 */}
      <div style={styles.pdfSection}>
        <h3 style={styles.pdfSectionTitle}>PDF 리포트 다운로드</h3>
        <div style={styles.pdfButtonGroup}>
          <button
            onClick={handleDownloadPDF}
            disabled={isDownloading}
            style={{
              ...styles.downloadButton,
              opacity: isDownloading ? 0.7 : 1,
            }}
          >
            {isDownloading ? '생성 중...' : '기본 PDF'}
          </button>
          <button
            onClick={handleDownloadPremiumPDF}
            disabled={isPremiumDownloading}
            style={{
              ...styles.premiumButton,
              opacity: isPremiumDownloading ? 0.7 : 1,
            }}
          >
            {isPremiumDownloading ? '생성 중...' : '프리미엄 PDF'}
          </button>
        </div>
        <p style={styles.pdfHint}>
          프리미엄 PDF: 표지, 요약, 종합해석 포함
        </p>
      </div>

      {/* 알림 메시지 */}
      {saveSuccess && (
        <div style={styles.successMessage}>
          히스토리에 저장되었습니다.
        </div>
      )}

      {downloadError && (
        <div style={styles.downloadError}>
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
    <div style={{
      ...styles.metricCard,
      borderLeft: `4px solid ${getLevelColor(level)}`,
      borderTop: 'none'
    }}>
      {/* 지표 이름 - 작게 */}
      <div style={styles.metricLabelRow}>
        <span style={styles.metricLabel}>{getMetricLabel(name)}</span>
        <span style={{
          ...styles.metricValueSmall,
          color: getLevelColor(level)
        }}>
          {formatted_value}
        </span>
      </div>

      {/* 설명 - 가장 크고 눈에 띄게 (숫자보다 설명 우선) */}
      <p style={styles.metricDescriptionMain}>{description}</p>

      {/* 맥락 설명 - 이해를 돕는 추가 정보 */}
      {context && (
        <div style={styles.metricContextBox}>
          <span style={styles.contextIcon}>💡</span>
          <p style={styles.metricContextText}>{context}</p>
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

// 스타일
const styles = {
  container: {
    maxWidth: '900px',
    margin: '0 auto',
    padding: '2rem',
  },
  header: {
    textAlign: 'center',
    marginBottom: '2rem',
  },
  title: {
    fontSize: '2rem',
    fontWeight: 'bold',
    color: '#333',
    marginBottom: '0.5rem',
  },
  subtitle: {
    color: '#666',
    fontSize: '1.1rem',
    marginBottom: '1rem',
  },
  notice: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
    background: 'linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%)',
    padding: '0.75rem 1.5rem',
    borderRadius: '8px',
    border: '1px solid #bbdefb',
    fontSize: '0.9rem',
    color: '#1565c0',
  },
  noticeIcon: {
    fontSize: '1.2rem',
  },
  inputSection: {
    background: '#fff',
    borderRadius: '12px',
    padding: '2rem',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  },
  formHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1.5rem',
  },
  sectionTitle: {
    fontSize: '1.3rem',
    fontWeight: 'bold',
    color: '#333',
    margin: 0,
  },
  exampleButton: {
    padding: '0.5rem 1rem',
    background: '#f5f5f5',
    border: '1px solid #ddd',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '0.9rem',
    color: '#666',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.5rem',
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
    gap: '1rem',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
  label: {
    fontSize: '0.9rem',
    fontWeight: '500',
    color: '#333',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.25rem',
  },
  hint: {
    fontSize: '0.75rem',
    color: '#888',
    fontWeight: 'normal',
  },
  input: {
    padding: '0.75rem',
    border: '1px solid #ddd',
    borderRadius: '6px',
    fontSize: '1rem',
    transition: 'border-color 0.2s',
  },
  errorMessage: {
    padding: '1rem',
    background: '#ffebee',
    color: '#c62828',
    borderRadius: '6px',
    fontSize: '0.9rem',
  },
  submitButton: {
    padding: '1rem 2rem',
    background: '#2196f3',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '1rem',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  resultSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.5rem',
  },
  summaryCard: {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    borderRadius: '12px',
    padding: '2rem',
    color: '#fff',
  },
  summaryTitle: {
    fontSize: '1.3rem',
    fontWeight: 'bold',
    marginBottom: '1rem',
    margin: '0 0 1rem 0',
  },
  summaryText: {
    fontSize: '1.1rem',
    lineHeight: '1.6',
    margin: 0,
  },
  section: {
    background: '#fff',
    borderRadius: '12px',
    padding: '1.5rem',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '1rem',
    marginTop: '1rem',
  },
  metricCard: {
    background: '#fff',
    borderRadius: '12px',
    padding: '1.5rem',
    boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
  },
  // 숫자보다 설명 우선 - 새로운 레이아웃
  metricLabelRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1rem',
    paddingBottom: '0.75rem',
    borderBottom: '1px solid #eee',
  },
  metricLabel: {
    fontSize: '0.85rem',
    color: '#888',
    fontWeight: '500',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  metricValueSmall: {
    fontSize: '0.9rem',
    fontWeight: '600',
    padding: '0.25rem 0.5rem',
    borderRadius: '4px',
    background: '#f5f5f5',
  },
  // 설명을 가장 크고 눈에 띄게
  metricDescriptionMain: {
    fontSize: '1.05rem',
    color: '#333',
    lineHeight: '1.7',
    margin: '0 0 1rem 0',
    fontWeight: '400',
  },
  // 맥락 설명 박스
  metricContextBox: {
    display: 'flex',
    gap: '0.5rem',
    padding: '1rem',
    background: '#f8f9fa',
    borderRadius: '8px',
    alignItems: 'flex-start',
  },
  contextIcon: {
    fontSize: '1rem',
    flexShrink: 0,
  },
  metricContextText: {
    fontSize: '0.85rem',
    color: '#666',
    lineHeight: '1.5',
    margin: 0,
  },
  // 레거시 스타일 유지 (하위 호환)
  metricHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '0.75rem',
  },
  metricName: {
    fontWeight: '600',
    color: '#333',
    fontSize: '0.95rem',
  },
  metricValue: {
    fontWeight: 'bold',
    fontSize: '1.2rem',
  },
  metricDescription: {
    fontSize: '0.9rem',
    color: '#555',
    lineHeight: '1.5',
    margin: '0 0 0.75rem 0',
  },
  metricContext: {
    fontSize: '0.8rem',
    color: '#888',
    lineHeight: '1.4',
    margin: 0,
    padding: '0.75rem',
    background: '#fff',
    borderRadius: '4px',
  },
  riskCard: {
    background: '#fff3e0',
    borderRadius: '8px',
    padding: '1.25rem',
    marginTop: '1rem',
  },
  riskText: {
    fontSize: '0.95rem',
    color: '#e65100',
    lineHeight: '1.6',
    margin: 0,
  },
  riskPeriodsSection: {
    marginTop: '1.5rem',
  },
  subTitle: {
    fontSize: '1rem',
    fontWeight: '600',
    color: '#333',
    marginBottom: '1rem',
  },
  riskPeriodItem: {
    background: '#f8f9fa',
    borderRadius: '8px',
    padding: '1rem',
    marginBottom: '0.75rem',
  },
  riskPeriodHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    marginBottom: '0.5rem',
  },
  severityBadge: {
    padding: '0.25rem 0.75rem',
    borderRadius: '4px',
    color: '#fff',
    fontSize: '0.75rem',
    fontWeight: '500',
  },
  periodDate: {
    fontSize: '0.85rem',
    color: '#666',
  },
  riskPeriodDesc: {
    fontSize: '0.9rem',
    color: '#555',
    margin: 0,
  },
  comparisonCard: {
    background: '#e8f5e9',
    borderRadius: '8px',
    padding: '1.25rem',
    marginTop: '1rem',
  },
  comparisonHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '0.75rem',
  },
  benchmarkName: {
    fontWeight: '600',
    color: '#2e7d32',
    fontSize: '1rem',
  },
  benchmarkReturn: {
    fontWeight: 'bold',
    color: '#2e7d32',
    fontSize: '1.1rem',
  },
  comparisonText: {
    fontSize: '0.95rem',
    color: '#1b5e20',
    lineHeight: '1.5',
    margin: '0 0 0.5rem 0',
  },
  comparisonNote: {
    fontSize: '0.8rem',
    color: '#558b2f',
    margin: 0,
  },
  disclaimerSection: {
    background: '#fafafa',
    borderRadius: '8px',
    padding: '1.25rem',
    border: '1px solid #eee',
  },
  disclaimerText: {
    fontSize: '0.85rem',
    color: '#666',
    lineHeight: '1.6',
    margin: 0,
  },
  buttonSection: {
    display: 'flex',
    justifyContent: 'center',
    gap: '1rem',
    marginTop: '1rem',
  },
  resetButton: {
    padding: '0.75rem 2rem',
    background: '#f5f5f5',
    color: '#333',
    border: '1px solid #ddd',
    borderRadius: '8px',
    fontSize: '1rem',
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  downloadButton: {
    padding: '0.75rem 1.5rem',
    background: '#667eea',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '0.95rem',
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  premiumButton: {
    padding: '0.75rem 1.5rem',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '0.95rem',
    cursor: 'pointer',
    transition: 'transform 0.2s',
    fontWeight: '500',
  },
  saveButton: {
    padding: '0.75rem 2rem',
    background: '#4caf50',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '1rem',
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  pdfSection: {
    marginTop: '1.5rem',
    padding: '1.25rem',
    background: '#f8f9fa',
    borderRadius: '12px',
    textAlign: 'center',
  },
  pdfSectionTitle: {
    fontSize: '1rem',
    fontWeight: '600',
    color: '#333',
    marginBottom: '1rem',
    margin: '0 0 1rem 0',
  },
  pdfButtonGroup: {
    display: 'flex',
    justifyContent: 'center',
    gap: '1rem',
    flexWrap: 'wrap',
  },
  pdfHint: {
    marginTop: '0.75rem',
    fontSize: '0.8rem',
    color: '#888',
    margin: '0.75rem 0 0 0',
  },
  successMessage: {
    marginTop: '1rem',
    padding: '0.75rem',
    background: '#e8f5e9',
    color: '#2e7d32',
    borderRadius: '6px',
    fontSize: '0.9rem',
    textAlign: 'center',
  },
  downloadError: {
    marginTop: '1rem',
    padding: '0.75rem',
    background: '#ffebee',
    color: '#c62828',
    borderRadius: '6px',
    fontSize: '0.9rem',
    textAlign: 'center',
  },
};

export default PortfolioExplanationPage;
