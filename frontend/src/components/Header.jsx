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
            title="KingoPortfolio 홈"
          >
            <span className="logo-icon">👑</span>
            <span className="logo-text">KingoPortfolio</span>
          </button>
        </div>

        {/* 네비게이션 */}
        <nav className="header-nav">
          <button
            className={`nav-link ${isActive('/survey') ? 'active' : ''}`}
            onClick={() => navigate('/survey')}
          >
            설문조사
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
            className={`nav-link ${isActive('/profile') ? 'active' : ''}`}
            onClick={() => navigate('/profile')}
            title="내 프로필"
          >
            프로필
          </button>
          <button
            className={`nav-link ${isActive('/admin') ? 'active' : ''}`}
            onClick={() => navigate('/admin')}
            title="데이터 수집 및 관리"
          >
            🔧 관리자
          </button>
        </nav>

        {/* 사용자 정보 및 로그아웃 */}
        <div className="header-user">
          {user && (
            <div className="user-info">
              <span className="user-name">{user.name || user.email}</span>
              <span className="user-email">({user.email})</span>
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