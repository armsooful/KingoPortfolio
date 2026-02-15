// frontend/src/pages/PortfolioComparisonPage.jsx

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import Disclaimer from '../components/Disclaimer';
import '../styles/PortfolioComparison.css';
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
        <div className="result-card pc-card">
          {/* Header */}
          <div className="result-header">
            <button className="admin-back-btn" onClick={() => navigate('/admin')}>
              ← 관리자 홈
            </button>
            <div className="result-icon">
              ⚙️
            </div>
            <h1 className="result-type" style={{ color: 'var(--primary)' }}>
              포트폴리오 성과 비교
            </h1>
            <p className="result-subtitle">
              여러 포트폴리오의 성과를 한눈에 비교하고 분석하세요
            </p>
          </div>

          {/* 면책 문구 */}
          <Disclaimer type="portfolio" />

          {/* 포트폴리오 선택 */}
          <div className="pc-section-panel">
            <h2 className="pc-section-title">
              비교할 포트폴리오 선택 (최대 5개)
            </h2>

            <div className="pc-portfolio-grid">
              {portfolios.map((portfolio) => (
                <div
                  key={portfolio.id}
                  onClick={() => togglePortfolio(portfolio.id)}
                  className={`pc-portfolio-item${selectedPortfolios.includes(portfolio.id) ? ' selected' : ''}`}
                >
                  <div className="pc-portfolio-name">
                    {portfolio.name}
                  </div>
                  <div className="pc-portfolio-meta">
                    총 자산: {formatNumber(portfolio.total_value)}원
                  </div>
                  <div className="pc-portfolio-meta">
                    수익률: {formatDecimal(portfolio.total_return)}%
                  </div>
                </div>
              ))}
            </div>

            <div className="pc-controls">
              <div>
                <label className="pc-label">
                  조회 기간
                </label>
                <select
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className="pc-select"
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
                className="btn btn-primary pc-compare-btn"
                disabled={loading || selectedPortfolios.length === 0}
              >
                {loading ? '분석 중...' : '비교하기'}
              </button>
            </div>
          </div>

          {/* 에러 메시지 */}
          {error && (
            <div className="pc-error">
              ❌ {error}
            </div>
          )}

          {/* 비교 결과 */}
          {comparisonData && (
            <div className="pc-results">
              {/* 기간 수익률 추이 차트 */}
              <div className="pc-chart-box">
                <h2 className="pc-chart-title">
                  📈 수익률 추이 ({days}일)
                </h2>
                <Line
                  data={getPerformanceChartData()}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
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
              <div className="pc-chart-box">
                <h2 className="pc-chart-title">
                  📊 기간 수익률 비교
                </h2>
                <Bar
                  data={getTotalReturnChartData()}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
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
              <div className="pc-stats-box">
                <h2 className="pc-chart-title">
                  📋 상세 통계
                </h2>
                <div className="pc-table-wrap">
                  <table className="pc-table">
                    <thead>
                      <tr>
                        <th>포트폴리오</th>
                        <th className="right">현재 총 자산</th>
                        <th className="right">기간 수익률</th>
                        <th className="right">최고가</th>
                        <th className="right">최저가</th>
                        <th className="right">평균가</th>
                        <th className="right">데이터 포인트</th>
                      </tr>
                    </thead>
                    <tbody>
                      {comparisonData.portfolios.map((item) => (
                        <tr key={item.portfolio.id}>
                          <td className="bold">
                            {item.portfolio.name}
                          </td>
                          <td className="right">
                            {formatNumber(item.portfolio.total_value)}원
                          </td>
                          <td className={`right ${item.statistics.period_return >= 0 ? 'return-positive' : 'return-negative'}`}>
                            {item.statistics.period_return >= 0 ? '+' : ''}{formatDecimal(item.statistics.period_return)}%
                          </td>
                          <td className="right">
                            {formatNumber(item.statistics.max_value)}원
                          </td>
                          <td className="right">
                            {formatNumber(item.statistics.min_value)}원
                          </td>
                          <td className="right">
                            {formatNumber(item.statistics.avg_value)}원
                          </td>
                          <td className="right">
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
          <div className="pc-footer">
            <button
              onClick={() => navigate('/admin')}
              className="btn btn-secondary"
            >
              🏠 관리자 메뉴로
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
