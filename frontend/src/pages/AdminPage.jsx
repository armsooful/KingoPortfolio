// frontend/src/pages/AdminPage.jsx

import { useNavigate } from 'react-router-dom';

export default function AdminPage() {
  const navigate = useNavigate();

  const menuItems = [
    {
      icon: '🗄️',
      title: '데이터 관리',
      description: '종목 정보 수집 및 데이터베이스 관리',
      path: '/admin/data',
      color: '#2196F3'
    },
    {
      icon: '⚙️',
      title: '배치 작업',
      description: '한국 주식 데이터 일괄 수집 및 작업 모니터링',
      path: '/admin/batch',
      color: '#FF9800'
    },
    {
      icon: '🔍',
      title: '종목 조회',
      description: '기본 정보, 시계열 데이터, 재무 지표 한눈에 확인',
      path: '/admin/stock-detail',
      color: '#673AB7'
    },
    {
      icon: '👥',
      title: '사용자 관리',
      description: '사용자 목록, 역할 변경, 계정 삭제',
      path: '/admin/users',
      color: '#00BCD4'
    },
    {
      icon: '🧾',
      title: '동의 이력',
      description: '유의사항 동의 기록 조회',
      path: '/admin/consents',
      color: '#ef4444'
    },
    {
      icon: '📊',
      title: '포트폴리오 관리',
      description: '투자 성향별 포트폴리오 전략 및 종목 구성',
      path: '/admin/portfolio',
      color: '#667eea'
    },
    {
      icon: '📈',
      title: '포트폴리오 성과 비교',
      description: '여러 포트폴리오의 수익률과 성과를 비교 분석',
      path: '/admin/portfolio-comparison',
      color: '#9c27b0'
    },
    {
      icon: '📊',
      title: '재무 분석',
      description: 'CAGR, ROE, 부채비율 등 재무제표 분석',
      path: '/admin/financial-analysis',
      color: '#4CAF50'
    },
    {
      icon: '💼',
      title: '밸류에이션',
      description: 'PER/PBR 비교, DCF, 배당할인모형',
      path: '/admin/valuation',
      color: '#9C27B0'
    },
    {
      icon: '📈',
      title: '퀀트/기술 분석',
      description: 'RSI, MACD, 변동성, 베타, 알파 분석',
      path: '/admin/quant',
      color: '#FF9800'
    },
    {
      icon: '📄',
      title: '종합 리포트',
      description: '모든 분석 결과 통합 리포트 (투자 권고 없음)',
      path: '/admin/report',
      color: '#E91E63'
    }
  ];

  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card" style={{ maxWidth: '1200px' }}>
          {/* Header */}
          <div className="result-header">
            <div className="result-icon" style={{ fontSize: '3rem' }}>
              ⚙️
            </div>
            <h1 className="result-type" style={{ color: '#667eea' }}>
              관리자 도구
            </h1>
            <p className="result-subtitle">
              투자 분석 도구 및 데이터 관리
            </p>
          </div>

          {/* Menu Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '24px',
            marginTop: '40px'
          }}>
            {menuItems.map((item, index) => (
              <div
                key={index}
                onClick={() => navigate(item.path)}
                style={{
                  background: 'white',
                  borderRadius: '16px',
                  padding: '32px',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  cursor: 'pointer',
                  transition: 'all 0.3s',
                  border: '2px solid transparent'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-8px)';
                  e.currentTarget.style.boxShadow = '0 12px 24px rgba(0,0,0,0.15)';
                  e.currentTarget.style.borderColor = item.color;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                  e.currentTarget.style.borderColor = 'transparent';
                }}
              >
                <div style={{ fontSize: '3rem', marginBottom: '16px' }}>
                  {item.icon}
                </div>
                <h3 style={{
                  fontSize: '1.5rem',
                  fontWeight: '700',
                  color: item.color,
                  marginBottom: '12px'
                }}>
                  {item.title}
                </h3>
                <p style={{
                  fontSize: '0.95rem',
                  color: '#666',
                  lineHeight: '1.6'
                }}>
                  {item.description}
                </p>
              </div>
            ))}
          </div>

          {/* Info Section */}
          <div style={{
            marginTop: '48px',
            padding: '24px',
            background: '#f8f9fa',
            borderRadius: '12px',
            borderLeft: '4px solid #667eea'
          }}>
            <h3 style={{ fontSize: '1.2rem', marginBottom: '12px', color: '#1a1a1a' }}>
              💡 사용 안내
            </h3>
            <ul style={{
              fontSize: '0.95rem',
              color: '#666',
              lineHeight: '1.8',
              paddingLeft: '20px'
            }}>
              <li>
                <strong>데이터 관리:</strong> yfinance, Alpha Vantage, pykrx를 통해 주식/ETF 데이터를 수집하고 관리합니다.
              </li>
              <li>
                <strong>재무 분석:</strong> 재무제표 기반으로 성장률, 수익성, 안정성을 종합 분석합니다.
              </li>
              <li>
                <strong>밸류에이션:</strong> 업종 평균 비교, DCF, DDM 등 다양한 방법으로 적정 주가를 산출합니다.
              </li>
              <li>
                <strong>퀀트/기술 분석:</strong> 기술적 지표와 리스크 지표를 통해 매매 타이밍과 리스크를 분석합니다.
              </li>
            </ul>
          </div>

          {/* Quick Links */}
          <div style={{
            marginTop: '32px',
            display: 'flex',
            gap: '16px',
            flexWrap: 'wrap',
            justifyContent: 'center'
          }}>
            <button
              onClick={() => navigate('/survey')}
              className="btn btn-secondary"
              style={{ padding: '12px 24px' }}
            >
              🏠 홈으로
            </button>
            <button
              onClick={() => navigate('/history')}
              className="btn btn-secondary"
              style={{ padding: '12px 24px' }}
            >
              📋 진단 이력
            </button>
            <button
              onClick={() => window.open('http://127.0.0.1:8000/docs', '_blank')}
              className="btn btn-secondary"
              style={{ padding: '12px 24px' }}
            >
              📚 API 문서
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
