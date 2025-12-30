import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import '../styles/UserManagement.css';

function UserManagementPage() {
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);

  // 사용자 목록 조회
  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/admin/users');
      setUsers(response.data.items);
    } catch (err) {
      console.error('Failed to fetch users:', err);
      setError(err.response?.data?.detail || '사용자 목록을 불러오는데 실패했습니다.');

      if (err.response?.status === 401 || err.response?.status === 403) {
        navigate('/login');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // 역할 변경
  const handleRoleChange = async (userId, newRole) => {
    if (!window.confirm(`정말로 이 사용자의 역할을 ${newRole}(으)로 변경하시겠습니까?`)) {
      return;
    }

    try {
      const response = await api.put(`/admin/users/${userId}/role?role=${newRole}`);
      setSuccessMessage(response.data.message);
      setTimeout(() => setSuccessMessage(''), 3000);
      await fetchUsers();
    } catch (err) {
      console.error('Failed to update user role:', err);
      setError(err.response?.data?.detail || '역할 변경에 실패했습니다.');
      setTimeout(() => setError(null), 5000);
    }
  };

  // 사용자 삭제
  const handleDeleteUser = async (userId, userEmail) => {
    if (!window.confirm(`정말로 사용자 "${userEmail}"를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.`)) {
      return;
    }

    try {
      const response = await api.delete(`/admin/users/${userId}`);
      setSuccessMessage(response.data.message);
      setTimeout(() => setSuccessMessage(''), 3000);
      await fetchUsers();
      if (selectedUser?.id === userId) {
        setSelectedUser(null);
      }
    } catch (err) {
      console.error('Failed to delete user:', err);
      setError(err.response?.data?.detail || '사용자 삭제에 실패했습니다.');
      setTimeout(() => setError(null), 5000);
    }
  };

  // 나이 계산
  const calculateAge = (birthDate) => {
    if (!birthDate) return null;
    const today = new Date();
    const birth = new Date(birthDate);
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--;
    }
    return age;
  };

  if (loading) {
    return (
      <div className="user-management-container">
        <div className="loading-spinner">사용자 목록을 불러오는 중...</div>
      </div>
    );
  }

  return (
    <div className="user-management-container">
      <div className="user-management-header">
        <h1>사용자 관리</h1>
        <button className="btn-back" onClick={() => navigate('/admin')}>
          관리자 페이지로 돌아가기
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {successMessage && <div className="alert alert-success">{successMessage}</div>}

      <div className="user-stats">
        <div className="stat-card">
          <h3>전체 사용자</h3>
          <p className="stat-value">{users.length}명</p>
        </div>
        <div className="stat-card">
          <h3>관리자</h3>
          <p className="stat-value">{users.filter(u => u.role === 'admin').length}명</p>
        </div>
        <div className="stat-card">
          <h3>일반 사용자</h3>
          <p className="stat-value">{users.filter(u => u.role === 'user').length}명</p>
        </div>
      </div>

      <div className="users-table-container">
        <table className="users-table">
          <thead>
            <tr>
              <th>이메일</th>
              <th>이름</th>
              <th>직업</th>
              <th>역할</th>
              <th>가입일</th>
              <th>관리</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.email}</td>
                <td>{user.name || '(없음)'}</td>
                <td>{user.occupation || '(없음)'}</td>
                <td>
                  <span className={`role-badge role-${user.role}`}>
                    {user.role === 'admin' ? '관리자' : '일반 사용자'}
                  </span>
                </td>
                <td>
                  {user.created_at
                    ? new Date(user.created_at).toLocaleDateString('ko-KR')
                    : '(알 수 없음)'}
                </td>
                <td>
                  <div className="action-buttons">
                    <button
                      className="btn-action btn-view"
                      onClick={() => setSelectedUser(user)}
                      title="상세 정보 보기"
                    >
                      상세 보기
                    </button>
                    {user.role === 'admin' ? (
                      <button
                        className="btn-action btn-demote"
                        onClick={() => handleRoleChange(user.id, 'user')}
                        title="일반 사용자로 변경"
                      >
                        일반으로 강등
                      </button>
                    ) : (
                      <button
                        className="btn-action btn-promote"
                        onClick={() => handleRoleChange(user.id, 'admin')}
                        title="관리자로 승격"
                      >
                        관리자로 승격
                      </button>
                    )}
                    <button
                      className="btn-action btn-delete"
                      onClick={() => handleDeleteUser(user.id, user.email)}
                      title="사용자 삭제"
                    >
                      삭제
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {users.length === 0 && (
          <div className="no-users">등록된 사용자가 없습니다.</div>
        )}
      </div>

      {/* User Detail Modal */}
      {selectedUser && (
        <div className="modal-overlay" onClick={() => setSelectedUser(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>사용자 상세 정보</h2>
              <button className="modal-close" onClick={() => setSelectedUser(null)}>
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div className="detail-section">
                <h3>기본 정보</h3>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span className="detail-label">이름</span>
                    <span className="detail-value">{selectedUser.name || '-'}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">이메일</span>
                    <span className="detail-value">{selectedUser.email}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">전화번호</span>
                    <span className="detail-value">{selectedUser.phone || '-'}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">생년월일</span>
                    <span className="detail-value">
                      {selectedUser.birth_date
                        ? `${new Date(selectedUser.birth_date).toLocaleDateString('ko-KR')} (만 ${calculateAge(selectedUser.birth_date)}세)`
                        : '-'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="detail-section">
                <h3>직업 및 재무 정보</h3>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span className="detail-label">직업</span>
                    <span className="detail-value">{selectedUser.occupation || '-'}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">회사명</span>
                    <span className="detail-value">{selectedUser.company || '-'}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">연봉</span>
                    <span className="detail-value">
                      {selectedUser.annual_income
                        ? `${selectedUser.annual_income.toLocaleString()}만원`
                        : '-'}
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">총 자산</span>
                    <span className="detail-value">
                      {selectedUser.total_assets
                        ? `${selectedUser.total_assets.toLocaleString()}만원`
                        : '-'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="detail-section">
                <h3>주소 정보</h3>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span className="detail-label">거주 도시</span>
                    <span className="detail-value">{selectedUser.city || '-'}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">구/군</span>
                    <span className="detail-value">{selectedUser.district || '-'}</span>
                  </div>
                </div>
              </div>

              <div className="detail-section">
                <h3>투자 성향</h3>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span className="detail-label">투자 경험</span>
                    <span className="detail-value">{selectedUser.investment_experience || '-'}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">투자 목표</span>
                    <span className="detail-value">{selectedUser.investment_goal || '-'}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">위험 감수 성향</span>
                    <span className="detail-value">{selectedUser.risk_tolerance || '-'}</span>
                  </div>
                </div>
              </div>

              <div className="detail-section">
                <h3>시스템 정보</h3>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span className="detail-label">사용자 ID</span>
                    <span className="detail-value">{selectedUser.id}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">역할</span>
                    <span className="detail-value">
                      <span className={`role-badge role-${selectedUser.role}`}>
                        {selectedUser.role === 'admin' ? '관리자' : '일반 사용자'}
                      </span>
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">가입일</span>
                    <span className="detail-value">
                      {selectedUser.created_at
                        ? new Date(selectedUser.created_at).toLocaleString('ko-KR')
                        : '-'}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn-modal btn-close" onClick={() => setSelectedUser(null)}>
                닫기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default UserManagementPage;
