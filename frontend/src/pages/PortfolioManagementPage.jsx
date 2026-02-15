import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../styles/PortfolioManagement.css';

export default function PortfolioManagementPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [strategies, setStrategies] = useState([]);
  const [selectedType, setSelectedType] = useState('conservative');
  const [detailPortfolio, setDetailPortfolio] = useState(null);
  const [topSecurities, setTopSecurities] = useState(null);
  const [availableSecurities, setAvailableSecurities] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    loadStrategies();
    loadAvailableSecurities();
  }, []);

  useEffect(() => {
    if (selectedType) {
      loadDetailPortfolio();
      loadTopSecurities();
    }
  }, [selectedType]);

  const loadStrategies = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `${import.meta.env.VITE_API_URL}/admin/portfolio/strategies`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setStrategies(response.data.data.strategies);
    } catch (err) {
      console.error('Failed to load strategies:', err);
    }
  };

  const loadDetailPortfolio = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `${import.meta.env.VITE_API_URL}/admin/portfolio/composition/${selectedType}?investment_amount=10000000`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setDetailPortfolio(response.data.data);
    } catch (err) {
      console.error('Failed to load portfolio:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadTopSecurities = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `${import.meta.env.VITE_API_URL}/admin/portfolio/top-securities/${selectedType}?limit=10`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setTopSecurities(response.data.data);
    } catch (err) {
      console.error('Failed to load top securities:', err);
    }
  };

  const loadAvailableSecurities = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `${import.meta.env.VITE_API_URL}/admin/portfolio/available-securities`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setAvailableSecurities(response.data.data);
    } catch (err) {
      console.error('Failed to load available securities:', err);
    }
  };

  const formatCurrency = (amount) => new Intl.NumberFormat('ko-KR').format(amount);

  const formatPercent = (value) => {
    if (value === undefined || value === null) return '0.0%';
    return `${Number(value).toFixed(1)}%`;
  };

  const getRiskLevelColor = (level) => {
    const colors = { low: '#4CAF50', medium: '#FF9800', high: '#F44336' };
    return colors[level] || '#666';
  };

  const getRiskLevelName = (level) => {
    const names = { low: '낮음', medium: '중간', high: '높음' };
    return names[level] || level;
  };

  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card" style={{ maxWidth: '1400px' }}>
          {/* Header */}
          <div className="result-header">
            <button className="admin-back-btn" onClick={() => navigate('/admin')}>
              ← 관리자 홈
            </button>
            <div className="result-icon" style={{ fontSize: '3rem' }}>
              ⚙️
            </div>
            <h1 className="result-type" style={{ color: 'var(--primary)' }}>
              포트폴리오 전략 관리
            </h1>
            <p className="result-subtitle">
              투자 성향별 포트폴리오 구성 및 종목 관리
            </p>
          </div>

          {/* Tab Navigation */}
          <div className="pm-tabs">
            {[
              { key: 'overview', label: '전략 개요' },
              { key: 'detail', label: '상세 구성' },
              { key: 'securities', label: '종목 풀 현황' },
            ].map((tab) => (
              <button
                key={tab.key}
                className={`pm-tab ${activeTab === tab.key ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="pm-tab-content">
              <h2>투자 성향별 전략 비교</h2>

              {strategies.map((strategy) => (
                <div key={strategy.investment_type} className="pm-strategy-card">
                  <div className="pm-strategy-header">
                    <h3>{strategy.display_name}</h3>
                    <button
                      className="pm-strategy-detail-btn"
                      onClick={() => {
                        setSelectedType(strategy.investment_type);
                        setActiveTab('detail');
                      }}
                    >
                      상세 보기 →
                    </button>
                  </div>

                  {/* Asset Allocation */}
                  <div className="pm-grid-4">
                    {Object.entries(strategy.allocation_strategy)
                      .filter(([key]) => ['stocks', 'etfs', 'bonds', 'deposits'].includes(key))
                      .map(([assetClass, weights]) => (
                      <div key={assetClass} className="pm-stat-box">
                        <div className="pm-stat-label">
                          {assetClass === 'stocks' ? '주식' : assetClass === 'etfs' ? 'ETF' : assetClass === 'bonds' ? '채권' : '예금'}
                        </div>
                        <div className="pm-stat-value" style={{ color: 'var(--primary)' }}>
                          {weights.target}%
                        </div>
                        <div className="pm-stat-range">
                          범위: {weights.min}-{weights.max}%
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Sample Portfolio Stats */}
                  {strategy.sample_portfolio && (
                    <div className="pm-grid-3">
                      <div className="pm-stat-box-compact">
                        <div className="pm-stat-label-sm">과거 연평균 수익률</div>
                        <div className="pm-stat-value-lg" style={{ color: 'var(--stock-up)' }}>
                          {formatPercent(strategy.sample_portfolio.statistics.expected_annual_return)}
                        </div>
                      </div>
                      <div className="pm-stat-box-compact">
                        <div className="pm-stat-label-sm">리스크 레벨</div>
                        <div className="pm-stat-value-lg" style={{ color: getRiskLevelColor(strategy.sample_portfolio.statistics.portfolio_risk) }}>
                          {getRiskLevelName(strategy.sample_portfolio.statistics.portfolio_risk)}
                        </div>
                      </div>
                      <div className="pm-stat-box-compact">
                        <div className="pm-stat-label-sm">총 종목 수</div>
                        <div className="pm-stat-value-lg" style={{ color: 'var(--primary)' }}>
                          {strategy.sample_portfolio.statistics.total_items}개
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Detail Tab */}
          {activeTab === 'detail' && (
            <div className="pm-tab-content">
              {/* Investment Type Selector */}
              <div className="pm-type-selector">
                {['conservative', 'moderate', 'aggressive'].map((type) => (
                  <button
                    key={type}
                    className={`pm-type-btn ${selectedType === type ? 'active' : ''}`}
                    onClick={() => setSelectedType(type)}
                  >
                    {type === 'conservative' ? '안정형' : type === 'moderate' ? '중립형' : '공격형'}
                  </button>
                ))}
              </div>

              {loading && <div className="pm-loading">로딩 중...</div>}

              {detailPortfolio && !loading && (
                <>
                  {/* Portfolio Statistics */}
                  <div className="pm-stats-panel">
                    <h3>포트폴리오 통계 (투자금 1,000만원 기준)</h3>
                    <div className="pm-grid-4">
                      <div className="pm-stat-box">
                        <div className="pm-stat-label">실투자액</div>
                        <div className="pm-stat-value-lg" style={{ color: 'var(--text)' }}>
                          {formatCurrency(detailPortfolio.statistics.actual_invested)}원
                        </div>
                      </div>
                      <div className="pm-stat-box">
                        <div className="pm-stat-label">과거 연평균 수익률</div>
                        <div className="pm-stat-value-lg" style={{ color: 'var(--stock-up)' }}>
                          {formatPercent(detailPortfolio.statistics.expected_annual_return)}
                        </div>
                      </div>
                      <div className="pm-stat-box">
                        <div className="pm-stat-label">리스크</div>
                        <div className="pm-stat-value-lg" style={{ color: getRiskLevelColor(detailPortfolio.statistics.portfolio_risk) }}>
                          {getRiskLevelName(detailPortfolio.statistics.portfolio_risk)}
                        </div>
                      </div>
                      <div className="pm-stat-box">
                        <div className="pm-stat-label">다각화 점수</div>
                        <div className="pm-stat-value-lg" style={{ color: 'var(--primary)' }}>
                          {detailPortfolio.statistics.diversification_score}/100
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Stocks */}
                  {detailPortfolio.portfolio.stocks.length > 0 && (
                    <div className="pm-asset-section">
                      <h3>📈 주식 ({detailPortfolio.portfolio.stocks.length}개)</h3>
                      <div className="pm-table-wrap">
                        <table className="pm-table">
                          <thead>
                            <tr>
                              <th>종목명</th>
                              <th>섹터</th>
                              <th className="right">현재가</th>
                              <th className="right">주식수</th>
                              <th className="right">투자액</th>
                              <th className="center">리스크</th>
                              <th className="right">점수</th>
                            </tr>
                          </thead>
                          <tbody>
                            {detailPortfolio.portfolio.stocks.map((stock) => (
                              <tr key={stock.ticker}>
                                <td>
                                  <div className="pm-cell-name">{stock.name}</div>
                                  <div className="pm-cell-ticker">{stock.ticker}</div>
                                </td>
                                <td>{stock.sector}</td>
                                <td className="right">{formatCurrency(stock.current_price)}원</td>
                                <td className="right">{formatCurrency(stock.shares)}주</td>
                                <td className="right">{formatCurrency(stock.invested_amount)}원</td>
                                <td className="center">
                                  <span className="pm-risk-badge" style={{
                                    background: getRiskLevelColor(stock.risk_level) + '20',
                                    color: getRiskLevelColor(stock.risk_level)
                                  }}>
                                    {getRiskLevelName(stock.risk_level)}
                                  </span>
                                </td>
                                <td className="right">{stock.score}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* ETFs */}
                  {detailPortfolio.portfolio.etfs.length > 0 && (
                    <div className="pm-asset-section">
                      <h3>📊 ETF ({detailPortfolio.portfolio.etfs.length}개)</h3>
                      <div className="pm-table-wrap">
                        <table className="pm-table">
                          <thead>
                            <tr>
                              <th>상품명</th>
                              <th>유형</th>
                              <th className="right">현재가</th>
                              <th className="right">수량</th>
                              <th className="right">투자액</th>
                              <th className="right">점수</th>
                            </tr>
                          </thead>
                          <tbody>
                            {detailPortfolio.portfolio.etfs.map((etf) => (
                              <tr key={etf.ticker}>
                                <td>
                                  <div className="pm-cell-name">{etf.name}</div>
                                  <div className="pm-cell-ticker">{etf.ticker}</div>
                                </td>
                                <td>{etf.etf_type}</td>
                                <td className="right">{formatCurrency(etf.current_price)}원</td>
                                <td className="right">{formatCurrency(etf.shares)}좌</td>
                                <td className="right">{formatCurrency(etf.invested_amount)}원</td>
                                <td className="right">{etf.score}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Top Securities */}
                  {topSecurities && (
                    <div className="pm-top-section">
                      <h3>⭐ 상위 점수 종목 (현재 전략 기준)</h3>

                      <h4>주식 Top 10</h4>
                      <div className="pm-table-wrap">
                        <table className="pm-table-sm">
                          <thead>
                            <tr>
                              <th>순위</th>
                              <th>종목명</th>
                              <th>섹터</th>
                              <th className="right">1년수익률</th>
                              <th className="right">배당률</th>
                              <th className="center">리스크</th>
                              <th className="right">점수</th>
                            </tr>
                          </thead>
                          <tbody>
                            {topSecurities.top_stocks.map((stock, idx) => (
                              <tr key={stock.ticker}>
                                <td>{idx + 1}</td>
                                <td>
                                  <div className="pm-cell-name-sm">{stock.name}</div>
                                  <div className="pm-cell-ticker-sm">{stock.ticker}</div>
                                </td>
                                <td>{stock.sector}</td>
                                <td className="right" style={{ color: stock.one_year_return > 0 ? '#4CAF50' : '#F44336' }}>
                                  {stock.one_year_return ? formatPercent(stock.one_year_return) : 'N/A'}
                                </td>
                                <td className="right">
                                  {stock.dividend_yield ? formatPercent(stock.dividend_yield) : 'N/A'}
                                </td>
                                <td className="center">
                                  <span className="pm-risk-badge-sm" style={{
                                    background: getRiskLevelColor(stock.risk_level) + '20',
                                    color: getRiskLevelColor(stock.risk_level)
                                  }}>
                                    {getRiskLevelName(stock.risk_level)}
                                  </span>
                                </td>
                                <td className="right bold">{stock.score}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      <h4>ETF Top 10</h4>
                      <div className="pm-table-wrap">
                        <table className="pm-table-sm">
                          <thead>
                            <tr>
                              <th>순위</th>
                              <th>상품명</th>
                              <th>유형</th>
                              <th className="right">1년수익률</th>
                              <th className="right">수수료</th>
                              <th className="center">리스크</th>
                              <th className="right">점수</th>
                            </tr>
                          </thead>
                          <tbody>
                            {topSecurities.top_etfs.map((etf, idx) => (
                              <tr key={etf.ticker}>
                                <td>{idx + 1}</td>
                                <td>
                                  <div className="pm-cell-name-sm">{etf.name}</div>
                                  <div className="pm-cell-ticker-sm">{etf.ticker}</div>
                                </td>
                                <td>{etf.etf_type}</td>
                                <td className="right" style={{ color: etf.one_year_return > 0 ? '#4CAF50' : '#F44336' }}>
                                  {etf.one_year_return ? formatPercent(etf.one_year_return) : 'N/A'}
                                </td>
                                <td className="right">
                                  {etf.expense_ratio ? formatPercent(etf.expense_ratio) : 'N/A'}
                                </td>
                                <td className="center">
                                  <span className="pm-risk-badge-sm" style={{
                                    background: getRiskLevelColor(etf.risk_level) + '20',
                                    color: getRiskLevelColor(etf.risk_level)
                                  }}>
                                    {getRiskLevelName(etf.risk_level)}
                                  </span>
                                </td>
                                <td className="right bold">{etf.score}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Securities Pool Tab */}
          {activeTab === 'securities' && availableSecurities && (
            <div className="pm-tab-content">
              <h2>종목 풀 현황</h2>

              {/* Totals */}
              <div className="pm-pool-grid">
                {[
                  { label: '전체 주식', count: availableSecurities.totals.stocks, bg: '#e3f2fd', color: '#2196F3' },
                  { label: '전체 ETF', count: availableSecurities.totals.etfs, bg: '#f3e5f5', color: '#9C27B0' },
                  { label: '전체 채권', count: availableSecurities.totals.bonds, bg: '#e8f5e9', color: '#4CAF50' },
                  { label: '전체 예금', count: availableSecurities.totals.deposits, bg: '#fff3e0', color: '#FF9800' },
                ].map((item) => (
                  <div key={item.label} className="pm-pool-card" style={{ background: item.bg }}>
                    <div className="pm-pool-card-label">{item.label}</div>
                    <div className="pm-pool-card-value" style={{ color: item.color }}>{item.count}</div>
                  </div>
                ))}
              </div>

              {/* By Investment Type */}
              <h3 style={{ marginBottom: '16px' }}>투자 성향별 종목 수</h3>
              <div className="pm-table-wrap">
                <table className="pm-table">
                  <thead>
                    <tr>
                      <th>자산군</th>
                      <th className="center">안정형</th>
                      <th className="center">중립형</th>
                      <th className="center">공격형</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="pm-cell-bold">📈 주식</td>
                      <td className="center">{availableSecurities.by_investment_type.stocks.conservative}개</td>
                      <td className="center">{availableSecurities.by_investment_type.stocks.moderate}개</td>
                      <td className="center">{availableSecurities.by_investment_type.stocks.aggressive}개</td>
                    </tr>
                    <tr>
                      <td className="pm-cell-bold">📊 ETF</td>
                      <td className="center">{availableSecurities.by_investment_type.etfs.conservative}개</td>
                      <td className="center">{availableSecurities.by_investment_type.etfs.moderate}개</td>
                      <td className="center">{availableSecurities.by_investment_type.etfs.aggressive}개</td>
                    </tr>
                    <tr>
                      <td className="pm-cell-bold">💰 채권</td>
                      <td className="center">{availableSecurities.by_investment_type.bonds.conservative}개</td>
                      <td className="center">{availableSecurities.by_investment_type.bonds.moderate}개</td>
                      <td className="center">{availableSecurities.by_investment_type.bonds.aggressive}개</td>
                    </tr>
                    <tr>
                      <td className="pm-cell-bold">🏦 예금</td>
                      <td colSpan={3} className="center">
                        {availableSecurities.by_investment_type.deposits.all}개 (전체 공통)
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="pm-info-box">
                <p>
                  💡 <strong>참고:</strong> 각 투자 성향별로 적합한 종목이 자동으로 필터링됩니다.
                  새로운 종목을 추가하려면 "데이터 관리" 메뉴에서 종목 데이터를 수집하세요.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
