// frontend/src/pages/FinancialAnalysisPage.jsx

import { useNavigate } from 'react-router-dom';
import FinancialAnalysis from '../components/FinancialAnalysis';

export default function FinancialAnalysisPage() {
  const navigate = useNavigate();
  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card" style={{ maxWidth: '1400px' }}>
          <button className="admin-back-btn" onClick={() => navigate('/admin')}>
            ← 관리자 홈
          </button>
          <FinancialAnalysis />
        </div>
      </div>
    </div>
  );
}
