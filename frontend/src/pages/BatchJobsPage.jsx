import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

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
        <div className="result-card" style={{ maxWidth: '1400px' }}>
          {/* Header */}
          <div className="result-header">
            <button
              onClick={() => navigate('/admin')}
              style={{
                position: 'absolute',
                top: '20px',
                left: '20px',
                background: 'white',
                border: '2px solid #e0e0e0',
                borderRadius: '8px',
                padding: '8px 16px',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              ← 뒤로
            </button>
            <div className="result-icon" style={{ fontSize: '3rem' }}>
              ⚙️
            </div>
            <h1 className="result-type" style={{ color: '#FF9800' }}>
              배치 작업 관리
            </h1>
            <p className="result-subtitle">
              한국 주식 데이터 일괄 수집
            </p>
          </div>

          {/* New Batch Job Section */}
          <div style={{
            background: '#f5f5f5',
            borderRadius: '12px',
            padding: '24px',
            marginTop: '32px'
          }}>
            <h2 style={{ marginBottom: '20px' }}>🚀 새 배치 작업 시작</h2>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '600' }}>
                  처리할 종목 수 (최대 500개)
                </label>
                <input
                  type="number"
                  value={limit}
                  onChange={(e) => setLimit(parseInt(e.target.value))}
                  min="1"
                  max="500"
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #e0e0e0',
                    borderRadius: '8px',
                    fontSize: '16px'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '600' }}>
                  시계열 데이터 수집 기간
                </label>
                <select
                  value={days}
                  onChange={(e) => setDays(parseInt(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #e0e0e0',
                    borderRadius: '8px',
                    fontSize: '16px'
                  }}
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

            <div style={{
              background: '#e3f2fd',
              borderRadius: '8px',
              padding: '16px',
              marginBottom: '20px',
              borderLeft: '4px solid #2196F3'
            }}>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '16px', color: '#333' }}>📋 작업 내용</h3>
              <ol style={{ margin: 0, paddingLeft: '20px', fontSize: '14px', color: '#666' }}>
                <li>기본 정보 수집 (종목명, 현재가, 시가총액)</li>
                <li>시계열 데이터 수집 (최근 {days}일, OHLCV)</li>
                <li>재무지표 수집 (PER, PBR, EPS, ROE, 배당률)</li>
              </ol>
              <div style={{ marginTop: '12px', fontSize: '13px', color: '#666' }}>
                ⏱️ 예상 소요 시간: 약 {Math.ceil(limit / 10)}분 (백그라운드 실행)
              </div>
            </div>

            <button
              onClick={startBatchJob}
              disabled={loading || pollingJobId}
              style={{
                width: '100%',
                padding: '16px',
                background: loading || pollingJobId ? '#ccc' : '#FF9800',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontSize: '18px',
                fontWeight: '600',
                cursor: loading || pollingJobId ? 'not-allowed' : 'pointer'
              }}
            >
              {loading ? '시작 중...' : pollingJobId ? '다른 작업 실행 중' : '배치 작업 시작'}
            </button>
          </div>

          {/* Current Job Status */}
          {currentJob && (
            <div style={{
              background: 'white',
              border: '2px solid #e0e0e0',
              borderRadius: '12px',
              padding: '24px',
              marginTop: '24px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 style={{ margin: 0 }}>📊 작업 상세 정보</h2>
                <button
                  onClick={() => setCurrentJob(null)}
                  style={{
                    padding: '8px 16px',
                    background: '#f5f5f5',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer'
                  }}
                >
                  닫기
                </button>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
                  <div>
                    <div style={{ fontSize: '13px', color: '#666' }}>작업 ID</div>
                    <div style={{ fontSize: '16px', fontWeight: '600', fontFamily: 'monospace' }}>{currentJob.job_id}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '13px', color: '#666' }}>상태</div>
                    <div style={{
                      display: 'inline-block',
                      padding: '4px 12px',
                      background: getStatusColor(currentJob.status) + '20',
                      color: getStatusColor(currentJob.status),
                      borderRadius: '12px',
                      fontSize: '14px',
                      fontWeight: '600'
                    }}>
                      {getStatusText(currentJob.status)}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '13px', color: '#666' }}>시작 시간</div>
                    <div style={{ fontSize: '14px' }}>{formatDateTime(currentJob.started_at)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '13px', color: '#666' }}>완료 시간</div>
                    <div style={{ fontSize: '14px' }}>{formatDateTime(currentJob.completed_at)}</div>
                  </div>
                </div>
              </div>

              {/* Progress */}
              {currentJob.status === 'running' && currentJob.progress && (
                <div style={{
                  background: '#f5f5f5',
                  borderRadius: '8px',
                  padding: '16px',
                  marginBottom: '20px'
                }}>
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ fontSize: '14px', fontWeight: '600', marginBottom: '4px' }}>
                      {currentJob.progress.phase}
                    </div>
                    <div style={{ fontSize: '13px', color: '#666' }}>
                      {currentJob.progress.details}
                    </div>
                  </div>
                  <div style={{
                    width: '100%',
                    height: '24px',
                    background: '#e0e0e0',
                    borderRadius: '12px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: currentJob.progress.total > 0
                        ? `${(currentJob.progress.current / currentJob.progress.total * 100)}%`
                        : '0%',
                      height: '100%',
                      background: 'linear-gradient(90deg, #2196F3, #4CAF50)',
                      transition: 'width 0.3s ease',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'white',
                      fontSize: '12px',
                      fontWeight: '600'
                    }}>
                      {currentJob.progress.total > 0
                        ? `${currentJob.progress.current} / ${currentJob.progress.total}`
                        : ''}
                    </div>
                  </div>
                </div>
              )}

              {/* Result */}
              {currentJob.status === 'completed' && currentJob.result && (
                <div style={{
                  background: '#E8F5E9',
                  borderRadius: '8px',
                  padding: '16px',
                  borderLeft: '4px solid #4CAF50'
                }}>
                  <h3 style={{ margin: '0 0 16px 0', color: '#2E7D32' }}>✅ 작업 완료</h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                    <div style={{ background: 'white', borderRadius: '8px', padding: '12px' }}>
                      <div style={{ fontSize: '13px', color: '#666', marginBottom: '4px' }}>기본 정보</div>
                      <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#4CAF50' }}>
                        {currentJob.result.basic_info?.success || 0} 성공
                      </div>
                      <div style={{ fontSize: '12px', color: '#F44336' }}>
                        {currentJob.result.basic_info?.failed || 0} 실패
                      </div>
                    </div>
                    <div style={{ background: 'white', borderRadius: '8px', padding: '12px' }}>
                      <div style={{ fontSize: '13px', color: '#666', marginBottom: '4px' }}>시계열 데이터</div>
                      <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#4CAF50' }}>
                        {currentJob.result.timeseries?.success || 0} 성공
                      </div>
                      <div style={{ fontSize: '12px', color: '#F44336' }}>
                        {currentJob.result.timeseries?.failed || 0} 실패
                      </div>
                    </div>
                    <div style={{ background: 'white', borderRadius: '8px', padding: '12px' }}>
                      <div style={{ fontSize: '13px', color: '#666', marginBottom: '4px' }}>재무지표</div>
                      <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#4CAF50' }}>
                        {currentJob.result.financial?.success || 0} 성공
                      </div>
                      <div style={{ fontSize: '12px', color: '#F44336' }}>
                        {currentJob.result.financial?.failed || 0} 실패
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Error */}
              {currentJob.status === 'failed' && currentJob.error && (
                <div style={{
                  background: '#FFEBEE',
                  borderRadius: '8px',
                  padding: '16px',
                  borderLeft: '4px solid #F44336'
                }}>
                  <h3 style={{ margin: '0 0 12px 0', color: '#C62828' }}>❌ 작업 실패</h3>
                  <div style={{ fontSize: '14px', color: '#666', fontFamily: 'monospace' }}>
                    {currentJob.error}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Job History */}
          <div style={{ marginTop: '32px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h2>📜 작업 기록</h2>
              <button
                onClick={loadJobs}
                style={{
                  padding: '8px 16px',
                  background: '#2196F3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                🔄 새로고침
              </button>
            </div>

            {jobs.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '40px',
                color: '#999',
                fontSize: '14px'
              }}>
                배치 작업 기록이 없습니다.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: '#f5f5f5' }}>
                      <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #e0e0e0' }}>작업 ID</th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #e0e0e0' }}>상태</th>
                      <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #e0e0e0' }}>시작 시간</th>
                      <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #e0e0e0' }}>완료 시간</th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #e0e0e0' }}>작업</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobs.map((job) => (
                      <tr key={job.job_id}>
                        <td style={{ padding: '12px', borderBottom: '1px solid #e0e0e0', fontFamily: 'monospace', fontSize: '13px' }}>
                          {job.job_id}
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #e0e0e0' }}>
                          <span style={{
                            padding: '4px 12px',
                            background: getStatusColor(job.status) + '20',
                            color: getStatusColor(job.status),
                            borderRadius: '12px',
                            fontSize: '12px',
                            fontWeight: '600'
                          }}>
                            {getStatusText(job.status)}
                          </span>
                        </td>
                        <td style={{ padding: '12px', borderBottom: '1px solid #e0e0e0', fontSize: '13px' }}>
                          {formatDateTime(job.started_at)}
                        </td>
                        <td style={{ padding: '12px', borderBottom: '1px solid #e0e0e0', fontSize: '13px' }}>
                          {formatDateTime(job.completed_at)}
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #e0e0e0' }}>
                          <button
                            onClick={() => viewJobDetail(job.job_id)}
                            style={{
                              padding: '6px 12px',
                              background: '#2196F3',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              cursor: 'pointer',
                              fontSize: '12px',
                              marginRight: '8px'
                            }}
                          >
                            상세
                          </button>
                          <button
                            onClick={() => deleteJob(job.job_id)}
                            disabled={job.status === 'running'}
                            style={{
                              padding: '6px 12px',
                              background: job.status === 'running' ? '#ccc' : '#F44336',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              cursor: job.status === 'running' ? 'not-allowed' : 'pointer',
                              fontSize: '12px'
                            }}
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
