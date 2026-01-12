import PropTypes from 'prop-types';

function SurveyQuestion({ question, answer, onAnswerChange }) {
  if (!question) {
    return <div className="question-placeholder">문항을 불러올 수 없습니다.</div>;
  }

  const { id, category, question: questionText, options } = question;

  return (
    <div className="survey-question">
      {/* 카테고리 배지 */}
      <div className="question-category">
        <span className={`category-badge category-${category}`}>
          {getCategoryLabel(category)}
        </span>
      </div>

      {/* 문항 텍스트 */}
      <h2 className="question-text">{questionText}</h2>

      {/* 선택지 */}
      <div className="options-container">
        {options && options.length > 0 ? (
          options.map((option, index) => {
            // weight를 answer_value로 사용 (1, 2, 3, ...)
            const answerValue = option.weight || (index + 1);
            
            return (
              <div key={index} className="option-item">
                <input
                  type="radio"
                  id={`option-${id}-${index}`}
                  name={`question-${id}`}
                  value={answerValue}
                  checked={answer === answerValue}
                  onChange={() => {
                    console.log(`선택됨: Q${id} = ${answerValue} (${option.text})`);
                    onAnswerChange(id, answerValue);
                  }}
                  className="option-input"
                />
                <label
                  htmlFor={`option-${id}-${index}`}
                  className={`option-label ${answer === answerValue ? 'selected' : ''}`}
                >
                  <span className="option-text">{option.text}</span>
                </label>
              </div>
            );
          })
        ) : (
          <div className="no-options">선택지가 없습니다.</div>
        )}
      </div>
    </div>
  );
}

function getCategoryLabel(category) {
  const categoryMap = {
    experience: '경험 수준',
    duration: '학습 방향',
    risk: '위험 성향',
    knowledge: '지식 수준',
    amount: '시뮬레이션 설정',
  };
  return categoryMap[category] || category;
}

SurveyQuestion.propTypes = {
  question: PropTypes.shape({
    id: PropTypes.number.isRequired,
    category: PropTypes.string.isRequired,
    question: PropTypes.string.isRequired,
    options: PropTypes.arrayOf(
      PropTypes.shape({
        value: PropTypes.string.isRequired,
        text: PropTypes.string.isRequired,
        weight: PropTypes.number.isRequired,
      })
    ).isRequired,
  }).isRequired,
  answer: PropTypes.number,
  onAnswerChange: PropTypes.func.isRequired,
};

SurveyQuestion.defaultProps = {
  answer: null,
};

export default SurveyQuestion;