// frontend/src/pages/QuantAnalysisPage.jsx

import { useNavigate } from 'react-router-dom';
import QuantAnalysis from '../components/QuantAnalysis';

export default function QuantAnalysisPage() {
  const navigate = useNavigate();
  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card" style={{ maxWidth: '1400px' }}>
          <button className="admin-back-btn" onClick={() => navigate('/admin')}>
            ← 관리자 홈
          </button>
          <QuantAnalysis />
        </div>
      </div>
    </div>
  );
}
