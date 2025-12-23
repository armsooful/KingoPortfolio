// frontend/src/pages/FinancialAnalysisPage.jsx

import FinancialAnalysis from '../components/FinancialAnalysis';

export default function FinancialAnalysisPage() {
  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card" style={{ maxWidth: '1400px' }}>
          <FinancialAnalysis />
        </div>
      </div>
    </div>
  );
}
