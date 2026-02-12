// frontend/src/pages/ValuationPage.jsx

import { useNavigate } from 'react-router-dom';
import Valuation from '../components/Valuation';

export default function ValuationPage() {
  const navigate = useNavigate();
  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card" style={{ maxWidth: '1400px' }}>
          <button className="admin-back-btn" onClick={() => navigate('/admin')}>
            ← 관리자 홈
          </button>
          <Valuation />
        </div>
      </div>
    </div>
  );
}
