import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  listStocks,
  listSectors,
  listMarkets,
  createPhase7Portfolio,
  listPhase7Portfolios,
} from '../services/api';
import '../styles/PortfolioBuilder.css';

const PortfolioBuilderPage = () => {
  const navigate = useNavigate();

  // ============================================================
  // State
  // ============================================================

  // Portfolio 유형
  const [portfolioType, setPortfolioType] = useState('SECURITY'); // SECURITY | SECTOR

  // Portfolio 정보
  const [portfolioName, setPortfolioName] = useState('');
  const [description, setDescription] = useState('');

  // 선택된 항목
  const [selectedItems, setSelectedItems] = useState([]);

  // 검색 및 필터
  const [searchQuery, setSearchQuery] = useState('');
  const [marketFilter, setMarketFilter] = useState('');
  const [sectorFilter, setSectorFilter] = useState('');

  // 데이터
  const [stocks, setStocks] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [markets, setMarkets] = useState([]);
  const [myPortfolios, setMyPortfolios] = useState([]);

  // UI 상태
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [showSearchResults, setShowSearchResults] = useState(false);

  // ============================================================
  // Data Loading
  // ============================================================

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (portfolioType === 'SECURITY') {
      loadStocks();
    } else {
      loadSectors();
    }
  }, [portfolioType, searchQuery, marketFilter, sectorFilter]);

  const loadInitialData = async () => {
    try {
      const [marketsRes, portfoliosRes] = await Promise.all([
        listMarkets(),
        listPhase7Portfolios(),
      ]);
      setMarkets(marketsRes.data.markets || []);
      setMyPortfolios(portfoliosRes.data.portfolios || []);
    } catch (err) {
      console.error('Failed to load initial data:', err);
    }
  };

  const loadStocks = async () => {
    if (!searchQuery && !marketFilter && !sectorFilter) {
      setStocks([]);
      return;
    }

    setLoading(true);
    try {
      const params = {
        limit: 50,
      };
      if (searchQuery) params.search = searchQuery;
      if (marketFilter) params.market = marketFilter;
      if (sectorFilter) params.sector = sectorFilter;

      const response = await listStocks(params);
      setStocks(response.data.stocks || []);
    } catch (err) {
      console.error('Failed to load stocks:', err);
      setError('종목 목록을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const loadSectors = async () => {
    setLoading(true);
    try {
      const params = {};
      if (marketFilter) params.market = marketFilter;

      const response = await listSectors(params);
      setSectors(response.data.sectors || []);
    } catch (err) {
      console.error('Failed to load sectors:', err);
      setError('섹터 목록을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // Selection Handlers
  // ============================================================

  const handleAddItem = (item) => {
    // 이미 선택된 항목인지 확인
    const itemKey = portfolioType === 'SECURITY' ? item.ticker : item.sector_code;
    if (selectedItems.some((i) => i.id === itemKey)) {
      return;
    }

    const newItem = {
      id: itemKey,
      name: portfolioType === 'SECURITY' ? item.name : item.sector_name,
      weight: 0,
      // 추가 정보
      ...(portfolioType === 'SECURITY' && {
        ticker: item.ticker,
        market: item.market,
        sector: item.sector,
        currentPrice: item.current_price,
        ytdReturn: item.ytd_return,
      }),
      ...(portfolioType === 'SECTOR' && {
        stockCount: item.stock_count,
        avgPeRatio: item.avg_pe_ratio,
        avgDividendYield: item.avg_dividend_yield,
      }),
    };

    setSelectedItems([...selectedItems, newItem]);
    setShowSearchResults(false);
    setSearchQuery('');
  };

  const handleRemoveItem = (itemId) => {
    setSelectedItems(selectedItems.filter((i) => i.id !== itemId));
  };

  const handleWeightChange = (itemId, weight) => {
    const numWeight = parseFloat(weight) || 0;
    setSelectedItems(
      selectedItems.map((item) =>
        item.id === itemId ? { ...item, weight: Math.min(100, Math.max(0, numWeight)) } : item
      )
    );
  };

  const handleEqualWeight = () => {
    if (selectedItems.length === 0) return;
    const equalWeight = Math.floor((100 / selectedItems.length) * 100) / 100;
    const remainder = 100 - equalWeight * selectedItems.length;

    setSelectedItems(
      selectedItems.map((item, idx) => ({
        ...item,
        weight: idx === 0 ? equalWeight + remainder : equalWeight,
      }))
    );
  };

  // ============================================================
  // Portfolio Save
  // ============================================================

  const totalWeight = useMemo(() => {
    return selectedItems.reduce((sum, item) => sum + (item.weight || 0), 0);
  }, [selectedItems]);

  const isValidPortfolio = useMemo(() => {
    return (
      portfolioName.trim() !== '' &&
      selectedItems.length > 0 &&
      Math.abs(totalWeight - 100) < 0.01
    );
  }, [portfolioName, selectedItems, totalWeight]);

  const handleSavePortfolio = async () => {
    if (!isValidPortfolio) {
      setError('포트폴리오 이름을 입력하고, 비중 합계가 100%인지 확인하세요.');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const payload = {
        portfolio_type: portfolioType,
        portfolio_name: portfolioName.trim(),
        description: description.trim() || null,
        items: selectedItems.map((item) => ({
          id: item.id,
          name: item.name,
          weight: item.weight / 100, // 0~1 범위로 변환
        })),
      };

      await createPhase7Portfolio(payload);

      // 성공 시 평가 페이지로 이동
      navigate('/portfolio-evaluation');
    } catch (err) {
      console.error('Failed to save portfolio:', err);
      setError(err.response?.data?.detail || '포트폴리오 저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  // ============================================================
  // Render
  // ============================================================

  const filteredStocks = useMemo(() => {
    // 이미 선택된 종목 제외
    return stocks.filter((s) => !selectedItems.some((i) => i.id === s.ticker));
  }, [stocks, selectedItems]);

  const filteredSectors = useMemo(() => {
    // 검색어로 필터링
    let filtered = sectors;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = sectors.filter(
        (s) =>
          s.sector_code.toLowerCase().includes(query) ||
          s.sector_name.toLowerCase().includes(query)
      );
    }
    // 이미 선택된 섹터 제외
    return filtered.filter((s) => !selectedItems.some((i) => i.id === s.sector_code));
  }, [sectors, searchQuery, selectedItems]);

  return (
    <div className="portfolio-builder-page">
      <div className="page-header">
        <h1>포트폴리오 구성</h1>
        <p className="subtitle">종목 또는 섹터를 선택하여 나만의 포트폴리오를 구성하세요</p>
      </div>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError(null)}>X</button>
        </div>
      )}

      <div className="builder-container">
        {/* 좌측: 포트폴리오 정보 및 선택된 항목 */}
        <div className="portfolio-panel">
          <div className="panel-section">
            <h3>포트폴리오 정보</h3>

            <div className="form-group">
              <label>포트폴리오 유형</label>
              <div className="type-selector">
                <button
                  className={portfolioType === 'SECURITY' ? 'active' : ''}
                  onClick={() => {
                    setPortfolioType('SECURITY');
                    setSelectedItems([]);
                    setSearchQuery('');
                  }}
                >
                  개별 종목
                </button>
                <button
                  className={portfolioType === 'SECTOR' ? 'active' : ''}
                  onClick={() => {
                    setPortfolioType('SECTOR');
                    setSelectedItems([]);
                    setSearchQuery('');
                  }}
                >
                  섹터
                </button>
              </div>
            </div>

            <div className="form-group">
              <label>포트폴리오 이름 *</label>
              <input
                type="text"
                value={portfolioName}
                onChange={(e) => setPortfolioName(e.target.value)}
                placeholder="예: 배당주 중심 포트폴리오"
                maxLength={50}
              />
            </div>

            <div className="form-group">
              <label>설명 (선택)</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="포트폴리오에 대한 설명을 입력하세요"
                rows={3}
                maxLength={200}
              />
            </div>
          </div>

          <div className="panel-section selected-items-section">
            <div className="section-header">
              <h3>선택된 {portfolioType === 'SECURITY' ? '종목' : '섹터'}</h3>
              <span className="item-count">{selectedItems.length}개</span>
            </div>

            {selectedItems.length === 0 ? (
              <div className="empty-state">
                <p>아직 선택된 항목이 없습니다.</p>
                <p className="hint">
                  오른쪽에서 {portfolioType === 'SECURITY' ? '종목을 검색하여' : '섹터를'} 추가하세요.
                </p>
              </div>
            ) : (
              <>
                <div className="weight-actions">
                  <button className="btn-equal-weight" onClick={handleEqualWeight}>
                    균등 비중 적용
                  </button>
                </div>

                <div className="selected-items-list">
                  {selectedItems.map((item) => (
                    <div key={item.id} className="selected-item">
                      <div className="item-info">
                        <span className="item-id">{item.id}</span>
                        <span className="item-name">{item.name}</span>
                        {item.market && <span className="item-market">{item.market}</span>}
                      </div>
                      <div className="item-weight">
                        <input
                          type="number"
                          value={item.weight || ''}
                          onChange={(e) => handleWeightChange(item.id, e.target.value)}
                          min="0"
                          max="100"
                          step="0.1"
                        />
                        <span>%</span>
                      </div>
                      <button className="btn-remove" onClick={() => handleRemoveItem(item.id)}>
                        X
                      </button>
                    </div>
                  ))}
                </div>

                <div className="weight-summary">
                  <div className="weight-bar-container">
                    <div
                      className={`weight-bar ${totalWeight > 100 ? 'over' : totalWeight === 100 ? 'complete' : ''}`}
                      style={{ width: `${Math.min(totalWeight, 100)}%` }}
                    />
                  </div>
                  <div className={`weight-total ${Math.abs(totalWeight - 100) < 0.01 ? 'valid' : 'invalid'}`}>
                    합계: {totalWeight.toFixed(2)}%
                    {Math.abs(totalWeight - 100) < 0.01 ? ' OK' : ' (100%가 되어야 합니다)'}
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="panel-actions">
            <button className="btn-secondary" onClick={() => navigate('/portfolio-evaluation')}>
              취소
            </button>
            <button
              className="btn-primary"
              onClick={handleSavePortfolio}
              disabled={!isValidPortfolio || saving}
            >
              {saving ? '저장 중...' : '포트폴리오 저장'}
            </button>
          </div>
        </div>

        {/* 우측: 검색 및 목록 */}
        <div className="search-panel">
          <div className="panel-section">
            <h3>{portfolioType === 'SECURITY' ? '종목 검색' : '섹터 선택'}</h3>

            <div className="search-box">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => setShowSearchResults(true)}
                placeholder={
                  portfolioType === 'SECURITY'
                    ? '종목명 또는 종목코드 검색...'
                    : '섹터 검색...'
                }
              />
              {searchQuery && (
                <button className="btn-clear" onClick={() => setSearchQuery('')}>
                  X
                </button>
              )}
            </div>

            {portfolioType === 'SECURITY' && (
              <div className="filters">
                <select value={marketFilter} onChange={(e) => setMarketFilter(e.target.value)}>
                  <option value="">전체 시장</option>
                  {markets.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="search-results">
            {loading ? (
              <div className="loading-state">검색 중...</div>
            ) : portfolioType === 'SECURITY' ? (
              filteredStocks.length > 0 ? (
                <div className="results-list">
                  {filteredStocks.map((stock) => (
                    <div key={stock.ticker} className="result-item" onClick={() => handleAddItem(stock)}>
                      <div className="result-main">
                        <span className="result-ticker">{stock.ticker}</span>
                        <span className="result-name">{stock.name}</span>
                      </div>
                      <div className="result-sub">
                        <span className="result-market">{stock.market}</span>
                        <span className="result-sector">{stock.sector}</span>
                        {stock.ytd_return !== null && (
                          <span className={`result-return ${stock.ytd_return >= 0 ? 'positive' : 'negative'}`}>
                            YTD {stock.ytd_return >= 0 ? '+' : ''}{stock.ytd_return?.toFixed(2)}%
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : searchQuery || marketFilter ? (
                <div className="empty-state">
                  <p>검색 결과가 없습니다.</p>
                </div>
              ) : (
                <div className="empty-state">
                  <p>종목명 또는 종목코드를 검색하세요.</p>
                </div>
              )
            ) : (
              <div className="results-list sectors">
                {filteredSectors.length > 0 ? (
                  filteredSectors.map((sector) => (
                    <div key={sector.sector_code} className="result-item" onClick={() => handleAddItem(sector)}>
                      <div className="result-main">
                        <span className="result-name">{sector.sector_name}</span>
                      </div>
                      <div className="result-sub">
                        <span>종목 수: {sector.stock_count}</span>
                        {sector.avg_pe_ratio && <span>평균 PER: {sector.avg_pe_ratio.toFixed(1)}</span>}
                        {sector.avg_dividend_yield && <span>평균 배당률: {sector.avg_dividend_yield.toFixed(2)}%</span>}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="empty-state">
                    <p>섹터가 없습니다.</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 기존 포트폴리오 목록 */}
      {myPortfolios.length > 0 && (
        <div className="existing-portfolios">
          <h3>내 포트폴리오</h3>
          <div className="portfolio-list">
            {myPortfolios.slice(0, 5).map((p) => (
              <div key={p.portfolio_id} className="portfolio-card">
                <div className="portfolio-info">
                  <span className="portfolio-type">{p.portfolio_type === 'SECURITY' ? '종목' : '섹터'}</span>
                  <span className="portfolio-name">{p.portfolio_name}</span>
                </div>
                <div className="portfolio-items">
                  {p.items?.slice(0, 3).map((item) => (
                    <span key={item.item_key} className="item-badge">
                      {item.item_name} ({(item.weight * 100).toFixed(0)}%)
                    </span>
                  ))}
                  {p.items?.length > 3 && <span className="more-badge">+{p.items.length - 3}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PortfolioBuilderPage;
