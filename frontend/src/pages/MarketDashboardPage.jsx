import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import api from '../services/api';
import '../styles/MarketDashboard.css';

function MarketDashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [marketData, setMarketData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchMarketData();
  }, []);

  const fetchMarketData = async () => {
    try {
      setLoading(true);
      // API 호출 (axios 사용)
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

  const formatNumber = (num) => {
    return new Intl.NumberFormat('ko-KR').format(num);
  };

  const formatChange = (change, percent) => {
    const sign = change >= 0 ? '+' : '';
    return `${sign}${change.toFixed(2)} (${sign}${percent.toFixed(2)}%)`;
  };

  if (loading) {
    return (
      <div className="market-dashboard">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>시장 데이터를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="market-dashboard">
        <div className="error-container">
          <p>{error}</p>
          <button onClick={fetchMarketData} className="btn-retry">다시 시도</button>
        </div>
      </div>
    );
  }

  return (
    <div className="market-dashboard">
      <div className="dashboard-header">
        <div className="header-content">
          <h1>📈 시장 현황</h1>
          <p className="subtitle">주식 시장 데이터를 학습용으로 확인하세요</p>
        </div>
        <button onClick={() => navigate('/survey')} className="btn-survey">
          학습 성향 진단하기
        </button>
      </div>

      {/* AI 시장 요약 */}
      {marketData?.summary && (
        <section className="market-summary">
          <div className="summary-card">
            <div className="summary-layout">
              <div className="traffic-light">
                <div className={`light ${marketData.summary.sentiment?.color === 'green' ? 'active' : ''}`} data-status="긍정적">
                  🟢
                </div>
                <div className={`light ${marketData.summary.sentiment?.color === 'yellow' ? 'active' : ''}`} data-status="중립">
                  🟡
                </div>
                <div className={`light ${marketData.summary.sentiment?.color === 'red' ? 'active' : ''}`} data-status="위험">
                  🔴
                </div>
              </div>
              <div className="summary-content">
                <div className="summary-title-row">
                  <h3>오늘의 시장 데이터 요약 (참고용)</h3>
                  <span className={`sentiment-badge ${marketData.summary.sentiment?.color || 'yellow'}`}>
                    {marketData.summary.sentiment?.emoji || '🟡'} {marketData.summary.sentiment?.status || '중립'}
                  </span>
                </div>
                <p className="summary-text">{marketData.summary.text || marketData.summary}</p>
                <p style={{ fontSize: '0.75rem', color: '#888', marginTop: '8px' }}>
                  ⚠️ 본 정보는 교육 목적의 참고 자료이며, 투자 권유·추천이 아닙니다.
                </p>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* 주요 지수 */}
      <section className="indices-section">
        <h2>주요 지수</h2>
        <div className="indices-grid">
          {marketData?.indices.map((index, idx) => (
            <div key={idx} className="index-card">
              <div className="index-name">{index.name}</div>
              <div className="index-value">{formatNumber(index.value)}</div>
              <div className={`index-change ${index.change >= 0 ? 'positive' : 'negative'}`}>
                {formatChange(index.change, index.changePercent)}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 상승/하락 종목 */}
      <div className="stocks-section">
        <div className="stocks-column">
          <h2>🔥 상승 종목</h2>
          <div className="stock-list">
            {marketData?.topGainers.map((stock, idx) => (
              <div key={idx} className="stock-item">
                <div className="stock-info">
                  <div className="stock-name">{stock.name}</div>
                  <div className="stock-symbol">{stock.symbol}</div>
                </div>
                <div className="stock-right">
                  <div className="stock-price">{formatNumber(stock.price)}원</div>
                  <div className="stock-change positive">+{stock.change}%</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="stocks-column">
          <h2>❄️ 하락 종목</h2>
          <div className="stock-list">
            {marketData?.topLosers.map((stock, idx) => (
              <div key={idx} className="stock-item">
                <div className="stock-info">
                  <div className="stock-name">{stock.name}</div>
                  <div className="stock-symbol">{stock.symbol}</div>
                </div>
                <div className="stock-right">
                  <div className="stock-price">{formatNumber(stock.price)}원</div>
                  <div className="stock-change negative">{stock.change}%</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 시장 뉴스 */}
      <section className="news-section">
        <h2>📰 시장 뉴스</h2>
        <div className="news-list">
          {marketData?.news.map((item, idx) => (
            <div key={idx} className="news-item">
              <div className="news-content">
                <h3 className="news-title">{item.title}</h3>
                <div className="news-meta">
                  <span className="news-source">
                    <span className="naver-logo">N</span>
                    {item.source}
                  </span>
                  <span className="news-time">{item.publishedAt}</span>
                </div>
              </div>
              <a href={item.url} className="news-link" target="_blank" rel="noopener noreferrer">
                자세히 보기 →
              </a>
            </div>
          ))}
        </div>
      </section>

      {/* 추가 기능 안내 */}
      <section className="cta-section">
        <div className="cta-card">
          <h3>🎯 학습 성향 진단</h3>
          <p>설문조사를 통해 투자 전략 학습 방향을 파악해보세요 (교육용)</p>
          <button onClick={() => navigate('/survey')} className="btn-cta">
            학습 성향 진단 시작
          </button>
        </div>
        <div className="cta-card">
          <h3>📊 시뮬레이션 학습</h3>
          <p>다양한 포트폴리오 구성 예시를 시뮬레이션으로 학습하세요</p>
          <button onClick={() => navigate('/profile')} className="btn-cta">
            프로필 설정하기
          </button>
        </div>
      </section>
    </div>
  );
}

export default MarketDashboardPage;
