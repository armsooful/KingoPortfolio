import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../App';

function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => {
    return location.pathname === path;
  };

  return (
    <header className="header">
      <div className="header-container">
        {/* 로고 */}
        <div className="header-logo">
          <button
            className="logo-button"
            onClick={() => navigate('/survey')}
            title="Foresto Compass 홈"
          >
            <span className="logo-icon">🌲</span>
            <span className="logo-text">Foresto Compass</span>
          </button>
        </div>

        {/* 네비게이션 */}
        <nav className="header-nav">
          <button
            className={`nav-link ${isActive('/dashboard') ? 'active' : ''}`}
            onClick={() => navigate('/dashboard')}
          >
            시장현황
          </button>
          <button
            className={`nav-link ${isActive('/survey') ? 'active' : ''}`}
            onClick={() => navigate('/survey')}
            title="용어 이해를 돕는 선택적 도구"
          >
            용어학습
          </button>
          <button
            className={`nav-link ${isActive('/result') ? 'active' : ''}`}
            onClick={() => navigate('/result')}
          >
            진단결과
          </button>
          <button
            className={`nav-link ${isActive('/history') ? 'active' : ''}`}
            onClick={() => navigate('/history')}
          >
            진단이력
          </button>
          <button
            className={`nav-link ${isActive('/scenarios') ? 'active' : ''}`}
            onClick={() => navigate('/scenarios')}
            title="시나리오 기반 모의실험"
          >
            시나리오
          </button>
          <button
            className={`nav-link ${isActive('/portfolio') ? 'active' : ''}`}
            onClick={() => navigate('/portfolio')}
            title="전략 시뮬레이션"
          >
            포트폴리오
          </button>
          <button
            className={`nav-link ${isActive('/backtest') ? 'active' : ''}`}
            onClick={() => navigate('/backtest')}
            title="백테스팅"
          >
            백테스팅
          </button>
          <button
            className={`nav-link ${isActive('/analysis') ? 'active' : ''}`}
            onClick={() => navigate('/analysis')}
            title="포트폴리오 성과 해석"
          >
            성과해석
          </button>
          <button
            className={`nav-link ${isActive('/phase7-evaluation') ? 'active' : ''}`}
            onClick={() => navigate('/phase7-evaluation')}
            title="직접 구성한 포트폴리오 평가"
          >
            포트폴리오 평가
          </button>
          <button
            className={`nav-link ${isActive('/report-history') ? 'active' : ''}`}
            onClick={() => navigate('/report-history')}
            title="리포트 히스토리"
          >
            리포트
          </button>
          <button
            className={`nav-link ${isActive('/profile') ? 'active' : ''}`}
            onClick={() => navigate('/profile')}
            title="내 프로필"
          >
            프로필
          </button>
          {user && user.role === 'admin' && (
            <button
              className={`nav-link ${isActive('/admin') ? 'active' : ''}`}
              onClick={() => navigate('/admin')}
              title="데이터 수집 및 관리"
            >
              🔧 관리자
            </button>
          )}
        </nav>

        {/* 사용자 정보 및 로그아웃 */}
        <div className="header-user">
          {user && (
            <div className="user-info">
              <div className="user-name-section">
                <span className="user-name">{user.name || user.email}</span>
                <span className="user-email">({user.email})</span>
              </div>
              <div className="user-tier-section">
                <span
                  className="tier-badge vip-tier"
                  style={{
                    color: user.vip_tier === 'diamond' ? '#b9f2ff' :
                           user.vip_tier === 'platinum' ? '#e5e4e2' :
                           user.vip_tier === 'gold' ? '#ffd700' :
                           user.vip_tier === 'silver' ? '#c0c0c0' : '#cd7f32'
                  }}
                  title={`활동 점수: ${user.activity_points || 0}점`}
                >
                  {user.vip_tier === 'diamond' && '💠'}
                  {user.vip_tier === 'platinum' && '💎'}
                  {user.vip_tier === 'gold' && '🥇'}
                  {user.vip_tier === 'silver' && '🥈'}
                  {(!user.vip_tier || user.vip_tier === 'bronze') && '🥉'}
                  {' '}
                  {(user.vip_tier || 'bronze').toUpperCase()}
                </span>
                <span
                  className="tier-badge membership-tier"
                  style={{
                    color: user.membership_plan === 'enterprise' ? '#8b5cf6' :
                           user.membership_plan === 'pro' ? '#3b82f6' :
                           user.membership_plan === 'starter' ? '#10b981' : '#6b7280'
                  }}
                >
                  {user.membership_plan === 'enterprise' && '🏢'}
                  {user.membership_plan === 'pro' && '🚀'}
                  {user.membership_plan === 'starter' && '🌱'}
                  {(!user.membership_plan || user.membership_plan === 'free') && '🆓'}
                  {' '}
                  {(user.membership_plan || 'free').toUpperCase()}
                </span>
              </div>
            </div>
          )}
          <button
            className="btn btn-logout"
            onClick={handleLogout}
            title="로그아웃"
          >
            로그아웃
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
