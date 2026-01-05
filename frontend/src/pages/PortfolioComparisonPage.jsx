// frontend/src/pages/PortfolioComparisonPage.jsx

import { useState, useEffect } from 'react';
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

const CHART_COLORS = [
  { border: '#667eea', bg: 'rgba(102, 126, 234, 0.1)' },
  { border: '#4caf50', bg: 'rgba(76, 175, 80, 0.1)' },
  { border: '#f44336', bg: 'rgba(244, 67, 54, 0.1)' },
  { border: '#ff9800', bg: 'rgba(255, 152, 0, 0.1)' },
  { border: '#9c27b0', bg: 'rgba(156, 39, 176, 0.1)' }
];

export default function PortfolioComparisonPage() {
  const navigate = useNavigate();
  const [portfolios, setPortfolios] = useState([]);
  const [selectedPortfolios, setSelectedPortfolios] = useState([]);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [comparisonData, setComparisonData] = useState(null);
  const [error, setError] = useState('');

  // 포트폴리오 목록 조회
  useEffect(() => {
    const fetchPortfolios = async () => {
      try {
        const response = await api.get('/admin/portfolio-comparison/list');
        if (response.data.success) {
          setPortfolios(response.data.data.portfolios);
        }
      } catch (err) {
        console.error('포트폴리오 목록 조회 실패:', err);
        setError('포트폴리오 목록을 가져오는데 실패했습니다.');
      }
    };

    fetchPortfolios();
  }, []);

  // 포트폴리오 선택/해제
  const togglePortfolio = (portfolioId) => {
    setSelectedPortfolios(prev => {
      if (prev.includes(portfolioId)) {
        return prev.filter(id => id !== portfolioId);
      } else {
        if (prev.length >= 5) {
          setError('최대 5개의 포트폴리오까지 선택할 수 있습니다.');
          return prev;
        }
        return [...prev, portfolioId];
      }
    });
    setError('');
  };

  // 비교 실행
  const handleCompare = async () => {
    if (selectedPortfolios.length < 1) {
      setError('최소 1개 이상의 포트폴리오를 선택해주세요.');
      return;
    }

    setLoading(true);
    setError('');
    setComparisonData(null);

    try {
      const response = await api.get(`/admin/portfolio-comparison/compare?portfolio_ids=${selectedPortfolios.join(',')}&days=${days}`);
      if (response.data.success) {
        setComparisonData(response.data.data);
      }
    } catch (err) {
      setError(err.response?.data?.detail || '비교 데이터를 가져오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 숫자 포맷
  const formatNumber = (num) => {
    if (num === null || num === undefined) return '-';
    return num.toLocaleString('ko-KR');
  };

  const formatDecimal = (num) => {
    if (num === null || num === undefined) return '-';
    return num.toFixed(2);
  };

  // 수익률 추이 차트 데이터 생성
  const getPerformanceChartData = () => {
    if (!comparisonData) return null;

    const allDates = new Set();
    comparisonData.portfolios.forEach(p => {
      p.timeseries.forEach(ts => allDates.add(ts.date));
    });
    const sortedDates = Array.from(allDates).sort();

    const datasets = comparisonData.portfolios.map((portfolio, idx) => {
      const color = CHART_COLORS[idx % CHART_COLORS.length];

      // 각 날짜별로 수익률 매핑
      const data = sortedDates.map(date => {
        const record = portfolio.timeseries.find(ts => ts.date === date);
        return record ? record.total_return : null;
      });

      return {
        label: portfolio.portfolio.name,
        data: data,
        borderColor: color.border,
        backgroundColor: color.bg,
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 2,
        pointHoverRadius: 5,
        spanGaps: true
      };
    });

    return {
      labels: sortedDates,
      datasets: datasets
    };
  };

  // 총 수익률 비교 차트 데이터
  const getTotalReturnChartData = () => {
    if (!comparisonData) return null;

    const labels = comparisonData.portfolios.map(p => p.portfolio.name);
    const data = comparisonData.portfolios.map(p => p.statistics.period_return);
    const backgroundColors = comparisonData.portfolios.map((p, idx) => {
      const color = CHART_COLORS[idx % CHART_COLORS.length];
      return p.statistics.period_return >= 0 ? color.bg.replace('0.1', '0.6') : 'rgba(244, 67, 54, 0.6)';
    });
    const borderColors = comparisonData.portfolios.map((p, idx) => {
      const color = CHART_COLORS[idx % CHART_COLORS.length];
      return p.statistics.period_return >= 0 ? color.border : '#f44336';
    });

    return {
      labels: labels,
      datasets: [
        {
          label: '기간 수익률 (%)',
          data: data,
          backgroundColor: backgroundColors,
          borderColor: borderColors,
          borderWidth: 1
        }
      ]
    };
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
              포트폴리오 성과 비교
            </h1>
            <p className="result-subtitle">
              여러 포트폴리오의 성과를 한눈에 비교하고 분석하세요
            </p>
          </div>

          {/* 면책 문구 */}
          <Disclaimer type="portfolio" />

          {/* 포트폴리오 선택 */}
          <div style={{
            marginTop: '32px',
            padding: '24px',
            background: '#f8f9fa',
            borderRadius: '12px'
          }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '16px', color: '#333' }}>
              비교할 포트폴리오 선택 (최대 5개)
            </h2>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '12px', marginBottom: '24px' }}>
              {portfolios.map((portfolio) => (
                <div
                  key={portfolio.id}
                  onClick={() => togglePortfolio(portfolio.id)}
                  style={{
                    padding: '16px',
                    background: selectedPortfolios.includes(portfolio.id) ? '#667eea' : 'white',
                    color: selectedPortfolios.includes(portfolio.id) ? 'white' : '#333',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    border: selectedPortfolios.includes(portfolio.id) ? '2px solid #667eea' : '2px solid #e0e0e0',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    if (!selectedPortfolios.includes(portfolio.id)) {
                      e.currentTarget.style.borderColor = '#667eea';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!selectedPortfolios.includes(portfolio.id)) {
                      e.currentTarget.style.borderColor = '#e0e0e0';
                    }
                  }}
                >
                  <div style={{ fontWeight: '600', fontSize: '1.1rem', marginBottom: '8px' }}>
                    {portfolio.name}
                  </div>
                  <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>
                    총 자산: {formatNumber(portfolio.total_value)}원
                  </div>
                  <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>
                    수익률: {formatDecimal(portfolio.total_return)}%
                  </div>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#333' }}>
                  조회 기간
                </label>
                <select
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  style={{
                    padding: '12px 16px',
                    border: '2px solid #e0e0e0',
                    borderRadius: '8px',
                    fontSize: '1rem'
                  }}
                >
                  <option value={7}>1주일</option>
                  <option value={30}>1개월</option>
                  <option value={90}>3개월</option>
                  <option value={180}>6개월</option>
                  <option value={365}>1년</option>
                </select>
              </div>

              <button
                onClick={handleCompare}
                className="btn btn-primary"
                disabled={loading || selectedPortfolios.length === 0}
                style={{ padding: '12px 32px', marginTop: '28px' }}
              >
                {loading ? '분석 중...' : '비교하기'}
              </button>
            </div>
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

          {/* 비교 결과 */}
          {comparisonData && (
            <div style={{ marginTop: '32px' }}>
              {/* 기간 수익률 추이 차트 */}
              <div style={{
                padding: '24px',
                background: 'white',
                borderRadius: '12px',
                border: '1px solid #e0e0e0',
                marginBottom: '24px'
              }}>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '20px', color: '#667eea' }}>
                  📈 수익률 추이 ({days}일)
                </h2>
                <Line
                  data={getPerformanceChartData()}
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
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + '%';
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
                            return value.toFixed(1) + '%';
                          }
                        }
                      }
                    }
                  }}
                />
              </div>

              {/* 총 수익률 비교 */}
              <div style={{
                padding: '24px',
                background: 'white',
                borderRadius: '12px',
                border: '1px solid #e0e0e0',
                marginBottom: '24px'
              }}>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '20px', color: '#667eea' }}>
                  📊 기간 수익률 비교
                </h2>
                <Bar
                  data={getTotalReturnChartData()}
                  options={{
                    responsive: true,
                    maintainAspectRatio: true,
                    aspectRatio: 3,
                    plugins: {
                      legend: {
                        display: false
                      },
                      tooltip: {
                        callbacks: {
                          label: function(context) {
                            return '수익률: ' + context.parsed.y.toFixed(2) + '%';
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
                            return value.toFixed(1) + '%';
                          }
                        }
                      }
                    }
                  }}
                />
              </div>

              {/* 상세 통계 */}
              <div style={{
                padding: '24px',
                background: 'white',
                borderRadius: '12px',
                border: '1px solid #e0e0e0'
              }}>
                <h2 style={{ fontSize: '1.5rem', marginBottom: '20px', color: '#667eea' }}>
                  📋 상세 통계
                </h2>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    fontSize: '0.9rem'
                  }}>
                    <thead style={{ background: '#f8f9fa' }}>
                      <tr>
                        <th style={{ padding: '12px', borderBottom: '2px solid #ddd', textAlign: 'left' }}>포트폴리오</th>
                        <th style={{ padding: '12px', borderBottom: '2px solid #ddd', textAlign: 'right' }}>현재 총 자산</th>
                        <th style={{ padding: '12px', borderBottom: '2px solid #ddd', textAlign: 'right' }}>기간 수익률</th>
                        <th style={{ padding: '12px', borderBottom: '2px solid #ddd', textAlign: 'right' }}>최고가</th>
                        <th style={{ padding: '12px', borderBottom: '2px solid #ddd', textAlign: 'right' }}>최저가</th>
                        <th style={{ padding: '12px', borderBottom: '2px solid #ddd', textAlign: 'right' }}>평균가</th>
                        <th style={{ padding: '12px', borderBottom: '2px solid #ddd', textAlign: 'right' }}>데이터 포인트</th>
                      </tr>
                    </thead>
                    <tbody>
                      {comparisonData.portfolios.map((item, idx) => (
                        <tr key={item.portfolio.id} style={{ background: idx % 2 === 0 ? 'white' : '#f9f9f9' }}>
                          <td style={{ padding: '12px', borderBottom: '1px solid #eee', fontWeight: '600' }}>
                            {item.portfolio.name}
                          </td>
                          <td style={{ padding: '12px', borderBottom: '1px solid #eee', textAlign: 'right' }}>
                            {formatNumber(item.portfolio.total_value)}원
                          </td>
                          <td style={{
                            padding: '12px',
                            borderBottom: '1px solid #eee',
                            textAlign: 'right',
                            fontWeight: '600',
                            color: item.statistics.period_return >= 0 ? '#4caf50' : '#f44336'
                          }}>
                            {item.statistics.period_return >= 0 ? '+' : ''}{formatDecimal(item.statistics.period_return)}%
                          </td>
                          <td style={{ padding: '12px', borderBottom: '1px solid #eee', textAlign: 'right' }}>
                            {formatNumber(item.statistics.max_value)}원
                          </td>
                          <td style={{ padding: '12px', borderBottom: '1px solid #eee', textAlign: 'right' }}>
                            {formatNumber(item.statistics.min_value)}원
                          </td>
                          <td style={{ padding: '12px', borderBottom: '1px solid #eee', textAlign: 'right' }}>
                            {formatNumber(item.statistics.avg_value)}원
                          </td>
                          <td style={{ padding: '12px', borderBottom: '1px solid #eee', textAlign: 'right' }}>
                            {item.statistics.data_points}개
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
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
