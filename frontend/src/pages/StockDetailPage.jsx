// frontend/src/pages/StockDetailPage.jsx

import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { getAiCommentary } from '../services/api';
import Disclaimer from '../components/Disclaimer';
import '../styles/StockDetail.css';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

// Chart.js 등록
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function StockDetailPage() {
  const navigate = useNavigate();
  const [ticker, setTicker] = useState('');
  const [days, setDays] = useState(90);
  const [loading, setLoading] = useState(false);
  const [stockData, setStockData] = useState(null);
  const [error, setError] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [aiCommentary, setAiCommentary] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);

  // 티커 검색 (자동완성)
  const searchTickers = async (query) => {
    if (!query || query.length < 1) {
      setSuggestions([]);
      return;
    }

    try {
      const response = await api.get(`/admin/stock-detail/search/ticker-list?q=${query}&limit=10`);
      if (response.data.success) {
        setSuggestions(response.data.data.tickers);
        setShowSuggestions(true);
      }
    } catch (err) {
      console.error('티커 검색 실패:', err);
    }
  };

  // 종목 상세 조회
  const fetchStockDetail = async (tickerCode) => {
    if (!tickerCode) {
      setError('종목 코드를 입력하세요.');
      return;
    }

    setLoading(true);
    setError('');
    setStockData(null);
    setAiCommentary(null);

    try {
      const response = await api.get(`/admin/stock-detail/${tickerCode}?days=${days}`);
      if (response.data.success) {
        setStockData(response.data.data);
      }
    } catch (err) {
      setError(err.response?.data?.error?.message || '종목 정보를 가져오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    fetchStockDetail(ticker);
    setShowSuggestions(false);
  };

  const handleTickerChange = (e) => {
    const value = e.target.value;
    setTicker(value);
    searchTickers(value);
  };

  const selectTicker = (selectedTicker) => {
    setTicker(selectedTicker.ticker);
    setShowSuggestions(false);
    fetchStockDetail(selectedTicker.ticker);
  };

  // 숫자 포맷 (천 단위 콤마)
  const formatNumber = (num) => {
    if (num === null || num === undefined) return '-';
    return num.toLocaleString('ko-KR');
  };

  // 숫자 포맷 (소수점 2자리)
  const formatDecimal = (num) => {
    if (num === null || num === undefined) return '-';
    return num.toFixed(2);
  };

  // 등급별 색상
  const getGradeColor = (grade) => {
    if (!grade) return '#999';
    const colors = { S: '#ff6b35', 'A+': '#4caf50', A: '#66bb6a', 'B+': '#42a5f5', B: '#90caf9', 'C+': '#ffa726', C: '#ff7043', D: '#ef5350', F: '#c62828' };
    return colors[grade] || '#999';
  };

  // AI 심층 해설 요청
  const fetchAiCommentary = async () => {
    if (!stockData?.basic_info?.ticker) return;
    setAiLoading(true);
    setAiCommentary(null);
    try {
      const response = await getAiCommentary(stockData.basic_info.ticker);
      if (response.data?.success) {
        setAiCommentary(response.data.commentary);
      }
    } catch (err) {
      setAiCommentary('AI 해설 생성에 실패했습니다.');
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card sd-card">
          {/* Header */}
          <div className="result-header">
            <button className="admin-back-btn" onClick={() => navigate('/admin')}>
              ← 관리자 홈
            </button>
            <div className="result-icon">
              ⚙️
            </div>
            <h1 className="result-type">
              종목 상세 조회
            </h1>
            <p className="result-subtitle">
              종목 코드를 입력하여 기본 정보, 재무 지표, 시계열 데이터를 확인하세요
            </p>
          </div>

          {/* 면책 문구 */}
          <Disclaimer type="stock" />

          {/* 검색 폼 */}
          <div className="sd-search-panel">
            <form onSubmit={handleSearch} className="sd-search-form">
              <div className="sd-search-field">
                <label className="sd-label">
                  종목 코드 또는 종목명
                </label>
                <input
                  type="text"
                  value={ticker}
                  onChange={handleTickerChange}
                  onFocus={() => ticker && setShowSuggestions(true)}
                  placeholder="예: 005930 또는 삼성전자"
                  className="sd-input"
                />

                {/* 자동완성 목록 */}
                {showSuggestions && suggestions.length > 0 && (
                  <div className="sd-suggestions">
                    {suggestions.map((item) => (
                      <div
                        key={item.ticker}
                        onClick={() => selectTicker(item)}
                        className="sd-suggestion-item"
                      >
                        <div className="sd-suggestion-name">
                          {item.ticker} - {item.name}
                        </div>
                        <div className="sd-suggestion-meta">
                          {item.market} | {formatNumber(item.current_price)}원
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="sd-days-field">
                <label className="sd-label">
                  조회 기간 (일)
                </label>
                <select
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className="sd-select"
                >
                  <option value={30}>30일</option>
                  <option value={60}>60일</option>
                  <option value={90}>90일</option>
                  <option value={180}>180일</option>
                  <option value={365}>365일</option>
                </select>
              </div>

              <button
                type="submit"
                className="btn btn-primary sd-search-btn"
                disabled={loading}
              >
                {loading ? '조회 중...' : '조회'}
              </button>
            </form>
          </div>

          {/* 에러 메시지 */}
          {error && (
            <div className="sd-error">
              ❌ {error}
            </div>
          )}

          {/* 결과 표시 */}
          {stockData && (
            <div className="sd-results">
              {/* 기본 정보 */}
              <div className="sd-section">
                <h2 className="sd-section-title">
                  📋 기본 정보
                </h2>
                <div className="sd-info-grid">
                  <div>
                    <div className="sd-info-label">종목코드</div>
                    <div className="sd-info-value">{stockData.basic_info.ticker}</div>
                  </div>
                  <div>
                    <div className="sd-info-label">종목명</div>
                    <div className="sd-info-value">{stockData.basic_info.name}</div>
                  </div>
                  <div>
                    <div className="sd-info-label">시장</div>
                    <div className="sd-info-value">{stockData.basic_info.market}</div>
                  </div>
                  <div>
                    <div className="sd-info-label">업종</div>
                    <div className="sd-info-value">{stockData.basic_info.sector}</div>
                  </div>
                  <div>
                    <div className="sd-info-label">현재가</div>
                    <div className="sd-info-value-highlight">
                      {formatNumber(stockData.basic_info.current_price)}원
                    </div>
                  </div>
                  <div>
                    <div className="sd-info-label">시가총액</div>
                    <div className="sd-info-value">
                      {formatNumber(stockData.basic_info.market_cap)}억원
                    </div>
                  </div>
                </div>
              </div>

              {/* Compass Score */}
              <div className="sd-section">
                <h2 className="sd-section-title">
                  🧭 Compass Score
                </h2>
                {stockData.compass?.score != null ? (
                  <>
                    <div className="sd-compass">
                      <div className="sd-compass-badge" style={{ background: `linear-gradient(135deg, ${getGradeColor(stockData.compass.grade)}, ${getGradeColor(stockData.compass.grade)}88)` }}>
                        <div className="sd-compass-badge-score">{stockData.compass.score}</div>
                        <div className="sd-compass-badge-grade">{stockData.compass.grade}</div>
                      </div>
                      <div className="sd-compass-bars">
                        {[
                          { label: '재무 (30%)', key: 'financial', color: '#4caf50' },
                          { label: '밸류 (20%)', key: 'valuation', color: '#2196f3' },
                          { label: '기술 (30%)', key: 'technical', color: '#ff9800' },
                          { label: '리스크 (20%)', key: 'risk', color: '#9c27b0' },
                        ].map(({ label, key, color }) => (
                          <div key={key} className="sd-compass-bar-row">
                            <span className="sd-compass-bar-label">{label}</span>
                            <div className="sd-compass-bar-track">
                              <div
                                className="sd-compass-bar-fill"
                                style={{ width: `${stockData.compass[key + '_score'] ?? 0}%`, backgroundColor: color }}
                              />
                            </div>
                            <span className="sd-compass-bar-value">
                              {stockData.compass[key + '_score'] != null ? `${stockData.compass[key + '_score']}점` : 'N/A'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {stockData.compass.summary && (
                      <div className="sd-compass-summary">
                        {stockData.compass.summary}
                      </div>
                    )}

                    {stockData.compass.commentary && (
                      <div className="sd-compass-commentary">
                        {stockData.compass.commentary}
                      </div>
                    )}

                    <div className="sd-compass-actions">
                      <button
                        className="sd-ai-btn"
                        onClick={fetchAiCommentary}
                        disabled={aiLoading}
                      >
                        {aiLoading ? '생성 중...' : '🤖 AI 심층 해설'}
                      </button>
                    </div>

                    {aiCommentary && (
                      <div className="sd-ai-result">
                        <div className="sd-ai-result-header">AI 심층 해설</div>
                        {aiCommentary}
                      </div>
                    )}

                    {stockData.compass.updated_at && (
                      <div className="sd-compass-meta">
                        마지막 산출: {new Date(stockData.compass.updated_at).toLocaleString('ko-KR')}
                      </div>
                    )}

                    <div className="sd-compass-disclaimer">
                      교육 목적 참고 정보이며 투자 권유가 아닙니다
                    </div>
                  </>
                ) : (
                  <div className="sd-empty">
                    Compass Score가 아직 산출되지 않았습니다. 관리자 페이지에서 일괄 계산을 실행하세요.
                  </div>
                )}
              </div>

              {/* 재무 지표 */}
              <div className="sd-section">
                <h2 className="sd-section-title">
                  💼 재무 지표
                </h2>
                <div className="sd-info-grid">
                  <div>
                    <div className="sd-info-label">PER (주가수익비율)</div>
                    <div className="sd-info-value">{formatDecimal(stockData.financials.pe_ratio)}</div>
                  </div>
                  <div>
                    <div className="sd-info-label">PBR (주가순자산비율)</div>
                    <div className="sd-info-value">{formatDecimal(stockData.financials.pb_ratio)}</div>
                  </div>
                  <div>
                    <div className="sd-info-label">배당수익률</div>
                    <div className="sd-info-value">{formatDecimal(stockData.financials.dividend_yield)}%</div>
                  </div>
                  <div>
                    <div className="sd-info-label">YTD 수익률</div>
                    <div className="sd-info-value">{formatDecimal(stockData.financials.ytd_return)}%</div>
                  </div>
                  <div>
                    <div className="sd-info-label">1년 수익률</div>
                    <div className="sd-info-value">{formatDecimal(stockData.financials.one_year_return)}%</div>
                  </div>
                </div>
              </div>

              {/* 통계 */}
              {stockData.statistics && (
                <div className="sd-section">
                  <h2 className="sd-section-title">
                    📈 기간 통계 ({days}일)
                  </h2>
                  <div className="sd-info-grid">
                    <div>
                      <div className="sd-info-label">거래일 수</div>
                      <div className="sd-info-value">{stockData.statistics.period_days}일</div>
                    </div>
                    <div>
                      <div className="sd-info-label">기간 수익률</div>
                      <div
                        className="sd-info-value-highlight"
                        style={{ color: stockData.statistics.period_return >= 0 ? '#4caf50' : '#f44336' }}
                      >
                        {stockData.statistics.period_return >= 0 ? '+' : ''}{formatDecimal(stockData.statistics.period_return)}%
                      </div>
                    </div>
                    <div>
                      <div className="sd-info-label">최고가</div>
                      <div className="sd-info-value">{formatNumber(stockData.statistics.high)}원</div>
                    </div>
                    <div>
                      <div className="sd-info-label">최저가</div>
                      <div className="sd-info-value">{formatNumber(stockData.statistics.low)}원</div>
                    </div>
                    <div>
                      <div className="sd-info-label">평균 종가</div>
                      <div className="sd-info-value">{formatNumber(stockData.statistics.avg_close)}원</div>
                    </div>
                    <div>
                      <div className="sd-info-label">평균 거래량</div>
                      <div className="sd-info-value">{formatNumber(stockData.statistics.avg_volume)}주</div>
                    </div>
                  </div>
                </div>
              )}

              {/* 가격 차트 */}
              {stockData.timeseries.data_count > 0 && (
                <div className="sd-section">
                  <h2 className="sd-section-title">
                    📈 가격 차트
                  </h2>
                  <Line
                    data={{
                      labels: stockData.timeseries.data.map(d => d.date),
                      datasets: [
                        {
                          label: '종가',
                          data: stockData.timeseries.data.map(d => d.close),
                          borderColor: '#667eea',
                          backgroundColor: 'rgba(102, 126, 234, 0.1)',
                          borderWidth: 2,
                          fill: true,
                          tension: 0.3,
                          pointRadius: 2,
                          pointHoverRadius: 5
                        },
                        {
                          label: '고가',
                          data: stockData.timeseries.data.map(d => d.high),
                          borderColor: '#f44336',
                          backgroundColor: 'rgba(244, 67, 54, 0.05)',
                          borderWidth: 1.5,
                          borderDash: [5, 5],
                          fill: false,
                          tension: 0.3,
                          pointRadius: 0,
                          pointHoverRadius: 4
                        },
                        {
                          label: '저가',
                          data: stockData.timeseries.data.map(d => d.low),
                          borderColor: '#2196f3',
                          backgroundColor: 'rgba(33, 150, 243, 0.05)',
                          borderWidth: 1.5,
                          borderDash: [5, 5],
                          fill: false,
                          tension: 0.3,
                          pointRadius: 0,
                          pointHoverRadius: 4
                        }
                      ]
                    }}
                    options={{
                      responsive: true,
                      maintainAspectRatio: true,
                      aspectRatio: 2.5,
                      plugins: {
                        legend: {
                          display: true,
                          position: 'top',
                        },
                        tooltip: {
                          mode: 'index',
                          intersect: false,
                          callbacks: {
                            label: function(context) {
                              return context.dataset.label + ': ' + context.parsed.y.toLocaleString('ko-KR') + '원';
                            }
                          }
                        }
                      },
                      scales: {
                        x: {
                          grid: {
                            display: false
                          }
                        },
                        y: {
                          grid: {
                            color: '#f0f0f0'
                          },
                          ticks: {
                            callback: function(value) {
                              return value.toLocaleString('ko-KR') + '원';
                            }
                          }
                        }
                      }
                    }}
                  />
                </div>
              )}

              {/* 거래량 차트 */}
              {stockData.timeseries.data_count > 0 && (
                <div className="sd-section">
                  <h2 className="sd-section-title">
                    📊 거래량 차트
                  </h2>
                  <Bar
                    data={{
                      labels: stockData.timeseries.data.map(d => d.date),
                      datasets: [
                        {
                          label: '거래량',
                          data: stockData.timeseries.data.map(d => d.volume),
                          backgroundColor: stockData.timeseries.data.map((d, idx) => {
                            if (idx === 0) return 'rgba(102, 126, 234, 0.6)';
                            const prevClose = stockData.timeseries.data[idx - 1].close;
                            return d.close >= prevClose
                              ? 'rgba(76, 175, 80, 0.6)'
                              : 'rgba(244, 67, 54, 0.6)';
                          }),
                          borderColor: stockData.timeseries.data.map((d, idx) => {
                            if (idx === 0) return '#667eea';
                            const prevClose = stockData.timeseries.data[idx - 1].close;
                            return d.close >= prevClose
                              ? '#4caf50'
                              : '#f44336';
                          }),
                          borderWidth: 1
                        }
                      ]
                    }}
                    options={{
                      responsive: true,
                      maintainAspectRatio: true,
                      aspectRatio: 3,
                      plugins: {
                        legend: {
                          display: true,
                          position: 'top',
                        },
                        tooltip: {
                          callbacks: {
                            label: function(context) {
                              return '거래량: ' + context.parsed.y.toLocaleString('ko-KR') + '주';
                            }
                          }
                        }
                      },
                      scales: {
                        x: {
                          grid: {
                            display: false
                          }
                        },
                        y: {
                          grid: {
                            color: '#f0f0f0'
                          },
                          ticks: {
                            callback: function(value) {
                              return value.toLocaleString('ko-KR');
                            }
                          }
                        }
                      }
                    }}
                  />
                </div>
              )}

              {/* 시계열 데이터 테이블 */}
              <div className="sd-section">
                <h2 className="sd-section-title">
                  📋 시계열 데이터 상세 ({stockData.timeseries.data_count}개 레코드)
                </h2>

                {stockData.timeseries.data_count > 0 ? (
                  <div className="sd-table-wrap">
                    <table className="sd-table">
                      <thead>
                        <tr>
                          <th>날짜</th>
                          <th className="right">시가</th>
                          <th className="right">고가</th>
                          <th className="right">저가</th>
                          <th className="right">종가</th>
                          <th className="right">거래량</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stockData.timeseries.data.slice().reverse().map((row, idx) => (
                          <tr key={idx}>
                            <td>{row.date}</td>
                            <td className="right">{formatNumber(row.open)}</td>
                            <td className="right high">{formatNumber(row.high)}</td>
                            <td className="right low">{formatNumber(row.low)}</td>
                            <td className="right bold">{formatNumber(row.close)}</td>
                            <td className="right">{formatNumber(row.volume)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="sd-empty">
                    시계열 데이터가 없습니다.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 워크플로우 내비게이션 */}
          <div className="admin-workflow-nav">
            <button
              className="admin-workflow-link"
              onClick={() => navigate('/admin/financial-analysis')}
            >
              재무 분석 →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
