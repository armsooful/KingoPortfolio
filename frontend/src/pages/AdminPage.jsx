// frontend/src/pages/AdminPage.jsx

import { useState } from 'react';
import api from '../services/api';

export default function AdminPage() {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [message, setMessage] = useState('');

  const handleLoadData = async (type) => {
    setLoading(true);
    try {
      const endpoint = type === 'all' ? '/admin/load-data' 
                      : type === 'stocks' ? '/admin/load-stocks'
                      : '/admin/load-etfs';
      
      const response = await api.post(endpoint);
      setStatus('success');
      setMessage(`${type} 데이터 적재 완료!`);
      console.log(response.data);
    } catch (error) {
      setStatus('error');
      setMessage(`적재 실패: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCheckStatus = async () => {
    try {
      const response = await api.get('/admin/data-status');
      setStatus('success');
      setMessage(`DB 통계: 주식 ${response.data.stocks}개, ETF ${response.data.etfs}개`);
    } catch (error) {
      setStatus('error');
      setMessage(`조회 실패: ${error.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-900 mb-8">관리자 콘솔</h1>

        <div className="bg-white rounded-lg shadow-md p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">종목 데이터 관리</h2>

          <div className="space-y-4">
            <button
              onClick={() => handleLoadData('all')}
              disabled={loading}
              className="w-full bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600 disabled:opacity-50"
            >
              {loading ? '적재 중...' : '모든 데이터 적재'}
            </button>

            <button
              onClick={() => handleLoadData('stocks')}
              disabled={loading}
              className="w-full bg-green-500 text-white px-6 py-3 rounded-lg hover:bg-green-600 disabled:opacity-50"
            >
              주식 데이터만 적재
            </button>

            <button
              onClick={() => handleLoadData('etfs')}
              disabled={loading}
              className="w-full bg-purple-500 text-white px-6 py-3 rounded-lg hover:bg-purple-600 disabled:opacity-50"
            >
              ETF 데이터만 적재
            </button>

            <button
              onClick={handleCheckStatus}
              className="w-full bg-gray-500 text-white px-6 py-3 rounded-lg hover:bg-gray-600"
            >
              DB 상태 확인
            </button>
          </div>

          {message && (
            <div className={`mt-6 p-4 rounded-lg ${
              status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}>
              {message}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}