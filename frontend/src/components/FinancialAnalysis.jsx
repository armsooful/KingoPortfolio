import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getFinancialAnalysis,
  getFinancialScore,
  getFinancialScoreV2,
} from '../services/api';
import '../styles/FinancialAnalysis.css';

const FinancialAnalysis = () => {
  const navigate = useNavigate();
  const [symbol, setSymbol] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [scoreV1, setScoreV1] = useState(null);
  const [scoreV2, setScoreV2] = useState(null);

  const handleAnalyze = async () => {
    if (!symbol.trim()) {
      setError('종목 심볼을 입력하세요.');
      return;
    }

    setLoading(true);
    setError(null);
    setAnalysis(null);
    setScoreV1(null);
    setScoreV2(null);

    try {
      const upperSymbol = symbol.toUpperCase();

      // 병렬로 모든 API 호출
      const [analysisRes, scoreV1Res, scoreV2Res] = await Promise.all([
        getFinancialAnalysis(upperSymbol),
        getFinancialScore(upperSymbol),
        getFinancialScoreV2(upperSymbol),
      ]);

      setAnalysis(analysisRes.data);
      setScoreV1(scoreV1Res.data);
      setScoreV2(scoreV2Res.data);
    } catch (err) {
      console.error('재무 분석 실패:', err);
      setError(
        err.response?.data?.detail || '재무 분석에 실패했습니다. 종목 심볼을 확인하세요.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleAnalyze();
    }
  };

  const formatNumber = (value) => {
    if (value === null || value === undefined) return 'N/A';
    return typeof value === 'number' ? value.toLocaleString() : value;
  };

  const getGradeColor = (grade) => {
    const colors = {
      'A+': '#4caf50',
      A: '#66bb6a',
      'B+': '#9ccc65',
      B: '#d4e157',
      'C+': '#ffee58',
      C: '#ffa726',
      D: '#ff7043',
      F: '#ef5350',
    };
    return colors[grade] || '#9e9e9e';
  };

  return (
    <div className="financial-analysis">
      <div className="analysis-header">
        <h2>⚙️ 재무 분석</h2>
        <div className="search-box">
          <input
            type="text"
            placeholder="종목 심볼 입력 (예: AAPL, GOOGL)"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
          />
          <button onClick={handleAnalyze} disabled={loading}>
            {loading ? '분석 중...' : '분석'}
          </button>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {analysis && (
        <div className="analysis-results">
          {/* 회사 정보 */}
          <div className="company-info">
            <h3>{analysis.company_name}</h3>
            <p className="symbol">{analysis.symbol}</p>
          </div>

          {/* 점수 비교 */}
          {scoreV1 && scoreV2 && (
            <div className="score-comparison">
              <div className="score-card">
                <h4>V1 평가 (보수적)</h4>
                <div
                  className="score-circle"
                  style={{ borderColor: getGradeColor(scoreV1.grade) }}
                >
                  <span className="score-value">{scoreV1.total_score}</span>
                  <span className="score-grade" style={{ color: getGradeColor(scoreV1.grade) }}>
                    {scoreV1.grade}
                  </span>
                </div>
                <p className="score-rating">{scoreV1.rating}</p>
              </div>

              <div className="score-card highlighted">
                <h4>V2 평가 (성장주 친화적)</h4>
                <div
                  className="score-circle"
                  style={{ borderColor: getGradeColor(scoreV2.grade) }}
                >
                  <span className="score-value">{scoreV2.total_score}</span>
                  <span className="score-grade" style={{ color: getGradeColor(scoreV2.grade) }}>
                    {scoreV2.grade}
                  </span>
                </div>
                <p className="score-rating">{scoreV2.rating}</p>
                {scoreV2.investment_style && (
                  <div className="investment-style">
                    <span className="style-badge">{scoreV2.investment_style.style}</span>
                    <p className="style-desc">{scoreV2.investment_style.description}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 세부 점수 */}
          {scoreV2 && scoreV2.score_details && (
            <div className="score-details">
              <h4>세부 점수 (V2)</h4>
              {scoreV2.korean_stock && (
                <div className="fa-warning-box">
                  ℹ️ 한국 주식은 성장성 제외, 수익성(40점), 안정성(35점), 배당(25점)으로 평가됩니다.
                </div>
              )}
              <div className="score-bars">
                {scoreV2.score_details.growth_score !== undefined && (
                  <div className="score-bar">
                    <span className="bar-label">성장성</span>
                    <div className="bar-container">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${(scoreV2.score_details.growth_score / 30) * 100}%`,
                        }}
                      ></div>
                    </div>
                    <span className="bar-value">
                      {scoreV2.score_details.growth_score ?? 0}/30
                    </span>
                  </div>
                )}
                {scoreV2.score_details.profitability_score !== undefined && (
                  <div className="score-bar">
                    <span className="bar-label">수익성</span>
                    <div className="bar-container">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${(scoreV2.score_details.profitability_score / (scoreV2.korean_stock ? 40 : 30)) * 100}%`,
                        }}
                      ></div>
                    </div>
                    <span className="bar-value">
                      {scoreV2.score_details.profitability_score ?? 0}/{scoreV2.korean_stock ? 40 : 30}
                    </span>
                  </div>
                )}
                {scoreV2.score_details.stability_score !== undefined && (
                  <div className="score-bar">
                    <span className="bar-label">안정성</span>
                    <div className="bar-container">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${(scoreV2.score_details.stability_score / (scoreV2.korean_stock ? 35 : 25)) * 100}%`,
                        }}
                      ></div>
                    </div>
                    <span className="bar-value">
                      {scoreV2.score_details.stability_score ?? 0}/{scoreV2.korean_stock ? 35 : 25}
                    </span>
                  </div>
                )}
                {scoreV2.score_details.dividend_score !== undefined && (
                  <div className="score-bar">
                    <span className="bar-label">배당/주주환원</span>
                    <div className="bar-container">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${(scoreV2.score_details.dividend_score / (scoreV2.korean_stock ? 25 : 15)) * 100}%`,
                        }}
                      ></div>
                    </div>
                    <span className="bar-value">
                      {scoreV2.score_details.dividend_score ?? 0}/{scoreV2.korean_stock ? 25 : 15}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 성장률 */}
          <div className="metrics-section">
            <h4>📈 성장률 (CAGR)</h4>
            <div className="metrics-grid">
              <div className="metric-item">
                <span className="metric-label">매출 3년 CAGR</span>
                <span className="metric-value">
                  {formatNumber(analysis.growth_metrics.revenue_cagr_3y)}%
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">매출 5년 CAGR</span>
                <span className="metric-value">
                  {formatNumber(analysis.growth_metrics.revenue_cagr_5y)}%
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">EPS 3년 CAGR</span>
                <span className="metric-value">
                  {formatNumber(analysis.growth_metrics.eps_cagr_3y)}%
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">EPS 5년 CAGR</span>
                <span className="metric-value">
                  {formatNumber(analysis.growth_metrics.eps_cagr_5y)}%
                </span>
              </div>
            </div>
          </div>

          {/* 이익률 */}
          <div className="metrics-section">
            <h4>💰 이익률</h4>
            <div className="metrics-grid">
              <div className="metric-item">
                <span className="metric-label">매출총이익률</span>
                <span className="metric-value">
                  {formatNumber(analysis.profit_margins.gross_margin)}%
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">영업이익률</span>
                <span className="metric-value">
                  {formatNumber(analysis.profit_margins.operating_margin)}%
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">순이익률</span>
                <span className="metric-value">
                  {formatNumber(analysis.profit_margins.net_margin)}%
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">FCF 마진</span>
                <span className="metric-value">
                  {formatNumber(analysis.profit_margins.fcf_margin)}%
                </span>
              </div>
            </div>
          </div>

          {/* 수익성 */}
          <div className="metrics-section">
            <h4>📊 수익성</h4>
            <div className="metrics-grid">
              <div className="metric-item">
                <span className="metric-label">ROE</span>
                <span className="metric-value">
                  {formatNumber(analysis.profitability.roe)}%
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">ROA</span>
                <span className="metric-value">
                  {formatNumber(analysis.profitability.roa)}%
                </span>
              </div>
            </div>
          </div>

          {/* 재무 건전성 */}
          <div className="metrics-section">
            <h4>🏦 재무 건전성</h4>
            <div className="metrics-grid">
              <div className="metric-item">
                <span className="metric-label">부채비율</span>
                <span className="metric-value">
                  {formatNumber(analysis.financial_health.debt_to_equity)}%
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">순부채비율</span>
                <span className="metric-value">
                  {formatNumber(analysis.financial_health.net_debt_ratio)}%
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">유동비율</span>
                <span className="metric-value">
                  {formatNumber(analysis.financial_health.current_ratio)}
                </span>
              </div>
            </div>
          </div>

          {/* 배당 */}
          <div className="metrics-section">
            <h4>💵 배당</h4>
            <div className="metrics-grid">
              <div className="metric-item">
                <span className="metric-label">배당수익률</span>
                <span className="metric-value">
                  {formatNumber(analysis.dividend_metrics.current_dividend_yield)}%
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">배당성향</span>
                <span className="metric-value">
                  {formatNumber(analysis.dividend_metrics.payout_ratio)}%
                </span>
              </div>
            </div>
          </div>

          {/* 밸류에이션 */}
          <div className="metrics-section">
            <h4>💼 밸류에이션</h4>
            <div className="metrics-grid">
              <div className="metric-item">
                <span className="metric-label">PER</span>
                <span className="metric-value">
                  {formatNumber(analysis.valuation.pe_ratio)}
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">PBR</span>
                <span className="metric-value">
                  {formatNumber(analysis.valuation.pb_ratio)}
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">PEG</span>
                <span className="metric-value">
                  {formatNumber(analysis.valuation.peg_ratio)}
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">시가총액</span>
                <span className="metric-value">
                  {analysis.valuation.market_cap
                    ? `$${(analysis.valuation.market_cap / 1e9).toFixed(1)}B`
                    : 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 워크플로우 내비게이션 */}
      <div className="admin-workflow-nav">
        <button
          className="admin-workflow-link"
          onClick={() => navigate('/admin/valuation')}
        >
          밸류에이션 →
        </button>
      </div>
    </div>
  );
};

export default FinancialAnalysis;
