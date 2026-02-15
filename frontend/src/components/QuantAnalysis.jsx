import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getComprehensiveQuant,
  getTechnicalIndicators,
  getRiskMetrics,
} from '../services/api';
import '../styles/QuantAnalysis.css';

const QuantAnalysis = () => {
  const navigate = useNavigate();
  const [symbol, setSymbol] = useState('');
  const [marketSymbol, setMarketSymbol] = useState('SPY');
  const [days, setDays] = useState(252);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('comprehensive');
  const [data, setData] = useState(null);

  const handleAnalyze = async () => {
    if (!symbol.trim()) {
      setError('종목 심볼을 입력하세요.');
      return;
    }

    setLoading(true);
    setError(null);
    setData(null);

    try {
      const upperSymbol = symbol.toUpperCase();
      const upperMarket = marketSymbol.toUpperCase();

      let res;
      if (activeTab === 'comprehensive') {
        res = await getComprehensiveQuant(upperSymbol, upperMarket, days);
      } else if (activeTab === 'technical') {
        res = await getTechnicalIndicators(upperSymbol, days);
      } else if (activeTab === 'risk') {
        res = await getRiskMetrics(upperSymbol, upperMarket, days);
      }

      setData(res.data);
    } catch (err) {
      console.error('퀀트 분석 실패:', err);
      setError(err.response?.data?.detail || '퀀트 분석에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleAnalyze();
    }
  };

  const getStatusColor = (status) => {
    if (!status) return '#999';

    const positiveKeywords = ['골든크로스', '상승', '양호', '낮음'];
    const negativeKeywords = ['데드크로스', '하락', '저조', '높음'];

    if (positiveKeywords.some(kw => status.includes(kw))) return '#4caf50';
    if (negativeKeywords.some(kw => status.includes(kw))) return '#f44336';
    return '#ff9800';
  };

  const renderTechnicalIndicators = () => {
    if (!data?.technical_indicators && !data?.moving_averages) return null;

    const tech = data.technical_indicators || data;

    return (
      <div className="quant-section">
        <h4>📊 기술적 지표</h4>

        {/* 이동평균 */}
        {tech.moving_averages && (
          <div className="indicator-card">
            <h5>📈 이동평균선 (Moving Averages)</h5>
            <div className="current-price">
              현재가: ${tech.moving_averages.current_price}
            </div>
            <div className="ma-grid">
              {Object.entries(tech.moving_averages.moving_averages || {}).map(([key, value]) => (
                <div key={key} className="ma-item">
                  <span className="ma-label">{key}</span>
                  <div className="ma-value">${value.value}</div>
                  <div className="ma-distance" style={{
                    color: value.distance > 0 ? '#4caf50' : '#f44336'
                  }}>
                    {value.distance > 0 ? '+' : ''}{value.distance}%
                  </div>
                </div>
              ))}
            </div>
            {tech.moving_averages.signal && (
              <div className="signal-badge" style={{
                backgroundColor: getStatusColor(tech.moving_averages.signal)
              }}>
                {tech.moving_averages.signal}
              </div>
            )}
          </div>
        )}

        {/* RSI */}
        {tech.rsi && !tech.rsi.error && (
          <div className="indicator-card">
            <h5>📉 RSI (Relative Strength Index)</h5>
            <div className="rsi-container">
              <div className="rsi-gauge">
                <div className="rsi-bar">
                  <div
                    className="rsi-fill"
                    style={{
                      width: `${tech.rsi.rsi}%`,
                      backgroundColor:
                        tech.rsi.rsi >= 70
                          ? '#f44336'
                          : tech.rsi.rsi <= 30
                          ? '#4caf50'
                          : '#ff9800',
                    }}
                  ></div>
                </div>
                <div className="rsi-labels">
                  <span>0</span>
                  <span>30</span>
                  <span>50</span>
                  <span>70</span>
                  <span>100</span>
                </div>
              </div>
              <div className="rsi-value">{tech.rsi.rsi}</div>
              <div className="rsi-status" style={{ color: getStatusColor(tech.rsi.status) }}>
                {tech.rsi.status}
              </div>
            </div>
          </div>
        )}

        {/* 볼린저 밴드 */}
        {tech.bollinger_bands && !tech.bollinger_bands.error && (
          <div className="indicator-card">
            <h5>📊 볼린저 밴드 (Bollinger Bands)</h5>
            <div className="bb-chart">
              <div className="bb-line upper">
                상단: ${tech.bollinger_bands.upper_band}
              </div>
              <div className="bb-line middle">
                중간: ${tech.bollinger_bands.middle_band}
              </div>
              <div className="bb-line lower">
                하단: ${tech.bollinger_bands.lower_band}
              </div>
              <div className="bb-current" style={{
                top: `${(1 - tech.bollinger_bands.percent_b) * 100}%`
              }}>
                현재: ${tech.bollinger_bands.current_price}
              </div>
            </div>
            <div className="bb-info">
              <div>%B: {tech.bollinger_bands.percent_b}</div>
              <div>밴드폭: {tech.bollinger_bands.bandwidth}%</div>
            </div>
            <div className="signal-badge" style={{
              backgroundColor: getStatusColor(tech.bollinger_bands.status)
            }}>
              {tech.bollinger_bands.status}
            </div>
          </div>
        )}

        {/* MACD */}
        {tech.macd && !tech.macd.error && (
          <div className="indicator-card">
            <h5>📉 MACD</h5>
            <div className="macd-values">
              <div className="macd-item">
                <span>MACD:</span>
                <strong>{tech.macd.macd}</strong>
              </div>
              <div className="macd-item">
                <span>Signal:</span>
                <strong>{tech.macd.signal}</strong>
              </div>
              <div className="macd-item">
                <span>Histogram:</span>
                <strong style={{
                  color: tech.macd.histogram > 0 ? '#4caf50' : '#f44336'
                }}>
                  {tech.macd.histogram}
                </strong>
              </div>
            </div>
            <div className="signal-badge" style={{
              backgroundColor: getStatusColor(tech.macd.status)
            }}>
              {tech.macd.status}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderRiskMetrics = () => {
    if (!data?.risk_metrics && !data?.volatility) return null;

    const risk = data.risk_metrics || data;

    return (
      <div className="quant-section">
        <h4>⚠️ 리스크 지표</h4>

        <div className="risk-grid">
          {/* 변동성 */}
          {risk.volatility !== undefined && (
            <div className="risk-card">
              <h5>변동성 (Volatility)</h5>
              <div className="risk-value">{risk.volatility}%</div>
              <div className="risk-desc">연율화 표준편차</div>
            </div>
          )}

          {/* 최대 낙폭 */}
          {risk.max_drawdown && !risk.max_drawdown.error && (
            <div className="risk-card">
              <h5>최대 낙폭 (MDD)</h5>
              <div className="risk-value" style={{ color: 'var(--stock-down)' }}>
                {risk.max_drawdown.max_drawdown}%
              </div>
              <div className="risk-desc">
                {risk.max_drawdown.peak_date} → {risk.max_drawdown.trough_date}
              </div>
            </div>
          )}

          {/* 샤프 비율 */}
          {risk.sharpe_ratio && !risk.sharpe_ratio.error && (
            <div className="risk-card">
              <h5>샤프 비율</h5>
              <div className="risk-value">{risk.sharpe_ratio.sharpe_ratio}</div>
              <div className="risk-desc">{risk.sharpe_ratio.interpretation}</div>
              <div className="risk-detail">
                수익: {risk.sharpe_ratio.avg_annual_return}% /
                변동성: {risk.sharpe_ratio.annual_volatility}%
              </div>
            </div>
          )}

          {/* 베타 */}
          {risk.beta && !risk.beta.error && (
            <div className="risk-card">
              <h5>베타 (Beta)</h5>
              <div className="risk-value">{risk.beta.beta}</div>
              <div className="risk-desc">{risk.beta.interpretation}</div>
            </div>
          )}

          {/* 알파 */}
          {risk.alpha && !risk.alpha.error && (
            <div className="risk-card">
              <h5>알파 (Alpha)</h5>
              <div className="risk-value" style={{
                color: risk.alpha.alpha > 0 ? '#4caf50' : '#f44336'
              }}>
                {risk.alpha.alpha > 0 ? '+' : ''}{risk.alpha.alpha}%
              </div>
              <div className="risk-desc">{risk.alpha.interpretation}</div>
              <div className="risk-detail">
                실제: {risk.alpha.actual_return}% /
                기대: {risk.alpha.expected_return}%
              </div>
            </div>
          )}

          {/* 트래킹 에러 */}
          {risk.tracking_error && !risk.tracking_error.error && (
            <div className="risk-card">
              <h5>트래킹 에러</h5>
              <div className="risk-value">{risk.tracking_error.tracking_error}%</div>
              <div className="risk-desc">{risk.tracking_error.interpretation}</div>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderMarketComparison = () => {
    if (!data?.market_comparison) return null;

    const market = data.market_comparison;

    return (
      <div className="quant-section">
        <h4>📊 시장 대비 성과 (vs {data.market_benchmark})</h4>
        <div className="risk-grid">
          {market.beta && !market.beta.error && (
            <div className="risk-card">
              <h5>베타 (Beta)</h5>
              <div className="risk-value">{market.beta.beta}</div>
              <div className="risk-desc">{market.beta.interpretation}</div>
            </div>
          )}

          {market.alpha && !market.alpha.error && (
            <div className="risk-card">
              <h5>알파 (Alpha)</h5>
              <div className="risk-value" style={{
                color: market.alpha.alpha > 0 ? '#4caf50' : '#f44336'
              }}>
                {market.alpha.alpha > 0 ? '+' : ''}{market.alpha.alpha}%
              </div>
              <div className="risk-desc">{market.alpha.interpretation}</div>
            </div>
          )}

          {market.tracking_error && !market.tracking_error.error && (
            <div className="risk-card">
              <h5>트래킹 에러</h5>
              <div className="risk-value">{market.tracking_error.tracking_error}%</div>
              <div className="risk-desc">{market.tracking_error.interpretation}</div>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="quant-analysis">
      <div className="quant-header">
        <h2>⚙️ 퀀트/기술 분석</h2>
        <div className="input-group">
          <input
            type="text"
            placeholder="종목 심볼 (예: AAPL)"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
          />
          <input
            type="text"
            placeholder="벤치마크 (기본: SPY)"
            value={marketSymbol}
            onChange={(e) => setMarketSymbol(e.target.value)}
            disabled={loading}
            className="small-input"
          />
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            disabled={loading}
            className="small-input"
          >
            <option value={30}>1개월</option>
            <option value={90}>3개월</option>
            <option value={180}>6개월</option>
            <option value={252}>1년</option>
            <option value={504}>2년</option>
          </select>
          <button onClick={handleAnalyze} disabled={loading}>
            {loading ? '분석 중...' : '분석'}
          </button>
        </div>
      </div>

      <div className="tab-buttons">
        <button
          className={activeTab === 'comprehensive' ? 'active' : ''}
          onClick={() => setActiveTab('comprehensive')}
        >
          종합 분석
        </button>
        <button
          className={activeTab === 'technical' ? 'active' : ''}
          onClick={() => setActiveTab('technical')}
        >
          기술적 지표
        </button>
        <button
          className={activeTab === 'risk' ? 'active' : ''}
          onClick={() => setActiveTab('risk')}
        >
          리스크 지표
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {data && (
        <div className="quant-results">
          <div className="data-info">
            <h3>{data.symbol}</h3>
            <p>
              분석 기간: {data.start_date} ~ {data.end_date} ({data.data_points}일)
            </p>
          </div>

          {activeTab === 'comprehensive' && (
            <>
              {renderTechnicalIndicators()}
              {renderRiskMetrics()}
              {renderMarketComparison()}
            </>
          )}

          {activeTab === 'technical' && renderTechnicalIndicators()}
          {activeTab === 'risk' && renderRiskMetrics()}
        </div>
      )}

      {/* 워크플로우 내비게이션 */}
      <div className="admin-workflow-nav">
        <button
          className="admin-workflow-link"
          onClick={() => navigate('/admin/report')}
        >
          종합 리포트 →
        </button>
      </div>
    </div>
  );
};

export default QuantAnalysis;
