import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getScenarios, getScenarioDetail, runBacktest } from '../services/api';
import Disclaimer from '../components/Disclaimer';
import '../styles/ScenarioSimulation.css';

function ScenarioSimulationPage() {
  const navigate = useNavigate();
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [scenarioDetail, setScenarioDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [error, setError] = useState(null);

  // 시뮬레이션 설정
  const [periodYears, setPeriodYears] = useState(3);
  const [investmentAmount, setInvestmentAmount] = useState(10000000);
  const [maxLossLimit, setMaxLossLimit] = useState(20); // 최대 허용 손실 %

  // 시나리오 목록 로드
  useEffect(() => {
    loadScenarios();
  }, []);

  // 선택된 시나리오 상세 로드
  useEffect(() => {
    if (selectedScenario) {
      loadScenarioDetail(selectedScenario);
    }
  }, [selectedScenario]);

  const loadScenarios = async () => {
    try {
      setLoading(true);
      const response = await getScenarios();
      setScenarios(response.data);
    } catch (err) {
      console.error('Failed to load scenarios:', err);
      setError('시나리오 목록을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const loadScenarioDetail = async (scenarioId) => {
    try {
      const response = await getScenarioDetail(scenarioId);
      setScenarioDetail(response.data);
    } catch (err) {
      console.error('Failed to load scenario detail:', err);
    }
  };

  const runSimulation = async () => {
    if (!selectedScenario || !scenarioDetail) {
      setError('시나리오를 선택해주세요.');
      return;
    }

    try {
      setSimulating(true);
      setError(null);

      // 시나리오의 자산 배분을 기반으로 백테스트 실행
      const response = await runBacktest({
        portfolio: {
          allocation: scenarioDetail.allocation,
          securities: [] // 시나리오 기반 시뮬레이션
        },
        investment_amount: investmentAmount,
        period_years: periodYears,
        rebalance_frequency: 'quarterly'
      });

      // 결과 페이지로 이동
      navigate('/backtest', {
        state: {
          backtestResult: response.data.data,
          scenarioInfo: {
            name: scenarioDetail.name_ko,
            maxLossLimit: maxLossLimit,
            disclaimer: scenarioDetail.disclaimer
          }
        }
      });
    } catch (err) {
      console.error('Simulation error:', err);
      if (err.response?.status === 429) {
        setError('모의실험은 시간당 5회만 가능합니다. 잠시 후 다시 시도해주세요.');
      } else {
        setError(err.response?.data?.detail || '모의실험 실행 중 오류가 발생했습니다.');
      }
    } finally {
      setSimulating(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ko-KR').format(amount);
  };

  // 시나리오 카드 색상
  const getScenarioColor = (scenarioId) => {
    const colors = {
      'MIN_VOL': '#4CAF50',
      'DEFENSIVE': '#2196F3',
      'GROWTH': '#FF9800'
    };
    return colors[scenarioId] || '#667eea';
  };

  if (loading) {
    return (
      <div className="scenario-page">
        <div className="scenario-loading">
          <div className="scenario-spinner"></div>
          <p>시나리오를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="scenario-page">
      {/* 헤더 */}
      <div className="scenario-header">
        <h1>시나리오 기반 모의실험</h1>
        <p className="subtitle">
          설문 없이 바로 시작하세요. 학습 목표에 맞는 시나리오를 선택하고 모의실험을 실행해보세요.
        </p>
      </div>

      {/* 면책 문구 */}
      <Disclaimer type="simulation" />

      {/* 시나리오 선택 */}
      <div className="scenario-selection">
        <h2>1. 학습 시나리오 선택</h2>
        <div className="scenario-cards">
          {scenarios.map((scenario) => (
            <div
              key={scenario.id}
              className={`scenario-card ${selectedScenario === scenario.id ? 'selected' : ''}`}
              onClick={() => setSelectedScenario(scenario.id)}
              style={{
                borderColor: selectedScenario === scenario.id ? getScenarioColor(scenario.id) : undefined
              }}
            >
              <div
                className="scenario-icon"
                style={{ backgroundColor: getScenarioColor(scenario.id) }}
              >
                {scenario.id === 'MIN_VOL' && '🛡️'}
                {scenario.id === 'DEFENSIVE' && '⚖️'}
                {scenario.id === 'GROWTH' && '📈'}
              </div>
              <h3>{scenario.name_ko}</h3>
              <p className="scenario-desc">{scenario.short_description}</p>
              {selectedScenario === scenario.id && (
                <div className="selected-badge">선택됨</div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 시나리오 상세 정보 */}
      {scenarioDetail && (
        <div className="scenario-detail">
          <h2>선택한 시나리오: {scenarioDetail.name_ko}</h2>
          <p className="detail-description">{scenarioDetail.description}</p>

          <div className="detail-grid">
            {/* 자산 배분 */}
            <div className="detail-card">
              <h4>자산 배분 비율</h4>
              <div className="allocation-bars">
                <div className="allocation-item">
                  <span>주식</span>
                  <div className="bar-container">
                    <div
                      className="bar bar-stocks"
                      style={{ width: `${scenarioDetail.allocation.stocks}%` }}
                    />
                  </div>
                  <span>{scenarioDetail.allocation.stocks}%</span>
                </div>
                <div className="allocation-item">
                  <span>채권</span>
                  <div className="bar-container">
                    <div
                      className="bar bar-bonds"
                      style={{ width: `${scenarioDetail.allocation.bonds}%` }}
                    />
                  </div>
                  <span>{scenarioDetail.allocation.bonds}%</span>
                </div>
                <div className="allocation-item">
                  <span>단기금융</span>
                  <div className="bar-container">
                    <div
                      className="bar bar-money-market"
                      style={{ width: `${scenarioDetail.allocation.money_market}%` }}
                    />
                  </div>
                  <span>{scenarioDetail.allocation.money_market}%</span>
                </div>
                <div className="allocation-item">
                  <span>금</span>
                  <div className="bar-container">
                    <div
                      className="bar bar-gold"
                      style={{ width: `${scenarioDetail.allocation.gold}%` }}
                    />
                  </div>
                  <span>{scenarioDetail.allocation.gold}%</span>
                </div>
              </div>
            </div>

            {/* 위험 지표 */}
            <div className="detail-card risk-card">
              <h4>예상 위험 지표 (참고용)</h4>
              <div className="risk-items">
                <div className="risk-item">
                  <span className="label">예상 변동성</span>
                  <span className="value">{scenarioDetail.risk_metrics.expected_volatility}</span>
                </div>
                <div className="risk-item">
                  <span className="label">과거 최대 낙폭</span>
                  <span className="value negative">{scenarioDetail.risk_metrics.historical_max_drawdown}</span>
                </div>
                <div className="risk-item">
                  <span className="label">회복 기간 예상</span>
                  <span className="value">{scenarioDetail.risk_metrics.recovery_expectation}</span>
                </div>
              </div>
              <p className="risk-disclaimer">* 과거 데이터 기반 참고치이며, 미래 성과를 보장하지 않습니다</p>
            </div>
          </div>

          {/* 학습 포인트 */}
          <div className="learning-points">
            <h4>이 시나리오에서 학습할 수 있는 내용</h4>
            <ul>
              {scenarioDetail.learning_points.map((point, idx) => (
                <li key={idx}>{point}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* 시뮬레이션 설정 */}
      {selectedScenario && (
        <div className="simulation-config">
          <h2>2. 모의실험 설정</h2>

          <div className="config-grid">
            <div className="config-item">
              <label>모의실험 기간</label>
              <select
                value={periodYears}
                onChange={(e) => setPeriodYears(parseInt(e.target.value))}
              >
                <option value="1">1년</option>
                <option value="3">3년</option>
                <option value="5">5년</option>
                <option value="10">10년</option>
              </select>
            </div>

            <div className="config-item">
              <label>가상 투자금액</label>
              <input
                type="text"
                value={formatCurrency(investmentAmount)}
                onChange={(e) => setInvestmentAmount(parseInt(e.target.value.replace(/,/g, '')) || 0)}
              />
              <span className="unit">원</span>
            </div>

            <div className="config-item">
              <label>최대 허용 손실</label>
              <div className="loss-limit-input">
                <input
                  type="range"
                  min="5"
                  max="50"
                  value={maxLossLimit}
                  onChange={(e) => setMaxLossLimit(parseInt(e.target.value))}
                />
                <span className="loss-value">-{maxLossLimit}%</span>
              </div>
              <p className="config-hint">
                이 수치를 초과하는 손실이 발생할 경우 알림을 받습니다
              </p>
            </div>
          </div>

          {/* 에러 메시지 */}
          {error && (
            <div className="scenario-error">
              <p>{error}</p>
            </div>
          )}

          {/* 실행 버튼 */}
          <button
            className="btn-simulate"
            onClick={runSimulation}
            disabled={simulating || !selectedScenario}
          >
            {simulating ? (
              <>
                <span className="scenario-spinner-small"></span>
                모의실험 실행 중...
              </>
            ) : (
              '모의실험 실행'
            )}
          </button>

          <p className="simulate-note">
            * 모의실험은 과거 데이터를 기반으로 한 시뮬레이션이며, 실제 투자 결과와 다를 수 있습니다.
          </p>
        </div>
      )}

      {/* 안내 섹션 (시나리오 미선택 시) */}
      {!selectedScenario && (
        <div className="info-section">
          <h3>시나리오 기반 학습이란?</h3>
          <p>
            설문 없이도 바로 투자 전략을 학습할 수 있는 방법입니다.
            미리 정의된 시나리오를 선택하고, 과거 데이터를 기반으로 모의실험을 실행하여
            각 전략의 특성을 이해할 수 있습니다.
          </p>

          <h3>어떤 시나리오를 선택해야 할까요?</h3>
          <ul>
            <li><strong>변동성 최소화</strong>: 안정성을 최우선으로 하는 전략을 학습하고 싶은 경우</li>
            <li><strong>방어형</strong>: 시장 하락에 대비하는 방어적 전략을 이해하고 싶은 경우</li>
            <li><strong>성장형</strong>: 장기적 자산 성장 전략의 특성을 파악하고 싶은 경우</li>
          </ul>

          <h3>용어가 어렵다면?</h3>
          <p>
            투자 용어가 생소하다면{' '}
            <button
              className="ss-link-btn"
              onClick={() => navigate('/terminology')}
            >
              용어학습 도구
            </button>
            를 이용해 보세요. 설문을 완료하지 않아도 모의실험은 언제든 이용 가능합니다.
          </p>
        </div>
      )}
    </div>
  );
}

export default ScenarioSimulationPage;
