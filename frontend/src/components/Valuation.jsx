import React, { useState } from 'react';
import {
  getValuationMultiples,
  getDCFValuation,
  getDDMValuation,
  getComprehensiveValuation,
} from '../services/api';
import '../styles/Valuation.css';

const Valuation = () => {
  const [symbol, setSymbol] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('comprehensive');
  const [multiples, setMultiples] = useState(null);
  const [dcf, setDcf] = useState(null);
  const [ddm, setDdm] = useState(null);
  const [comprehensive, setComprehensive] = useState(null);

  const handleAnalyze = async () => {
    if (!symbol.trim()) {
      setError('종목 심볼을 입력하세요.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const upperSymbol = symbol.toUpperCase();

      if (activeTab === 'comprehensive') {
        const res = await getComprehensiveValuation(upperSymbol);
        setComprehensive(res.data);
      } else if (activeTab === 'multiples') {
        const res = await getValuationMultiples(upperSymbol);
        setMultiples(res.data);
      } else if (activeTab === 'dcf') {
        const res = await getDCFValuation(upperSymbol);
        setDcf(res.data);
      } else if (activeTab === 'ddm') {
        const res = await getDDMValuation(upperSymbol);
        setDdm(res.data);
      }
    } catch (err) {
      console.error('밸류에이션 분석 실패:', err);
      setError(
        err.response?.data?.detail || '밸류에이션 분석에 실패했습니다.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleAnalyze();
    }
  };

  const getValuationColor = (status) => {
    if (status === '저평가' || status === '매수 검토') return '#4caf50';
    if (status === '고평가' || status === '매도 검토') return '#f44336';
    return '#ff9800';
  };

  const renderComprehensive = () => {
    if (!comprehensive) return null;

    const { summary, multiple_comparison, dcf_valuation, ddm_valuation } = comprehensive;

    return (
      <div className="valuation-results">
        <div className="company-info">
          <h3>{comprehensive.symbol}</h3>
          <p className="timestamp">{new Date(comprehensive.timestamp).toLocaleString('ko-KR')}</p>
        </div>

        {summary && (
          <div className="summary-section">
            <h4>📊 종합 평가</h4>
            <div className="recommendation-card">
              <div className="recommendation-badge" style={{ backgroundColor: getValuationColor(summary.recommendation) }}>
                {summary.recommendation}
              </div>
              <div className="valuations-list">
                {summary.valuations.map((val, idx) => (
                  <div key={idx} className="valuation-item">
                    <span className="method">{val.method}</span>
                    <span className="result" style={{ color: getValuationColor(val.result) }}>
                      {val.result}
                      {val.upside && ` (${val.upside > 0 ? '+' : ''}${val.upside.toFixed(2)}%)`}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {multiple_comparison && !multiple_comparison.error && (
          <div className="section-card">
            <h4>📈 멀티플 비교</h4>
            <p className="sector-info">{multiple_comparison.sector} / {multiple_comparison.industry}</p>
            <div className="multiples-grid">
              {multiple_comparison.pe_comparison && (
                <div className="multiple-card">
                  <h5>PER</h5>
                  <div className="value-row">
                    <span>현재</span>
                    <strong>{multiple_comparison.pe_comparison.current}</strong>
                  </div>
                  <div className="value-row">
                    <span>업종 평균</span>
                    <span>{multiple_comparison.pe_comparison.industry_avg}</span>
                  </div>
                  <div className="status-badge" style={{ backgroundColor: getValuationColor(multiple_comparison.pe_comparison.status) }}>
                    {multiple_comparison.pe_comparison.status}
                  </div>
                </div>
              )}
              {multiple_comparison.pb_comparison && (
                <div className="multiple-card">
                  <h5>PBR</h5>
                  <div className="value-row">
                    <span>현재</span>
                    <strong>{multiple_comparison.pb_comparison.current}</strong>
                  </div>
                  <div className="value-row">
                    <span>업종 평균</span>
                    <span>{multiple_comparison.pb_comparison.industry_avg}</span>
                  </div>
                  <div className="status-badge" style={{ backgroundColor: getValuationColor(multiple_comparison.pb_comparison.status) }}>
                    {multiple_comparison.pb_comparison.status}
                  </div>
                </div>
              )}
              {multiple_comparison.dividend_yield_comparison && (
                <div className="multiple-card">
                  <h5>배당수익률</h5>
                  <div className="value-row">
                    <span>현재</span>
                    <strong>{multiple_comparison.dividend_yield_comparison.current}%</strong>
                  </div>
                  <div className="value-row">
                    <span>업종 평균</span>
                    <span>{multiple_comparison.dividend_yield_comparison.industry_avg}%</span>
                  </div>
                  <div className="status-badge" style={{ backgroundColor: getValuationColor(multiple_comparison.dividend_yield_comparison.status) }}>
                    {multiple_comparison.dividend_yield_comparison.status}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {dcf_valuation && !dcf_valuation.error && (
          <div className="section-card">
            <h4>💵 DCF 밸류에이션</h4>
            <div className="scenarios-grid">
              {Object.entries(dcf_valuation.scenarios).map(([name, data]) => (
                <div key={name} className="scenario-card">
                  <h5>{name}</h5>
                  <p className="description">{data.assumptions.description}</p>
                  {data.fair_value_per_share && (
                    <>
                      <div className="price-row">
                        <span>적정가</span>
                        <strong>${data.fair_value_per_share}</strong>
                      </div>
                      <div className="price-row">
                        <span>현재가</span>
                        <span>${data.current_price}</span>
                      </div>
                      <div className="upside-badge" style={{
                        backgroundColor: data.upside_downside > 0 ? '#4caf50' : '#f44336'
                      }}>
                        {data.upside_downside > 0 ? '+' : ''}{data.upside_downside}%
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {ddm_valuation && !ddm_valuation.error && (
          <div className="section-card">
            <h4>💰 배당할인모형 (DDM)</h4>
            <p className="note">{ddm_valuation.note}</p>
            <div className="scenarios-grid">
              {Object.entries(ddm_valuation.scenarios).map(([name, data]) => (
                <div key={name} className="scenario-card">
                  <h5>{name}</h5>
                  {data.error ? (
                    <p className="error-text">{data.error}</p>
                  ) : (
                    <>
                      <p className="description">{data.assumptions.description}</p>
                      <div className="price-row">
                        <span>적정가</span>
                        <strong>${data.fair_value}</strong>
                      </div>
                      <div className="price-row">
                        <span>현재가</span>
                        <span>${data.current_price}</span>
                      </div>
                      <div className="upside-badge" style={{
                        backgroundColor: data.upside_downside > 0 ? '#4caf50' : '#f44336'
                      }}>
                        {data.upside_downside > 0 ? '+' : ''}{data.upside_downside}%
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="valuation">
      <div className="valuation-header">
        <h2>💼 밸류에이션 분석</h2>
        <div className="search-box">
          <input
            type="text"
            placeholder="종목 심볼 입력 (예: AAPL, GOOGL)"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
          />
          <button onClick={handleAnalyze} disabled={loading}>
            {loading ? '분석 중...' : '분석'}
          </button>
        </div>
      </div>

      <div className="tab-buttons">
        <button
          className={activeTab === 'comprehensive' ? 'active' : ''}
          onClick={() => setActiveTab('comprehensive')}
        >
          종합 분석
        </button>
        <button
          className={activeTab === 'multiples' ? 'active' : ''}
          onClick={() => setActiveTab('multiples')}
        >
          멀티플 비교
        </button>
        <button
          className={activeTab === 'dcf' ? 'active' : ''}
          onClick={() => setActiveTab('dcf')}
        >
          DCF
        </button>
        <button
          className={activeTab === 'ddm' ? 'active' : ''}
          onClick={() => setActiveTab('ddm')}
        >
          DDM
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {activeTab === 'comprehensive' && comprehensive && renderComprehensive()}
    </div>
  );
};

export default Valuation;
