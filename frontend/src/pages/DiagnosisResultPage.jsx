import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function DiagnosisResultPage() {
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    // sessionStorage에서 진단 결과 로드
    const savedResult = sessionStorage.getItem('diagnosisResult');
    if (savedResult) {
      try {
        setResult(JSON.parse(savedResult));
      } catch (error) {
        console.error('Failed to parse diagnosis result:', error);
        navigate('/survey');
      }
    } else {
      navigate('/survey');
    }
    setIsLoading(false);
  }, [navigate]);

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>결과를 준비 중입니다...</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="result-container">
        <div className="error-message">진단 결과를 찾을 수 없습니다.</div>
      </div>
    );
  }

  const { investment_type, score, confidence, description, characteristics, recommended_ratio, expected_annual_return, monthly_investment, ai_analysis } = result;

  // 학습 성향별 색상 및 아이콘
  const typeConfig = {
    conservative: {
      label: '안정성 중심 학습 성향',
      color: '#4CAF50',
      icon: '🛡️',
      description: '안정적인 자산 운용 전략을 학습하고자 하는 성향입니다.',
    },
    moderate: {
      label: '균형형 학습 성향',
      color: '#FF9800',
      icon: '⚖️',
      description: '안정성과 성장성의 균형을 이해하고자 하는 학습 성향입니다.',
    },
    aggressive: {
      label: '성장성 중심 학습 성향',
      color: '#F44336',
      icon: '🚀',
      description: '성장성 높은 자산군의 특성을 학습하고자 하는 성향입니다.',
    },
  };

  const config = typeConfig[investment_type] || typeConfig.moderate;

  return (
    <div className="result-container">
      <div className="result-card">
        {/* 학습 성향 결과 */}
        <div className="result-header">
          <div className="result-icon" style={{ fontSize: '3rem' }}>
            {config.icon}
          </div>
          <h1 className="result-type" style={{ color: config.color }}>
            {config.label}
          </h1>
          <p className="result-subtitle">{config.description}</p>
        </div>

        {/* 점수 및 신뢰도 */}
        <div className="scores-section">
          <div className="score-card">
            <div className="score-label">진단 점수</div>
            <div className="score-value" style={{ color: config.color }}>
              {score.toFixed(2)} / 10
            </div>
            <div className="score-bar">
              <div
                className="score-fill"
                style={{
                  width: `${(score / 10) * 100}%`,
                  backgroundColor: config.color,
                }}
              ></div>
            </div>
          </div>

          <div className="score-card">
            <div className="score-label">신뢰도</div>
            <div className="score-value" style={{ color: config.color }}>
              {(confidence * 100).toFixed(0)}%
            </div>
            <div className="score-bar">
              <div
                className="score-fill"
                style={{
                  width: `${confidence * 100}%`,
                  backgroundColor: config.color,
                }}
              ></div>
            </div>
          </div>
        </div>

        {/* 설명 */}
        <div className="description-section">
          <h2>학습 성향 설명</h2>
          <p>{description}</p>
        </div>

        {/* AI 분석 섹션 */}
        {ai_analysis && (
          <div className="ai-analysis-section">
            <h2>
              <span className="ai-badge">🤖 AI 분석</span>
            </h2>

            {ai_analysis.personalized_analysis && (
              <div className="ai-card">
                <h3>개인화된 학습 성향 분석</h3>
                <p className="ai-content">{ai_analysis.personalized_analysis}</p>
              </div>
            )}

            {ai_analysis.investment_advice && (
              <div className="ai-card">
                <h3>학습 방향 제안</h3>
                <p className="ai-content">{ai_analysis.investment_advice}</p>
              </div>
            )}

            {ai_analysis.risk_warning && (
              <div className="ai-card risk-warning">
                <h3>⚠️ 위험 주의사항</h3>
                <p className="ai-content">{ai_analysis.risk_warning}</p>
              </div>
            )}
          </div>
        )}

        {/* 특징 */}
        <div className="characteristics-section">
          <h2>당신의 특징</h2>
          <ul className="characteristics-list">
            {characteristics &&
              characteristics.map((char, index) => (
                <li key={index}>{char}</li>
              ))}
          </ul>
        </div>

        {/* 시뮬레이션 예시 */}
        <div className="portfolio-section">
          <h2>시뮬레이션용 자산 배분 예시</h2>
          <p style={{ fontSize: '0.9rem', color: '#666', marginBottom: '1rem' }}>
            ⚠️ 본 배분은 교육 목적의 일반적 예시이며, 특정인에 대한 맞춤형 투자 권유가 아닙니다.
          </p>
          <div className="portfolio-grid">
            {recommended_ratio &&
              Object.entries(recommended_ratio).map(([asset, ratio]) => (
                <div key={asset} className="portfolio-item">
                  <div className="asset-name">{getAssetLabel(asset)}</div>
                  <div className="asset-ratio">{ratio}%</div>
                  <div className="asset-bar">
                    <div
                      className="asset-fill"
                      style={{
                        width: `${ratio}%`,
                        backgroundColor: getAssetColor(asset),
                      }}
                    ></div>
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* 과거 평균 수익률 */}
        <div className="return-section">
          <h2>과거 평균 수익률 (참고)</h2>
          <div className="return-value" style={{ color: config.color }}>
            {expected_annual_return}
          </div>
          <p style={{ fontSize: '0.85rem', color: '#888', marginTop: '0.5rem' }}>
            * 과거 수익률은 미래 성과를 예측하지 않습니다
          </p>
        </div>

        {/* 월 시뮬레이션 금액 */}
        {monthly_investment && (
          <div className="investment-section">
            <h2>시뮬레이션 월 투입 금액</h2>
            <div className="investment-value">{monthly_investment}만원</div>
          </div>
        )}

        {/* 버튼 영역 */}
        <div className="button-section">
          <button
            className="btn btn-secondary"
            onClick={() => navigate('/history')}
          >
            진단 이력 보기
          </button>
          <button
            className="btn btn-primary"
            onClick={() => navigate('/survey')}
          >
            다시 진단하기
          </button>
        </div>

        {/* 안내 메시지 */}
        <div className="result-info">
          <p>
            💡 본 결과는 현재 시점의 학습 성향 분석이며 시간이 지나면서 변할 수 있습니다. 정기적인 재진단을 권장합니다.
          </p>
          <p style={{ fontSize: '0.85rem', color: '#888', marginTop: '0.5rem' }}>
            ⚠️ 본 서비스는 교육 목적의 학습 도구이며, 투자 권유·자문 서비스를 제공하지 않습니다.
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * 자산 이름을 한글로 변환
 */
function getAssetLabel(asset) {
  const assetMap = {
    stocks: '주식',
    bonds: '채권',
    money_market: '머니마켓',
    gold: '금',
    other: '기타',
  };
  return assetMap[asset] || asset;
}

/**
 * 자산별 색상
 */
function getAssetColor(asset) {
  const colorMap = {
    stocks: '#FF6B6B',
    bonds: '#4ECDC4',
    money_market: '#45B7D1',
    gold: '#FFA500',
    other: '#95E1D3',
  };
  return colorMap[asset] || '#999';
}

export default DiagnosisResultPage;