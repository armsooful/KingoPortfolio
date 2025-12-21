// frontend/src/components/DataTable.jsx

import { useState, useEffect } from 'react';

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
      // 1조 이상: 조 단위로 표시
      return `${(num / trillion).toFixed(2)}조`;
    } else if (num >= hundredMillion) {
      // 1억 이상: 억 단위로 표시
      return `${(num / hundredMillion).toFixed(2)}억`;
    } else {
      // 1억 미만: 그대로 표시
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
    const rowStyle = {
      borderBottom: '1px solid #e0e0e0',
    };
    const cellStyle = {
      padding: '12px 15px',
    };

    switch (type) {
      case 'stocks':
        return (
          <tr key={item.id} style={rowStyle}>
            <td style={cellStyle}>{item.ticker}</td>
            <td style={cellStyle}>{item.name}</td>
            <td style={{ ...cellStyle, textAlign: 'right' }}>{formatCurrency(item.current_price)}</td>
            <td style={{ ...cellStyle, textAlign: 'right' }}>{formatMarketCap(item.market_cap)}</td>
            <td style={cellStyle}>{item.sector || '-'}</td>
            <td style={{ ...cellStyle, fontSize: '0.85rem', color: '#666' }}>{formatDate(item.updated_at)}</td>
          </tr>
        );
      case 'etfs':
        return (
          <tr key={item.id} style={rowStyle}>
            <td style={cellStyle}>{item.ticker}</td>
            <td style={cellStyle}>{item.name}</td>
            <td style={{ ...cellStyle, textAlign: 'right' }}>{formatCurrency(item.current_price)}</td>
            <td style={{ ...cellStyle, textAlign: 'right' }}>{formatNumber(item.net_asset_value)}</td>
            <td style={{ ...cellStyle, textAlign: 'right' }}>{formatPercent(item.expense_ratio)}</td>
            <td style={{ ...cellStyle, fontSize: '0.85rem', color: '#666' }}>{formatDate(item.updated_at)}</td>
          </tr>
        );
      case 'bonds':
        return (
          <tr key={item.id} style={rowStyle}>
            <td style={cellStyle}>{item.name}</td>
            <td style={cellStyle}>{item.issuer}</td>
            <td style={{ ...cellStyle, textAlign: 'right' }}>{formatPercent(item.interest_rate)}</td>
            <td style={{ ...cellStyle, textAlign: 'right' }}>{item.maturity_years}년</td>
            <td style={cellStyle}>{item.credit_rating || '-'}</td>
            <td style={{ ...cellStyle, fontSize: '0.85rem', color: '#666' }}>{formatDate(item.updated_at)}</td>
          </tr>
        );
      case 'deposits':
        return (
          <tr key={item.id} style={rowStyle}>
            <td style={cellStyle}>{item.name}</td>
            <td style={cellStyle}>{item.bank}</td>
            <td style={{ ...cellStyle, textAlign: 'right' }}>{formatPercent(item.interest_rate)}</td>
            <td style={{ ...cellStyle, textAlign: 'right' }}>{item.term_months}개월</td>
            <td style={cellStyle}>{item.product_type}</td>
            <td style={{ ...cellStyle, fontSize: '0.85rem', color: '#666' }}>{formatDate(item.updated_at)}</td>
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
        <h3>❌ 오류</h3>
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
    <div style={{ marginTop: '20px' }}>
      <div style={{ overflowX: 'auto', border: '1px solid #e0e0e0', borderRadius: '8px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', background: 'white' }}>
          <thead>
            <tr style={{ background: typeInfo.color, color: 'white' }}>
              {typeInfo.columns.map((col, idx) => (
                <th key={idx} style={{ padding: '15px', textAlign: 'left', fontWeight: 'bold', fontSize: '0.9rem' }}>
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.items.map(item => renderRow(item))}
          </tbody>
        </table>
      </div>

      <div style={{
        marginTop: '15px',
        padding: '15px',
        background: '#f5f5f5',
        borderRadius: '8px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '10px'
      }}>
        <div>
          <span style={{ fontSize: '0.9rem', color: '#666' }}>총 </span>
          <span style={{ fontSize: '1.5rem', fontWeight: 'bold', color: typeInfo.color }}>{data.total}</span>
          <span style={{ fontSize: '0.9rem', color: '#666' }}> 개</span>
          <span style={{ margin: '0 10px', color: '#ccc' }}>|</span>
          <span style={{ fontSize: '0.9rem', color: '#666' }}>현재 {data.items.length}개 표시</span>
        </div>
        {data.total > data.items.length && (
          <button
            onClick={fetchDataItems}
            className="btn btn-secondary"
            style={{ padding: '8px 16px' }}
          >
            새로고침
          </button>
        )}
      </div>
    </div>
  );
}
