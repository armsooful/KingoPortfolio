import { useState, useRef, useCallback, useEffect } from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { searchStocks, compareStocks } from '../services/api';
import Disclaimer from '../components/Disclaimer';
import '../styles/StockComparison.css';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

// 4축 색상 (StockDetailPage 패턴)
const AXIS_COLORS = [
  { label: '재무 (30%)', key: 'compass_financial_score', color: '#4caf50', bg: 'rgba(76,175,80,0.7)' },
  { label: '밸류 (20%)', key: 'compass_valuation_score', color: '#2196f3', bg: 'rgba(33,150,243,0.7)' },
  { label: '기술 (30%)', key: 'compass_technical_score', color: '#ff9800', bg: 'rgba(255,152,0,0.7)' },
  { label: '리스크 (20%)', key: 'compass_risk_score', color: '#9c27b0', bg: 'rgba(156,39,176,0.7)' },
];

// 종목별 색상
const STOCK_COLORS = ['#667eea', '#4caf50', '#f44336'];

function gradeColor(grade) {
  if (!grade) return '#6b7280';
  if (['S', 'A+', 'A'].includes(grade)) return '#16a34a';
  if (['B+', 'B'].includes(grade)) return '#2563eb';
  if (['C+', 'C'].includes(grade)) return '#ea580c';
  return '#dc2626';
}

function formatNumber(n) {
  if (n == null) return '-';
  if (n >= 1e12) return (n / 1e12).toFixed(1) + '조';
  if (n >= 1e8) return (n / 1e8).toFixed(0) + '억';
  if (n >= 1e4) return (n / 1e4).toFixed(0) + '만';
  return n.toLocaleString();
}

function formatPrice(n) {
  if (n == null) return '-';
  return n.toLocaleString() + '원';
}

function formatRatio(n) {
  if (n == null) return '-';
  return n.toFixed(2);
}

function formatPercent(n) {
  if (n == null) return '-';
  return n.toFixed(2) + '%';
}

function StockComparisonPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedStocks, setSelectedStocks] = useState([]);
  const [compareResult, setCompareResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const debounceRef = useRef(null);
  const dropdownRef = useRef(null);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearchChange = useCallback((e) => {
    const q = e.target.value;
    setSearchQuery(q);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (!q.trim()) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      try {
        const res = await searchStocks(q.trim());
        const data = res.data || [];
        // 이미 선택된 종목 제외
        const filtered = data.filter(
          (s) => !selectedStocks.some((sel) => sel.ticker === s.ticker)
        );
        setSearchResults(filtered);
        setShowDropdown(filtered.length > 0);
      } catch {
        setSearchResults([]);
        setShowDropdown(false);
      }
    }, 300);
  }, [selectedStocks]);

  const handleSelectStock = (stock) => {
    if (selectedStocks.length >= 3) return;
    setSelectedStocks((prev) => [...prev, stock]);
    setSearchQuery('');
    setSearchResults([]);
    setShowDropdown(false);
  };

  const handleRemoveStock = (ticker) => {
    setSelectedStocks((prev) => prev.filter((s) => s.ticker !== ticker));
  };

  const handleCompare = async () => {
    if (selectedStocks.length < 2) return;
    setLoading(true);
    setError('');
    setCompareResult(null);

    try {
      const tickers = selectedStocks.map((s) => s.ticker);
      const res = await compareStocks(tickers);
      setCompareResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || '비교 데이터를 불러오지 못했습니다');
    } finally {
      setLoading(false);
    }
  };

  // 4축 그룹 바 차트 데이터
  const getChartData = () => {
    if (!compareResult) return null;
    const stocks = compareResult.stocks;

    return {
      labels: AXIS_COLORS.map((a) => a.label),
      datasets: stocks.map((s, idx) => ({
        label: s.name || s.ticker,
        data: AXIS_COLORS.map((a) => s[a.key] ?? 0),
        backgroundColor: STOCK_COLORS[idx % STOCK_COLORS.length],
        borderRadius: 4,
        barPercentage: 0.7,
        categoryPercentage: 0.7,
      })),
    };
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          usePointStyle: true,
          pointStyle: 'circle',
          padding: 16,
          color: '#6b7280',
        },
      },
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y?.toFixed(1)}점`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#6b7280' },
      },
      y: {
        min: 0,
        max: 100,
        grid: { color: 'rgba(0,0,0,0.06)' },
        ticks: {
          color: '#6b7280',
          callback: (v) => v + '점',
        },
      },
    },
  };

  // 비교 테이블 행 정의
  const tableRows = [
    { label: '시장', getValue: (s) => s.market || '-' },
    { label: '섹터', getValue: (s) => s.sector || '-' },
    { label: '현재가', getValue: (s) => formatPrice(s.current_price) },
    { label: '시가총액', getValue: (s) => formatNumber(s.market_cap) },
    { label: 'PER', getValue: (s) => formatRatio(s.pe_ratio) },
    { label: 'PBR', getValue: (s) => formatRatio(s.pb_ratio) },
    { label: '배당수익률', getValue: (s) => formatPercent(s.dividend_yield) },
    { label: 'Compass Score', getValue: (s) => s.compass_score != null ? s.compass_score.toFixed(1) : '-' },
  ];

  return (
    <div className="sc-container">
      <h1 className="sc-title">종목 비교</h1>
      <p className="sc-subtitle">최대 3개 종목의 Compass Score와 기본 지표를 비교합니다</p>

      {/* 검색 영역 */}
      <div className="sc-search-section">
        <label className="sc-search-label">종목 검색 (최대 3개)</label>
        <div className="sc-search-row">
          <div className="sc-search-wrapper" ref={dropdownRef}>
            <input
              type="text"
              className="sc-search-input"
              placeholder="종목명 또는 코드를 입력하세요"
              value={searchQuery}
              onChange={handleSearchChange}
              onFocus={() => searchResults.length > 0 && setShowDropdown(true)}
              disabled={selectedStocks.length >= 3}
            />
            {showDropdown && (
              <div className="sc-dropdown">
                {searchResults.length > 0 ? (
                  searchResults.map((s) => (
                    <button
                      key={s.ticker}
                      className="sc-dropdown-item"
                      onClick={() => handleSelectStock(s)}
                    >
                      <span>
                        <span className="sc-dropdown-name">{s.name}</span>
                        <span className="sc-dropdown-ticker">{s.ticker}</span>
                      </span>
                      {s.compass_score != null && (
                        <span
                          className="sc-dropdown-score"
                          style={{ color: gradeColor(s.compass_grade) }}
                        >
                          {s.compass_score.toFixed(1)}
                        </span>
                      )}
                    </button>
                  ))
                ) : (
                  <div className="sc-dropdown-empty">검색 결과가 없습니다</div>
                )}
              </div>
            )}
          </div>
          <button
            className="sc-compare-btn"
            onClick={handleCompare}
            disabled={selectedStocks.length < 2 || loading}
          >
            {loading ? '분석 중...' : '비교하기'}
          </button>
        </div>

        {/* 선택된 종목 칩 */}
        {selectedStocks.length > 0 && (
          <div className="sc-chips">
            {selectedStocks.map((s, idx) => (
              <span
                key={s.ticker}
                className="sc-chip"
                style={{ borderColor: STOCK_COLORS[idx % STOCK_COLORS.length] }}
              >
                {s.name} ({s.ticker})
                <button
                  className="sc-chip-remove"
                  onClick={() => handleRemoveStock(s.ticker)}
                  title="제거"
                >
                  &times;
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* 에러 */}
      {error && <div className="sc-error">{error}</div>}

      {/* 로딩 */}
      {loading && (
        <div className="sc-loading">
          <div className="spinner"></div>
          <p>종목 데이터를 비교하고 있습니다...</p>
        </div>
      )}

      {/* 결과 */}
      {compareResult && !loading && (
        <div className="sc-result-section">
          {/* Score Cards */}
          <div className="sc-score-cards">
            {compareResult.stocks.map((s, idx) => (
              <div key={s.ticker} className="sc-score-card">
                <div className="sc-score-card-name">{s.name}</div>
                <div className="sc-score-card-ticker">{s.ticker} · {s.market}</div>
                <div
                  className="sc-score-value"
                  style={{ color: gradeColor(s.compass_grade) }}
                >
                  {s.compass_score != null ? s.compass_score.toFixed(1) : '-'}
                </div>
                {s.compass_grade && (
                  <span
                    className="sc-grade-badge"
                    style={{ background: gradeColor(s.compass_grade) }}
                  >
                    {s.compass_grade}
                  </span>
                )}
                {s.compass_summary && (
                  <div className="sc-score-summary">{s.compass_summary}</div>
                )}
              </div>
            ))}
          </div>

          {/* 4축 바 차트 */}
          <div className="sc-chart-box">
            <h3 className="sc-chart-title">Compass Score 4축 비교</h3>
            <div className="sc-chart-wrap">
              <Bar data={getChartData()} options={chartOptions} />
            </div>
          </div>

          {/* 기본 지표 테이블 */}
          <div className="sc-table-wrap">
            <h3 className="sc-table-title">기본 지표 비교</h3>
            <table className="sc-table">
              <thead>
                <tr>
                  <th>지표</th>
                  {compareResult.stocks.map((s) => (
                    <th key={s.ticker}>{s.name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tableRows.map((row) => (
                  <tr key={row.label}>
                    <td>{row.label}</td>
                    {compareResult.stocks.map((s) => (
                      <td key={s.ticker}>{row.getValue(s)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Disclaimer />
        </div>
      )}
    </div>
  );
}

export default StockComparisonPage;
