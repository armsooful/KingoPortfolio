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
      title: '학습 성향 분석',
      description: '교육 목적의 성향 분석과 다양한 전략 구성 예시를 제공합니다'
    },
    {
      icon: '💼',
      title: '재무 데이터 학습',
      description: 'CAGR, ROE, 부채비율 등 재무지표를 이해하고 학습합니다'
    },
    {
      icon: '📈',
      title: '퀀트 지표 학습',
      description: '데이터 기반 분석 기법을 이해하고 학습할 수 있습니다'
    },
    {
      icon: '🎯',
      title: '전략 시뮬레이션',
      description: '다양한 자산 배분 전략을 시뮬레이션으로 학습합니다 (교육용)'
    },
    {
      icon: '📰',
      title: '정보 분석 학습',
      description: 'AI 기반 감성 분석 기법과 시장 정보를 학습합니다'
    },
    {
      icon: '📉',
      title: '리스크 개념 학습',
      description: '포트폴리오의 리스크 개념과 분석 방법을 이해합니다'
    }
  ];

  return (
    <div className="landing-container">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-badge">🌲 Foresto Compass</div>
          <h1 className="hero-title">
            투자 전략을 학습하는
            <br />
            <span className="gradient-text">교육용 시뮬레이션 플랫폼</span>
          </h1>
          <p className="hero-description">
            AI 기반 분석 기법을 이해하고 다양한 전략을 학습합니다.
            <br />
            지금 시작하여 자산 운용 지식을 쌓아보세요.
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
            <a
              href="https://blog.foresto.co.kr"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-blog-link"
            >
              📝 블로그
            </a>
          </div>
        </div>
        <div className="hero-illustration">
          <div className="illustration-card card-1">
            <div className="card-icon">📊</div>
            <div className="card-text">성향 분석</div>
          </div>
          <div className="illustration-card card-2">
            <div className="card-icon">📈</div>
            <div className="card-text">전략 시뮬레이션</div>
          </div>
          <div className="illustration-card card-3">
            <div className="card-icon">🎯</div>
            <div className="card-text">지식 학습</div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <div className="section-header">
          <h2>Foresto Compass의 특별한 기능</h2>
          <p>다양한 분석 기법과 투자 지식을 학습해보세요</p>
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
          <p>복잡한 절차 없이 빠르게 학습 성향 분석을 받아보실 수 있습니다</p>
        </div>
        <div className="steps-container">
          <div className="step-card">
            <div className="step-number">1</div>
            <h3 className="step-title">회원가입</h3>
            <p className="step-description">
              간단한 정보 입력으로 계정을 만들고 학습 환경을 설정합니다
            </p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step-card">
            <div className="step-number">2</div>
            <h3 className="step-title">학습 성향 진단</h3>
            <p className="step-description">
              설문조사를 통해 학습 성향과 관심 분야를 분석합니다
            </p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step-card">
            <div className="step-number">3</div>
            <h3 className="step-title">전략 시뮬레이션</h3>
            <p className="step-description">
              다양한 자산 배분 전략의 구성 예시를 시뮬레이션으로 확인합니다
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="cta-content">
          <h2 className="cta-title">지금 바로 시작하세요</h2>
          <p className="cta-description">
            무료 회원가입으로 투자 전략 학습과 시뮬레이션을 경험해보세요
          </p>
          <button
            className="btn-cta"
            onClick={() => navigate('/signup')}
          >
            무료로 시작하기
          </button>
        </div>
      </section>

    </div>
  );
}

export default LandingPage;
