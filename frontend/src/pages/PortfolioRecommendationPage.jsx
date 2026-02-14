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
  const [showDiagnosisModal, setShowDiagnosisModal] = useState(false);

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
      const apiMessage = err.response?.data?.detail || err.response?.data?.error?.message || '';
      if (err.response?.status === 400 && apiMessage.includes('No diagnosis found')) {
        setShowDiagnosisModal(true);
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

  const diagnosisModal = showDiagnosisModal && (
    <div className="portfolio-modal-overlay" onClick={() => setShowDiagnosisModal(false)}>
      <div className="portfolio-modal" onClick={(e) => e.stopPropagation()}>
        <div className="portfolio-modal-header">
          <h2>진단 결과 없음</h2>
          <button className="portfolio-modal-close" onClick={() => setShowDiagnosisModal(false)}>
            ✕
          </button>
        </div>
        <div className="portfolio-modal-body">
          <p>진단 결과가 없습니다. 먼저 투자 성향 진단을 진행해주세요.</p>
        </div>
        <div className="portfolio-modal-footer">
          <button className="pr-btn-primary" onClick={() => navigate('/survey')}>
            진단 바로가기
          </button>
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="portfolio-page">
        <div className="pr-loading">
          <div className="pr-spinner"></div>
          <p>포트폴리오를 생성하고 있습니다...</p>
        </div>
        {diagnosisModal}
      </div>
    );
  }

  if (error) {
    return (
      <div className="portfolio-page">
        <div className="pr-error">
          <p className="pr-error-message">{error}</p>
          <button onClick={() => navigate('/survey')} className="pr-btn-primary">
            학습 성향 진단하기
          </button>
        </div>
        {diagnosisModal}
      </div>
    );
  }

  if (!portfolio) {
    return (
      <div className="portfolio-page">
        {diagnosisModal}
      </div>
    );
  }

  return (
    <div className="portfolio-page">
      {diagnosisModal}
      {/* 헤더 */}
      <div className="portfolio-header">
        <div className="header-content">
          <h1>📊 AI 시뮬레이션</h1>
          <p className="subtitle">학습 성향별 자산 배분 예시를 시뮬레이션으로 학습하세요 (교육용)</p>
        </div>
        <div className="pr-header-actions">
          <button
            onClick={handleDownloadPDF}
            className="pr-pdf-btn"
            disabled={downloadingPDF}
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

      {/* 학습 성향 요약 */}
      <section className="investment-profile">
        <div className="profile-card">
          <h3>학습 성향 진단 결과</h3>
          <div className="profile-info">
            <div className="info-item">
              <span className="label">학습 성향</span>
              <span className={`value type-${portfolio.investment_type}`}>
                {portfolio.investment_type === 'conservative' && '안정성 중심'}
                {portfolio.investment_type === 'moderate' && '균형형'}
                {portfolio.investment_type === 'aggressive' && '성장성 중심'}
              </span>
            </div>
            <div className="info-item">
              <span className="label">과거 평균 수익률 (참고)</span>
              <span className="value">{formatPercent(portfolio.statistics?.expected_annual_return)}</span>
            </div>
            <div className="info-item">
              <span className="label">리스크 레벨</span>
              <span className="value">{portfolio.statistics?.portfolio_risk || '중간'}</span>
            </div>
          </div>
          <p className="pr-disclaimer-text">
            ⚠️ 본 결과는 교육 목적의 시뮬레이션 예시이며, 투자 권유가 아닙니다.
          </p>
        </div>
      </section>

      {/* 시뮬레이션 금액 설정 */}
      <section className="amount-setting">
        <div className="amount-card">
          <h3>시뮬레이션 금액</h3>
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
              시뮬레이션 재생성
            </button>
            <button onClick={() => handleBacktest(1)} className="btn-backtest">
              📊 백테스트 학습 (1년)
            </button>
            <button onClick={() => handleBacktest(3)} className="btn-backtest">
              📊 백테스트 학습 (3년)
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

      {/* 샘플 종목 */}
      <section className="sample-assets">
        <h2>시뮬레이션 구성 예시 종목</h2>
        <p className="pr-sample-disclaimer">
          ⚠️ 교육 목적의 예시 종목이며, 학습용 시나리오입니다.
        </p>
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
                  <span className="label">시뮬레이션 금액</span>
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

      {/* 학습 가이드 */}
      <section className="investment-tips">
        <h2>💡 자산 운용 학습 가이드</h2>
        <div className="tips-card">
          <div className="tip-item">
            <h4>분산 투자 개념 학습</h4>
            <p>한 종목 집중이 아닌 여러 자산에 분산하여 리스크를 관리하는 방법을 이해해보세요.</p>
          </div>
          <div className="tip-item">
            <h4>리밸런싱 학습</h4>
            <p>시장 상황에 따라 자산 배분 비율이 달라지는 과정을 학습하고, 정기적인 조정 방법을 이해하세요.</p>
          </div>
          <div className="tip-item">
            <h4>장기 투자 전략 이해</h4>
            <p>단기 변동성과 장기 성장의 차이를 학습하고, 다양한 투자 기간별 전략을 이해하세요.</p>
          </div>
          {portfolio.investment_type === 'conservative' && (
            <div className="tip-item">
              <h4>안정성 중심 전략 학습</h4>
              <p>원금 보존 우선 전략과 인플레이션 방어 개념을 함께 학습해보세요.</p>
            </div>
          )}
          {portfolio.investment_type === 'aggressive' && (
            <div className="tip-item">
              <h4>성장성 중심 전략 학습</h4>
              <p>고수익 추구 전략과 리스크 관리 기법을 균형있게 학습하세요.</p>
            </div>
          )}
        </div>
      </section>

      {/* CTA */}
      <section className="portfolio-cta">
        <div className="cta-card">
          <h3>더 많은 자산 배분 전략을 학습하시겠습니까?</h3>
          <p>⚠️ 본 시뮬레이션은 교육 목적의 학습 도구이며, 투자 권유·자문 서비스를 제공하지 않습니다. 실제 투자 결정은 본인의 판단과 책임 하에 신중히 하시기 바랍니다.</p>
          <div className="cta-buttons">
            <button onClick={() => navigate('/diagnosis/history')} className="pr-btn-secondary">
              이전 진단 보기
            </button>
            <button onClick={() => navigate('/survey')} className="pr-btn-primary">
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
