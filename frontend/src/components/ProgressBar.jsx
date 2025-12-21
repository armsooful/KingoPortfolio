import { useEffect, useState } from 'react';
import * as api from '../services/api';

function ProgressBar({ taskId, onComplete }) {
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!taskId) return;

    // 진행 상황을 1초마다 폴링
    const interval = setInterval(async () => {
      try {
        const response = await api.getProgress(taskId);
        setProgress(response.data);

        // 완료되면 폴링 중지
        if (response.data.status === 'completed' || response.data.status === 'failed') {
          clearInterval(interval);
          if (onComplete) {
            onComplete(response.data);
          }
        }
      } catch (err) {
        if (err.response?.status === 404) {
          // 작업이 없으면 폴링 중지
          clearInterval(interval);
        } else {
          setError('진행 상황을 가져올 수 없습니다');
        }
      }
    }, 1000); // 1초마다 업데이트

    // 컴포넌트 언마운트 시 정리
    return () => clearInterval(interval);
  }, [taskId, onComplete]);

  if (!progress) {
    return <div className="progress-container">진행 상황 로딩 중...</div>;
  }

  const percentage = progress.total > 0
    ? Math.round((progress.current / progress.total) * 100)
    : 0;

  return (
    <div className="progress-container">
      <div className="progress-header">
        <div className="progress-title">
          <strong>{progress.description}</strong>
          {progress.current_item && (
            <span className="current-item"> - {progress.current_item}</span>
          )}
        </div>
        <div className="progress-stats">
          {progress.current} / {progress.total} ({percentage}%)
        </div>
      </div>

      <div className="progress-bar-wrapper">
        <div
          className="progress-bar-fill"
          style={{ width: `${percentage}%` }}
        >
          {percentage > 10 && <span className="progress-percent">{percentage}%</span>}
        </div>
      </div>

      <div className="progress-details">
        <span className="progress-success">✅ 성공: {progress.success_count}</span>
        <span className="progress-failed">❌ 실패: {progress.failed_count}</span>
        {progress.status === 'completed' && (
          <span className="progress-status completed">완료</span>
        )}
        {progress.status === 'running' && (
          <span className="progress-status running">진행 중...</span>
        )}
      </div>

      {error && (
        <div className="progress-error">{error}</div>
      )}

      {progress.error_message && (
        <div className="progress-error-message">
          ⚠️ {progress.error_message}
        </div>
      )}

      <style jsx>{`
        .progress-container {
          margin: 20px 0;
          padding: 15px;
          background: #f8f9fa;
          border-radius: 8px;
          border: 1px solid #e9ecef;
        }

        .progress-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
        }

        .progress-title {
          font-size: 14px;
          color: #495057;
        }

        .current-item {
          font-weight: normal;
          color: #6c757d;
        }

        .progress-stats {
          font-size: 14px;
          font-weight: bold;
          color: #007bff;
        }

        .progress-bar-wrapper {
          width: 100%;
          height: 30px;
          background: #e9ecef;
          border-radius: 15px;
          overflow: hidden;
          margin-bottom: 10px;
        }

        .progress-bar-fill {
          height: 100%;
          background: linear-gradient(90deg, #007bff, #0056b3);
          transition: width 0.3s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: bold;
          font-size: 12px;
        }

        .progress-details {
          display: flex;
          gap: 15px;
          font-size: 13px;
        }

        .progress-success {
          color: #28a745;
        }

        .progress-failed {
          color: #dc3545;
        }

        .progress-status {
          padding: 2px 8px;
          border-radius: 4px;
          font-weight: bold;
          font-size: 12px;
        }

        .progress-status.completed {
          background: #d4edda;
          color: #155724;
        }

        .progress-status.running {
          background: #cce5ff;
          color: #004085;
        }

        .progress-error {
          color: #dc3545;
          font-size: 12px;
          margin-top: 10px;
        }

        .progress-error-message {
          color: #856404;
          background: #fff3cd;
          border: 1px solid #ffeeba;
          padding: 8px;
          border-radius: 4px;
          font-size: 12px;
          margin-top: 10px;
        }
      `}</style>
    </div>
  );
}

export default ProgressBar;
