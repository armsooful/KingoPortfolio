import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDiagnosisHistory, getDiagnosis, downloadDiagnosisPDF } from '../services/api';

function DiagnosisHistoryPage() {
  const [historyList, setHistoryList] = useState([]);
  const [selectedDiagnosis, setSelectedDiagnosis] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloadingPDF, setDownloadingPDF] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadDiagnosisHistory();
  }, []);

  const loadDiagnosisHistory = async () => {
    try {
      setIsLoading(true);
      const response = await getDiagnosisHistory(10);
      setHistoryList(response.data.diagnoses || []);
      setError('');
    } catch (err) {
      setError('진단 이력을 불러올 수 없습니다.');
      console.error('Load history error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectDiagnosis = async (diagnosisId) => {
    try {
      const response = await getDiagnosis(diagnosisId);
      setSelectedDiagnosis(response.data);
    } catch (err) {
      setError('진단 상세 정보를 불러올 수 없습니다.');
      console.error('Load diagnosis error:', err);
    }
  };

  const handleDownloadPDF = async (diagnosisId) => {
    try {
      setDownloadingPDF(diagnosisId);
      await downloadDiagnosisPDF(diagnosisId);
      alert('PDF 리포트가 다운로드되었습니다!');
    } catch (err) {
      console.error('PDF download error:', err);
      alert('PDF 다운로드 중 오류가 발생했습니다.');
    } finally {
      setDownloadingPDF(null);
    }
  };

  const getTypeConfig = (investmentType) => {
    const typeConfig = {
      conservative: {
        label: '보수형',
        color: '#4CAF50',
        icon: '🛡️',
      },
      moderate: {
        label: '중도형',
        color: '#FF9800',
        icon: '⚖️',
      },
      aggressive: {
        label: '적극형',
        color: '#F44336',
        icon: '🚀',
      },
    };
    return typeConfig[investmentType] || typeConfig.moderate;
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>진단 이력을 로딩 중입니다...</p>
      </div>
    );
  }

  return (
    <div className="history-container">
      {error && <div className="error-message">{error}</div>}

      <div className="history-layout">
        {/* 왼쪽: 진단 이력 목록 */}
        <div className="history-list-section">
          <div className="history-header">
            <h1>진단 이력</h1>
            <p className="history-count">총 {historyList.length}개</p>
          </div>

          {historyList.length === 0 ? (
            <div className="empty-state">
              <p>진단 이력이 없습니다.</p>
              <button
                className="btn btn-primary"
                onClick={() => navigate('/survey')}
              >
                첫 진단 시작하기
              </button>
            </div>
          ) : (
            <div className="history-list">
              {historyList.map((diagnosis) => {
                const typeConfig = getTypeConfig(diagnosis.investment_type);
                const isSelected =
                  selectedDiagnosis?.diagnosis_id === diagnosis.diagnosis_id;

                return (
                  <div
                    key={diagnosis.diagnosis_id}
                    className={`history-item ${isSelected ? 'selected' : ''}`}
                    onClick={() => handleSelectDiagnosis(diagnosis.diagnosis_id)}
                  >
                    <div className="history-item-header">
                      <span className="history-type-badge" style={{ color: typeConfig.color }}>
                        {typeConfig.icon} {typeConfig.label}
                      </span>
                      <span className="history-date">
                        {formatDate(diagnosis.created_at)}
                      </span>
                    </div>

                    <div className="history-item-body">
                      <div className="history-score">
                        <span className="label">점수:</span>
                        <span className="value" style={{ color: typeConfig.color }}>
                          {diagnosis.score.toFixed(2)}/10
                        </span>
                      </div>
                      <div className="history-confidence">
                        <span className="label">신뢰도:</span>
                        <span className="value">
                          {(diagnosis.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>

                    {diagnosis.monthly_investment && (
                      <div className="history-investment">
                        월 투자액: {diagnosis.monthly_investment}만원
                      </div>
                    )}

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDownloadPDF(diagnosis.diagnosis_id);
                      }}
                      disabled={downloadingPDF === diagnosis.diagnosis_id}
                      style={{
                        marginTop: '10px',
                        width: '100%',
                        padding: '8px 12px',
                        background: downloadingPDF === diagnosis.diagnosis_id ? '#ccc' : '#667eea',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: downloadingPDF === diagnosis.diagnosis_id ? 'not-allowed' : 'pointer',
                        fontSize: '0.9rem',
                        fontWeight: '500'
                      }}
                    >
                      {downloadingPDF === diagnosis.diagnosis_id ? '⏳ 생성 중...' : '📄 PDF 다운로드'}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 오른쪽: 진단 상세 정보 */}
        <div className="history-detail-section">
          {selectedDiagnosis ? (
            <div className="detail-card">
              {/* 헤더 */}
              <div className="detail-header">
                <div className="detail-type-badge">
                  {getTypeConfig(selectedDiagnosis.investment_type).icon}
                  {getTypeConfig(selectedDiagnosis.investment_type).label}
                </div>
                <div className="detail-date">
                  {formatDate(selectedDiagnosis.created_at)}
                </div>
              </div>

              {/* 점수 및 신뢰도 */}
              <div className="detail-scores">
                <div className="score-box">
                  <div className="score-label">진단 점수</div>
                  <div
                    className="score-value"
                    style={{
                      color: getTypeConfig(selectedDiagnosis.investment_type).color,
                    }}
                  >
                    {selectedDiagnosis.score.toFixed(2)}/10
                  </div>
                </div>
                <div className="score-box">
                  <div className="score-label">신뢰도</div>
                  <div
                    className="score-value"
                    style={{
                      color: getTypeConfig(selectedDiagnosis.investment_type).color,
                    }}
                  >
                    {(selectedDiagnosis.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              </div>

              {/* 설명 */}
              <div className="detail-description">
                <h3>투자성향</h3>
                <p>{selectedDiagnosis.description}</p>
              </div>

              {/* 특징 */}
              <div className="detail-characteristics">
                <h3>특징</h3>
                <ul>
                  {selectedDiagnosis.characteristics &&
                    selectedDiagnosis.characteristics.map((char, index) => (
                      <li key={index}>{char}</li>
                    ))}
                </ul>
              </div>

              {/* 포트폴리오 */}
              <div className="detail-portfolio">
                <h3>추천 포트폴리오</h3>
                <div className="portfolio-items">
                  {selectedDiagnosis.recommended_ratio &&
                    Object.entries(selectedDiagnosis.recommended_ratio).map(
                      ([asset, ratio]) => (
                        <div key={asset} className="portfolio-row">
                          <span className="portfolio-asset">
                            {getAssetLabel(asset)}
                          </span>
                          <span className="portfolio-ratio">{ratio}%</span>
                        </div>
                      )
                    )}
                </div>
              </div>

              {/* 기대 수익률 */}
              <div className="detail-return">
                <h3>기대 연 수익률</h3>
                <p className="return-value">
                  {selectedDiagnosis.expected_annual_return}
                </p>
              </div>

              {/* 월 투자액 */}
              {selectedDiagnosis.monthly_investment && (
                <div className="detail-investment">
                  <h3>월 투자액</h3>
                  <p>{selectedDiagnosis.monthly_investment}만원</p>
                </div>
              )}

              {/* 액션 버튼 */}
              <div className="detail-buttons">
                <button
                  className="btn btn-primary"
                  onClick={() => navigate('/survey')}
                >
                  새로운 진단 시작
                </button>
              </div>
            </div>
          ) : (
            <div className="empty-detail">
              <p>진단 기록을 선택하면 상세 정보가 표시됩니다.</p>
            </div>
          )}
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

export default DiagnosisHistoryPage;