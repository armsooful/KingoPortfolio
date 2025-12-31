import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { changePassword } from '../services/api';
import '../styles/ProfilePage.css';

function ProfilePage() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({});

  // 비밀번호 변경 관련 상태
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');

  // 프로필 조회
  const fetchProfile = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/auth/profile');
      setProfile(response.data);
      setFormData(response.data);
    } catch (err) {
      console.error('Failed to fetch profile:', err);
      setError(err.response?.data?.detail || '프로필을 불러오는데 실패했습니다.');

      if (err.response?.status === 401) {
        navigate('/login');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  // 프로필 수정
  const handleUpdate = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage('');

    try {
      const updateData = {
        name: formData.name || null,
        phone: formData.phone || null,
        birth_date: formData.birth_date || null,
        occupation: formData.occupation || null,
        company: formData.company || null,
        annual_income: formData.annual_income ? parseInt(formData.annual_income) : null,
        total_assets: formData.total_assets ? parseInt(formData.total_assets) : null,
        city: formData.city || null,
        district: formData.district || null,
        investment_experience: formData.investment_experience || null,
        investment_goal: formData.investment_goal || null,
        risk_tolerance: formData.risk_tolerance || null,
      };

      const response = await api.put('/auth/profile', updateData);
      setProfile(response.data);
      setFormData(response.data);
      setIsEditing(false);
      setSuccessMessage('프로필이 성공적으로 업데이트되었습니다.');
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      console.error('Failed to update profile:', err);
      setError(err.response?.data?.detail || '프로필 업데이트에 실패했습니다.');
    }
  };

  // 수정 취소
  const handleCancel = () => {
    setFormData(profile);
    setIsEditing(false);
    setError(null);
  };

  // 입력 변경
  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
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

  // 비밀번호 변경 처리
  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');

    // 유효성 검증
    if (!passwordData.current_password || !passwordData.new_password || !passwordData.confirm_password) {
      setPasswordError('모든 필드를 입력해주세요.');
      return;
    }

    if (passwordData.new_password.length < 8) {
      setPasswordError('새 비밀번호는 최소 8자 이상이어야 합니다.');
      return;
    }

    if (passwordData.new_password !== passwordData.confirm_password) {
      setPasswordError('새 비밀번호가 일치하지 않습니다.');
      return;
    }

    try {
      await changePassword({
        current_password: passwordData.current_password,
        new_password: passwordData.new_password
      });

      setPasswordSuccess('비밀번호가 성공적으로 변경되었습니다.');
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
      setIsChangingPassword(false);
      setTimeout(() => setPasswordSuccess(''), 3000);
    } catch (err) {
      console.error('Failed to change password:', err);
      setPasswordError(err.response?.data?.detail || '비밀번호 변경에 실패했습니다.');
    }
  };

  // 비밀번호 변경 취소
  const handlePasswordCancel = () => {
    setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
    setIsChangingPassword(false);
    setPasswordError('');
  };

  if (loading) {
    return (
      <div className="profile-container">
        <div className="loading-spinner">프로필을 불러오는 중...</div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="profile-container">
        <div className="error-message">프로필을 불러올 수 없습니다.</div>
      </div>
    );
  }

  return (
    <div className="profile-container">
      <div className="profile-header">
        <h1>내 프로필</h1>
        <div className="header-actions">
          {!isEditing ? (
            <button className="btn-edit" onClick={() => setIsEditing(true)}>
              프로필 수정
            </button>
          ) : (
            <>
              <button className="btn-cancel" onClick={handleCancel}>
                취소
              </button>
              <button className="btn-save" onClick={handleUpdate}>
                저장
              </button>
            </>
          )}
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {successMessage && <div className="alert alert-success">{successMessage}</div>}

      <form onSubmit={handleUpdate}>
        {/* 기본 정보 */}
        <div className="profile-section">
          <h2>기본 정보</h2>
          <div className="profile-grid">
            <div className="profile-field">
              <label>이메일</label>
              <input
                type="email"
                value={profile.email}
                disabled
                className="disabled-input"
              />
              <small>이메일은 변경할 수 없습니다</small>
            </div>

            <div className="profile-field">
              <label>이름</label>
              <input
                type="text"
                value={formData.name || ''}
                onChange={(e) => handleChange('name', e.target.value)}
                disabled={!isEditing}
                placeholder="이름을 입력하세요"
              />
            </div>

            <div className="profile-field">
              <label>전화번호</label>
              <input
                type="tel"
                value={formData.phone || ''}
                onChange={(e) => handleChange('phone', e.target.value)}
                disabled={!isEditing}
                placeholder="010-1234-5678"
              />
            </div>

            <div className="profile-field">
              <label>생년월일</label>
              <input
                type="date"
                value={formData.birth_date || ''}
                onChange={(e) => handleChange('birth_date', e.target.value)}
                disabled={!isEditing}
              />
              {formData.birth_date && (
                <small>만 {calculateAge(formData.birth_date)}세</small>
              )}
            </div>
          </div>
        </div>

        {/* 직업 및 재무 정보 */}
        <div className="profile-section">
          <h2>직업 및 재무 정보</h2>
          <div className="profile-grid">
            <div className="profile-field">
              <label>직업</label>
              <input
                type="text"
                value={formData.occupation || ''}
                onChange={(e) => handleChange('occupation', e.target.value)}
                disabled={!isEditing}
                placeholder="예: 소프트웨어 엔지니어"
              />
            </div>

            <div className="profile-field">
              <label>회사명</label>
              <input
                type="text"
                value={formData.company || ''}
                onChange={(e) => handleChange('company', e.target.value)}
                disabled={!isEditing}
                placeholder="예: 테크컴퍼니"
              />
            </div>

            <div className="profile-field">
              <label>연봉 (만원)</label>
              <input
                type="number"
                value={formData.annual_income || ''}
                onChange={(e) => handleChange('annual_income', e.target.value)}
                disabled={!isEditing}
                placeholder="예: 5000"
                min="0"
              />
            </div>

            <div className="profile-field">
              <label>총 자산 (만원)</label>
              <input
                type="number"
                value={formData.total_assets || ''}
                onChange={(e) => handleChange('total_assets', e.target.value)}
                disabled={!isEditing}
                placeholder="예: 10000"
                min="0"
              />
            </div>
          </div>
        </div>

        {/* 주소 정보 */}
        <div className="profile-section">
          <h2>주소 정보</h2>
          <div className="profile-grid">
            <div className="profile-field">
              <label>거주 도시</label>
              <input
                type="text"
                value={formData.city || ''}
                onChange={(e) => handleChange('city', e.target.value)}
                disabled={!isEditing}
                placeholder="예: 서울"
              />
            </div>

            <div className="profile-field">
              <label>구/군</label>
              <input
                type="text"
                value={formData.district || ''}
                onChange={(e) => handleChange('district', e.target.value)}
                disabled={!isEditing}
                placeholder="예: 강남구"
              />
            </div>
          </div>
        </div>

        {/* 투자 성향 */}
        <div className="profile-section">
          <h2>투자 성향</h2>
          <div className="profile-grid">
            <div className="profile-field">
              <label>투자 경험</label>
              <select
                value={formData.investment_experience || '초보'}
                onChange={(e) => handleChange('investment_experience', e.target.value)}
                disabled={!isEditing}
              >
                <option value="초보">초보 - 투자 경험이 거의 없음</option>
                <option value="중급">중급 - 1~3년 정도 투자 경험</option>
                <option value="고급">고급 - 3년 이상 투자 경험</option>
                <option value="전문가">전문가 - 전문적인 투자 지식 보유</option>
              </select>
            </div>

            <div className="profile-field">
              <label>위험 감수 성향</label>
              <select
                value={formData.risk_tolerance || '중립적'}
                onChange={(e) => handleChange('risk_tolerance', e.target.value)}
                disabled={!isEditing}
              >
                <option value="보수적">보수적 - 안정적인 수익을 선호</option>
                <option value="중립적">중립적 - 균형잡힌 투자 선호</option>
                <option value="공격적">공격적 - 높은 수익을 위해 위험 감수 가능</option>
              </select>
            </div>

            <div className="profile-field full-width">
              <label>투자 목표</label>
              <input
                type="text"
                value={formData.investment_goal || ''}
                onChange={(e) => handleChange('investment_goal', e.target.value)}
                disabled={!isEditing}
                placeholder="예: 노후 준비, 주택 구입, 자녀 교육비 등"
              />
            </div>
          </div>
        </div>

        {/* 시스템 정보 */}
        <div className="profile-section">
          <h2>시스템 정보</h2>
          <div className="profile-grid">
            <div className="profile-field">
              <label>사용자 ID</label>
              <input
                type="text"
                value={profile.id}
                disabled
                className="disabled-input"
              />
            </div>

            <div className="profile-field">
              <label>역할</label>
              <input
                type="text"
                value={profile.role === 'admin' ? '관리자' : '일반 사용자'}
                disabled
                className="disabled-input"
              />
            </div>

            <div className="profile-field">
              <label>가입일</label>
              <input
                type="text"
                value={new Date(profile.created_at).toLocaleString('ko-KR')}
                disabled
                className="disabled-input"
              />
            </div>
          </div>
        </div>
      </form>

      {/* 비밀번호 변경 */}
      <div className="profile-section">
        <h2>비밀번호 변경</h2>

        {passwordSuccess && (
          <div className="success-message">{passwordSuccess}</div>
        )}

        {!isChangingPassword ? (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setIsChangingPassword(true)}
          >
            비밀번호 변경
          </button>
        ) : (
          <form onSubmit={handlePasswordChange} className="password-form">
            {passwordError && (
              <div className="error-message">{passwordError}</div>
            )}

            <div className="profile-field">
              <label>현재 비밀번호 *</label>
              <input
                type="password"
                value={passwordData.current_password}
                onChange={(e) => setPasswordData(prev => ({ ...prev, current_password: e.target.value }))}
                placeholder="현재 비밀번호를 입력하세요"
                required
              />
            </div>

            <div className="profile-field">
              <label>새 비밀번호 *</label>
              <input
                type="password"
                value={passwordData.new_password}
                onChange={(e) => setPasswordData(prev => ({ ...prev, new_password: e.target.value }))}
                placeholder="새 비밀번호 (최소 8자)"
                required
                minLength={8}
              />
            </div>

            <div className="profile-field">
              <label>새 비밀번호 확인 *</label>
              <input
                type="password"
                value={passwordData.confirm_password}
                onChange={(e) => setPasswordData(prev => ({ ...prev, confirm_password: e.target.value }))}
                placeholder="새 비밀번호를 다시 입력하세요"
                required
                minLength={8}
              />
            </div>

            <div className="form-actions">
              <button type="submit" className="btn btn-primary">
                비밀번호 변경
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handlePasswordCancel}
              >
                취소
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default ProfilePage;
