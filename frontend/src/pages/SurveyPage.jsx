import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getSurveyQuestions, recordConsent, submitDiagnosis, getProfileCompletionStatus } from '../services/api';
import SurveyQuestion from '../components/SurveyQuestion';
import Disclaimer from '../components/Disclaimer';
import ProfileCompletionModal from '../components/ProfileCompletionModal';
import '../styles/Survey.css';

function SurveyPage() {
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [monthlyInvestment, setMonthlyInvestment] = useState('50');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [agreedToNotice, setAgreedToNotice] = useState(false);
  const [showSurvey, setShowSurvey] = useState(false);
  const [isRecordingConsent, setIsRecordingConsent] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [showProfileModal, setShowProfileModal] = useState(false);
  const navigate = useNavigate();

  // 설문 문항 로드
  useEffect(() => {
  const loadQuestions = async () => {
    try {
      const response = await getSurveyQuestions();
      console.log('첫 번째 설문 전체:', JSON.stringify(response.data.questions[0], null, 2));
      console.log('첫 번째 선택지:', response.data.questions[0].options[0]);
      setQuestions(response.data.questions);
        // 초기 답변 상태 설정
        const initialAnswers = {};
        response.data.questions.forEach((q) => {
          initialAnswers[q.id] = null;
        });
        setAnswers(initialAnswers);
      } catch (err) {
        setError('설문 문항을 불러올 수 없습니다.');
        console.error('Load questions error:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadQuestions();
  }, []);

  const handleAnswerChange = (questionId, answerValue) => {
  console.log(`답변 저장: Q${questionId} = ${answerValue} (타입: ${typeof answerValue})`);
  setAnswers({
    ...answers,
    [questionId]: Number(answerValue),
  });
};

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  const isAllAnswered = () => {
    return questions.every((q) => answers[q.id] !== null);
  };

const handleSubmit = async () => {
  if (!isAllAnswered()) {
    setError('모든 문항에 답변해주세요.');
    return;
  }

  setIsSubmitting(true);
  setError('');

  try {
    // 답변 형식 변환
    console.log('원본 answers:', answers); 

    const submissionData = {
      answers: Object.entries(answers).map(([questionId, answerValue]) => ({
        question_id: parseInt(questionId),
        answer_value: parseInt(answerValue), // ← 수정: parseInt 사용
      })),
      monthly_investment: parseInt(monthlyInvestment) || null,
    };

    console.log('제출 데이터:', submissionData); // 디버깅용
    console.log('첫 번째 답변:', submissionData.answers[0]);
    console.log('모든 답변 값:', submissionData.answers.map(a => ({ id: a.question_id, value: a.answer_value })));

    // API 호출
    const response = await submitDiagnosis(submissionData);

    console.log('진단 결과:', response.data); // 디버깅용

    // 진단 결과를 세션 스토리지에 저장
    sessionStorage.setItem('diagnosisResult', JSON.stringify(response.data));

    // 결과 페이지로 이동
    navigate('/result');
  } catch (err) {
    // 에러 메시지 추출 (객체가 아닌 문자열만)
    let errorMessage = '진단 중 오류가 발생했습니다.';
    
    if (err.response?.data?.detail) {
      errorMessage = typeof err.response.data.detail === 'string' 
        ? err.response.data.detail 
        : JSON.stringify(err.response.data.detail);
    }
    
    setError(errorMessage);
    console.error('Submit diagnosis error:', err);
  } finally {
    setIsSubmitting(false);
  }
};

  if (isLoading) {
    return (
      <div className="sv-loading">
        <div className="sv-spinner"></div>
        <p>설문을 준비 중입니다...</p>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className="survey-container">
        <div className="sv-error">설문을 불러올 수 없습니다.</div>
      </div>
    );
  }

  const currentQuestion = questions[currentIndex];
  const progress = ((currentIndex + 1) / questions.length) * 100;
  const isAnswered = answers[currentQuestion.id] !== null;

  const handleStartSurvey = async () => {
    setError('');
    setIsRecordingConsent(true);
    try {
      // 프로필 완성도 체크
      const profileRes = await getProfileCompletionStatus();
      if (!profileRes.data.is_complete) {
        setShowProfileModal(true);
        setIsRecordingConsent(false);
        return;
      }

      await recordConsent({
        consent_type: 'diagnosis_notice',
        consent_version: 'v1',
        consent_text:
          '본 투자 성향 진단은 교육 및 정보 제공 목적의 자가 점검 도구이며, 특정 금융상품·종목에 대한 투자 권유, 추천 또는 자문을 제공하지 않습니다.\n' +
          '진단 결과는 이용자의 설문 응답 시점을 기준으로 산출된 참고 정보로, 개인의 재무 상황, 시장 환경, 시간의 경과 등에 따라 달라질 수 있습니다.\n' +
          '본 서비스는 이용자의 투자 판단 또는 투자 결정을 대행하지 않으며, 투자 판단 및 그에 따른 책임은 전적으로 이용자 본인에게 있습니다.\n' +
          '본 서비스는 자본시장과 금융투자업에 관한 법률에 따른 투자자문업 또는 투자일임업에 해당하는 행위를 수행하지 않도록 설계되었습니다.',
      });
      setShowSurvey(true);
    } catch (err) {
      setError('유의사항 동의 기록에 실패했습니다.');
    } finally {
      setIsRecordingConsent(false);
    }
  };

  return (
    <div className="survey-container">
      <div className="survey-card">
        {!showSurvey ? (
          <>
            <Disclaimer type="diagnosis" />
            {error && <div className="sv-error">{error}</div>}
            <div className="notice-consent">
              <label className="notice-checkbox">
                <input
                  type="checkbox"
                  checked={agreedToNotice}
                  onChange={(event) => setAgreedToNotice(event.target.checked)}
                />
                유의사항을 읽고 이해했으며, 이에 동의합니다.
              </label>
              <button
                className="sv-btn sv-btn-primary"
                onClick={handleStartSurvey}
                disabled={!agreedToNotice || isRecordingConsent}
              >
                {isRecordingConsent ? '기록 중...' : '설문 시작'}
              </button>
            </div>
          </>
        ) : (
          <>

        {/* 진행률 */}
        <div className="progress-section">
          <div className="progress-header">
            <span className="progress-text">
              {currentIndex + 1} / {questions.length}
            </span>
            <span className="progress-percent">{Math.round(progress)}%</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
        </div>

        {/* 에러 메시지 */}
        {error && <div className="sv-error">{error}</div>}

        {/* 설문 문항 */}
        <div className="question-section">
          <SurveyQuestion
            question={currentQuestion}
            answer={answers[currentQuestion.id]}
            onAnswerChange={handleAnswerChange}
          />
        </div>

        {/* 월 투자액 입력 (마지막 문항 다음) */}
        {currentIndex === questions.length - 1 && (
          <div className="investment-section">
            <label htmlFor="monthlyInvestment">월 투자 예상액 (만원)</label>
            <input
              type="number"
              id="monthlyInvestment"
              value={monthlyInvestment}
              onChange={(e) => setMonthlyInvestment(e.target.value)}
              placeholder="50"
              min="0"
            />
            <small>선택 사항: 시뮬레이션 금액 설정에 활용됩니다.</small>
          </div>
        )}

        {/* 버튼 영역 */}
        <div className="button-section">
          <button
            className="sv-btn sv-btn-secondary"
            onClick={handlePrev}
            disabled={currentIndex === 0 || isSubmitting}
          >
            이전
          </button>

          {currentIndex === questions.length - 1 ? (
            <button
              className="sv-btn sv-btn-primary"
              onClick={handleSubmit}
              disabled={!isAllAnswered() || isSubmitting}
            >
              {isSubmitting ? '진단 중...' : '진단 완료'}
            </button>
          ) : (
            <button
              className="sv-btn sv-btn-primary"
              onClick={handleNext}
              disabled={!isAnswered || isSubmitting}
            >
              다음
            </button>
          )}
        </div>

        {/* 안내 메시지 */}
        <div className="survey-info">
          <p>💡 이 설문은 투자 성향을 진단하기 위한 도구입니다.</p>
          <p className="survey-info-sub">
            ⚠️ 설문 완료 여부와 관계없이 시나리오 기반 모의실험을 이용할 수 있습니다.
          </p>
        </div>
          </>
        )}
      </div>

      {showProfileModal && (
        <ProfileCompletionModal
          onClose={() => setShowProfileModal(false)}
          onComplete={() => {
            setShowProfileModal(false);
            // 프로필 완성 후 자동으로 설문 시작 재시도
            handleStartSurvey();
          }}
        />
      )}
    </div>
  );
}

export default SurveyPage;
