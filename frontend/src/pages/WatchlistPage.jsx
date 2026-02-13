import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getWatchlist,
  removeFromWatchlist,
  getWatchlistAlertStatus,
  toggleWatchlistAlerts,
} from '../services/api';
import '../styles/Watchlist.css';

function gradeColor(grade) {
  if (!grade) return '#6b7280';
  if (['S', 'A+', 'A'].includes(grade)) return '#16a34a';
  if (['B+', 'B'].includes(grade)) return '#2563eb';
  if (['C+', 'C'].includes(grade)) return '#ea580c';
  return '#dc2626';
}

function WatchlistPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [alertEnabled, setAlertEnabled] = useState(false);
  const [alertLoading, setAlertLoading] = useState(false);
  const [isEmailVerified, setIsEmailVerified] = useState(false);
  const [removingTicker, setRemovingTicker] = useState(null);

  const fetchWatchlist = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getWatchlist();
      setItems(res.data.items || []);
    } catch (err) {
      setError(err.response?.data?.detail || '관심 종목을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAlertStatus = useCallback(async () => {
    try {
      const res = await getWatchlistAlertStatus();
      setAlertEnabled(res.data.enabled);
      setIsEmailVerified(res.data.is_email_verified);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchWatchlist();
    fetchAlertStatus();
  }, [fetchWatchlist, fetchAlertStatus]);

  const handleToggleAlert = async () => {
    setAlertLoading(true);
    try {
      const res = await toggleWatchlistAlerts();
      setAlertEnabled(res.data.enabled);
    } catch (err) {
      alert(err.response?.data?.detail || '알림 설정 변경에 실패했습니다.');
    } finally {
      setAlertLoading(false);
    }
  };

  const handleRemove = async (ticker, e) => {
    e.stopPropagation();
    if (removingTicker) return;
    setRemovingTicker(ticker);
    try {
      await removeFromWatchlist(ticker);
      setItems(prev => prev.filter(item => item.ticker !== ticker));
    } catch (err) {
      alert(err.response?.data?.detail || '삭제에 실패했습니다.');
    } finally {
      setRemovingTicker(null);
    }
  };

  return (
    <div className="watchlist-page">
      <div className="watchlist-header">
        <div>
          <h1>관심 종목</h1>
          <p className="watchlist-subtitle">Compass Score 변동을 추적하세요 (교육 목적 참고 정보)</p>
        </div>
        <div className="watchlist-alert-toggle">
          <label className="alert-switch-label">
            <span className="alert-label-text">
              점수 변동 이메일 알림
              {!isEmailVerified && <span className="alert-hint"> (이메일 인증 필요)</span>}
            </span>
            <button
              className={`alert-toggle-btn ${alertEnabled ? 'enabled' : ''}`}
              onClick={handleToggleAlert}
              disabled={alertLoading || !isEmailVerified}
              title={!isEmailVerified ? '이메일 인증 후 사용 가능합니다' : ''}
            >
              {alertEnabled ? 'ON' : 'OFF'}
            </button>
          </label>
        </div>
      </div>

      {error && <div className="watchlist-error">{error}</div>}

      {!loading && !error && items.length === 0 && (
        <div className="watchlist-empty">
          <p>관심 종목이 없습니다.</p>
          <button
            className="watchlist-go-screener"
            onClick={() => navigate('/screener')}
          >
            스크리너에서 추가하기
          </button>
        </div>
      )}

      {items.length > 0 && (
        <div className="watchlist-table-wrapper">
          <table className="watchlist-table">
            <thead>
              <tr>
                <th>종목명</th>
                <th>티커</th>
                <th>시장</th>
                <th>현재가</th>
                <th>Score</th>
                <th>등급</th>
                <th>변동</th>
                <th>요약</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => (
                <tr
                  key={item.ticker}
                  className="watchlist-row"
                  onClick={() => navigate(`/admin/stock-detail?ticker=${item.ticker}`)}
                >
                  <td className="stock-name">{item.name || '-'}</td>
                  <td className="stock-ticker">{item.ticker}</td>
                  <td>{item.market || '-'}</td>
                  <td className="num">
                    {item.current_price != null ? item.current_price.toLocaleString() : '-'}
                  </td>
                  <td>
                    <span
                      className="compass-badge"
                      style={{ borderColor: gradeColor(item.compass_grade) }}
                    >
                      {item.compass_score != null ? item.compass_score.toFixed(1) : '-'}
                    </span>
                  </td>
                  <td>
                    <span className="grade-tag" style={{ color: gradeColor(item.compass_grade) }}>
                      {item.compass_grade || '-'}
                    </span>
                  </td>
                  <td className="num">
                    {item.score_change != null ? (
                      <span className={item.score_change > 0 ? 'change-up' : item.score_change < 0 ? 'change-down' : ''}>
                        {item.score_change > 0 ? '+' : ''}{item.score_change}
                      </span>
                    ) : '-'}
                  </td>
                  <td className="summary-cell">{item.compass_summary || '-'}</td>
                  <td>
                    <button
                      className="watchlist-remove-btn"
                      onClick={(e) => handleRemove(item.ticker, e)}
                      disabled={removingTicker === item.ticker}
                      title="관심 종목에서 삭제"
                    >
                      {removingTicker === item.ticker ? '...' : '✕'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {loading && <div className="watchlist-loading">불러오는 중...</div>}

      <p className="watchlist-disclaimer">
        * 교육 목적 참고 정보이며 투자 권유가 아닙니다.
      </p>
    </div>
  );
}

export default WatchlistPage;
