import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getExplanationHistory,
  deleteExplanationHistory,
  downloadPremiumReportPDF
} from '../services/api';
import Disclaimer from '../components/Disclaimer';
import '../styles/ReportHistory.css';

/**
 * Phase 3-B: 리포트 히스토리 관리 페이지
 *
 * - 과거 리포트 목록 조회
 * - 리포트 상세 보기
 * - PDF 다시 다운로드
 * - 리포트 삭제
 */
function ReportHistoryPage() {
  const navigate = useNavigate();
  const [histories, setHistories] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [selectedHistory, setSelectedHistory] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isDownloading, setIsDownloading] = useState(null);

  const PAGE_SIZE = 10;

  // 히스토리 목록 로드
  useEffect(() => {
    loadHistories();
  }, [page]);

  const loadHistories = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await getExplanationHistory(page * PAGE_SIZE, PAGE_SIZE);
      setHistories(response.data.items);
      setTotal(response.data.total);
    } catch (err) {
      console.error('Load history error:', err);
      setError('히스토리를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  // 히스토리 삭제
  const handleDelete = async (historyId) => {
    if (!window.confirm('이 리포트를 삭제하시겠습니까?')) return;

    setIsDeleting(true);
    try {
      await deleteExplanationHistory(historyId);
      setHistories(prev => prev.filter(h => h.history_id !== historyId));
      setTotal(prev => prev - 1);
      if (selectedHistory?.history_id === historyId) {
        setSelectedHistory(null);
      }
    } catch (err) {
      console.error('Delete error:', err);
      setError('삭제 중 오류가 발생했습니다.');
    } finally {
      setIsDeleting(false);
    }
  };

  // PDF 다운로드
  const handleDownloadPDF = async (history) => {
    setIsDownloading(history.history_id);

    try {
      const metrics = history.input_metrics;
      const requestData = {
        cagr: metrics.cagr,
        volatility: metrics.volatility,
        mdd: metrics.mdd,
        sharpe: metrics.sharpe,
        start_date: history.period_start.split('T')[0],
        end_date: history.period_end.split('T')[0],
        rf_annual: metrics.rf_annual || 0,
        benchmark_name: metrics.benchmark_name,
        benchmark_return: metrics.benchmark_return,
        report_title: history.report_title || '나의 포트폴리오 해석 리포트',
      };

      await downloadPremiumReportPDF(requestData);
    } catch (err) {
      console.error('Download error:', err);
      setError('PDF 다운로드 중 오류가 발생했습니다.');
    } finally {
      setIsDownloading(null);
    }
  };

  // 날짜 포맷
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  // 지표 포맷
  const formatMetric = (value, type) => {
    if (value === null || value === undefined) return '-';
    if (type === 'percent') return `${(value * 100).toFixed(1)}%`;
    if (type === 'number') return value.toFixed(2);
    return value;
  };

  return (
    <div className="rh-container">
      <Disclaimer type="portfolio" />

      <div className="rh-header">
        <h1 className="rh-title">📊 리포트 히스토리</h1>
        <p className="rh-subtitle">
          저장된 성과 해석 리포트를 관리하세요
        </p>
        <button
          onClick={() => navigate('/analysis')}
          className="rh-new-report-button"
        >
          + 새 분석 시작
        </button>
      </div>

      {error && (
        <div className="rh-error-message">{error}</div>
      )}

      {isLoading ? (
        <div className="rh-loading">로딩 중...</div>
      ) : histories.length === 0 ? (
        <div className="rh-empty-state">
          <p className="rh-empty-text">저장된 리포트가 없습니다.</p>
          <button
            onClick={() => navigate('/analysis')}
            className="rh-empty-button"
          >
            첫 분석 시작하기
          </button>
        </div>
      ) : (
        <>
          {/* 히스토리 목록 */}
          <div className="rh-list-container">
            {histories.map((history) => (
              <div
                key={history.history_id}
                className={`rh-history-card ${selectedHistory?.history_id === history.history_id ? 'selected' : ''}`}
                onClick={() => setSelectedHistory(history)}
              >
                <div className="rh-card-header">
                  <h3 className="rh-card-title">
                    {history.report_title || '분석 리포트'}
                  </h3>
                  <span className="rh-card-date">
                    {formatDate(history.created_at)}
                  </span>
                </div>

                <div className="rh-card-period">
                  <span className="rh-period-label">분석 기간:</span>
                  <span>{formatDate(history.period_start)} ~ {formatDate(history.period_end)}</span>
                </div>

                <div className="rh-card-metrics">
                  <div className="rh-metric-item">
                    <span className="rh-metric-label">CAGR</span>
                    <span className="rh-metric-value">
                      {formatMetric(history.input_metrics?.cagr, 'percent')}
                    </span>
                  </div>
                  <div className="rh-metric-item">
                    <span className="rh-metric-label">변동성</span>
                    <span className="rh-metric-value">
                      {formatMetric(history.input_metrics?.volatility, 'percent')}
                    </span>
                  </div>
                  <div className="rh-metric-item">
                    <span className="rh-metric-label">MDD</span>
                    <span className="rh-metric-value">
                      {formatMetric(history.input_metrics?.mdd, 'percent')}
                    </span>
                  </div>
                </div>

                <div className="rh-card-actions">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDownloadPDF(history);
                    }}
                    disabled={isDownloading === history.history_id}
                    className="rh-download-btn"
                  >
                    {isDownloading === history.history_id ? '생성 중...' : 'PDF 다운로드'}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(history.history_id);
                    }}
                    disabled={isDeleting}
                    className="rh-delete-btn"
                  >
                    삭제
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* 페이지네이션 */}
          {total > PAGE_SIZE && (
            <div className="rh-pagination">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="rh-page-btn"
              >
                이전
              </button>
              <span className="rh-page-info">
                {page + 1} / {Math.ceil(total / PAGE_SIZE)}
              </span>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={(page + 1) * PAGE_SIZE >= total}
                className="rh-page-btn"
              >
                다음
              </button>
            </div>
          )}

          {/* 선택된 리포트 상세 */}
          {selectedHistory && (
            <div className="rh-detail-section">
              <h2 className="rh-detail-title">리포트 상세</h2>

              <div className="rh-detail-summary">
                <h3 className="rh-detail-subtitle">요약</h3>
                <p className="rh-detail-text">
                  {selectedHistory.explanation_result?.summary || '요약 없음'}
                </p>
              </div>

              <div className="rh-detail-metrics">
                <h3 className="rh-detail-subtitle">지표 해석</h3>
                {selectedHistory.explanation_result?.performance_explanation?.map((exp, idx) => (
                  <div key={idx} className="rh-exp-item">
                    <div className="rh-exp-header">
                      <span className="rh-exp-metric">{exp.metric}</span>
                      <span className="rh-exp-value">{exp.formatted_value}</span>
                    </div>
                    <p className="rh-exp-desc">{exp.description}</p>
                  </div>
                ))}
              </div>

              <div className="rh-detail-actions">
                <button
                  onClick={() => handleDownloadPDF(selectedHistory)}
                  className="rh-detail-download-btn"
                >
                  프리미엄 PDF 다운로드
                </button>
                <button
                  onClick={() => navigate('/analysis', {
                    state: {
                      metrics: selectedHistory.input_metrics
                    }
                  })}
                  className="rh-reanalyze-btn"
                >
                  이 데이터로 다시 분석하기 →
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default ReportHistoryPage;
