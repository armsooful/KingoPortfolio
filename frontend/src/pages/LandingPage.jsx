import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { useEffect } from 'react';
import '../styles/LandingPage.css';

function LandingPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  // 이미 로그인한 사용자는 설문조사 페이지로 리다이렉트
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/survey');
    }
  }, [isAuthenticated, navigate]);

  const features = [
    {
      icon: '📊',
      title: '포트폴리오 진단',
      description: '투자 성향을 분석하고 다양한 전략 구성 예시를 제공합니다'
    },
    {
      icon: '💼',
      title: '재무 분석',
      description: 'CAGR, ROE, 부채비율 등 상세한 재무제표 분석을 제공합니다'
    },
    {
      icon: '📈',
      title: '퀀트 분석',
      description: '데이터 기반 투자 전략으로 수익률을 극대화합니다'
    },
    {
      icon: '🎯',
      title: '전략 학습',
      description: '다양한 투자 전략의 포트폴리오 구성 방식을 시뮬레이션으로 학습합니다'
    },
    {
      icon: '📰',
      title: '뉴스 분석',
      description: 'AI 기반 뉴스 감성 분석으로 시장 동향을 파악합니다'
    },
    {
      icon: '📉',
      title: '리스크 관리',
      description: '포트폴리오의 리스크를 분석하고 관리 방안을 제시합니다'
    }
  ];

  return (
    <div className="landing-container">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-badge">👑 KingoPortfolio</div>
          <h1 className="hero-title">
            당신만을 위한
            <br />
            <span className="gradient-text">스마트 투자 포트폴리오</span>
          </h1>
          <p className="hero-description">
            AI 기반 분석으로 최적의 투자 전략을 제공합니다.
            <br />
            지금 시작하여 성공적인 투자의 첫 걸음을 내디뎌보세요.
          </p>
          <div className="hero-actions">
            <button
              className="btn-primary-large"
              onClick={() => navigate('/signup')}
            >
              무료로 시작하기
            </button>
            <button
              className="btn-secondary-large"
              onClick={() => navigate('/login')}
            >
              로그인
            </button>
          </div>
        </div>
        <div className="hero-illustration">
          <div className="illustration-card card-1">
            <div className="card-icon">📊</div>
            <div className="card-text">포트폴리오 분석</div>
          </div>
          <div className="illustration-card card-2">
            <div className="card-icon">📈</div>
            <div className="card-text">수익률 극대화</div>
          </div>
          <div className="illustration-card card-3">
            <div className="card-icon">🎯</div>
            <div className="card-text">전략 학습</div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <div className="section-header">
          <h2>KingoPortfolio의 특별한 기능</h2>
          <p>전문가 수준의 투자 분석 도구를 지금 경험해보세요</p>
        </div>
        <div className="features-grid">
          {features.map((feature, index) => (
            <div key={index} className="feature-card">
              <div className="feature-icon">{feature.icon}</div>
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-description">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works Section */}
      <section className="how-it-works-section">
        <div className="section-header">
          <h2>간단한 3단계로 시작하세요</h2>
          <p>복잡한 절차 없이 빠르게 투자 분석을 받아보실 수 있습니다</p>
        </div>
        <div className="steps-container">
          <div className="step-card">
            <div className="step-number">1</div>
            <h3 className="step-title">회원가입</h3>
            <p className="step-description">
              간단한 정보 입력으로 계정을 만들고 투자 성향을 설정합니다
            </p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step-card">
            <div className="step-number">2</div>
            <h3 className="step-title">포트폴리오 진단</h3>
            <p className="step-description">
              설문조사를 통해 당신의 투자 성향과 목표를 분석합니다
            </p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step-card">
            <div className="step-number">3</div>
            <h3 className="step-title">전략 시뮬레이션</h3>
            <p className="step-description">
              다양한 투자 전략의 포트폴리오 구성 예시를 시뮬레이션으로 확인합니다
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="cta-content">
          <h2 className="cta-title">지금 바로 시작하세요</h2>
          <p className="cta-description">
            무료 회원가입으로 전문가 수준의 포트폴리오 분석을 경험해보세요
          </p>
          <button
            className="btn-cta"
            onClick={() => navigate('/signup')}
          >
            무료로 시작하기
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <p>&copy; 2025 KingoPortfolio. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default LandingPage;
