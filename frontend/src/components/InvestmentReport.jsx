import React, { useState } from 'react';
import { getComprehensiveReport } from '../services/api';
import '../styles/InvestmentReport.css';

const InvestmentReport = () => {
  const [symbol, setSymbol] = useState('');
  const [marketSymbol, setMarketSymbol] = useState('SPY');
  const [days, setDays] = useState(252);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [report, setReport] = useState(null);

  const handleGenerate = async () => {
    if (!symbol.trim()) {
      setError('종목 심볼을 입력하세요.');
      return;
    }

    setLoading(true);
    setError(null);
    setReport(null);

    try {
      const res = await getComprehensiveReport(symbol.toUpperCase(), marketSymbol, days);
      setReport(res.data);
    } catch (err) {
      console.error('리포트 생성 실패:', err);
      setError(err.response?.data?.detail || '리포트 생성에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleGenerate();
    }
  };

  return (
    <div className="investment-report">
      <div className="report-header">
        <h2>⚙️ 종합 투자 리포트</h2>
        <p className="report-subtitle">객관적 분석 정보 제공 (투자 권고 아님)</p>

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
            <option value={90}>3개월</option>
            <option value={180}>6개월</option>
            <option value={252}>1년</option>
            <option value={504}>2년</option>
          </select>
          <button onClick={handleGenerate} disabled={loading}>
            {loading ? '생성 중...' : '리포트 생성'}
          </button>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {report && (
        <div className="report-content">
          {/* 면책 조항 */}
          <div className="disclaimer">
            ⚠️ {report.disclaimer}
          </div>

          {/* 리포트 정보 */}
          <div className="report-info">
            <h3>{report.symbol}</h3>
            <div className="meta-info">
              <span>생성 시각: {new Date(report.generated_at).toLocaleString('ko-KR')}</span>
              <span>분석 기간: {report.analysis_period_days}일</span>
              <span>벤치마크: {report.benchmark}</span>
            </div>
          </div>

          {/* 1. 재무 건전성 */}
          {report.financial_analysis && !report.financial_analysis.error && (
            <div className="report-section">
              <h4>💰 재무 건전성</h4>
              <div className="health-card" style={{
                borderLeft: `4px solid ${report.financial_analysis.health_category.color}`
              }}>
                <div className="health-header">
                  <div className="health-score">
                    <span className="score-label">종합 점수</span>
                    <span className="score-value">{report.financial_analysis.total_score}/100</span>
                    <span className="score-grade">{report.financial_analysis.grade}</span>
                  </div>
                  <div className="health-category">
                    <div className="category-label">
                      {report.financial_analysis.health_category.category}
                    </div>
                    <div className="category-tier">
                      {report.financial_analysis.health_category.tier} 구간
                    </div>
                  </div>
                </div>

                {report.financial_analysis.investment_style && (
                  <div className="investment-style">
                    <span className="style-badge">
                      {report.financial_analysis.investment_style.style}
                    </span>
                    <p>{report.financial_analysis.investment_style.description}</p>
                  </div>
                )}

                <div className="score-breakdown">
                  <div className="breakdown-item">
                    <span>성장성</span>
                    <strong>{report.financial_analysis.score_details.growth_score}/30</strong>
                  </div>
                  <div className="breakdown-item">
                    <span>수익성</span>
                    <strong>{report.financial_analysis.score_details.profitability_score}/30</strong>
                  </div>
                  <div className="breakdown-item">
                    <span>안정성</span>
                    <strong>{report.financial_analysis.score_details.stability_score}/25</strong>
                  </div>
                  <div className="breakdown-item">
                    <span>배당/주주환원</span>
                    <strong>{report.financial_analysis.score_details.dividend_score}/15</strong>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 2. 밸류에이션 */}
          {report.valuation && !report.valuation.error && (
            <div className="report-section">
              <h4>💼 밸류에이션</h4>
              <div className="valuation-card" style={{
                borderLeft: `4px solid ${report.valuation.category.color}`
              }}>
                <div className="valuation-header">
                  <div className="valuation-category">
                    {report.valuation.category.category}
                  </div>
                  <div className="valuation-description">
                    {report.valuation.category.description}
                  </div>
                </div>

                {report.valuation.dcf_neutral && (
                  <div className="dcf-summary">
                    <h5>DCF 밸류에이션 (중립 시나리오)</h5>
                    <div className="dcf-values">
                      <div className="dcf-item">
                        <span>적정가</span>
                        <strong>${report.valuation.dcf_neutral.fair_value}</strong>
                      </div>
                      <div className="dcf-item">
                        <span>현재가</span>
                        <strong>${report.valuation.dcf_neutral.current_price}</strong>
                      </div>
                      <div className="dcf-item">
                        <span>차이</span>
                        <strong style={{
                          color: report.valuation.dcf_neutral.upside_downside > 0 ? '#4caf50' : '#f44336'
                        }}>
                          {report.valuation.dcf_neutral.upside_downside > 0 ? '+' : ''}
                          {report.valuation.dcf_neutral.upside_downside}%
                        </strong>
                      </div>
                    </div>
                  </div>
                )}

                {report.valuation.multiples && (
                  <div className="multiples-summary">
                    <h5>주요 멀티플</h5>
                    <div className="multiples-grid">
                      {report.valuation.multiples.pe_comparison && (
                        <div className="multiple-item">
                          <span>PER</span>
                          <strong>{report.valuation.multiples.pe_comparison.current}</strong>
                          <small>업종 평균: {report.valuation.multiples.pe_comparison.industry_avg}</small>
                        </div>
                      )}
                      {report.valuation.multiples.pb_comparison && (
                        <div className="multiple-item">
                          <span>PBR</span>
                          <strong>{report.valuation.multiples.pb_comparison.current}</strong>
                          <small>업종 평균: {report.valuation.multiples.pb_comparison.industry_avg}</small>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 3. 리스크 분석 */}
          {report.risk_analysis && !report.risk_analysis.error && (
            <div className="report-section">
              <h4>⚠️ 리스크 분석</h4>
              <div className="risk-card" style={{
                borderLeft: `4px solid ${report.risk_analysis.risk_category.color}`
              }}>
                <div className="risk-header">
                  <div className="risk-category">
                    {report.risk_analysis.risk_category.category}
                  </div>
                  <div className="risk-level">
                    리스크 {report.risk_analysis.risk_category.level}
                  </div>
                </div>
                <div className="risk-description">
                  {report.risk_analysis.risk_category.description}
                </div>

                <div className="risk-metrics">
                  <div className="risk-metric">
                    <span>변동성 (연율화)</span>
                    <strong>{report.risk_analysis.volatility}%</strong>
                  </div>
                  <div className="risk-metric">
                    <span>최대 낙폭 (MDD)</span>
                    <strong style={{ color: 'var(--stock-down)' }}>
                      {report.risk_analysis.max_drawdown}%
                    </strong>
                  </div>
                  <div className="risk-metric">
                    <span>샤프 비율</span>
                    <strong>{report.risk_analysis.sharpe_ratio}</strong>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 4. 시장 대비 성과 */}
          {report.market_performance && (
            <div className="report-section">
              <h4>📊 시장 대비 성과</h4>
              <div className="performance-card">
                <div className="performance-category">
                  {report.market_performance.category}
                </div>
                <div className="performance-details">
                  <div className="performance-item">
                    <span>알파 (Alpha)</span>
                    <strong style={{
                      color: report.market_performance.alpha_value > 0 ? '#4caf50' : '#f44336'
                    }}>
                      {report.market_performance.alpha_value > 0 ? '+' : ''}
                      {report.market_performance.alpha_value}%
                    </strong>
                    <small>{report.market_performance.alpha_description}</small>
                  </div>
                  <div className="performance-item">
                    <span>베타 (Beta)</span>
                    <strong>{report.market_performance.beta_value}</strong>
                    <small>{report.market_performance.beta_description}</small>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 5. 기술적 신호 */}
          {report.technical_signals && report.technical_signals.length > 0 && (
            <div className="report-section">
              <h4>📈 기술적 신호</h4>
              <div className="signals-grid">
                {report.technical_signals.map((signal, idx) => (
                  <div key={idx} className="signal-item">
                    <div className="signal-indicator">{signal.indicator}</div>
                    <div className="signal-status">{signal.signal}</div>
                    {signal.value && (
                      <div className="signal-value">값: {signal.value}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 6. 뉴스 감성 분석 */}
          {report.news_sentiment && !report.news_sentiment.error && (
            <div className="report-section">
              <h4>📰 뉴스 감성 분석 (AI)</h4>
              <div className="news-sentiment-card" style={{
                borderLeft: `4px solid ${report.news_sentiment.category.color}`
              }}>
                <div className="sentiment-header">
                  <div className="sentiment-category">
                    {report.news_sentiment.category.category}
                  </div>
                  <div className="sentiment-score">
                    점수: {report.news_sentiment.sentiment_score > 0 ? '+' : ''}
                    {report.news_sentiment.sentiment_score.toFixed(3)}
                  </div>
                </div>
                <div className="sentiment-description">
                  {report.news_sentiment.category.description}
                </div>

                {/* 감성 분포 게이지 바 */}
                {report.news_sentiment.sentiment_distribution && (
                  <div className="sentiment-distribution">
                    <h5>📊 감성 분포 ({report.news_sentiment.news_count}개 뉴스)</h5>
                    <div className="gauge-container">
                      <div className="gauge-bar">
                        <div
                          className="gauge-positive"
                          style={{ width: `${report.news_sentiment.sentiment_distribution.positive_ratio}%` }}
                          title={`긍정: ${report.news_sentiment.sentiment_distribution.positive_count}개`}
                        >
                          {report.news_sentiment.sentiment_distribution.positive_ratio > 10 &&
                            `${report.news_sentiment.sentiment_distribution.positive_ratio.toFixed(0)}%`
                          }
                        </div>
                        <div
                          className="gauge-neutral"
                          style={{ width: `${report.news_sentiment.sentiment_distribution.neutral_ratio}%` }}
                          title={`중립: ${report.news_sentiment.sentiment_distribution.neutral_count}개`}
                        >
                          {report.news_sentiment.sentiment_distribution.neutral_ratio > 10 &&
                            `${report.news_sentiment.sentiment_distribution.neutral_ratio.toFixed(0)}%`
                          }
                        </div>
                        <div
                          className="gauge-negative"
                          style={{ width: `${report.news_sentiment.sentiment_distribution.negative_ratio}%` }}
                          title={`부정: ${report.news_sentiment.sentiment_distribution.negative_count}개`}
                        >
                          {report.news_sentiment.sentiment_distribution.negative_ratio > 10 &&
                            `${report.news_sentiment.sentiment_distribution.negative_ratio.toFixed(0)}%`
                          }
                        </div>
                      </div>
                      <div className="gauge-legend">
                        <span className="legend-item">
                          <span className="legend-dot positive"></span>
                          긍정 {report.news_sentiment.sentiment_distribution.positive_count}개
                        </span>
                        <span className="legend-item">
                          <span className="legend-dot neutral"></span>
                          중립 {report.news_sentiment.sentiment_distribution.neutral_count}개
                        </span>
                        <span className="legend-item">
                          <span className="legend-dot negative"></span>
                          부정 {report.news_sentiment.sentiment_distribution.negative_count}개
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* 투자 인사이트 */}
                {report.news_sentiment.investment_insights && report.news_sentiment.investment_insights.length > 0 && (
                  <div className="investment-insights">
                    <h5>💡 투자 인사이트</h5>
                    <ul>
                      {report.news_sentiment.investment_insights.map((insight, idx) => (
                        <li key={idx}>{insight}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 시장 포지션 & 액션 가이드 */}
                {report.news_sentiment.market_position && (
                  <div className="market-action-guide">
                    <div className="market-position">
                      <span className="label">시장 포지션</span>
                      <span className="value">{report.news_sentiment.market_position}</span>
                    </div>
                    <div className="action-guide">
                      <span className="label">액션 가이드</span>
                      <span className="value">{report.news_sentiment.action_guide}</span>
                    </div>
                  </div>
                )}

                {report.news_sentiment.summary && (
                  <div className="sentiment-summary">
                    <p>{report.news_sentiment.summary}</p>
                  </div>
                )}

                {report.news_sentiment.positive_factors && report.news_sentiment.positive_factors.length > 0 && (
                  <div className="sentiment-factors">
                    <h5>🟢 긍정 요인</h5>
                    <ul>
                      {report.news_sentiment.positive_factors.map((factor, idx) => (
                        <li key={idx}>{factor}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {report.news_sentiment.negative_factors && report.news_sentiment.negative_factors.length > 0 && (
                  <div className="sentiment-factors">
                    <h5>🔴 부정 요인</h5>
                    <ul>
                      {report.news_sentiment.negative_factors.map((factor, idx) => (
                        <li key={idx}>{factor}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {report.news_sentiment.key_issues && report.news_sentiment.key_issues.length > 0 && (
                  <div className="sentiment-factors">
                    <h5>🔑 핵심 이슈</h5>
                    <ul>
                      {report.news_sentiment.key_issues.map((issue, idx) => (
                        <li key={idx}>{issue}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {report.news_sentiment.recent_news && report.news_sentiment.recent_news.length > 0 && (
                  <div className="recent-news">
                    <h5>📑 최근 뉴스 ({report.news_sentiment.news_count}개)</h5>
                    <ul>
                      {report.news_sentiment.recent_news.map((news, idx) => (
                        <li key={idx}>
                          <a href={news.url} target="_blank" rel="noopener noreferrer">
                            {news.title}
                          </a>
                          <small> - {news.source}</small>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="ai-disclaimer">
                  <small>
                    💡 본 분석은 AI 기반 정성적 평가이며, 투자 권고가 아닙니다.
                  </small>
                </div>
              </div>
            </div>
          )}

          {/* 7. 종합 평가 */}
          {report.overall_assessment && (
            <div className="report-section">
              <h4>✅ 종합 평가</h4>
              <div className="assessment-card">
                <p className="assessment-summary">{report.overall_assessment.summary}</p>

                {report.overall_assessment.strengths.length > 0 && (
                  <div className="assessment-group">
                    <h5>🟢 강점</h5>
                    <ul>
                      {report.overall_assessment.strengths.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {report.overall_assessment.concerns.length > 0 && (
                  <div className="assessment-group">
                    <h5>🟠 개선 필요 영역</h5>
                    <ul>
                      {report.overall_assessment.concerns.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 하단 면책 조항 */}
          <div className="disclaimer bottom">
            <p>
              ⚠️ <strong>중요 안내</strong>
            </p>
            <ul>
              <li>본 리포트는 객관적인 분석 정보만을 제공하며, 특정 투자 상품의 매수나 매도를 권고하지 않습니다.</li>
              <li>모든 투자 결정은 투자자 본인의 판단과 책임하에 이루어져야 합니다.</li>
              <li>과거 데이터 기반 분석이므로 미래 수익을 보장하지 않습니다.</li>
              <li>투자 전 반드시 전문가와 상담하시기 바랍니다.</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default InvestmentReport;
