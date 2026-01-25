import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../App';

function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [openGroup, setOpenGroup] = useState(null);
  const navRef = useRef(null);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => {
    return location.pathname === path;
  };

  const isAnyActive = (paths = []) => {
    return paths.some((path) => isActive(path));
  };

  const navGroups = useMemo(() => {
    const groups = [
      {
        label: '학습',
        items: [
          { label: '시장현황', path: '/dashboard' },
          { label: '시나리오', path: '/scenarios' },
          { label: '용어학습', path: '/terminology' },
        ],
      },
      {
        label: '진단',
        items: [
          { label: '투자성향진단', path: '/survey' },
          { label: '진단결과', path: '/result' },
          { label: '진단이력', path: '/history' },
        ],
      },
      {
        label: '포트폴리오',
        items: [
          { label: '포트폴리오', path: '/portfolio' },
          { label: '백테스팅', path: '/backtest' },
          { label: '성과해석', path: '/analysis' },
          { label: '포트폴리오 구성', path: '/portfolio-builder' },
          {
            label: '포트폴리오 평가',
            path: '/portfolio-evaluation',
            activePaths: ['/portfolio-evaluation', '/phase7-evaluation'],
          },
          { label: '리포트', path: '/report-history' },
        ],
      },
      {
        label: '계정',
        items: [{ label: '프로필', path: '/profile' }],
      },
    ];

    if (user && user.role === 'admin') {
      groups.push({
        label: '관리',
        items: [
          { label: '관리자 홈', path: '/admin' },
          { label: '데이터 관리', path: '/admin/data' },
          { label: '사용자 관리', path: '/admin/users' },
          { label: '포트폴리오 관리', path: '/admin/portfolio' },
          { label: '포트폴리오 비교', path: '/admin/portfolio-comparison' },
          { label: '배치 작업', path: '/admin/batch' },
          { label: '종목 상세', path: '/admin/stock-detail' },
          { label: '재무 분석', path: '/admin/financial-analysis' },
          { label: '밸류에이션', path: '/admin/valuation' },
          { label: '퀀트 분석', path: '/admin/quant' },
          { label: '리포트', path: '/admin/report' },
        ],
      });
    }

    return groups;
  }, [user]);

  const handleToggleGroup = (label) => {
    setOpenGroup((prev) => (prev === label ? null : label));
  };

  const handleNavigate = (path) => {
    setOpenGroup(null);
    navigate(path);
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (navRef.current && !navRef.current.contains(event.target)) {
        setOpenGroup(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
        <nav className="header-nav" ref={navRef}>
          {navGroups.map((group) => {
            const groupPaths = group.items.flatMap((item) =>
              item.activePaths ? item.activePaths : [item.path]
            );
            const isGroupActive = isAnyActive(groupPaths);
            const isOpen = openGroup === group.label;
            return (
              <div key={group.label} className="nav-group">
                <button
                  type="button"
                  className={`nav-group-button ${isGroupActive ? 'active' : ''}`}
                  onClick={() => handleToggleGroup(group.label)}
                  aria-haspopup="true"
                  aria-expanded={isOpen}
                >
                  {group.label}
                  <span className="nav-caret">▾</span>
                </button>
                {isOpen && (
                  <div className="nav-dropdown">
                    {group.items.map((item) => {
                      const itemPaths = item.activePaths || [item.path];
                      const isItemActive = isAnyActive(itemPaths);
                      return (
                        <button
                          key={item.label}
                          type="button"
                          className={`nav-dropdown-item ${isItemActive ? 'active' : ''}`}
                          onClick={() => handleNavigate(item.path)}
                        >
                          {item.label}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
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
