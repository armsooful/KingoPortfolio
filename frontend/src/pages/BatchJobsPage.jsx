import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../styles/BatchJobs.css';

export default function BatchJobsPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [currentJob, setCurrentJob] = useState(null);
  const [pollingJobId, setPollingJobId] = useState(null);

  // 배치 설정
  const [days, setDays] = useState(365);
  const [limit, setLimit] = useState(200);

  useEffect(() => {
    loadJobs();
  }, []);

  // 진행 중인 작업 폴링
  useEffect(() => {
    if (!pollingJobId) return;

    const interval = setInterval(async () => {
      try {
        const token = localStorage.getItem('access_token');
        const response = await axios.get(
          `${import.meta.env.VITE_API_URL}/admin/batch/status/${pollingJobId}`,
          {
            headers: { Authorization: `Bearer ${token}` }
          }
        );

        setCurrentJob(response.data.data);

        // 완료되거나 실패하면 폴링 중지
        if (response.data.data.status === 'completed' || response.data.data.status === 'failed') {
          setPollingJobId(null);
          loadJobs();
        }
      } catch (err) {
        console.error('Failed to poll job status:', err);
      }
    }, 3000); // 3초마다 업데이트

    return () => clearInterval(interval);
  }, [pollingJobId]);

  const loadJobs = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `${import.meta.env.VITE_API_URL}/admin/batch/jobs`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      setJobs(response.data.data.jobs);
    } catch (err) {
      console.error('Failed to load jobs:', err);
    }
  };

  const startBatchJob = async () => {
    if (!window.confirm(
      `${limit}개 종목의 전체 데이터를 수집하시겠습니까?\n\n` +
      `작업 내용:\n` +
      `1. 기본 정보 (종목명, 현재가, 시가총액)\n` +
      `2. 시계열 데이터 (최근 ${days}일, OHLCV)\n` +
      `3. 재무지표 (PER, PBR, EPS, 배당률)\n\n` +
      `예상 소요 시간: 약 ${Math.ceil(limit / 10)}분`
    )) {
      return;
    }

    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      const response = await axios.post(
        `${import.meta.env.VITE_API_URL}/admin/batch/krx-full-collection?days=${days}&limit=${limit}`,
        {},
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      const jobId = response.data.data.job_id;
      setPollingJobId(jobId);

      alert(`✅ 배치 작업이 시작되었습니다.\n작업 ID: ${jobId}`);
      loadJobs();
    } catch (err) {
      console.error('Failed to start batch job:', err);
      alert('❌ 배치 작업 시작 실패: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const viewJobDetail = async (jobId) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get(
        `${import.meta.env.VITE_API_URL}/admin/batch/status/${jobId}`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      setCurrentJob(response.data.data);

      // 실행 중이면 폴링 시작
      if (response.data.data.status === 'running') {
        setPollingJobId(jobId);
      }
    } catch (err) {
      console.error('Failed to load job detail:', err);
      alert('작업 상세 정보를 불러올 수 없습니다.');
    }
  };

  const deleteJob = async (jobId) => {
    if (!window.confirm('이 작업 기록을 삭제하시겠습니까?')) {
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      await axios.delete(
        `${import.meta.env.VITE_API_URL}/admin/batch/jobs/${jobId}`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      alert('✅ 작업 기록이 삭제되었습니다.');
      loadJobs();
      if (currentJob?.job_id === jobId) {
        setCurrentJob(null);
      }
    } catch (err) {
      console.error('Failed to delete job:', err);
      alert('❌ 삭제 실패: ' + (err.response?.data?.detail || err.message));
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: '#FFC107',
      running: '#2196F3',
      completed: '#4CAF50',
      failed: '#F44336'
    };
    return colors[status] || '#666';
  };

  const getStatusText = (status) => {
    const texts = {
      pending: '대기 중',
      running: '실행 중',
      completed: '완료',
      failed: '실패'
    };
    return texts[status] || status;
  };

  const formatDateTime = (isoString) => {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleString('ko-KR');
  };

  return (
    <div className="main-content">
      <div className="result-container">
        <div className="result-card bj-card">
          {/* Header */}
          <div className="result-header">
            <button className="admin-back-btn" onClick={() => navigate('/admin')}>
              ← 관리자 홈
            </button>
            <div className="result-icon">
              ⚙️
            </div>
            <h1 className="result-type">
              배치 작업 관리
            </h1>
            <p className="result-subtitle">
              한국 주식 데이터 일괄 수집
            </p>
          </div>

          {/* New Batch Job Section */}
          <div className="bj-new-job-section">
            <h2>🚀 새 배치 작업 시작</h2>

            <div className="bj-config-grid">
              <div>
                <label className="bj-label">
                  처리할 종목 수 (최대 500개)
                </label>
                <input
                  type="number"
                  value={limit}
                  onChange={(e) => setLimit(parseInt(e.target.value))}
                  min="1"
                  max="500"
                  className="bj-input"
                />
              </div>

              <div>
                <label className="bj-label">
                  시계열 데이터 수집 기간
                </label>
                <select
                  value={days}
                  onChange={(e) => setDays(parseInt(e.target.value))}
                  className="bj-select"
                >
                  <option value="90">3개월 (90일)</option>
                  <option value="180">6개월 (180일)</option>
                  <option value="365">1년 (365일)</option>
                  <option value="730">2년 (730일)</option>
                  <option value="1825">5년 (1825일)</option>
                  <option value="3650">10년 (3650일)</option>
                </select>
              </div>
            </div>

            <div className="bj-info-box">
              <h3>📋 작업 내용</h3>
              <ol>
                <li>기본 정보 수집 (종목명, 현재가, 시가총액)</li>
                <li>시계열 데이터 수집 (최근 {days}일, OHLCV)</li>
                <li>재무지표 수집 (PER, PBR, EPS, ROE, 배당률)</li>
              </ol>
              <div className="bj-estimate">
                ⏱️ 예상 소요 시간: 약 {Math.ceil(limit / 10)}분 (백그라운드 실행)
              </div>
            </div>

            <button
              onClick={startBatchJob}
              disabled={loading || pollingJobId}
              className="bj-start-btn"
            >
              {loading ? '시작 중...' : pollingJobId ? '다른 작업 실행 중' : '배치 작업 시작'}
            </button>
          </div>

          {/* Current Job Status */}
          {currentJob && (
            <div className="bj-detail-panel">
              <div className="bj-detail-header">
                <h2>📊 작업 상세 정보</h2>
                <button
                  onClick={() => setCurrentJob(null)}
                  className="bj-close-btn"
                >
                  닫기
                </button>
              </div>

              <div className="bj-info-grid">
                <div className="bj-info-grid-inner">
                  <div>
                    <div className="bj-info-label">작업 ID</div>
                    <div className="bj-info-value">{currentJob.job_id}</div>
                  </div>
                  <div>
                    <div className="bj-info-label">상태</div>
                    <span
                      className="bj-status-badge"
                      style={{
                        background: getStatusColor(currentJob.status) + '20',
                        color: getStatusColor(currentJob.status)
                      }}
                    >
                      {getStatusText(currentJob.status)}
                    </span>
                  </div>
                  <div>
                    <div className="bj-info-label">시작 시간</div>
                    <div className="bj-info-value-sm">{formatDateTime(currentJob.started_at)}</div>
                  </div>
                  <div>
                    <div className="bj-info-label">완료 시간</div>
                    <div className="bj-info-value-sm">{formatDateTime(currentJob.completed_at)}</div>
                  </div>
                </div>
              </div>

              {/* Progress */}
              {currentJob.status === 'running' && currentJob.progress && (
                <div className="bj-progress-section">
                  <div className="bj-progress-info">
                    <div className="bj-progress-phase">
                      {currentJob.progress.phase}
                    </div>
                    <div className="bj-progress-details">
                      {currentJob.progress.details}
                    </div>
                  </div>
                  <div className="bj-progress-track">
                    <div
                      className="bj-progress-fill"
                      style={{
                        width: currentJob.progress.total > 0
                          ? `${(currentJob.progress.current / currentJob.progress.total * 100)}%`
                          : '0%'
                      }}
                    >
                      {currentJob.progress.total > 0
                        ? `${currentJob.progress.current} / ${currentJob.progress.total}`
                        : ''}
                    </div>
                  </div>
                </div>
              )}

              {/* Result */}
              {currentJob.status === 'completed' && currentJob.result && (
                <div className="bj-result-success">
                  <h3>✅ 작업 완료</h3>
                  <div className="bj-result-grid">
                    <div className="bj-result-card">
                      <div className="bj-result-card-label">기본 정보</div>
                      <div className="bj-result-card-success">
                        {currentJob.result.basic_info?.success || 0} 성공
                      </div>
                      <div className="bj-result-card-failed">
                        {currentJob.result.basic_info?.failed || 0} 실패
                      </div>
                    </div>
                    <div className="bj-result-card">
                      <div className="bj-result-card-label">시계열 데이터</div>
                      <div className="bj-result-card-success">
                        {currentJob.result.timeseries?.success || 0} 성공
                      </div>
                      <div className="bj-result-card-failed">
                        {currentJob.result.timeseries?.failed || 0} 실패
                      </div>
                    </div>
                    <div className="bj-result-card">
                      <div className="bj-result-card-label">재무지표</div>
                      <div className="bj-result-card-success">
                        {currentJob.result.financial?.success || 0} 성공
                      </div>
                      <div className="bj-result-card-failed">
                        {currentJob.result.financial?.failed || 0} 실패
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Error */}
              {currentJob.status === 'failed' && currentJob.error && (
                <div className="bj-result-error">
                  <h3>❌ 작업 실패</h3>
                  <div className="bj-result-error-msg">
                    {currentJob.error}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Job History */}
          <div className="bj-history-section">
            <div className="bj-history-header">
              <h2>📜 작업 기록</h2>
              <button
                onClick={loadJobs}
                className="bj-refresh-btn"
              >
                🔄 새로고침
              </button>
            </div>

            {jobs.length === 0 ? (
              <div className="bj-empty">
                배치 작업 기록이 없습니다.
              </div>
            ) : (
              <div className="bj-table-wrap">
                <table className="bj-table">
                  <thead>
                    <tr>
                      <th>작업 ID</th>
                      <th className="center">상태</th>
                      <th>시작 시간</th>
                      <th>완료 시간</th>
                      <th className="center">작업</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobs.map((job) => (
                      <tr key={job.job_id}>
                        <td className="mono">
                          {job.job_id}
                        </td>
                        <td className="center">
                          <span
                            className="bj-status-badge-sm"
                            style={{
                              background: getStatusColor(job.status) + '20',
                              color: getStatusColor(job.status)
                            }}
                          >
                            {getStatusText(job.status)}
                          </span>
                        </td>
                        <td className="small">
                          {formatDateTime(job.started_at)}
                        </td>
                        <td className="small">
                          {formatDateTime(job.completed_at)}
                        </td>
                        <td className="center">
                          <button
                            onClick={() => viewJobDetail(job.job_id)}
                            className="bj-action-btn detail"
                          >
                            상세
                          </button>
                          <button
                            onClick={() => deleteJob(job.job_id)}
                            disabled={job.status === 'running'}
                            className="bj-action-btn delete"
                          >
                            삭제
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
