import { useEffect, useRef, useState } from 'react';
import * as api from '../services/api';
import '../styles/ProgressModal.css';

function ProgressModal({ taskId, onComplete, onClose }) {
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState(null);
  const [logs, setLogs] = useState([]);
  const lastHistoryLenRef = useRef(0);

  const formatLogTimestamp = (timestamp) => {
    if (!timestamp) return '';
    const hasTimezone = /[zZ]|[+-]\d{2}:?\d{2}$/.test(timestamp);
    const isoTimestamp = hasTimezone ? timestamp : `${timestamp}Z`;
    const date = new Date(isoTimestamp);
    if (Number.isNaN(date.getTime())) return timestamp;
    return date.toLocaleTimeString('ko-KR', { timeZone: 'Asia/Seoul', hour12: false });
  };

  useEffect(() => {
    if (!taskId) return;

    setProgress(null);
    setError(null);
    setLogs([]);
    lastHistoryLenRef.current = 0;

    // 임시 task_id인지 확인
    const isTempTask = taskId.startsWith('temp_');
    let notFoundCount = 0; // 404 에러 카운트

    // 진행 상황을 1초마다 폴링
    const interval = setInterval(async () => {
      // 임시 task_id면 실제 데이터를 기다림
      if (isTempTask) {
        return;
      }

      try {
        const response = await api.getProgress(taskId);
        const data = response.data;
        notFoundCount = 0; // 성공하면 카운트 초기화

        // 디버깅 로깅
        console.log('[ProgressModal] API Response:', {
          taskId,
          status: data.status,
          current: data.current,
          total: data.total,
          success_count: data.success_count,
          phase: data.phase,
          current_item: data.current_item
        });

        setProgress(data);

        // items_history를 사용하여 로그 업데이트
        if (data.items_history && data.items_history.length > lastHistoryLenRef.current) {
          const newItems = data.items_history.slice(lastHistoryLenRef.current);
          lastHistoryLenRef.current = data.items_history.length;
          const newLogs = newItems.map((item) => {
            const timestamp = formatLogTimestamp(item.timestamp);
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
          console.log('[ProgressModal] Task completed with status:', data.status);
          clearInterval(interval);
          if (onComplete) {
            onComplete(data);
          }
          // 자동 종료 제거 - 사용자가 버튼 클릭할 때까지 대기
        }
      } catch (err) {
        if (err.response?.status === 404) {
          // 404가 3회 연속 발생하면 폴링 중지 (작업이 완료되고 정리됨)
          notFoundCount++;
          if (notFoundCount >= 3) {
            clearInterval(interval);
            // 진행 상황 모달 자동 종료
            if (onClose) {
              onClose();
            }
          }
        } else {
          setError('진행 상황을 가져올 수 없습니다');
        }
      }
    }, 1000);

    // 컴포넌트 언마운트 시 정리
    return () => {
      clearInterval(interval);
    };
  }, [taskId, onComplete, onClose]);

  // 자동 종료 제거 - 사용자 버튼 클릭 대기

  if (!progress) {
    return (
      <div className="modal-overlay">
        <div className="progress-modal">
          <div className="modal-header">
            <h3>📊 데이터 적재</h3>
            <button className="close-button" onClick={onClose}>×</button>
          </div>
          <div className="modal-body">
            <div className="progress-section">
              <div className="loading-spinner">
                <div className="spinner-animation"></div>
              </div>
              <h3 style={{ marginTop: '20px', textAlign: 'center' }}>⏳ Phase 1: 데이터 수집 중</h3>
              <p style={{ marginTop: '10px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                FSC API를 통해 주식 정보를 병렬로 수집 중입니다...
              </p>
              <p style={{ marginTop: '5px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                (약 2-3분 소요)
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const percentage = progress.total > 0
    ? Math.round((progress.current / progress.total) * 100)
    : 0;

  const isComplete = progress.status === 'completed' || progress.status === 'failed';

  // 채권/예금/적금/연금저축/주담대/전세대출 적재의 경우 Phase 1 없음 - Phase 배지 숨김
  const isBondTask = taskId && (taskId.startsWith('bonds_') || taskId.startsWith('deposits_') || taskId.startsWith('savings_') || taskId.startsWith('annuity_') || taskId.startsWith('mortgage_') || taskId.startsWith('rentloan_') || taskId.startsWith('creditloan_'));

  // Phase 판별: backend의 phase 필드 사용, 없으면 current_item 기반으로 판단
  const currentPhase = progress.phase ||
    (progress.current_item && progress.current_item.includes('[Phase 1]') ? 'Phase 1' : 'Phase 2');
  const isPhase1 = !isBondTask && progress.status === 'running' && currentPhase === 'Phase 1';

  // Phase 1 상태 표시
  if (isPhase1) {
    return (
      <div className="modal-overlay">
        <div className="progress-modal">
          <div className="modal-header">
            <h3>📊 {progress.description}</h3>
            <button className="close-button" onClick={onClose}>×</button>
          </div>

          <div className="modal-body">
            <div className="progress-section">
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
                <span style={{ backgroundColor: '#4CAF50', color: 'white', padding: '5px 15px', borderRadius: '20px', fontSize: '0.9rem', fontWeight: 'bold' }}>
                  Phase 1
                </span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>데이터 수집</span>
              </div>
              <div className="loading-spinner">
                <div className="spinner-animation"></div>
              </div>
              <h3 style={{ marginTop: '20px', textAlign: 'center' }}>⏳ 진행 중...</h3>
              <p style={{ marginTop: '15px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
                {progress.current_item || 'FSC API를 통해 주식 정보를 병렬로 수집 중...'}
              </p>
              <p style={{ marginTop: '10px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                이 단계는 약 2-3분이 소요됩니다
              </p>
              <p style={{ marginTop: '5px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                완료 후 Phase 2에서 데이터베이스에 저장됩니다
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay">
      <div className="progress-modal">
        <div className="modal-header">
          <h3>📊 {progress.description}</h3>
          <button className="close-button" onClick={onClose}>×</button>
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
            {/* Phase Badge - 채권은 단일 단계이므로 숨김 */}
            {!isBondTask && (
              <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginTop: '15px', marginBottom: '10px' }}>
                <span style={{
                  backgroundColor: currentPhase === 'Phase 1' ? '#4CAF50' : 'var(--border)',
                  color: currentPhase === 'Phase 1' ? 'white' : 'var(--text-secondary)',
                  padding: '5px 15px',
                  borderRadius: '20px',
                  fontSize: '0.9rem',
                  fontWeight: 'bold'
                }}>
                  Phase 1: 수집
                </span>
                <span style={{
                  backgroundColor: currentPhase === 'Phase 2' ? '#2196F3' : 'var(--border)',
                  color: currentPhase === 'Phase 2' ? 'white' : 'var(--text-secondary)',
                  padding: '5px 15px',
                  borderRadius: '20px',
                  fontSize: '0.9rem',
                  fontWeight: 'bold'
                }}>
                  Phase 2: 저장
                </span>
              </div>
            )}

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
                 `⏳ 진행 중`}
              </span>
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

          {/* Completion Status */}
          {isComplete && (
            <div style={{ marginTop: '20px', padding: '15px', backgroundColor: progress.status === 'completed' ? '#E8F5E9' : '#FFEBEE', borderRadius: '8px', textAlign: 'center' }}>
              <p style={{ margin: '0 0 10px 0', fontSize: '1.1rem', fontWeight: 'bold', color: progress.status === 'completed' ? '#2E7D32' : '#C62828' }}>
                {progress.status === 'completed' ? '✅ 데이터 적재 완료!' : '⚠️ 작업이 실패했습니다'}
              </p>
              <p style={{ margin: '0', color: progress.status === 'completed' ? '#558B2F' : '#B71C1C', fontSize: '0.9rem' }}>
                총 {progress.success_count + progress.failed_count}건 중 {progress.success_count}건 성공
              </p>
            </div>
          )}

          {/* Close Button for Completed */}
          {isComplete && (
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={onClose} style={{ marginTop: '15px' }}>
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
