import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { generatePortfolio, runBacktest as runBacktestAPI, downloadPortfolioPDF } from '../services/api';
import Disclaimer from '../components/Disclaimer';
import '../styles/PortfolioRecommendation.css';

function PortfolioRecommendationPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [investmentAmount, setInvestmentAmount] = useState(10000000); // 기본 1000만원
  const [downloadingPDF, setDownloadingPDF] = useState(false);

  useEffect(() => {
    fetchPortfolio();
  }, []);

  const fetchPortfolio = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await generatePortfolio({
        investment_amount: investmentAmount
      });

      console.log('Portfolio response:', response.data);
      setPortfolio(response.data);
    } catch (err) {
      console.error('Portfolio fetch error:', err);
      if (err.response?.status === 400 && err.response?.data?.detail?.includes('No diagnosis found')) {
        setError('투자 성향 분석을 먼저 진행해주세요.');
      } else {
        setError('포트폴리오를 불러오는데 실패했습니다.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAmountChange = (e) => {
    const value = parseInt(e.target.value.replace(/,/g, '')) || 0;
    setInvestmentAmount(value);
  };

  const handleRegenerate = () => {
    fetchPortfolio();
  };

  const handleBacktest = async (periodYears = 1) => {
    if (!portfolio) return;

    try {
      setLoading(true);
      const response = await runBacktestAPI({
        portfolio: portfolio,
        investment_amount: investmentAmount,
        period_years: periodYears,
        rebalance_frequency: 'quarterly'
      });

      // 백테스트 결과를 상태로 전달하며 백테스트 페이지로 이동
      navigate('/backtest', {
        state: {
          backtestResult: response.data.data,
          portfolio: portfolio
        }
      });
    } catch (err) {
      console.error('Backtest error:', err);
      setError('백테스트 실행 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPDF = async () => {
    try {
      setDownloadingPDF(true);
      await downloadPortfolioPDF(investmentAmount);
      alert('PDF 리포트가 다운로드되었습니다!');
    } catch (err) {
      console.error('PDF download error:', err);
      alert('PDF 다운로드 중 오류가 발생했습니다.');
    } finally {
      setDownloadingPDF(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ko-KR').format(amount);
  };

  const formatPercent = (value) => {
    if (value === undefined || value === null) return '0.0%';
    return `${Number(value).toFixed(1)}%`;
  };

  if (loading) {
    return (
      <div className="portfolio-page">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>포트폴리오를 생성하고 있습니다...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="portfolio-page">
        <div className="error-container">
          <p className="error-message">{error}</p>
          <button onClick={() => navigate('/survey')} className="btn-primary">
            투자 성향 분석하기
          </button>
        </div>
      </div>
    );
  }

  if (!portfolio) {
    return null;
  }

  return (
    <div className="portfolio-page">
      {/* 헤더 */}
      <div className="portfolio-header">
        <div className="header-content">
          <h1>💼 맞춤 포트폴리오</h1>
          <p className="subtitle">당신의 투자 성향에 맞는 포트폴리오를 추천해드립니다</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handleDownloadPDF}
            className="btn-secondary"
            disabled={downloadingPDF}
            style={{
              background: downloadingPDF ? '#ccc' : '#4caf50',
              color: 'white',
              border: 'none',
              padding: '10px 20px',
              borderRadius: '8px',
              cursor: downloadingPDF ? 'not-allowed' : 'pointer',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            {downloadingPDF ? (
              <>⏳ 생성 중...</>
            ) : (
              <>📄 PDF 리포트 다운로드</>
            )}
          </button>
          <button onClick={() => navigate('/dashboard')} className="btn-back">
            ← 시장 현황으로
          </button>
        </div>
      </div>

      {/* 면책 문구 */}
      <Disclaimer type="portfolio" />

      {/* 투자 성향 요약 */}
      <section className="investment-profile">
        <div className="profile-card">
          <h3>투자 성향 분석 결과</h3>
          <div className="profile-info">
            <div className="info-item">
              <span className="label">투자 성향</span>
              <span className={`value type-${portfolio.investment_type}`}>
                {portfolio.investment_type === 'conservative' && '안정형'}
                {portfolio.investment_type === 'moderate' && '중립형'}
                {portfolio.investment_type === 'aggressive' && '공격형'}
              </span>
            </div>
            <div className="info-item">
              <span className="label">기대 수익률</span>
              <span className="value">{formatPercent(portfolio.statistics?.expected_annual_return)}</span>
            </div>
            <div className="info-item">
              <span className="label">리스크 레벨</span>
              <span className="value">{portfolio.statistics?.portfolio_risk || '중간'}</span>
            </div>
          </div>
        </div>
      </section>

      {/* 투자 금액 설정 */}
      <section className="amount-setting">
        <div className="amount-card">
          <h3>투자 금액</h3>
          <div className="amount-input-group">
            <input
              type="text"
              value={formatCurrency(investmentAmount)}
              onChange={handleAmountChange}
              className="amount-input"
            />
            <span className="currency">원</span>
          </div>
          <div className="quick-amounts">
            <button onClick={() => setInvestmentAmount(5000000)}>500만</button>
            <button onClick={() => setInvestmentAmount(10000000)}>1000만</button>
            <button onClick={() => setInvestmentAmount(30000000)}>3000만</button>
            <button onClick={() => setInvestmentAmount(50000000)}>5000만</button>
          </div>
          <div className="action-buttons">
            <button onClick={handleRegenerate} className="btn-regenerate">
              포트폴리오 재생성
            </button>
            <button onClick={() => handleBacktest(1)} className="btn-backtest">
              📊 백테스트 (1년)
            </button>
            <button onClick={() => handleBacktest(3)} className="btn-backtest">
              📊 백테스트 (3년)
            </button>
          </div>
        </div>
      </section>

      {/* 자산 배분 */}
      <section className="asset-allocation">
        <h2>자산 배분</h2>
        <div className="allocation-card">
          <div className="allocation-chart">
            {portfolio.allocation && Object.entries(portfolio.allocation).map(([assetType, data], idx) => (
              <div
                key={idx}
                className="chart-segment"
                style={{
                  width: `${(data.ratio || 0)}%`,
                  backgroundColor: getAssetColor(assetType)
                }}
                title={`${translateAssetType(assetType)}: ${formatPercent(data.ratio || 0)}`}
              />
            ))}
          </div>
          <div className="allocation-list">
            {portfolio.allocation && Object.entries(portfolio.allocation).map(([assetType, data], idx) => (
              <div key={idx} className="allocation-item">
                <div className="item-header">
                  <span
                    className="color-indicator"
                    style={{ backgroundColor: getAssetColor(assetType) }}
                  />
                  <span className="asset-name">{translateAssetType(assetType)}</span>
                  <span className="asset-percentage">{formatPercent(data.ratio || 0)}</span>
                </div>
                <div className="item-amount">
                  {formatCurrency(data.amount || 0)}원
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 추천 종목 */}
      <section className="recommended-assets">
        <h2>추천 종목</h2>
        <div className="assets-grid">
          {portfolio.portfolio && [
            ...(portfolio.portfolio.stocks || []).map(s => ({...s, asset_type: 'Stock'})),
            ...(portfolio.portfolio.etfs || []).map(e => ({...e, asset_type: 'ETF'})),
            ...(portfolio.portfolio.bonds || []).map(b => ({...b, asset_type: 'Bond'})),
            ...(portfolio.portfolio.deposits || []).map(d => ({...d, asset_type: 'Cash'}))
          ].map((asset, idx) => (
            <div key={idx} className="asset-card">
              <div className="asset-header">
                <h3>{asset.name}</h3>
                <span className={`asset-type ${asset.asset_type}`}>{translateAssetType(asset.asset_type)}</span>
              </div>
              <div className="asset-info">
                <div className="info-row">
                  <span className="label">투자 금액</span>
                  <span className="value">{formatCurrency(asset.invested_amount || 0)}원</span>
                </div>
                <div className="info-row">
                  <span className="label">수량</span>
                  <span className="value">{asset.shares || 0}주</span>
                </div>
                {asset.current_price && (
                  <div className="info-row">
                    <span className="label">현재가</span>
                    <span className="value">{formatCurrency(asset.current_price)}원</span>
                  </div>
                )}
                {asset.sector && (
                  <div className="info-row">
                    <span className="label">섹터</span>
                    <span className="value">{asset.sector}</span>
                  </div>
                )}
              </div>
              {asset.rationale && (
                <div className="asset-reason">
                  <p>{asset.rationale}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* 투자 팁 */}
      <section className="investment-tips">
        <h2>💡 투자 가이드</h2>
        <div className="tips-card">
          <div className="tip-item">
            <h4>분산 투자의 중요성</h4>
            <p>한 종목에 집중하지 말고, 여러 자산에 분산 투자하여 리스크를 관리하세요.</p>
          </div>
          <div className="tip-item">
            <h4>정기적인 리밸런싱</h4>
            <p>시장 상황에 따라 자산 배분 비율이 달라질 수 있습니다. 분기마다 포트폴리오를 점검하세요.</p>
          </div>
          <div className="tip-item">
            <h4>장기 투자</h4>
            <p>단기적인 시장 변동에 흔들리지 말고, 장기적인 관점으로 투자하세요.</p>
          </div>
          {portfolio.investment_type === 'conservative' && (
            <div className="tip-item">
              <h4>안정형 투자자를 위한 팁</h4>
              <p>원금 보존을 최우선으로 하되, 인플레이션을 고려한 수익률도 생각해보세요.</p>
            </div>
          )}
          {portfolio.investment_type === 'aggressive' && (
            <div className="tip-item">
              <h4>공격형 투자자를 위한 팁</h4>
              <p>높은 수익을 추구하되, 손실 감수 범위를 미리 정하고 지키세요.</p>
            </div>
          )}
        </div>
      </section>

      {/* CTA */}
      <section className="portfolio-cta">
        <div className="cta-card">
          <h3>투자를 시작할 준비가 되셨나요?</h3>
          <p>포트폴리오는 참고용이며, 실제 투자 결정은 신중히 하시기 바랍니다.</p>
          <div className="cta-buttons">
            <button onClick={() => navigate('/diagnosis/history')} className="btn-secondary">
              이전 진단 보기
            </button>
            <button onClick={() => navigate('/survey')} className="btn-primary">
              새로운 분석하기
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

// 자산 타입 한글 변환
function translateAssetType(assetType) {
  const translations = {
    'stocks': '주식',
    'etfs': 'ETF',
    'bonds': '채권',
    'deposits': '예적금',
    'Stock': '주식',
    'ETF': 'ETF',
    'Bond': '채권',
    'Cash': '예적금'
  };
  return translations[assetType] || assetType;
}

// 자산 타입별 색상
function getAssetColor(assetType) {
  const colors = {
    '주식': '#4CAF50',
    '채권': '#2196F3',
    '예적금': '#FF9800',
    'ETF': '#FF5722',
    '부동산': '#9C27B0',
    '기타': '#607D8B',
    'stocks': '#4CAF50',
    'bonds': '#2196F3',
    'deposits': '#FF9800',
    'etfs': '#FF5722',
    'Stock': '#4CAF50',
    'Bond': '#2196F3',
    'Cash': '#FF9800'
  };
  return colors[assetType] || '#9E9E9E';
}

export default PortfolioRecommendationPage;
