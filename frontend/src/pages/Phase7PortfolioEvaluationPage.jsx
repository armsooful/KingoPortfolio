import { useEffect, useMemo, useState } from 'react';
import Disclaimer from '../components/Disclaimer';
import {
  createPhase7Portfolio,
  listPhase7Portfolios,
  evaluatePhase7Portfolio,
  listPhase7Evaluations,
  getPhase7EvaluationDetail,
  comparePhase7Portfolios,
} from '../services/api';
import '../styles/Phase7PortfolioEvaluation.css';

const emptyItem = () => ({ id: '', name: '', weight: '' });

function Phase7PortfolioEvaluationPage() {
  const [portfolioType, setPortfolioType] = useState('SECURITY');
  const [portfolioName, setPortfolioName] = useState('');
  const [portfolioDescription, setPortfolioDescription] = useState('');
  const [items, setItems] = useState([emptyItem()]);
  const [portfolios, setPortfolios] = useState([]);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState('');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [rebalance, setRebalance] = useState('NONE');
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [historyItems, setHistoryItems] = useState([]);
  const [historyDetail, setHistoryDetail] = useState(null);
  const [comparisonSelection, setComparisonSelection] = useState({});
  const [comparisonResult, setComparisonResult] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');

  const portfolioMap = useMemo(() => {
    const map = new Map();
    portfolios.forEach((portfolio) => map.set(portfolio.portfolio_id, portfolio));
    return map;
  }, [portfolios]);

  const weightSum = useMemo(() => {
    return items.reduce((sum, item) => sum + Number(item.weight || 0), 0);
  }, [items]);

  const refreshPortfolios = async () => {
    const response = await listPhase7Portfolios();
    setPortfolios(response.data.portfolios || []);
  };

  const refreshHistory = async (portfolioId) => {
    if (!portfolioId) {
      setHistoryItems([]);
      return;
    }
    const response = await listPhase7Evaluations(portfolioId);
    setHistoryItems(response.data.evaluations || []);
  };

  useEffect(() => {
    refreshPortfolios();
  }, []);

  useEffect(() => {
    refreshHistory(selectedPortfolioId);
  }, [selectedPortfolioId]);

  const handleItemChange = (index, field, value) => {
    const next = items.map((item, idx) =>
      idx === index ? { ...item, [field]: value } : item
    );
    setItems(next);
  };

  const addItem = () => {
    setItems([...items, emptyItem()]);
  };

  const removeItem = (index) => {
    if (items.length === 1) {
      return;
    }
    setItems(items.filter((_, idx) => idx !== index));
  };

  const handleCreatePortfolio = async () => {
    setStatusMessage('');
    const normalizedItems = items
      .filter((item) => item.id && item.name)
      .map((item) => ({
        id: item.id.trim(),
        name: item.name.trim(),
        weight: Number(item.weight || 0),
      }));

    if (normalizedItems.length === 0) {
      setStatusMessage('구성 항목을 입력해 주세요.');
      return;
    }

    if (Math.abs(weightSum - 1) > 0.0001) {
      setStatusMessage('비중 합계는 1.0이어야 합니다.');
      return;
    }

    await createPhase7Portfolio({
      portfolio_type: portfolioType,
      portfolio_name: portfolioName,
      description: portfolioDescription || null,
      items: normalizedItems,
    });

    setPortfolioName('');
    setPortfolioDescription('');
    setItems([emptyItem()]);
    await refreshPortfolios();
    setStatusMessage('포트폴리오가 저장되었습니다.');
  };

  const handleEvaluate = async () => {
    setStatusMessage('');
    if (!selectedPortfolioId) {
      setStatusMessage('평가할 포트폴리오를 선택해 주세요.');
      return;
    }
    if (!periodStart || !periodEnd) {
      setStatusMessage('분석 기간을 입력해 주세요.');
      return;
    }
    const response = await evaluatePhase7Portfolio({
      portfolio_id: Number(selectedPortfolioId),
      period: { start: periodStart, end: periodEnd },
      rebalance,
    });
    setEvaluationResult(response.data);
    await refreshHistory(selectedPortfolioId);
  };

  const handleHistoryDetail = async (evaluationId) => {
    const response = await getPhase7EvaluationDetail(evaluationId);
    setHistoryDetail(response.data);
  };

  const handleToggleComparison = (portfolioId) => {
    setComparisonSelection((prev) => ({
      ...prev,
      [portfolioId]: !prev[portfolioId],
    }));
  };

  const handleCompare = async () => {
    const selectedIds = Object.keys(comparisonSelection)
      .filter((id) => comparisonSelection[id])
      .map((id) => Number(id));
    if (selectedIds.length < 2) {
      setStatusMessage('비교 대상은 최소 2개가 필요합니다.');
      return;
    }
    const response = await comparePhase7Portfolios({
      portfolio_ids: selectedIds,
    });
    setComparisonResult(response.data);
  };

  return (
    <div className="phase7-eval-page">
      <h1 className="phase7-title">포트폴리오 평가(Phase 7)</h1>
      <p className="phase7-subtitle">
        사용자가 직접 구성한 포트폴리오의 과거 데이터 기반 성과·리스크를 확인합니다.
      </p>

      {statusMessage && <div className="phase7-status">{statusMessage}</div>}

      <section className="phase7-card">
        <h2>1) 포트폴리오 구성 저장</h2>
        <div className="phase7-form-row">
          <label>
            유형
            <select
              value={portfolioType}
              onChange={(event) => setPortfolioType(event.target.value)}
            >
              <option value="SECURITY">종목</option>
              <option value="SECTOR">섹터</option>
            </select>
          </label>
          <label>
            이름
            <input
              value={portfolioName}
              onChange={(event) => setPortfolioName(event.target.value)}
              placeholder="포트폴리오 이름"
            />
          </label>
          <label>
            메모
            <input
              value={portfolioDescription}
              onChange={(event) => setPortfolioDescription(event.target.value)}
              placeholder="선택 사항"
            />
          </label>
        </div>

        <div className="phase7-items">
          {items.map((item, index) => (
            <div key={`item-${index}`} className="phase7-item-row">
              <input
                value={item.id}
                onChange={(event) => handleItemChange(index, 'id', event.target.value)}
                placeholder={portfolioType === 'SECTOR' ? '섹터 코드' : '종목 코드'}
              />
              <input
                value={item.name}
                onChange={(event) => handleItemChange(index, 'name', event.target.value)}
                placeholder="이름"
              />
              <input
                type="number"
                step="0.0001"
                value={item.weight}
                onChange={(event) => handleItemChange(index, 'weight', event.target.value)}
                placeholder="비중"
              />
              <button type="button" onClick={() => removeItem(index)}>
                삭제
              </button>
            </div>
          ))}
          <div className="phase7-item-actions">
            <button type="button" onClick={addItem}>
              항목 추가
            </button>
            <span>합계: {weightSum.toFixed(4)}</span>
          </div>
        </div>
        <button type="button" className="phase7-primary" onClick={handleCreatePortfolio}>
          저장
        </button>
      </section>

      <section className="phase7-card">
        <h2>2) 평가 실행</h2>
        <div className="phase7-form-row">
          <label>
            포트폴리오 선택
            <select
              value={selectedPortfolioId}
              onChange={(event) => setSelectedPortfolioId(event.target.value)}
            >
              <option value="">선택</option>
              {portfolios.map((portfolio) => (
                <option key={portfolio.portfolio_id} value={portfolio.portfolio_id}>
                  {portfolio.portfolio_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            시작일
            <input
              type="date"
              value={periodStart}
              onChange={(event) => setPeriodStart(event.target.value)}
            />
          </label>
          <label>
            종료일
            <input
              type="date"
              value={periodEnd}
              onChange={(event) => setPeriodEnd(event.target.value)}
            />
          </label>
          <label>
            리밸런싱
            <select
              value={rebalance}
              onChange={(event) => setRebalance(event.target.value)}
            >
              <option value="NONE">없음</option>
              <option value="MONTHLY">월간</option>
              <option value="QUARTERLY">분기</option>
            </select>
          </label>
        </div>
        <button type="button" className="phase7-primary" onClick={handleEvaluate}>
          평가 실행
        </button>

        {evaluationResult && (
          <div className="phase7-result">
            <h3>평가 결과</h3>
            <p>
              기간: {evaluationResult.period.start} ~ {evaluationResult.period.end}
            </p>
            <div className="phase7-metrics">
              <div className="phase7-metric">
                <span>누적수익률</span>
                <strong>{evaluationResult.metrics.cumulative_return}</strong>
              </div>
              <div className="phase7-metric">
                <span>CAGR</span>
                <strong>{evaluationResult.metrics.cagr}</strong>
              </div>
              <div className="phase7-metric">
                <span>변동성</span>
                <strong>{evaluationResult.metrics.volatility}</strong>
              </div>
              <div className="phase7-metric">
                <span>MDD</span>
                <strong>{evaluationResult.metrics.max_drawdown}</strong>
              </div>
            </div>
            <div className="phase7-disclaimer">
              <Disclaimer type="portfolio" />
            </div>
          </div>
        )}
      </section>

      <section className="phase7-card">
        <h2>3) 평가 히스토리</h2>
        {historyItems.length === 0 ? (
          <p>평가 이력이 없습니다.</p>
        ) : (
          <ul className="phase7-history">
            {historyItems.map((item) => (
              <li key={item.evaluation_id}>
                <span>
                  {item.period.start} ~ {item.period.end} ({item.rebalance})
                </span>
                <span className="phase7-hash">{item.result_hash}</span>
                <button type="button" onClick={() => handleHistoryDetail(item.evaluation_id)}>
                  상세
                </button>
              </li>
            ))}
          </ul>
        )}
        {historyDetail && (
          <div className="phase7-result">
            <h3>상세 결과</h3>
            <p>
              기간: {historyDetail.result.period.start} ~ {historyDetail.result.period.end}
            </p>
            <div className="phase7-metrics">
              <div className="phase7-metric">
                <span>누적수익률</span>
                <strong>{historyDetail.result.metrics.cumulative_return}</strong>
              </div>
              <div className="phase7-metric">
                <span>CAGR</span>
                <strong>{historyDetail.result.metrics.cagr}</strong>
              </div>
              <div className="phase7-metric">
                <span>변동성</span>
                <strong>{historyDetail.result.metrics.volatility}</strong>
              </div>
              <div className="phase7-metric">
                <span>MDD</span>
                <strong>{historyDetail.result.metrics.max_drawdown}</strong>
              </div>
            </div>
          </div>
        )}
      </section>

      <section className="phase7-card">
        <h2>4) 포트폴리오 비교</h2>
        <div className="phase7-compare-list">
          {portfolios.map((portfolio) => (
            <label key={`compare-${portfolio.portfolio_id}`}>
              <input
                type="checkbox"
                checked={!!comparisonSelection[portfolio.portfolio_id]}
                onChange={() => handleToggleComparison(portfolio.portfolio_id)}
              />
              {portfolio.portfolio_name}
            </label>
          ))}
        </div>
        <button type="button" className="phase7-primary" onClick={handleCompare}>
          비교 실행
        </button>
        {comparisonResult && (
          <div className="phase7-result">
            <h3>비교 결과</h3>
            <div className="phase7-compare-grid">
              {comparisonResult.portfolios.map((item) => (
                <div key={`compare-result-${item.portfolio_id}`} className="phase7-compare-card">
                  <div className="phase7-compare-header">
                    <span>포트폴리오</span>
                    <strong>
                      {portfolioMap.get(item.portfolio_id)?.portfolio_name ||
                        `#${item.portfolio_id}`}
                    </strong>
                  </div>
                  <p>
                    기간: {item.period.start} ~ {item.period.end}
                  </p>
                  <div className="phase7-metric">
                    <span>누적수익률</span>
                    <strong>{item.metrics.cumulative_return}</strong>
                  </div>
                  <div className="phase7-metric">
                    <span>CAGR</span>
                    <strong>{item.metrics.cagr}</strong>
                  </div>
                  <div className="phase7-metric">
                    <span>변동성</span>
                    <strong>{item.metrics.volatility}</strong>
                  </div>
                  <div className="phase7-metric">
                    <span>MDD</span>
                    <strong>{item.metrics.max_drawdown}</strong>
                  </div>
                </div>
              ))}
            </div>
            <div className="phase7-disclaimer">
              <Disclaimer type="portfolio" />
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

export default Phase7PortfolioEvaluationPage;
