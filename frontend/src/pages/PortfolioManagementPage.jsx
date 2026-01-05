import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

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
        {
          headers: { Authorization: `Bearer ${token}` }
        }
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
        {
          headers: { Authorization: `Bearer ${token}` }
        }
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
        {
          headers: { Authorization: `Bearer ${token}` }
        }
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
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      setAvailableSecurities(response.data.data);
    } catch (err) {
      console.error('Failed to load available securities:', err);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ko-KR').format(amount);
  };

  const formatPercent = (value) => {
    if (value === undefined || value === null) return '0.0%';
    return `${Number(value).toFixed(1)}%`;
  };

  const getRiskLevelColor = (level) => {
    const colors = {
      low: '#4CAF50',
      medium: '#FF9800',
      high: '#F44336'
    };
    return colors[level] || '#666';
  };

  const getRiskLevelName = (level) => {
    const names = {
      low: '낮음',
      medium: '중간',
      high: '높음'
    };
    return names[level] || level;
  };

  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card" style={{ maxWidth: '1400px' }}>
          {/* Header */}
          <div className="result-header">
            <button
              onClick={() => navigate('/admin')}
              style={{
                position: 'absolute',
                top: '20px',
                left: '20px',
                background: 'white',
                border: '2px solid #e0e0e0',
                borderRadius: '8px',
                padding: '8px 16px',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              ← 뒤로
            </button>
            <div className="result-icon" style={{ fontSize: '3rem' }}>
              📊
            </div>
            <h1 className="result-type" style={{ color: '#667eea' }}>
              포트폴리오 전략 관리
            </h1>
            <p className="result-subtitle">
              투자 성향별 포트폴리오 구성 및 종목 관리
            </p>
          </div>

          {/* Tab Navigation */}
          <div style={{ display: 'flex', gap: '10px', marginTop: '32px', borderBottom: '2px solid #e0e0e0' }}>
            <button
              onClick={() => setActiveTab('overview')}
              style={{
                padding: '12px 24px',
                background: activeTab === 'overview' ? '#667eea' : 'white',
                color: activeTab === 'overview' ? 'white' : '#666',
                border: 'none',
                borderBottom: activeTab === 'overview' ? '3px solid #667eea' : 'none',
                cursor: 'pointer',
                fontSize: '16px',
                fontWeight: '600'
              }}
            >
              전략 개요
            </button>
            <button
              onClick={() => setActiveTab('detail')}
              style={{
                padding: '12px 24px',
                background: activeTab === 'detail' ? '#667eea' : 'white',
                color: activeTab === 'detail' ? 'white' : '#666',
                border: 'none',
                borderBottom: activeTab === 'detail' ? '3px solid #667eea' : 'none',
                cursor: 'pointer',
                fontSize: '16px',
                fontWeight: '600'
              }}
            >
              상세 구성
            </button>
            <button
              onClick={() => setActiveTab('securities')}
              style={{
                padding: '12px 24px',
                background: activeTab === 'securities' ? '#667eea' : 'white',
                color: activeTab === 'securities' ? 'white' : '#666',
                border: 'none',
                borderBottom: activeTab === 'securities' ? '3px solid #667eea' : 'none',
                cursor: 'pointer',
                fontSize: '16px',
                fontWeight: '600'
              }}
            >
              종목 풀 현황
            </button>
          </div>

          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div style={{ marginTop: '32px' }}>
              <h2 style={{ marginBottom: '24px' }}>투자 성향별 전략 비교</h2>

              {strategies.map((strategy) => (
                <div
                  key={strategy.investment_type}
                  style={{
                    background: '#f5f5f5',
                    borderRadius: '12px',
                    padding: '24px',
                    marginBottom: '24px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <h3 style={{ margin: 0, fontSize: '1.5rem', color: '#333' }}>
                      {strategy.display_name}
                    </h3>
                    <button
                      onClick={() => {
                        setSelectedType(strategy.investment_type);
                        setActiveTab('detail');
                      }}
                      style={{
                        padding: '8px 16px',
                        background: '#667eea',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '14px'
                      }}
                    >
                      상세 보기 →
                    </button>
                  </div>

                  {/* Asset Allocation */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '16px' }}>
                    {Object.entries(strategy.allocation_strategy).map(([assetClass, weights]) => (
                      <div
                        key={assetClass}
                        style={{
                          background: 'white',
                          borderRadius: '8px',
                          padding: '16px',
                          textAlign: 'center'
                        }}
                      >
                        <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>
                          {assetClass === 'stocks' ? '주식' : assetClass === 'etfs' ? 'ETF' : assetClass === 'bonds' ? '채권' : '예금'}
                        </div>
                        <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#667eea', marginBottom: '4px' }}>
                          {weights.target}%
                        </div>
                        <div style={{ fontSize: '12px', color: '#999' }}>
                          범위: {weights.min}-{weights.max}%
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Sample Portfolio Stats */}
                  {strategy.sample_portfolio && (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginTop: '16px' }}>
                      <div style={{ background: 'white', borderRadius: '8px', padding: '12px' }}>
                        <div style={{ fontSize: '13px', color: '#666' }}>기대 수익률 (연)</div>
                        <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#4CAF50' }}>
                          {formatPercent(strategy.sample_portfolio.statistics.expected_annual_return)}
                        </div>
                      </div>
                      <div style={{ background: 'white', borderRadius: '8px', padding: '12px' }}>
                        <div style={{ fontSize: '13px', color: '#666' }}>리스크 레벨</div>
                        <div style={{ fontSize: '20px', fontWeight: 'bold', color: getRiskLevelColor(strategy.sample_portfolio.statistics.portfolio_risk) }}>
                          {getRiskLevelName(strategy.sample_portfolio.statistics.portfolio_risk)}
                        </div>
                      </div>
                      <div style={{ background: 'white', borderRadius: '8px', padding: '12px' }}>
                        <div style={{ fontSize: '13px', color: '#666' }}>총 종목 수</div>
                        <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#2196F3' }}>
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
            <div style={{ marginTop: '32px' }}>
              {/* Investment Type Selector */}
              <div style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
                {['conservative', 'moderate', 'aggressive'].map((type) => (
                  <button
                    key={type}
                    onClick={() => setSelectedType(type)}
                    style={{
                      flex: 1,
                      padding: '16px',
                      background: selectedType === type ? '#667eea' : 'white',
                      color: selectedType === type ? 'white' : '#666',
                      border: selectedType === type ? 'none' : '2px solid #e0e0e0',
                      borderRadius: '12px',
                      cursor: 'pointer',
                      fontSize: '16px',
                      fontWeight: '600'
                    }}
                  >
                    {type === 'conservative' ? '안정형' : type === 'moderate' ? '중립형' : '공격형'}
                  </button>
                ))}
              </div>

              {loading && <div style={{ textAlign: 'center', padding: '40px' }}>로딩 중...</div>}

              {detailPortfolio && !loading && (
                <>
                  {/* Portfolio Statistics */}
                  <div style={{ background: '#f5f5f5', borderRadius: '12px', padding: '24px', marginBottom: '24px' }}>
                    <h3 style={{ marginBottom: '16px' }}>포트폴리오 통계 (투자금 1,000만원 기준)</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
                      <div style={{ background: 'white', borderRadius: '8px', padding: '16px' }}>
                        <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>실투자액</div>
                        <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#333' }}>
                          {formatCurrency(detailPortfolio.statistics.actual_invested)}원
                        </div>
                      </div>
                      <div style={{ background: 'white', borderRadius: '8px', padding: '16px' }}>
                        <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>기대 수익률</div>
                        <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#4CAF50' }}>
                          {formatPercent(detailPortfolio.statistics.expected_annual_return)}
                        </div>
                      </div>
                      <div style={{ background: 'white', borderRadius: '8px', padding: '16px' }}>
                        <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>리스크</div>
                        <div style={{ fontSize: '20px', fontWeight: 'bold', color: getRiskLevelColor(detailPortfolio.statistics.portfolio_risk) }}>
                          {getRiskLevelName(detailPortfolio.statistics.portfolio_risk)}
                        </div>
                      </div>
                      <div style={{ background: 'white', borderRadius: '8px', padding: '16px' }}>
                        <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>다각화 점수</div>
                        <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#2196F3' }}>
                          {detailPortfolio.statistics.diversification_score}/100
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Stocks */}
                  {detailPortfolio.portfolio.stocks.length > 0 && (
                    <div style={{ marginBottom: '32px' }}>
                      <h3 style={{ marginBottom: '16px' }}>📈 주식 ({detailPortfolio.portfolio.stocks.length}개)</h3>
                      <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                          <thead>
                            <tr style={{ background: '#f5f5f5' }}>
                              <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #e0e0e0' }}>종목명</th>
                              <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #e0e0e0' }}>섹터</th>
                              <th style={{ padding: '12px', textAlign: 'right', borderBottom: '2px solid #e0e0e0' }}>현재가</th>
                              <th style={{ padding: '12px', textAlign: 'right', borderBottom: '2px solid #e0e0e0' }}>주식수</th>
                              <th style={{ padding: '12px', textAlign: 'right', borderBottom: '2px solid #e0e0e0' }}>투자액</th>
                              <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #e0e0e0' }}>리스크</th>
                              <th style={{ padding: '12px', textAlign: 'right', borderBottom: '2px solid #e0e0e0' }}>점수</th>
                            </tr>
                          </thead>
                          <tbody>
                            {detailPortfolio.portfolio.stocks.map((stock) => (
                              <tr key={stock.id}>
                                <td style={{ padding: '12px', borderBottom: '1px solid #e0e0e0' }}>
                                  <div style={{ fontWeight: 'bold' }}>{stock.name}</div>
                                  <div style={{ fontSize: '12px', color: '#666' }}>{stock.ticker}</div>
                                </td>
                                <td style={{ padding: '12px', borderBottom: '1px solid #e0e0e0' }}>{stock.sector}</td>
                                <td style={{ padding: '12px', textAlign: 'right', borderBottom: '1px solid #e0e0e0' }}>
                                  {formatCurrency(stock.current_price)}원
                                </td>
                                <td style={{ padding: '12px', textAlign: 'right', borderBottom: '1px solid #e0e0e0' }}>
                                  {formatCurrency(stock.shares)}주
                                </td>
                                <td style={{ padding: '12px', textAlign: 'right', borderBottom: '1px solid #e0e0e0' }}>
                                  {formatCurrency(stock.invested_amount)}원
                                </td>
                                <td style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #e0e0e0' }}>
                                  <span style={{
                                    padding: '4px 8px',
                                    background: getRiskLevelColor(stock.risk_level) + '20',
                                    color: getRiskLevelColor(stock.risk_level),
                                    borderRadius: '4px',
                                    fontSize: '12px'
                                  }}>
                                    {getRiskLevelName(stock.risk_level)}
                                  </span>
                                </td>
                                <td style={{ padding: '12px', textAlign: 'right', borderBottom: '1px solid #e0e0e0' }}>
                                  {stock.score}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* ETFs */}
                  {detailPortfolio.portfolio.etfs.length > 0 && (
                    <div style={{ marginBottom: '32px' }}>
                      <h3 style={{ marginBottom: '16px' }}>📊 ETF ({detailPortfolio.portfolio.etfs.length}개)</h3>
                      <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                          <thead>
                            <tr style={{ background: '#f5f5f5' }}>
                              <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #e0e0e0' }}>상품명</th>
                              <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #e0e0e0' }}>유형</th>
                              <th style={{ padding: '12px', textAlign: 'right', borderBottom: '2px solid #e0e0e0' }}>현재가</th>
                              <th style={{ padding: '12px', textAlign: 'right', borderBottom: '2px solid #e0e0e0' }}>수량</th>
                              <th style={{ padding: '12px', textAlign: 'right', borderBottom: '2px solid #e0e0e0' }}>투자액</th>
                              <th style={{ padding: '12px', textAlign: 'right', borderBottom: '2px solid #e0e0e0' }}>점수</th>
                            </tr>
                          </thead>
                          <tbody>
                            {detailPortfolio.portfolio.etfs.map((etf) => (
                              <tr key={etf.id}>
                                <td style={{ padding: '12px', borderBottom: '1px solid #e0e0e0' }}>
                                  <div style={{ fontWeight: 'bold' }}>{etf.name}</div>
                                  <div style={{ fontSize: '12px', color: '#666' }}>{etf.ticker}</div>
                                </td>
                                <td style={{ padding: '12px', borderBottom: '1px solid #e0e0e0' }}>{etf.etf_type}</td>
                                <td style={{ padding: '12px', textAlign: 'right', borderBottom: '1px solid #e0e0e0' }}>
                                  {formatCurrency(etf.current_price)}원
                                </td>
                                <td style={{ padding: '12px', textAlign: 'right', borderBottom: '1px solid #e0e0e0' }}>
                                  {formatCurrency(etf.shares)}좌
                                </td>
                                <td style={{ padding: '12px', textAlign: 'right', borderBottom: '1px solid #e0e0e0' }}>
                                  {formatCurrency(etf.invested_amount)}원
                                </td>
                                <td style={{ padding: '12px', textAlign: 'right', borderBottom: '1px solid #e0e0e0' }}>
                                  {etf.score}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Top Securities */}
                  {topSecurities && (
                    <div style={{ marginTop: '40px' }}>
                      <h3 style={{ marginBottom: '16px' }}>⭐ 상위 점수 종목 (현재 전략 기준)</h3>

                      <h4 style={{ marginTop: '24px', marginBottom: '12px', fontSize: '1.1rem' }}>주식 Top 10</h4>
                      <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                          <thead>
                            <tr style={{ background: '#f5f5f5' }}>
                              <th style={{ padding: '10px', textAlign: 'left', borderBottom: '2px solid #e0e0e0' }}>순위</th>
                              <th style={{ padding: '10px', textAlign: 'left', borderBottom: '2px solid #e0e0e0' }}>종목명</th>
                              <th style={{ padding: '10px', textAlign: 'left', borderBottom: '2px solid #e0e0e0' }}>섹터</th>
                              <th style={{ padding: '10px', textAlign: 'right', borderBottom: '2px solid #e0e0e0' }}>1년수익률</th>
                              <th style={{ padding: '10px', textAlign: 'right', borderBottom: '2px solid #e0e0e0' }}>배당률</th>
                              <th style={{ padding: '10px', textAlign: 'center', borderBottom: '2px solid #e0e0e0' }}>리스크</th>
                              <th style={{ padding: '10px', textAlign: 'right', borderBottom: '2px solid #e0e0e0' }}>점수</th>
                            </tr>
                          </thead>
                          <tbody>
                            {topSecurities.top_stocks.map((stock, idx) => (
                              <tr key={stock.ticker}>
                                <td style={{ padding: '10px', borderBottom: '1px solid #e0e0e0' }}>{idx + 1}</td>
                                <td style={{ padding: '10px', borderBottom: '1px solid #e0e0e0' }}>
                                  <div style={{ fontWeight: '600' }}>{stock.name}</div>
                                  <div style={{ fontSize: '11px', color: '#999' }}>{stock.ticker}</div>
                                </td>
                                <td style={{ padding: '10px', borderBottom: '1px solid #e0e0e0' }}>{stock.sector}</td>
                                <td style={{ padding: '10px', textAlign: 'right', borderBottom: '1px solid #e0e0e0', color: stock.one_year_return > 0 ? '#4CAF50' : '#F44336' }}>
                                  {stock.one_year_return ? formatPercent(stock.one_year_return) : 'N/A'}
                                </td>
                                <td style={{ padding: '10px', textAlign: 'right', borderBottom: '1px solid #e0e0e0' }}>
                                  {stock.dividend_yield ? formatPercent(stock.dividend_yield) : 'N/A'}
                                </td>
                                <td style={{ padding: '10px', textAlign: 'center', borderBottom: '1px solid #e0e0e0' }}>
                                  <span style={{
                                    padding: '3px 6px',
                                    background: getRiskLevelColor(stock.risk_level) + '20',
                                    color: getRiskLevelColor(stock.risk_level),
                                    borderRadius: '3px',
                                    fontSize: '11px'
                                  }}>
                                    {getRiskLevelName(stock.risk_level)}
                                  </span>
                                </td>
                                <td style={{ padding: '10px', textAlign: 'right', borderBottom: '1px solid #e0e0e0', fontWeight: 'bold' }}>
                                  {stock.score}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      <h4 style={{ marginTop: '24px', marginBottom: '12px', fontSize: '1.1rem' }}>ETF Top 10</h4>
                      <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                          <thead>
                            <tr style={{ background: '#f5f5f5' }}>
                              <th style={{ padding: '10px', textAlign: 'left', borderBottom: '2px solid #e0e0e0' }}>순위</th>
                              <th style={{ padding: '10px', textAlign: 'left', borderBottom: '2px solid #e0e0e0' }}>상품명</th>
                              <th style={{ padding: '10px', textAlign: 'left', borderBottom: '2px solid #e0e0e0' }}>유형</th>
                              <th style={{ padding: '10px', textAlign: 'right', borderBottom: '2px solid #e0e0e0' }}>1년수익률</th>
                              <th style={{ padding: '10px', textAlign: 'right', borderBottom: '2px solid #e0e0e0' }}>수수료</th>
                              <th style={{ padding: '10px', textAlign: 'center', borderBottom: '2px solid #e0e0e0' }}>리스크</th>
                              <th style={{ padding: '10px', textAlign: 'right', borderBottom: '2px solid #e0e0e0' }}>점수</th>
                            </tr>
                          </thead>
                          <tbody>
                            {topSecurities.top_etfs.map((etf, idx) => (
                              <tr key={etf.ticker}>
                                <td style={{ padding: '10px', borderBottom: '1px solid #e0e0e0' }}>{idx + 1}</td>
                                <td style={{ padding: '10px', borderBottom: '1px solid #e0e0e0' }}>
                                  <div style={{ fontWeight: '600' }}>{etf.name}</div>
                                  <div style={{ fontSize: '11px', color: '#999' }}>{etf.ticker}</div>
                                </td>
                                <td style={{ padding: '10px', borderBottom: '1px solid #e0e0e0' }}>{etf.etf_type}</td>
                                <td style={{ padding: '10px', textAlign: 'right', borderBottom: '1px solid #e0e0e0', color: etf.one_year_return > 0 ? '#4CAF50' : '#F44336' }}>
                                  {etf.one_year_return ? formatPercent(etf.one_year_return) : 'N/A'}
                                </td>
                                <td style={{ padding: '10px', textAlign: 'right', borderBottom: '1px solid #e0e0e0' }}>
                                  {etf.expense_ratio ? formatPercent(etf.expense_ratio) : 'N/A'}
                                </td>
                                <td style={{ padding: '10px', textAlign: 'center', borderBottom: '1px solid #e0e0e0' }}>
                                  <span style={{
                                    padding: '3px 6px',
                                    background: getRiskLevelColor(etf.risk_level) + '20',
                                    color: getRiskLevelColor(etf.risk_level),
                                    borderRadius: '3px',
                                    fontSize: '11px'
                                  }}>
                                    {getRiskLevelName(etf.risk_level)}
                                  </span>
                                </td>
                                <td style={{ padding: '10px', textAlign: 'right', borderBottom: '1px solid #e0e0e0', fontWeight: 'bold' }}>
                                  {etf.score}
                                </td>
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
            <div style={{ marginTop: '32px' }}>
              <h2 style={{ marginBottom: '24px' }}>종목 풀 현황</h2>

              {/* Totals */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '32px' }}>
                <div style={{ background: '#e3f2fd', borderRadius: '12px', padding: '20px', textAlign: 'center' }}>
                  <div style={{ fontSize: '16px', color: '#666', marginBottom: '8px' }}>전체 주식</div>
                  <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#2196F3' }}>
                    {availableSecurities.totals.stocks}
                  </div>
                </div>
                <div style={{ background: '#f3e5f5', borderRadius: '12px', padding: '20px', textAlign: 'center' }}>
                  <div style={{ fontSize: '16px', color: '#666', marginBottom: '8px' }}>전체 ETF</div>
                  <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#9C27B0' }}>
                    {availableSecurities.totals.etfs}
                  </div>
                </div>
                <div style={{ background: '#e8f5e9', borderRadius: '12px', padding: '20px', textAlign: 'center' }}>
                  <div style={{ fontSize: '16px', color: '#666', marginBottom: '8px' }}>전체 채권</div>
                  <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#4CAF50' }}>
                    {availableSecurities.totals.bonds}
                  </div>
                </div>
                <div style={{ background: '#fff3e0', borderRadius: '12px', padding: '20px', textAlign: 'center' }}>
                  <div style={{ fontSize: '16px', color: '#666', marginBottom: '8px' }}>전체 예금</div>
                  <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#FF9800' }}>
                    {availableSecurities.totals.deposits}
                  </div>
                </div>
              </div>

              {/* By Investment Type */}
              <h3 style={{ marginBottom: '16px' }}>투자 성향별 종목 수</h3>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: '#f5f5f5' }}>
                      <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #e0e0e0' }}>자산군</th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #e0e0e0' }}>안정형</th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #e0e0e0' }}>중립형</th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #e0e0e0' }}>공격형</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td style={{ padding: '12px', borderBottom: '1px solid #e0e0e0', fontWeight: '600' }}>📈 주식</td>
                      <td style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #e0e0e0' }}>
                        {availableSecurities.by_investment_type.stocks.conservative}개
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #e0e0e0' }}>
                        {availableSecurities.by_investment_type.stocks.moderate}개
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #e0e0e0' }}>
                        {availableSecurities.by_investment_type.stocks.aggressive}개
                      </td>
                    </tr>
                    <tr>
                      <td style={{ padding: '12px', borderBottom: '1px solid #e0e0e0', fontWeight: '600' }}>📊 ETF</td>
                      <td style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #e0e0e0' }}>
                        {availableSecurities.by_investment_type.etfs.conservative}개
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #e0e0e0' }}>
                        {availableSecurities.by_investment_type.etfs.moderate}개
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #e0e0e0' }}>
                        {availableSecurities.by_investment_type.etfs.aggressive}개
                      </td>
                    </tr>
                    <tr>
                      <td style={{ padding: '12px', borderBottom: '1px solid #e0e0e0', fontWeight: '600' }}>💰 채권</td>
                      <td style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #e0e0e0' }}>
                        {availableSecurities.by_investment_type.bonds.conservative}개
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #e0e0e0' }}>
                        {availableSecurities.by_investment_type.bonds.moderate}개
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #e0e0e0' }}>
                        {availableSecurities.by_investment_type.bonds.aggressive}개
                      </td>
                    </tr>
                    <tr>
                      <td style={{ padding: '12px', borderBottom: '1px solid #e0e0e0', fontWeight: '600' }}>🏦 예금</td>
                      <td colSpan={3} style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #e0e0e0' }}>
                        {availableSecurities.by_investment_type.deposits.all}개 (전체 공통)
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div style={{ marginTop: '24px', padding: '16px', background: '#fff3e0', borderRadius: '8px', borderLeft: '4px solid #FF9800' }}>
                <p style={{ margin: 0, fontSize: '14px', color: '#666' }}>
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
