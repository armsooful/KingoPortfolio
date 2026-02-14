import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import api, { getMarketSubscriptionStatus, subscribeMarketEmail, getWatchlist, getProfileCompletionStatus } from '../services/api';
import ProfileCompletionModal from '../components/ProfileCompletionModal';
import '../styles/MarketDashboard.css';

/* ── helpers ── */

const gradeColor = (grade) => {
  if (!grade) return '#6b7280';
  const g = grade.charAt(0).toUpperCase();
  if (g === 'S' || g === 'A') return '#16a34a';
  if (g === 'B') return '#2563eb';
  if (g === 'C') return '#d97706';
  return '#dc2626';
};

const axisColors = { financial: '#4caf50', valuation: '#2196f3', technical: '#ff9800', risk: '#9c27b0' };

/* SVG sparkline from 8 data points */
function Sparkline({ points, color }) {
  if (!points || points.length < 2) return null;
  const h = 40;
  const w = 120;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const coords = points.map((v, i) => {
    const x = (i / (points.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    return `${x},${y}`;
  });
  const polyline = coords.join(' ');
  const polygon = `${polyline} ${w},${h} 0,${h}`;
  const id = `sg-${color.replace('#', '')}`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="kpi-sparkline-svg">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.15" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon fill={`url(#${id})`} points={polygon} />
      <polyline fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" points={polyline} />
    </svg>
  );
}

/* ── Skeleton loading view ── */
function DashboardSkeleton() {
  return (
    <div className="dashboard-redesign">
      <div className="dash-header">
        <div>
          <h1><span className="dash-brand">Foresto Compass</span> 시장 현황</h1>
          <div className="dash-date">데이터 불러오는 중...</div>
        </div>
      </div>

      <div className="kpi-grid">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="kpi-card skel-kpi">
            <div className="skeleton skel-text" style={{ width: '40%' }} />
            <div className="skeleton skel-title" style={{ width: '70%' }} />
            <div className="skeleton skel-text" style={{ width: '50%' }} />
            <div className="skeleton skel-chart" />
          </div>
        ))}
      </div>

      <div className="skel-ai-block">
        <div className="skeleton skel-text" style={{ width: '30%', marginBottom: 12 }} />
        <div className="skeleton skel-text" style={{ width: '90%' }} />
        <div className="skeleton skel-text" style={{ width: '75%' }} />
        <div className="skeleton skel-text" style={{ width: '60%' }} />
      </div>

      <div className="two-col">
        {[1, 2].map((i) => (
          <div key={i} className="section-card">
            <div className="skeleton skel-title" style={{ marginBottom: 16 }} />
            {[1, 2, 3, 4, 5].map((j) => (
              <div key={j} className="skeleton" style={{ height: 40, marginBottom: 8 }} />
            ))}
          </div>
        ))}
      </div>

      <div className="section-card" style={{ marginBottom: 24 }}>
        <div className="skeleton skel-title" style={{ marginBottom: 16 }} />
        <div className="watchlist-grid">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="wl-card" style={{ padding: 20 }}>
              <div className="skeleton" style={{ height: 16, width: '50%', marginBottom: 8 }} />
              <div className="skeleton" style={{ height: 12, width: '35%', marginBottom: 16 }} />
              {[1, 2, 3, 4].map((j) => (
                <div key={j} className="skeleton" style={{ height: 4, marginBottom: 4 }} />
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Main component ── */
function MarketDashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [marketData, setMarketData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [emailSub, setEmailSub] = useState(null);
  const [subLoading, setSubLoading] = useState(false);
  const [watchlistItems, setWatchlistItems] = useState([]);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [profileIncomplete, setProfileIncomplete] = useState(false);
  const [profilePercent, setProfilePercent] = useState(0);

  useEffect(() => {
    fetchMarketData();
    fetchEmailSub();
    fetchWatchlist();
    checkProfileCompletion();
  }, []);

  const checkProfileCompletion = async () => {
    try {
      const res = await getProfileCompletionStatus();
      const { is_complete, completion_percent } = res.data;
      setProfilePercent(completion_percent);
      if (!is_complete) {
        setProfileIncomplete(true);
        const dismissed = sessionStorage.getItem('profile_modal_dismissed');
        if (!dismissed) setShowProfileModal(true);
      }
    } catch { /* ignore */ }
  };

  const handleProfileModalClose = () => {
    setShowProfileModal(false);
    sessionStorage.setItem('profile_modal_dismissed', 'true');
  };

  const handleProfileComplete = () => {
    setProfileIncomplete(false);
    setProfilePercent(100);
    setShowProfileModal(false);
  };

  const fetchWatchlist = async () => {
    try {
      const res = await getWatchlist();
      setWatchlistItems(res.data.items || []);
    } catch { /* ignore */ }
  };

  const fetchEmailSub = async () => {
    try {
      const res = await getMarketSubscriptionStatus();
      setEmailSub(res.data);
    } catch { /* ignore */ }
  };

  const handleSubscribe = async () => {
    setSubLoading(true);
    try {
      await subscribeMarketEmail();
      await fetchEmailSub();
    } catch { /* ignore */ } finally {
      setSubLoading(false);
    }
  };

  const fetchMarketData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/market/overview');
      if (response.data) {
        setMarketData(response.data);
      } else {
        setError('시장 데이터를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.');
      }
    } catch (err) {
      console.error('Failed to fetch market data:', err);
      setError('시장 데이터를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.');
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num) => new Intl.NumberFormat('ko-KR').format(num);

  const formatChange = (change, percent) => {
    const sign = change >= 0 ? '+' : '';
    return `${sign}${change.toFixed(2)} (${sign}${percent.toFixed(2)}%)`;
  };

  const now = new Date();
  const dateStr = `${now.getFullYear()}년 ${String(now.getMonth() + 1).padStart(2, '0')}월 ${String(now.getDate()).padStart(2, '0')}일 (${['일', '월', '화', '수', '목', '금', '토'][now.getDay()]})`;

  /* ── Loading state ── */
  if (loading) {
    return (
      <div className="market-dashboard-v2">
        <DashboardSkeleton />
      </div>
    );
  }

  /* ── Error state ── */
  if (error) {
    return (
      <div className="market-dashboard-v2">
        <div className="dashboard-redesign">
          <div className="error-card">
            <p>{error}</p>
            <button onClick={fetchMarketData} className="refresh-btn">다시 시도</button>
          </div>
        </div>
      </div>
    );
  }

  /* ── Determine sentiment signal ── */
  const sentimentColor = marketData?.summary?.sentiment?.color || 'yellow';

  return (
    <div className="market-dashboard-v2">
      <div className="dashboard-redesign">

        {/* Profile completion banner */}
        {profileIncomplete && (
          <div className="compare-banner">
            <span className="compare-label">프로필</span>
            <span className="compare-text">
              프로필 완성하고 맞춤 학습을 시작하세요 — 현재 {profilePercent}% 완료
            </span>
            <button className="refresh-btn" onClick={() => setShowProfileModal(true)}>
              프로필 완성하기
            </button>
          </div>
        )}

        {/* ── Header ── */}
        <div className="dash-header">
          <div>
            <h1><span className="dash-brand">Foresto Compass</span> 시장 현황</h1>
            <div className="dash-date">{dateStr} 기준</div>
          </div>
          <button className="refresh-btn" onClick={fetchMarketData}>새로고침</button>
        </div>

        {/* ── KPI Cards ── */}
        <div className="kpi-grid">
          {marketData?.indices?.map((idx, i) => {
            const isUp = idx.change >= 0;
            const color = isUp ? 'var(--stock-up)' : 'var(--stock-down)';
            return (
              <div key={i} className="kpi-card">
                <div className="kpi-label">{idx.name}</div>
                <div className="kpi-value">{formatNumber(idx.value)}</div>
                <div className={`kpi-change ${isUp ? 'up' : 'down'}`}>
                  {formatChange(idx.change, idx.changePercent)}
                </div>
                <div className="kpi-sparkline">
                  <Sparkline
                    points={idx.sparkline || [idx.value - Math.abs(idx.change) * 3, idx.value - Math.abs(idx.change) * 2, idx.value - Math.abs(idx.change), idx.value - Math.abs(idx.change) * 1.5, idx.value - Math.abs(idx.change) * 0.5, idx.value + idx.change * 0.3, idx.value + idx.change * 0.7, idx.value]}
                    color={isUp ? '#e53935' : '#1e88e5'}
                  />
                </div>
              </div>
            );
          })}
        </div>

        {/* ── AI Summary ── */}
        {marketData?.summary && (
          <div className="ai-summary">
            <div className="ai-signal">
              <div className={`dot green ${sentimentColor === 'green' ? 'active' : ''}`} />
              <div className={`dot yellow ${sentimentColor === 'yellow' ? 'active' : ''}`} />
              <div className={`dot red ${sentimentColor === 'red' ? 'active' : ''}`} />
            </div>
            <div className="ai-content-block">
              <div className="ai-title">
                오늘의 시장 데이터 요약 (참고용)
                <span className="ai-badge-tag">AI 분석</span>
              </div>
              <p className="ai-text">{marketData.summary.text || marketData.summary}</p>
              <div className="ai-disclaimer">
                본 정보는 교육 목적의 참고 자료이며, 투자 권유/추천이 아닙니다.
              </div>
            </div>
          </div>
        )}

        {/* ── Gainers / Losers ── */}
        <div className="two-col">
          <div className="section-card">
            <div className="section-title">
              <span className="icon" style={{ color: 'var(--stock-up)' }}>&#9650;</span>
              상승 종목 Top 5
            </div>
            {marketData?.topGainers?.map((stock, i) => {
              const pct = Math.abs(stock.change);
              const maxPct = Math.abs(marketData.topGainers[0]?.change || 1);
              const barW = Math.max(10, (pct / maxPct) * 100);
              return (
                <div key={i} className="mover-item">
                  <div className="mover-rank up">{i + 1}</div>
                  <div className="mover-info">
                    <div className="mover-name">{stock.name}</div>
                    <div className="mover-code">{stock.symbol}</div>
                  </div>
                  <div className="mover-bar-wrap">
                    <div className="mover-bar-bg">
                      <div className="mover-bar up" style={{ width: `${barW}%` }} />
                    </div>
                  </div>
                  <div className="mover-values">
                    <div className="mover-price">{formatNumber(stock.price)}원</div>
                    <div className="mover-change up">+{stock.change}%</div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="section-card">
            <div className="section-title">
              <span className="icon" style={{ color: 'var(--stock-down)' }}>&#9660;</span>
              하락 종목 Top 5
            </div>
            {marketData?.topLosers?.map((stock, i) => {
              const pct = Math.abs(stock.change);
              const maxPct = Math.abs(marketData.topLosers[0]?.change || 1);
              const barW = Math.max(10, (pct / maxPct) * 100);
              return (
                <div key={i} className="mover-item">
                  <div className="mover-rank down">{i + 1}</div>
                  <div className="mover-info">
                    <div className="mover-name">{stock.name}</div>
                    <div className="mover-code">{stock.symbol}</div>
                  </div>
                  <div className="mover-bar-wrap">
                    <div className="mover-bar-bg">
                      <div className="mover-bar down" style={{ width: `${barW}%` }} />
                    </div>
                  </div>
                  <div className="mover-values">
                    <div className="mover-price">{formatNumber(stock.price)}원</div>
                    <div className="mover-change down">{stock.change}%</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Watchlist ── */}
        <div className="section-card" style={{ marginBottom: 24 }}>
          <div className="wl-section-header">
            <div className="section-title" style={{ margin: 0 }}>
              <span className="icon">&#9733;</span>
              관심 종목
            </div>
            {watchlistItems.length > 0 && (
              <button className="wl-view-all" onClick={() => navigate('/watchlist')}>
                전체 {watchlistItems.length}개 보기 &rarr;
              </button>
            )}
          </div>
          {watchlistItems.length > 0 ? (
            <div className="watchlist-grid">
              {watchlistItems.slice(0, 4).map((item) => {
                const score = item.compass_score;
                const grade = item.compass_grade || '-';
                const gc = gradeColor(grade);
                return (
                  <div
                    key={item.ticker}
                    className="wl-card"
                    onClick={() => navigate(`/admin/stock-detail?ticker=${item.ticker}`)}
                  >
                    <div className="wl-card-header">
                      <div>
                        <div className="wl-card-name">{item.name}</div>
                        <div className="wl-card-code">{item.ticker}</div>
                      </div>
                      {score != null && (
                        <div className="wl-score-circle" style={{ background: `linear-gradient(135deg, ${gc}, ${gc}dd)` }}>
                          {score.toFixed(0)}
                        </div>
                      )}
                    </div>
                    {score != null && (
                      <div className="wl-axes">
                        {[
                          { label: '재무', key: 'compass_financial_score', color: axisColors.financial },
                          { label: '밸류', key: 'compass_valuation_score', color: axisColors.valuation },
                          { label: '기술', key: 'compass_technical_score', color: axisColors.technical },
                          { label: '리스크', key: 'compass_risk_score', color: axisColors.risk },
                        ].map(({ label, key, color }) => {
                          const val = item[key] ?? 0;
                          return (
                            <div key={label} className="wl-axis">
                              <span className="wl-axis-label">{label}</span>
                              <div className="wl-axis-bar">
                                <div className="wl-axis-fill" style={{ width: `${val}%`, background: color }} />
                              </div>
                              <span className="wl-axis-val">{val.toFixed(0)}</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                    <div className="wl-footer">
                      <span>{grade} 등급</span>
                      {item.score_change != null && item.score_change !== 0 && (
                        <span style={{ color: item.score_change > 0 ? 'var(--stock-up)' : 'var(--stock-down)' }}>
                          {item.score_change > 0 ? '+' : ''}{item.score_change.toFixed(1)}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="wl-empty">
              <p>관심 종목이 없습니다</p>
              <button className="cta-btn" onClick={() => navigate('/screener')}>스크리너에서 추가</button>
            </div>
          )}
        </div>

        {/* ── News ── */}
        <div className="section-card" style={{ marginBottom: 24 }}>
          <div className="section-title">
            <span className="icon">&#128240;</span>
            시장 뉴스
          </div>
          <div className="news-grid">
            {marketData?.news?.map((item, idx) => (
              <a key={idx} href={item.url} className="news-item-link" target="_blank" rel="noopener noreferrer">
                <div className="news-item-v2">
                  <div className="news-time-col"><span className="news-time">{item.publishedAt}</span></div>
                  <div className="news-dot-col">
                    <div className="news-dot" />
                    {idx < (marketData.news.length - 1) && <div className="news-line" />}
                  </div>
                  <div className="news-body">
                    <div className="news-headline">{item.title}</div>
                    <div className="news-meta-v2">
                      <span className="news-naver">N</span>
                      {item.source}
                    </div>
                  </div>
                </div>
              </a>
            ))}
          </div>
        </div>

        {/* ── CTA (3-column horizontal) ── */}
        <div className="cta-grid">
          <div className="cta-card cta-horizontal">
            <div className="cta-icon">&#127919;</div>
            <div className="cta-body">
              <div className="cta-title">학습 성향 진단</div>
              <div className="cta-desc">설문조사를 통해 투자 전략 학습 방향을 파악해보세요</div>
            </div>
            <button className="cta-btn" onClick={() => navigate('/survey')}>시작</button>
          </div>
          <div className="cta-card cta-horizontal">
            <div className="cta-icon">&#128202;</div>
            <div className="cta-body">
              <div className="cta-title">종목 스크리너</div>
              <div className="cta-desc">Compass Score 기반 종목 탐색 및 비교</div>
            </div>
            <button className="cta-btn" onClick={() => navigate('/screener')}>열기</button>
          </div>
          <div className="cta-card cta-horizontal">
            <div className="cta-icon">&#128231;</div>
            <div className="cta-body">
              <div className="cta-title">시장 요약 이메일</div>
              <div className="cta-desc">매일 아침 시장 현황을 이메일로 받아보세요</div>
            </div>
            {emailSub?.subscribed ? (
              <button className="cta-btn subscribed">구독 중</button>
            ) : emailSub?.is_email_verified === false ? (
              <button className="cta-btn" disabled>인증 필요</button>
            ) : (
              <button className="cta-btn" onClick={handleSubscribe} disabled={subLoading}>
                {subLoading ? '처리 중...' : '구독하기'}
              </button>
            )}
          </div>
        </div>

        {/* ── Footer ── */}
        <footer className="dash-footer">
          <div className="footer-inner">
            <p>&copy; 2026 Foresto Compass. All rights reserved.</p>
            <p>본 서비스는 교육 목적의 참고 자료이며, 투자 권유/추천이 아닙니다.</p>
          </div>
        </footer>

      </div>

      {/* Profile completion modal */}
      {showProfileModal && (
        <ProfileCompletionModal
          onClose={handleProfileModalClose}
          onComplete={handleProfileComplete}
        />
      )}
    </div>
  );
}

export default MarketDashboardPage;
