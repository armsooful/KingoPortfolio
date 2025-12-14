import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getSurveyQuestions, submitDiagnosis } from '../services/api';
import SurveyQuestion from '../components/SurveyQuestion';

function SurveyPage() {
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [monthlyInvestment, setMonthlyInvestment] = useState('50');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
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
      <div className="loading-container">
        <div className="spinner"></div>
        <p>설문을 준비 중입니다...</p>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className="survey-container">
        <div className="error-message">설문을 불러올 수 없습니다.</div>
      </div>
    );
  }

  const currentQuestion = questions[currentIndex];
  const progress = ((currentIndex + 1) / questions.length) * 100;
  const isAnswered = answers[currentQuestion.id] !== null;

  return (
    <div className="survey-container">
      <div className="survey-card">
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
        {error && <div className="error-message">{error}</div>}

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
            <small>선택 사항: 포트폴리오 추천에 참고됩니다.</small>
          </div>
        )}

        {/* 버튼 영역 */}
        <div className="button-section">
          <button
            className="btn btn-secondary"
            onClick={handlePrev}
            disabled={currentIndex === 0 || isSubmitting}
          >
            이전
          </button>

          {currentIndex === questions.length - 1 ? (
            <button
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={!isAllAnswered() || isSubmitting}
            >
              {isSubmitting ? '진단 중...' : '진단 완료'}
            </button>
          ) : (
            <button
              className="btn btn-primary"
              onClick={handleNext}
              disabled={!isAnswered || isSubmitting}
            >
              다음
            </button>
          )}
        </div>

        {/* 안내 메시지 */}
        <div className="survey-info">
          <p>💡 각 문항에 정직하게 답변할수록 더 정확한 진단 결과를 얻을 수 있습니다.</p>
        </div>
      </div>
    </div>
  );
}

export default SurveyPage;