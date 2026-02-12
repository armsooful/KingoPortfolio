// frontend/src/pages/ReportPage.jsx

import { useNavigate } from 'react-router-dom';
import InvestmentReport from '../components/InvestmentReport';

export default function ReportPage() {
  const navigate = useNavigate();
  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card" style={{ maxWidth: '1200px' }}>
          <button className="admin-back-btn" onClick={() => navigate('/admin')}>
            ← 관리자 홈
          </button>
          <InvestmentReport />
        </div>
      </div>
    </div>
  );
}
