// frontend/src/pages/QuantAnalysisPage.jsx

import QuantAnalysis from '../components/QuantAnalysis';

export default function QuantAnalysisPage() {
  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card" style={{ maxWidth: '1400px' }}>
          <QuantAnalysis />
        </div>
      </div>
    </div>
  );
}
