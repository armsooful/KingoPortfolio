// frontend/src/components/DataTable.jsx

import { useState, useEffect } from 'react';
import '../styles/DataTable.css';

export default function DataTable({ type, fetchData }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchDataItems = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchData();
      setData(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || '데이터 조회 실패');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!data) {
      fetchDataItems();
    }
  }, []);

  const getTypeInfo = () => {
    switch (type) {
      case 'stocks':
        return {
          title: '주식 데이터',
          icon: '📈',
          color: '#2196F3',
          columns: ['티커', '이름', '현재가', '시가총액', '섹터', '업데이트'],
        };
      case 'etfs':
        return {
          title: 'ETF 데이터',
          icon: '📊',
          color: '#9C27B0',
          columns: ['티커', '이름', '현재가', 'AUM', '운용수수료', '업데이트'],
        };
      case 'bonds':
        return {
          title: '채권 데이터',
          icon: '💰',
          color: '#4CAF50',
          columns: ['이름', '발행자', '현재가', '만기연수', '신용등급', '업데이트'],
        };
      case 'deposits':
        return {
          title: '예적금 상품',
          icon: '🏦',
          color: '#FF9800',
          columns: ['상품명', '은행', '금리', '기간(개월)', '상품유형', '업데이트'],
        };
      default:
        return {
          title: '데이터',
          icon: '📋',
          color: '#666',
          columns: [],
        };
    }
  };

  const formatNumber = (num) => {
    if (!num) return '-';
    return new Intl.NumberFormat('ko-KR').format(num);
  };

  const formatCurrency = (num) => {
    if (!num) return '-';
    return `₩${formatNumber(num)}`;
  };

  const formatMarketCap = (num) => {
    if (!num) return '-';

    const trillion = 1000000000000; // 1조
    const hundredMillion = 100000000; // 1억

    if (num >= trillion) {
      return `${(num / trillion).toFixed(2)}조`;
    } else if (num >= hundredMillion) {
      return `${(num / hundredMillion).toFixed(2)}억`;
    } else {
      return formatNumber(num);
    }
  };

  const formatPercent = (num) => {
    if (!num) return '-';
    return `${num}%`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderRow = (item) => {
    switch (type) {
      case 'stocks':
        return (
          <tr key={item.ticker}>
            <td>{item.ticker}</td>
            <td>{item.name}</td>
            <td className="right">{formatCurrency(item.current_price)}</td>
            <td className="right">{formatMarketCap(item.market_cap)}</td>
            <td>{item.sector || '-'}</td>
            <td className="date">{formatDate(item.updated_at)}</td>
          </tr>
        );
      case 'etfs':
        return (
          <tr key={item.ticker}>
            <td>{item.ticker}</td>
            <td>{item.name}</td>
            <td className="right">{formatCurrency(item.current_price)}</td>
            <td className="right">{formatNumber(item.net_asset_value)}</td>
            <td className="right">{formatPercent(item.expense_ratio)}</td>
            <td className="date">{formatDate(item.updated_at)}</td>
          </tr>
        );
      case 'bonds':
        return (
          <tr key={item.id}>
            <td>{item.name}</td>
            <td>{item.issuer}</td>
            <td className="right">{formatPercent(item.interest_rate)}</td>
            <td className="right">{item.maturity_years}년</td>
            <td>{item.credit_rating || '-'}</td>
            <td className="date">{formatDate(item.updated_at)}</td>
          </tr>
        );
      case 'deposits':
        return (
          <tr key={item.id}>
            <td>{item.name}</td>
            <td>{item.bank}</td>
            <td className="right">{formatPercent(item.interest_rate)}</td>
            <td className="right">{item.term_months}개월</td>
            <td>{item.product_type}</td>
            <td className="date">{formatDate(item.updated_at)}</td>
          </tr>
        );
      default:
        return null;
    }
  };

  const typeInfo = getTypeInfo();

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>데이터 로딩 중...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="ai-card risk-warning">
        <h3>오류</h3>
        <p className="ai-content">{error}</p>
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="ai-card" style={{ textAlign: 'center', padding: '40px' }}>
        <div style={{ fontSize: '3rem', marginBottom: '15px' }}>📭</div>
        <h3>데이터가 없습니다</h3>
        <p className="ai-content">데이터 수집 버튼을 클릭하여 데이터를 수집하세요.</p>
      </div>
    );
  }

  return (
    <div className="dt-wrapper">
      <div className="dt-table-container">
        <table className="dt-table">
          <thead>
            <tr style={{ background: typeInfo.color }}>
              {typeInfo.columns.map((col, idx) => (
                <th key={idx}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.items.map(item => renderRow(item))}
          </tbody>
        </table>
      </div>

      <div className="dt-footer">
        <div>
          <span className="dt-footer-text">총 </span>
          <span className="dt-footer-count" style={{ color: typeInfo.color }}>{data.total}</span>
          <span className="dt-footer-text"> 개</span>
          <span className="dt-footer-separator">|</span>
          <span className="dt-footer-text">현재 {data.items.length}개 표시</span>
        </div>
        {data.total > data.items.length && (
          <button
            onClick={fetchDataItems}
            className="btn btn-secondary"
          >
            새로고침
          </button>
        )}
      </div>
    </div>
  );
}
