// frontend/src/pages/ReportPage.jsx

import InvestmentReport from '../components/InvestmentReport';

export default function ReportPage() {
  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card" style={{ maxWidth: '1200px' }}>
          <InvestmentReport />
        </div>
      </div>
    </div>
  );
}
