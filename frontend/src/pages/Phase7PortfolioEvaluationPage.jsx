import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
  const [assetClass, setAssetClass] = useState('');
  const [currency, setCurrency] = useState('');
  const [returnType, setReturnType] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [historyItems, setHistoryItems] = useState([]);
  const [historyDetail, setHistoryDetail] = useState(null);
  const [comparisonSelection, setComparisonSelection] = useState({});
  const [comparisonResult, setComparisonResult] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [activeTab, setActiveTab] = useState('summary');
  const navigate = useNavigate();

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
    const extensions = {};
    if (assetClass) {
      extensions.asset_class = assetClass;
    }
    if (currency) {
      extensions.currency = currency;
    }
    if (returnType) {
      extensions.return_type = returnType;
    }
    const response = await evaluatePhase7Portfolio({
      portfolio_id: Number(selectedPortfolioId),
      period: { start: periodStart, end: periodEnd },
      rebalance,
      extensions: Object.keys(extensions).length ? extensions : undefined,
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
      <h1 className="phase7-title">포트폴리오 평가</h1>
      <p className="phase7-subtitle">
        사용자가 직접 구성한 포트폴리오의 과거 데이터 기반 성과·리스크를 확인합니다.
      </p>

      {statusMessage && <div className="phase7-status">{statusMessage}</div>}

      <section className="phase7-card">
        <h2>1) 평가 실행</h2>
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
        <div className="phase7-advanced">
          <button
            type="button"
            className="phase7-advanced-toggle"
            onClick={() => setShowAdvanced((prev) => !prev)}
          >
            {showAdvanced ? '고급 옵션 닫기' : '고급 옵션 열기'}
          </button>
          {showAdvanced && (
            <div className="phase7-form-row phase7-advanced-panel">
              <label>
                자산군
                <select value={assetClass} onChange={(event) => setAssetClass(event.target.value)}>
                  <option value="">선택</option>
                  <option value="EQUITY">국내 주식</option>
                  <option value="BOND">채권</option>
                  <option value="COMMODITY">원자재</option>
                  <option value="GOLD">금</option>
                  <option value="REIT">리츠</option>
                  <option value="ETF">ETF</option>
                </select>
              </label>
              <label>
                통화 기준
                <select value={currency} onChange={(event) => setCurrency(event.target.value)}>
                  <option value="">선택</option>
                  <option value="KRW">KRW</option>
                  <option value="USD">USD</option>
                </select>
              </label>
              <label>
                수익 기준
                <select value={returnType} onChange={(event) => setReturnType(event.target.value)}>
                  <option value="">선택</option>
                  <option value="PRICE">가격 수익</option>
                  <option value="TOTAL_RETURN">총수익(배당 포함)</option>
                </select>
              </label>
            </div>
          )}
        </div>
        <button type="button" className="phase7-primary" onClick={handleEvaluate}>
          평가 실행
        </button>

        {evaluationResult && (
          <div className="phase7-result">
            <div className="phase7-tab-header">
              <button
                type="button"
                className={`phase7-tab ${activeTab === 'summary' ? 'active' : ''}`}
                onClick={() => setActiveTab('summary')}
              >
                요약
              </button>
              <button
                type="button"
                className={`phase7-tab ${activeTab === 'detail' ? 'active' : ''}`}
                onClick={() => setActiveTab('detail')}
              >
                분석 상세
              </button>
            </div>

            {activeTab === 'summary' && (
              <>
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
              </>
            )}

            {activeTab === 'detail' && (
              <>
                <h3>분석 상세</h3>
                <div className="phase7-detail-grid">
                  <div className="phase7-detail-card">
                    <h4>롤링 수익률</h4>
                    <p>3Y 데이터: {evaluationResult.extensions?.rolling_returns?.window_3y?.length || 0}건</p>
                    <p>5Y 데이터: {evaluationResult.extensions?.rolling_returns?.window_5y?.length || 0}건</p>
                  </div>
                  <div className="phase7-detail-card">
                    <h4>롤링 변동성</h4>
                    <p>3Y 데이터: {evaluationResult.extensions?.rolling_volatility?.window_3y?.length || 0}건</p>
                  </div>
                  <div className="phase7-detail-card">
                    <h4>연도별 성과</h4>
                    <p>연도 수: {evaluationResult.extensions?.yearly_returns?.length || 0}</p>
                  </div>
                  <div className="phase7-detail-card">
                    <h4>기여도</h4>
                    <p>항목 수: {evaluationResult.extensions?.contributions?.length || 0}</p>
                  </div>
                  <div className="phase7-detail-card">
                    <h4>드로다운 구간</h4>
                    <p>구간 수: {evaluationResult.extensions?.drawdown_segments?.length || 0}</p>
                  </div>
                </div>
                <div className="phase7-note">
                  표와 그래프는 계산 기준 값만 제공합니다.
                </div>
              </>
            )}

            <div className="phase7-disclaimer">
              <Disclaimer type="portfolio" />
            </div>
          </div>
        )}
      </section>

      <section className="phase7-card">
        <h2>2) 평가 히스토리</h2>
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
        <h2>3) 포트폴리오 비교</h2>
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
