import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { runBacktest as runBacktestAPI, comparePortfolios as comparePortfoliosAPI } from '../services/api';
import Disclaimer from '../components/Disclaimer';
import '../styles/Backtest.css';

function BacktestPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [compareMode, setCompareMode] = useState(false);

  // 단일 백테스트 설정
  const [investmentType, setInvestmentType] = useState('moderate');
  const [investmentAmount, setInvestmentAmount] = useState(10000000);
  const [periodYears, setPeriodYears] = useState(1);

  // 비교 모드 설정
  const [selectedTypes, setSelectedTypes] = useState(['moderate']);

  // 포트폴리오 페이지에서 넘어온 백테스트 결과 처리
  useEffect(() => {
    if (location.state?.backtestResult) {
      setResult(location.state.backtestResult);
    }
  }, [location.state]);

  const runBacktest = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await runBacktestAPI({
        investment_type: investmentType,
        investment_amount: investmentAmount,
        period_years: periodYears,
        rebalance_frequency: 'quarterly'
      });

      setResult(response.data.data);
    } catch (err) {
      console.error('Backtest error:', err);
      if (err.response?.status === 429) {
        setError('백테스트는 시간당 5회만 가능합니다. 잠시 후 다시 시도해주세요.');
      } else {
        setError(err.response?.data?.detail || '백테스트 실행 중 오류가 발생했습니다.');
      }
    } finally {
      setLoading(false);
    }
  };

  const comparePortfolios = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await comparePortfoliosAPI({
        investment_types: selectedTypes,
        investment_amount: investmentAmount,
        period_years: periodYears
      });

      setResult(response.data.data);
    } catch (err) {
      console.error('Comparison error:', err);
      if (err.response?.status === 429) {
        setError('비교 분석은 시간당 5회만 가능합니다. 잠시 후 다시 시도해주세요.');
      } else {
        setError(err.response?.data?.detail || '비교 분석 중 오류가 발생했습니다.');
      }
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ko-KR').format(amount);
  };

  const formatPercent = (value) => {
    if (value === undefined || value === null) return '0.0%';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${Number(value).toFixed(2)}%`;
  };

  const toggleTypeSelection = (type) => {
    if (selectedTypes.includes(type)) {
      setSelectedTypes(selectedTypes.filter(t => t !== type));
    } else {
      setSelectedTypes([...selectedTypes, type]);
    }
  };

  if (loading) {
    return (
      <div className="backtest-page">
        <div className="backtest-loading">
          <div className="backtest-spinner"></div>
          <p>백테스트를 실행하고 있습니다...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="backtest-page">
      {/* 헤더 */}
      <div className="backtest-header">
        <h1>📊 포트폴리오 백테스팅</h1>
        <p className="subtitle">과거 데이터로 포트폴리오 성과를 검증하세요</p>
      </div>

      {/* 면책 문구 */}
      <Disclaimer type="backtest" />

      {/* 모드 전환 */}
      <div className="backtest-mode-selector">
        <button
          className={`backtest-mode-btn ${!compareMode ? 'active' : ''}`}
          onClick={() => setCompareMode(false)}
        >
          단일 백테스트
        </button>
        <button
          className={`backtest-mode-btn ${compareMode ? 'active' : ''}`}
          onClick={() => setCompareMode(true)}
        >
          포트폴리오 비교
        </button>
      </div>

      {/* 설정 패널 */}
      <div className="config-panel">
        {!compareMode ? (
          /* 단일 백테스트 설정 */
          <>
            <div className="config-group">
              <label>투자 성향</label>
              <select value={investmentType} onChange={(e) => setInvestmentType(e.target.value)}>
                <option value="conservative">안정형</option>
                <option value="moderate">중립형</option>
                <option value="aggressive">공격형</option>
              </select>
            </div>

            <div className="config-group">
              <label>투자 금액</label>
              <input
                type="text"
                value={formatCurrency(investmentAmount)}
                onChange={(e) => setInvestmentAmount(parseInt(e.target.value.replace(/,/g, '')) || 0)}
              />
            </div>

            <div className="config-group">
              <label>백테스트 기간</label>
              <select value={periodYears} onChange={(e) => setPeriodYears(parseInt(e.target.value))}>
                <option value="1">1년</option>
                <option value="3">3년</option>
                <option value="5">5년</option>
                <option value="10">10년</option>
              </select>
            </div>

            <button className="btn-run" onClick={runBacktest}>
              백테스트 실행
            </button>
          </>
        ) : (
          /* 비교 모드 설정 */
          <>
            <div className="config-group">
              <label>비교할 투자 성향 (복수 선택)</label>
              <div className="type-checkboxes">
                <label>
                  <input
                    type="checkbox"
                    checked={selectedTypes.includes('conservative')}
                    onChange={() => toggleTypeSelection('conservative')}
                  />
                  안정형
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={selectedTypes.includes('moderate')}
                    onChange={() => toggleTypeSelection('moderate')}
                  />
                  중립형
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={selectedTypes.includes('aggressive')}
                    onChange={() => toggleTypeSelection('aggressive')}
                  />
                  공격형
                </label>
              </div>
            </div>

            <div className="config-group">
              <label>투자 금액</label>
              <input
                type="text"
                value={formatCurrency(investmentAmount)}
                onChange={(e) => setInvestmentAmount(parseInt(e.target.value.replace(/,/g, '')) || 0)}
              />
            </div>

            <div className="config-group">
              <label>백테스트 기간</label>
              <select value={periodYears} onChange={(e) => setPeriodYears(parseInt(e.target.value))}>
                <option value="1">1년</option>
                <option value="3">3년</option>
                <option value="5">5년</option>
                <option value="10">10년</option>
              </select>
            </div>

            <button
              className="btn-run"
              onClick={comparePortfolios}
              disabled={selectedTypes.length === 0}
            >
              비교 분석 실행
            </button>
          </>
        )}
      </div>

      {/* 에러 메시지 */}
      {error && (
        <div className="backtest-error">
          <p>{error}</p>
        </div>
      )}

      {/* 결과 표시 */}
      {result && !compareMode && (
        <div className="results-container">
          <h2>백테스트 결과</h2>

          {/* 손실/회복 지표 (핵심 KPI) - 상단 배치 */}
          <div className="risk-metrics-section">
            <h3 className="section-title">📉 손실/회복 지표 (핵심)</h3>
            <div className="metrics-grid primary">
              <div className="metric-card highlight-risk">
                <div className="metric-label">최대 낙폭 (MDD)</div>
                <div className="metric-value negative">
                  -{(result.risk_metrics?.max_drawdown ?? result.max_drawdown).toFixed(2)}%
                </div>
                <div className="metric-hint">고점 대비 최대 하락폭</div>
              </div>

              <div className="metric-card highlight-risk">
                <div className="metric-label">최대 회복 기간</div>
                <div className="metric-value">
                  {result.risk_metrics?.max_recovery_days
                    ? `${result.risk_metrics.max_recovery_days}일`
                    : '데이터 없음'}
                </div>
                <div className="metric-hint">낙폭 후 원금 회복까지 소요 기간</div>
              </div>

              <div className="metric-card highlight-risk">
                <div className="metric-label">최악의 1개월 수익률</div>
                <div className="metric-value negative">
                  {result.risk_metrics?.worst_1m_return
                    ? `${result.risk_metrics.worst_1m_return.toFixed(2)}%`
                    : '데이터 없음'}
                </div>
                <div className="metric-hint">단기 최대 손실 가능성</div>
              </div>

              <div className="metric-card highlight-risk">
                <div className="metric-label">변동성 (위험도)</div>
                <div className="metric-value">
                  {formatPercent(result.risk_metrics?.volatility ?? result.volatility)}
                </div>
                <div className="metric-hint">수익률의 변동 폭</div>
              </div>
            </div>

            {/* 해석 도움 문구 */}
            <div className="interpretation-help">
              <p>💡 <strong>해석 도움:</strong> 낙폭이 크면 회복에 시간이 걸릴 수 있습니다.
              MDD가 높을수록 심리적 압박이 커지며, 회복 기간 동안 인내심이 필요합니다.</p>
            </div>
          </div>

          {/* 수익률 지표 (보조) - 하단 배치 */}
          <div className="return-metrics-section">
            <h3 className="section-title">📈 과거 수익률 (참고용)</h3>
            <p className="section-disclaimer">* 과거 수익률은 미래 성과를 보장하지 않습니다</p>
            <div className="metrics-grid secondary">
              <div className="metric-card">
                <div className="metric-label">총 수익률</div>
                <div className={`metric-value ${result.total_return >= 0 ? 'positive' : 'negative'}`}>
                  {formatPercent(result.historical_observation?.total_return ?? result.total_return)}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">연평균 수익률 (CAGR)</div>
                <div className={`metric-value ${result.annualized_return >= 0 ? 'positive' : 'negative'}`}>
                  {formatPercent(result.historical_observation?.cagr ?? result.annualized_return)}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">샤프 비율</div>
                <div className="metric-value">
                  {(result.historical_observation?.sharpe_ratio ?? result.sharpe_ratio).toFixed(2)}
                </div>
                <div className="metric-hint">위험 대비 초과 수익</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">최종 자산</div>
                <div className="metric-value">{formatCurrency(result.final_value)}원</div>
              </div>
            </div>
          </div>

          {/* 기간 정보 */}
          <div className="period-info">
            <p>백테스트 기간: {new Date(result.start_date).toLocaleDateString()} ~ {new Date(result.end_date).toLocaleDateString()}</p>
            <p>초기 투자: {formatCurrency(result.initial_investment)}원</p>
            <p>리밸런싱 주기: 분기별 (3개월)</p>
          </div>

          {/* 성과 해석 이동 */}
          <div className="nav-link-section">
            <button
              className="backtest-nav-btn"
              onClick={() => navigate('/analysis', {
                state: {
                  metrics: {
                    total_return: result.historical_observation?.total_return ?? result.total_return,
                    cagr: result.historical_observation?.cagr ?? result.annualized_return,
                    volatility: result.risk_metrics?.volatility ?? result.volatility,
                    sharpe_ratio: result.historical_observation?.sharpe_ratio ?? result.sharpe_ratio,
                    max_drawdown: result.risk_metrics?.max_drawdown ?? result.max_drawdown,
                  }
                }
              })}
            >
              성과 해석하기 →
            </button>
          </div>
        </div>
      )}

      {/* 비교 결과 */}
      {result && compareMode && result.comparison && (
        <div className="comparison-container">
          <h2>포트폴리오 비교 결과</h2>

          {/* 최고 성과 - 손실/회복 중심 재정렬 */}
          <div className="best-performers">
            <div className="best-item highlight">
              <span className="label">최저 위험도:</span>
              <span className="value">{result.lowest_risk}</span>
            </div>
            <div className="best-item">
              <span className="label">최고 위험 조정 수익:</span>
              <span className="value">{result.best_risk_adjusted}</span>
            </div>
            <div className="best-item secondary">
              <span className="label">최고 수익률:</span>
              <span className="value">{result.best_return}</span>
            </div>
          </div>

          {/* 해석 도움 문구 */}
          <div className="interpretation-help">
            <p>💡 <strong>해석 도움:</strong> 최저 위험도 포트폴리오는 변동성이 낮습니다.
            낙폭이 클수록 회복에 오래 걸릴 수 있습니다.</p>
          </div>

          {/* 비교 테이블 - 손실/회복 지표 먼저 */}
          <div className="comparison-table">
            <table>
              <thead>
                <tr>
                  <th>포트폴리오</th>
                  <th className="risk-col">최대 낙폭 (MDD)</th>
                  <th className="risk-col">변동성</th>
                  <th>샤프 비율</th>
                  <th className="return-col">총 수익률</th>
                  <th className="return-col">연평균 수익률</th>
                </tr>
              </thead>
              <tbody>
                {result.comparison.map((item, idx) => (
                  <tr key={idx}>
                    <td><strong>{item.portfolio_name}</strong></td>
                    <td className="negative risk-col">-{item.max_drawdown.toFixed(2)}%</td>
                    <td className="risk-col">{formatPercent(item.volatility)}</td>
                    <td>{item.sharpe_ratio.toFixed(2)}</td>
                    <td className={`return-col ${item.total_return >= 0 ? 'positive' : 'negative'}`}>
                      {formatPercent(item.total_return)}
                    </td>
                    <td className={`return-col ${item.annualized_return >= 0 ? 'positive' : 'negative'}`}>
                      {formatPercent(item.annualized_return)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="table-disclaimer">* 과거 수익률은 미래 성과를 보장하지 않습니다</p>
        </div>
      )}

      {/* 안내 사항 */}
      {!result && (
        <div className="info-section">
          <h3>백테스팅이란?</h3>
          <p>
            과거 데이터를 사용하여 투자 전략이나 포트폴리오의 성과를 시뮬레이션하는 방법입니다.
            실제 투자 전에 전략의 유효성을 검증할 수 있습니다.
          </p>

          <h3>주요 지표 설명</h3>
          <h4>📉 손실/회복 지표 (핵심)</h4>
          <ul>
            <li><strong>최대 낙폭 (MDD)</strong>: 고점 대비 최대 하락폭 - 심리적 압박 수준을 나타냅니다</li>
            <li><strong>최대 회복 기간</strong>: 낙폭 후 원금 회복까지 걸린 시간</li>
            <li><strong>변동성</strong>: 수익률의 변동 폭 (높을수록 불안정)</li>
            <li><strong>샤프 비율</strong>: 위험 대비 초과 수익 (높을수록 효율적)</li>
          </ul>
          <h4>📈 과거 수익률 (참고용)</h4>
          <ul>
            <li><strong>총 수익률</strong>: 전체 기간 동안의 누적 수익률</li>
            <li><strong>연평균 수익률 (CAGR)</strong>: 연간 기준으로 환산한 복리 수익률</li>
          </ul>

          <h3>주의사항</h3>
          <p className="warning">
            ⚠️ 백테스팅 결과는 과거 데이터를 기반으로 한 시뮬레이션이며, 미래 수익을 보장하지 않습니다.
            실제 투자 시에는 추가적인 분석과 전문가 상담이 필요합니다.
          </p>
        </div>
      )}
    </div>
  );
}

export default BacktestPage;
