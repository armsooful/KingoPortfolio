// frontend/src/pages/StockDetailPage.jsx

import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import Disclaimer from '../components/Disclaimer';
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

  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card" style={{ maxWidth: '1400px' }}>
          {/* Header */}
          <div className="result-header">
            <div className="result-icon" style={{ fontSize: '3rem' }}>
              📊
            </div>
            <h1 className="result-type" style={{ color: '#667eea' }}>
              종목 상세 조회
            </h1>
            <p className="result-subtitle">
              종목 코드를 입력하여 기본 정보, 재무 지표, 시계열 데이터를 확인하세요
            </p>
          </div>

          {/* 면책 문구 */}
          <Disclaimer type="stock" />

          {/* 검색 폼 */}
          <div style={{
            marginTop: '32px',
            padding: '24px',
            background: '#f8f9fa',
            borderRadius: '12px'
          }}>
            <form onSubmit={handleSearch} style={{ display: 'flex', gap: '16px', alignItems: 'flex-end', position: 'relative' }}>
              <div style={{ flex: 1, position: 'relative' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#333' }}>
                  종목 코드 또는 종목명
                </label>
                <input
                  type="text"
                  value={ticker}
                  onChange={handleTickerChange}
                  onFocus={() => ticker && setShowSuggestions(true)}
                  placeholder="예: 005930 또는 삼성전자"
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    border: '2px solid #e0e0e0',
                    borderRadius: '8px',
                    fontSize: '1rem'
                  }}
                />

                {/* 자동완성 목록 */}
                {showSuggestions && suggestions.length > 0 && (
                  <div style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    background: 'white',
                    border: '1px solid #ddd',
                    borderRadius: '8px',
                    marginTop: '4px',
                    maxHeight: '300px',
                    overflowY: 'auto',
                    zIndex: 1000,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                  }}>
                    {suggestions.map((item) => (
                      <div
                        key={item.ticker}
                        onClick={() => selectTicker(item)}
                        style={{
                          padding: '12px 16px',
                          cursor: 'pointer',
                          borderBottom: '1px solid #f0f0f0',
                          transition: 'background 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = '#f8f9fa'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                      >
                        <div style={{ fontWeight: '600', color: '#333' }}>
                          {item.ticker} - {item.name}
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '4px' }}>
                          {item.market} | {formatNumber(item.current_price)}원
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div style={{ width: '150px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#333' }}>
                  조회 기간 (일)
                </label>
                <select
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    border: '2px solid #e0e0e0',
                    borderRadius: '8px',
                    fontSize: '1rem'
                  }}
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
                className="btn btn-primary"
                disabled={loading}
                style={{ padding: '12px 32px', whiteSpace: 'nowrap' }}
              >
                {loading ? '조회 중...' : '조회'}
              </button>
            </form>
          </div>

          {/* 에러 메시지 */}
          {error && (
            <div style={{
              marginTop: '24px',
              padding: '16px',
              background: '#fee',
              borderRadius: '8px',
              color: '#c33',
              border: '1px solid #fcc'
            }}>
              ❌ {error}
            </div>
          )}

          {/* 결과 표시 */}
          {stockData && (
            <div style={{ marginTop: '32px' }}>
              {/* 기본 정보 */}
              <div style={{
                padding: '24px',
                background: 'white',
                borderRadius: '12px',
                border: '1px solid #e0e0e0',
                marginBottom: '24px'
              }}>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '20px', color: '#667eea' }}>
                  📋 기본 정보
                </h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>종목코드</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>{stockData.basic_info.ticker}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>종목명</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>{stockData.basic_info.name}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>시장</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>{stockData.basic_info.market}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>업종</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>{stockData.basic_info.sector}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>현재가</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#667eea' }}>
                      {formatNumber(stockData.basic_info.current_price)}원
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>시가총액</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>
                      {formatNumber(stockData.basic_info.market_cap)}억원
                    </div>
                  </div>
                </div>
              </div>

              {/* 재무 지표 */}
              <div style={{
                padding: '24px',
                background: 'white',
                borderRadius: '12px',
                border: '1px solid #e0e0e0',
                marginBottom: '24px'
              }}>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '20px', color: '#667eea' }}>
                  💼 재무 지표
                </h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>PER (주가수익비율)</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>{formatDecimal(stockData.financials.pe_ratio)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>PBR (주가순자산비율)</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>{formatDecimal(stockData.financials.pb_ratio)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>배당수익률</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>{formatDecimal(stockData.financials.dividend_yield)}%</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>YTD 수익률</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>{formatDecimal(stockData.financials.ytd_return)}%</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>1년 수익률</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>{formatDecimal(stockData.financials.one_year_return)}%</div>
                  </div>
                </div>
              </div>

              {/* 통계 */}
              {stockData.statistics && (
                <div style={{
                  padding: '24px',
                  background: 'white',
                  borderRadius: '12px',
                  border: '1px solid #e0e0e0',
                  marginBottom: '24px'
                }}>
                  <h2 style={{ fontSize: '1.5rem', marginBottom: '20px', color: '#667eea' }}>
                    📈 기간 통계 ({days}일)
                  </h2>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                    <div>
                      <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>거래일 수</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>{stockData.statistics.period_days}일</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>기간 수익률</div>
                      <div style={{
                        fontSize: '1.1rem',
                        fontWeight: '700',
                        color: stockData.statistics.period_return >= 0 ? '#4caf50' : '#f44336'
                      }}>
                        {stockData.statistics.period_return >= 0 ? '+' : ''}{formatDecimal(stockData.statistics.period_return)}%
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>최고가</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>{formatNumber(stockData.statistics.high)}원</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>최저가</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>{formatNumber(stockData.statistics.low)}원</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>평균 종가</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>{formatNumber(stockData.statistics.avg_close)}원</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>평균 거래량</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>{formatNumber(stockData.statistics.avg_volume)}주</div>
                    </div>
                  </div>
                </div>
              )}

              {/* 가격 차트 */}
              {stockData.timeseries.data_count > 0 && (
                <div style={{
                  padding: '24px',
                  background: 'white',
                  borderRadius: '12px',
                  border: '1px solid #e0e0e0',
                  marginBottom: '24px'
                }}>
                  <h2 style={{ fontSize: '1.5rem', marginBottom: '20px', color: '#667eea' }}>
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
                <div style={{
                  padding: '24px',
                  background: 'white',
                  borderRadius: '12px',
                  border: '1px solid #e0e0e0',
                  marginBottom: '24px'
                }}>
                  <h2 style={{ fontSize: '1.5rem', marginBottom: '20px', color: '#667eea' }}>
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
              <div style={{
                padding: '24px',
                background: 'white',
                borderRadius: '12px',
                border: '1px solid #e0e0e0'
              }}>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '20px', color: '#667eea' }}>
                  📋 시계열 데이터 상세 ({stockData.timeseries.data_count}개 레코드)
                </h2>

                {stockData.timeseries.data_count > 0 ? (
                  <div style={{ overflowX: 'auto', maxHeight: '500px', overflowY: 'auto' }}>
                    <table style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      fontSize: '0.9rem'
                    }}>
                      <thead style={{ position: 'sticky', top: 0, background: '#f8f9fa' }}>
                        <tr>
                          <th style={{ padding: '12px', borderBottom: '2px solid #ddd', textAlign: 'left' }}>날짜</th>
                          <th style={{ padding: '12px', borderBottom: '2px solid #ddd', textAlign: 'right' }}>시가</th>
                          <th style={{ padding: '12px', borderBottom: '2px solid #ddd', textAlign: 'right' }}>고가</th>
                          <th style={{ padding: '12px', borderBottom: '2px solid #ddd', textAlign: 'right' }}>저가</th>
                          <th style={{ padding: '12px', borderBottom: '2px solid #ddd', textAlign: 'right' }}>종가</th>
                          <th style={{ padding: '12px', borderBottom: '2px solid #ddd', textAlign: 'right' }}>거래량</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stockData.timeseries.data.slice().reverse().map((row, idx) => (
                          <tr key={idx} style={{ background: idx % 2 === 0 ? 'white' : '#f9f9f9' }}>
                            <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>{row.date}</td>
                            <td style={{ padding: '10px', borderBottom: '1px solid #eee', textAlign: 'right' }}>{formatNumber(row.open)}</td>
                            <td style={{ padding: '10px', borderBottom: '1px solid #eee', textAlign: 'right', color: '#f44336' }}>{formatNumber(row.high)}</td>
                            <td style={{ padding: '10px', borderBottom: '1px solid #eee', textAlign: 'right', color: '#2196f3' }}>{formatNumber(row.low)}</td>
                            <td style={{ padding: '10px', borderBottom: '1px solid #eee', textAlign: 'right', fontWeight: '600' }}>{formatNumber(row.close)}</td>
                            <td style={{ padding: '10px', borderBottom: '1px solid #eee', textAlign: 'right' }}>{formatNumber(row.volume)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                    시계열 데이터가 없습니다.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 버튼 */}
          <div style={{ marginTop: '32px', display: 'flex', gap: '12px', justifyContent: 'center' }}>
            <button
              onClick={() => navigate('/admin')}
              className="btn btn-secondary"
              style={{ padding: '12px 24px' }}
            >
              🏠 관리자 메뉴로
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
