import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listAdminConsents } from '../services/api';
import '../styles/AdminConsentPage.css';

function AdminConsentPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState({
    q: '',
    consent_type: '',
    start_date: '',
    end_date: '',
  });
  const [consents, setConsents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchConsents = async () => {
    setLoading(true);
    setError('');
    try {
      const params = {
        limit: 100,
        offset: 0,
      };
      if (filters.q) params.q = filters.q;
      if (filters.consent_type) params.consent_type = filters.consent_type;
      if (filters.start_date) params.start_date = filters.start_date;
      if (filters.end_date) params.end_date = filters.end_date;

      const response = await listAdminConsents(params);
      setConsents(response.data.consents || []);
    } catch (err) {
      setError('동의 이력을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConsents();
  }, []);

  const handleChange = (field, value) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    fetchConsents();
  };

  return (
    <div className="admin-consent-page">
      <div className="admin-consent-card">
        <button className="admin-back-btn" onClick={() => navigate('/admin')}>
          ← 관리자 홈
        </button>
        <div className="admin-consent-header">
          <h1>⚙️ 동의 이력 조회</h1>
          <p>투자 성향 진단 유의사항 동의 내역을 조회합니다.</p>
        </div>

        <form className="admin-consent-filters" onSubmit={handleSubmit}>
          <div className="filter-field">
            <label>사용자 검색</label>
            <input
              type="text"
              value={filters.q}
              onChange={(event) => handleChange('q', event.target.value)}
              placeholder="이메일 또는 이름"
            />
          </div>
          <div className="filter-field">
            <label>동의 유형</label>
            <input
              type="text"
              value={filters.consent_type}
              onChange={(event) => handleChange('consent_type', event.target.value)}
              placeholder="예: diagnosis_notice"
            />
          </div>
          <div className="filter-field">
            <label>시작 일시</label>
            <input
              type="datetime-local"
              value={filters.start_date}
              onChange={(event) => handleChange('start_date', event.target.value)}
            />
          </div>
          <div className="filter-field">
            <label>종료 일시</label>
            <input
              type="datetime-local"
              value={filters.end_date}
              onChange={(event) => handleChange('end_date', event.target.value)}
            />
          </div>
          <button type="submit" className="btn btn-primary">
            조회
          </button>
        </form>

        {loading && <div className="info-message">불러오는 중...</div>}
        {error && <div className="error-message">{error}</div>}
        {!loading && !error && consents.length === 0 && (
          <div className="info-message">동의 이력이 없습니다.</div>
        )}
        {!loading && !error && consents.length > 0 && (
          <div className="admin-consent-table">
            <div className="admin-consent-row admin-consent-header-row">
              <span>사용자</span>
              <span>이메일</span>
              <span>유형</span>
              <span>버전</span>
              <span>동의 일시</span>
            </div>
            {consents.map((consent) => (
              <div key={consent.consent_id} className="admin-consent-row">
                <span>{consent.user_name || '-'}</span>
                <span>{consent.user_email || '-'}</span>
                <span>{consent.consent_type}</span>
                <span>{consent.consent_version}</span>
                <span>{new Date(consent.agreed_at).toLocaleString('ko-KR')}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default AdminConsentPage;
