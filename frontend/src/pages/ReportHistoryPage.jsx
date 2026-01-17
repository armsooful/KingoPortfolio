import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getExplanationHistory,
  deleteExplanationHistory,
  downloadPremiumReportPDF
} from '../services/api';

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
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>리포트 히스토리</h1>
        <p style={styles.subtitle}>
          저장된 성과 해석 리포트를 관리하세요
        </p>
        <button
          onClick={() => navigate('/analysis')}
          style={styles.newReportButton}
        >
          + 새 분석 시작
        </button>
      </div>

      {error && (
        <div style={styles.errorMessage}>{error}</div>
      )}

      {isLoading ? (
        <div style={styles.loading}>로딩 중...</div>
      ) : histories.length === 0 ? (
        <div style={styles.emptyState}>
          <p style={styles.emptyText}>저장된 리포트가 없습니다.</p>
          <button
            onClick={() => navigate('/analysis')}
            style={styles.emptyButton}
          >
            첫 분석 시작하기
          </button>
        </div>
      ) : (
        <>
          {/* 히스토리 목록 */}
          <div style={styles.listContainer}>
            {histories.map((history) => (
              <div
                key={history.history_id}
                style={{
                  ...styles.historyCard,
                  borderColor: selectedHistory?.history_id === history.history_id
                    ? '#667eea' : '#e0e0e0'
                }}
                onClick={() => setSelectedHistory(history)}
              >
                <div style={styles.cardHeader}>
                  <h3 style={styles.cardTitle}>
                    {history.report_title || '분석 리포트'}
                  </h3>
                  <span style={styles.cardDate}>
                    {formatDate(history.created_at)}
                  </span>
                </div>

                <div style={styles.cardPeriod}>
                  <span style={styles.periodLabel}>분석 기간:</span>
                  <span>{formatDate(history.period_start)} ~ {formatDate(history.period_end)}</span>
                </div>

                <div style={styles.cardMetrics}>
                  <div style={styles.metricItem}>
                    <span style={styles.metricLabel}>CAGR</span>
                    <span style={styles.metricValue}>
                      {formatMetric(history.input_metrics?.cagr, 'percent')}
                    </span>
                  </div>
                  <div style={styles.metricItem}>
                    <span style={styles.metricLabel}>변동성</span>
                    <span style={styles.metricValue}>
                      {formatMetric(history.input_metrics?.volatility, 'percent')}
                    </span>
                  </div>
                  <div style={styles.metricItem}>
                    <span style={styles.metricLabel}>MDD</span>
                    <span style={styles.metricValue}>
                      {formatMetric(history.input_metrics?.mdd, 'percent')}
                    </span>
                  </div>
                </div>

                <div style={styles.cardActions}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDownloadPDF(history);
                    }}
                    disabled={isDownloading === history.history_id}
                    style={styles.downloadBtn}
                  >
                    {isDownloading === history.history_id ? '생성 중...' : 'PDF 다운로드'}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(history.history_id);
                    }}
                    disabled={isDeleting}
                    style={styles.deleteBtn}
                  >
                    삭제
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* 페이지네이션 */}
          {total > PAGE_SIZE && (
            <div style={styles.pagination}>
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                style={styles.pageBtn}
              >
                이전
              </button>
              <span style={styles.pageInfo}>
                {page + 1} / {Math.ceil(total / PAGE_SIZE)}
              </span>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={(page + 1) * PAGE_SIZE >= total}
                style={styles.pageBtn}
              >
                다음
              </button>
            </div>
          )}

          {/* 선택된 리포트 상세 */}
          {selectedHistory && (
            <div style={styles.detailSection}>
              <h2 style={styles.detailTitle}>리포트 상세</h2>

              <div style={styles.detailSummary}>
                <h3 style={styles.detailSubtitle}>요약</h3>
                <p style={styles.detailText}>
                  {selectedHistory.explanation_result?.summary || '요약 없음'}
                </p>
              </div>

              <div style={styles.detailMetrics}>
                <h3 style={styles.detailSubtitle}>지표 해석</h3>
                {selectedHistory.explanation_result?.performance_explanation?.map((exp, idx) => (
                  <div key={idx} style={styles.expItem}>
                    <div style={styles.expHeader}>
                      <span style={styles.expMetric}>{exp.metric}</span>
                      <span style={styles.expValue}>{exp.formatted_value}</span>
                    </div>
                    <p style={styles.expDesc}>{exp.description}</p>
                  </div>
                ))}
              </div>

              <div style={styles.detailActions}>
                <button
                  onClick={() => handleDownloadPDF(selectedHistory)}
                  style={styles.detailDownloadBtn}
                >
                  프리미엄 PDF 다운로드
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

const styles = {
  container: {
    maxWidth: '1000px',
    margin: '0 auto',
    padding: '2rem',
  },
  header: {
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
    fontSize: '1rem',
    marginBottom: '1rem',
  },
  newReportButton: {
    padding: '0.75rem 1.5rem',
    background: '#667eea',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '1rem',
    cursor: 'pointer',
  },
  errorMessage: {
    padding: '1rem',
    background: '#ffebee',
    color: '#c62828',
    borderRadius: '8px',
    marginBottom: '1rem',
  },
  loading: {
    textAlign: 'center',
    padding: '3rem',
    color: '#666',
  },
  emptyState: {
    textAlign: 'center',
    padding: '4rem 2rem',
    background: '#f8f9fa',
    borderRadius: '12px',
  },
  emptyText: {
    fontSize: '1.1rem',
    color: '#666',
    marginBottom: '1.5rem',
  },
  emptyButton: {
    padding: '0.75rem 2rem',
    background: '#667eea',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '1rem',
    cursor: 'pointer',
  },
  listContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  historyCard: {
    background: '#fff',
    borderRadius: '12px',
    padding: '1.5rem',
    border: '2px solid #e0e0e0',
    cursor: 'pointer',
    transition: 'border-color 0.2s, box-shadow 0.2s',
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '0.75rem',
  },
  cardTitle: {
    fontSize: '1.1rem',
    fontWeight: '600',
    color: '#333',
    margin: 0,
  },
  cardDate: {
    fontSize: '0.85rem',
    color: '#888',
  },
  cardPeriod: {
    fontSize: '0.9rem',
    color: '#666',
    marginBottom: '1rem',
  },
  periodLabel: {
    fontWeight: '500',
    marginRight: '0.5rem',
  },
  cardMetrics: {
    display: 'flex',
    gap: '2rem',
    marginBottom: '1rem',
    flexWrap: 'wrap',
  },
  metricItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.25rem',
  },
  metricLabel: {
    fontSize: '0.75rem',
    color: '#888',
    textTransform: 'uppercase',
  },
  metricValue: {
    fontSize: '1rem',
    fontWeight: '600',
    color: '#333',
  },
  cardActions: {
    display: 'flex',
    gap: '0.75rem',
    marginTop: '0.5rem',
  },
  downloadBtn: {
    padding: '0.5rem 1rem',
    background: '#667eea',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '0.85rem',
    cursor: 'pointer',
  },
  deleteBtn: {
    padding: '0.5rem 1rem',
    background: '#fff',
    color: '#dc3545',
    border: '1px solid #dc3545',
    borderRadius: '6px',
    fontSize: '0.85rem',
    cursor: 'pointer',
  },
  pagination: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '1rem',
    marginTop: '2rem',
  },
  pageBtn: {
    padding: '0.5rem 1rem',
    background: '#f5f5f5',
    border: '1px solid #ddd',
    borderRadius: '6px',
    cursor: 'pointer',
  },
  pageInfo: {
    color: '#666',
  },
  detailSection: {
    marginTop: '2rem',
    padding: '1.5rem',
    background: '#f8f9fa',
    borderRadius: '12px',
  },
  detailTitle: {
    fontSize: '1.3rem',
    fontWeight: 'bold',
    color: '#333',
    marginBottom: '1.5rem',
    margin: '0 0 1.5rem 0',
  },
  detailSummary: {
    marginBottom: '1.5rem',
  },
  detailSubtitle: {
    fontSize: '1rem',
    fontWeight: '600',
    color: '#333',
    marginBottom: '0.75rem',
    margin: '0 0 0.75rem 0',
  },
  detailText: {
    color: '#555',
    lineHeight: '1.6',
    margin: 0,
  },
  detailMetrics: {
    marginBottom: '1.5rem',
  },
  expItem: {
    background: '#fff',
    padding: '1rem',
    borderRadius: '8px',
    marginBottom: '0.75rem',
  },
  expHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '0.5rem',
  },
  expMetric: {
    fontWeight: '600',
    color: '#667eea',
  },
  expValue: {
    fontWeight: '500',
    color: '#333',
  },
  expDesc: {
    fontSize: '0.9rem',
    color: '#555',
    lineHeight: '1.5',
    margin: 0,
  },
  detailActions: {
    display: 'flex',
    justifyContent: 'center',
  },
  detailDownloadBtn: {
    padding: '0.75rem 2rem',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '1rem',
    cursor: 'pointer',
    fontWeight: '500',
  },
};

export default ReportHistoryPage;
