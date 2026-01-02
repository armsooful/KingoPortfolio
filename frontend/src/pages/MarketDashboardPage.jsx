import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
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
      // TODO: 실제 API 엔드포인트로 교체
      const response = await fetch('http://localhost:8000/api/market/overview', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setMarketData(data);
      } else {
        // Mock data for development
        setMarketData({
          indices: [
            {
              name: 'KOSPI',
              value: 2645.85,
              change: 15.32,
              changePercent: 0.58,
              updatedAt: new Date().toISOString()
            },
            {
              name: 'KOSDAQ',
              value: 845.23,
              change: -3.45,
              changePercent: -0.41,
              updatedAt: new Date().toISOString()
            },
            {
              name: 'S&P 500',
              value: 4783.45,
              change: 12.87,
              changePercent: 0.27,
              updatedAt: new Date().toISOString()
            },
            {
              name: 'NASDAQ',
              value: 15043.97,
              change: 45.23,
              changePercent: 0.30,
              updatedAt: new Date().toISOString()
            }
          ],
          topGainers: [
            { symbol: '005930', name: '삼성전자', price: 78500, change: 3.5 },
            { symbol: '000660', name: 'SK하이닉스', price: 145000, change: 4.2 },
            { symbol: '035420', name: 'NAVER', price: 245000, change: 2.8 }
          ],
          topLosers: [
            { symbol: '051910', name: 'LG화학', price: 425000, change: -2.3 },
            { symbol: '006400', name: '삼성SDI', price: 485000, change: -1.8 },
            { symbol: '028260', name: '삼성물산', price: 128000, change: -1.5 }
          ],
          news: [
            {
              title: '미 연준 금리 동결 전망... 국내 증시 영향은?',
              source: '한국경제',
              publishedAt: '2시간 전',
              url: '#'
            },
            {
              title: '삼성전자, AI 반도체 신제품 공개',
              source: '전자신문',
              publishedAt: '4시간 전',
              url: '#'
            },
            {
              title: 'KOSPI 2650 돌파... 외국인 매수세 지속',
              source: '연합뉴스',
              publishedAt: '5시간 전',
              url: '#'
            }
          ]
        });
      }
    } catch (err) {
      console.error('Failed to fetch market data:', err);
      setError('시장 데이터를 불러오는데 실패했습니다.');
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
          <p className="subtitle">실시간 주식 시장 동향을 확인하세요</p>
        </div>
        <button onClick={() => navigate('/survey')} className="btn-survey">
          투자 성향 분석하기
        </button>
      </div>

      {/* AI 시장 요약 */}
      {marketData?.summary && (
        <section className="market-summary">
          <div className="summary-card">
            <div className="summary-header">
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
            </div>
            <div className="summary-content">
              <div className="summary-title-row">
                <h3>오늘의 시장 한눈에 보기</h3>
                <span className={`sentiment-badge ${marketData.summary.sentiment?.color || 'yellow'}`}>
                  {marketData.summary.sentiment?.emoji || '🟡'} {marketData.summary.sentiment?.status || '중립'}
                </span>
              </div>
              <p className="summary-text">{marketData.summary.text || marketData.summary}</p>
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
                  <span className="news-source">{item.source}</span>
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
          <h3>🎯 맞춤형 투자 분석</h3>
          <p>설문조사를 통해 당신에게 맞는 투자 전략을 찾아보세요</p>
          <button onClick={() => navigate('/survey')} className="btn-cta">
            투자 성향 분석 시작
          </button>
        </div>
        <div className="cta-card">
          <h3>📊 포트폴리오 관리</h3>
          <p>체계적인 포트폴리오 분석과 관리를 시작하세요</p>
          <button onClick={() => navigate('/profile')} className="btn-cta">
            프로필 설정하기
          </button>
        </div>
      </section>
    </div>
  );
}

export default MarketDashboardPage;
