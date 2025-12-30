import { useEffect, useState } from 'react';
import * as api from '../services/api';
import '../styles/ProgressModal.css';

function ProgressModal({ taskId, onComplete, onClose }) {
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState(null);
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    if (!taskId) return;

    // 임시 task_id인지 확인
    const isTempTask = taskId.startsWith('temp_');

    // 진행 상황을 300ms마다 폴링 (더 빠른 업데이트)
    const interval = setInterval(async () => {
      // 임시 task_id면 실제 데이터를 기다림
      if (isTempTask) {
        return;
      }

      try {
        const response = await api.getProgress(taskId);
        const data = response.data;
        setProgress(data);

        // items_history를 사용하여 로그 업데이트
        if (data.items_history && data.items_history.length > logs.length) {
          // 새로운 항목이 있으면 로그에 추가
          const newItems = data.items_history.slice(logs.length);
          const newLogs = newItems.map(item => {
            const timestamp = new Date(item.timestamp).toLocaleTimeString();
            const status = item.success ? '✅' : '❌';
            return {
              id: `${item.index}-${item.timestamp}`,
              text: `[${timestamp}] ${status} ${item.item}`,
              timestamp: item.timestamp
            };
          });

          setLogs(prev => [...prev, ...newLogs].slice(-50));
        }

        // 완료되면 폴링 중지
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval);
          if (onComplete) {
            onComplete(data);
          }
        }
      } catch (err) {
        if (err.response?.status === 404) {
          // 작업이 없으면 계속 대기 (임시에서 실제 task_id로 전환 중일 수 있음)
        } else {
          setError('진행 상황을 가져올 수 없습니다');
        }
      }
    }, 300); // 300ms마다 업데이트 (더 빠른 반응)

    // 컴포넌트 언마운트 시 정리
    return () => clearInterval(interval);
  }, [taskId, onComplete, logs.length]);

  if (!progress) {
    return (
      <div className="modal-overlay">
        <div className="progress-modal">
          <div className="modal-header">
            <h3>진행 상황</h3>
            <button className="close-button" onClick={onClose}>×</button>
          </div>
          <div className="modal-body">
            <p>진행 상황 로딩 중...</p>
          </div>
        </div>
      </div>
    );
  }

  const percentage = progress.total > 0
    ? Math.round((progress.current / progress.total) * 100)
    : 0;

  const isComplete = progress.status === 'completed' || progress.status === 'failed';

  return (
    <div className="modal-overlay">
      <div className="progress-modal">
        <div className="modal-header">
          <h3>📊 {progress.description}</h3>
          {isComplete && (
            <button className="close-button" onClick={onClose}>×</button>
          )}
        </div>

        <div className="modal-body">
          {/* Progress Bar */}
          <div className="progress-section">
            <div className="progress-stats">
              <span className="stats-text">
                {progress.current} / {progress.total} 완료
              </span>
              <span className="stats-percent">{percentage}%</span>
            </div>
            <div className="progress-bar-wrapper">
              <div
                className="progress-bar-fill"
                style={{ width: `${percentage}%` }}
              />
            </div>
            <div className="progress-details">
              <span className="detail-item success">
                ✅ 성공: {progress.success_count}
              </span>
              <span className="detail-item failed">
                ❌ 실패: {progress.failed_count}
              </span>
              <span className={`detail-item status ${progress.status}`}>
                {progress.status === 'completed' ? '✔️ 완료' :
                 progress.status === 'failed' ? '⚠️ 실패' :
                 '⏳ 진행 중'}
              </span>
            </div>
          </div>

          {/* Logs Section */}
          <div className="logs-section">
            <div className="logs-header">
              <h4>📋 실시간 로그</h4>
              <span className="log-count">{logs.length}개 항목</span>
            </div>
            <div className="logs-container">
              {logs.length === 0 ? (
                <p className="no-logs">로그를 기다리는 중...</p>
              ) : (
                logs.map((log, index) => (
                  <div key={log.id || index} className="log-item">
                    {typeof log === 'string' ? log : (log.text || JSON.stringify(log))}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Error Messages */}
          {error && (
            <div className="error-banner">
              ⚠️ {error}
            </div>
          )}

          {progress.error_message && (
            <div className="error-banner">
              ⚠️ {progress.error_message}
            </div>
          )}

          {/* Close Button for Completed */}
          {isComplete && (
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={onClose}>
                닫기
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ProgressModal;
