// frontend/src/pages/ValuationPage.jsx

import Valuation from '../components/Valuation';

export default function ValuationPage() {
  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card" style={{ maxWidth: '1400px' }}>
          <Valuation />
        </div>
      </div>
    </div>
  );
}
