import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { signUp as signUpApi } from '../services/api';
import { useAuth } from '../App';
import '../styles/SignupPage.css';

function SignupPage() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    // 필수 정보
    email: '',
    password: '',
    passwordConfirm: '',
    name: '',

    // 추가 정보
    phone: '',
    birthDate: '',
    occupation: '',
    company: '',
    annualIncome: '',
    totalAssets: '',
    city: '',
    district: '',
    investmentExperience: '초보',
    investmentGoal: '',
    riskTolerance: '중립적'
  });

  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setError('');
  };

  const validateEmail = (email) => {
    // 이메일 정규식 (RFC 5322 기반)
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return emailRegex.test(email);
  };

  const validateStep1 = () => {
    if (!formData.email || !formData.password || !formData.passwordConfirm || !formData.name) {
      setError('모든 필수 항목을 입력해주세요.');
      return false;
    }

    if (!validateEmail(formData.email)) {
      setError('올바른 이메일 형식을 입력해주세요. (예: user@example.com)');
      return false;
    }

    if (formData.password.length < 8) {
      setError('비밀번호는 8자 이상이어야 합니다.');
      return false;
    }

    if (formData.password !== formData.passwordConfirm) {
      setError('비밀번호가 일치하지 않습니다.');
      return false;
    }

    if (formData.name.length < 2) {
      setError('이름은 2자 이상이어야 합니다.');
      return false;
    }

    return true;
  };

  const handleNext = () => {
    if (step === 1 && !validateStep1()) {
      return;
    }
    setStep(step + 1);
  };

  const handleBack = () => {
    setStep(step - 1);
    setError('');
  };

  const handleSubmit = async (e) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }

    // 3단계가 아니면 제출하지 않음
    if (step !== 3) {
      console.log('Form submission blocked - not on step 3. Current step:', step);
      return;
    }

    console.log('Form submission allowed - on step 3');
    setError('');
    setIsLoading(true);

    try {
      // API 호출 데이터 준비
      const signupData = {
        email: formData.email,
        password: formData.password,
        name: formData.name,
        phone: formData.phone || undefined,
        birth_date: formData.birthDate || undefined,
        occupation: formData.occupation || undefined,
        company: formData.company || undefined,
        annual_income: formData.annualIncome ? parseInt(formData.annualIncome) : undefined,
        total_assets: formData.totalAssets ? parseInt(formData.totalAssets) : undefined,
        city: formData.city || undefined,
        district: formData.district || undefined,
        investment_experience: formData.investmentExperience,
        investment_goal: formData.investmentGoal || undefined,
        risk_tolerance: formData.riskTolerance
      };

      // API 호출
      const response = await signUpApi(signupData);

      // 성공
      const { access_token, user } = response.data;
      login(user, access_token);

      // 이메일 인증 안내 메시지 표시
      alert('회원가입이 완료되었습니다! 📧\n\n이메일 주소로 인증 메일이 발송되었습니다.\n이메일을 확인하여 인증을 완료해주세요.');

      navigate('/survey');
    } catch (err) {
      if (err.response?.status === 400) {
        setError(err.response?.data?.detail || '회원가입에 실패했습니다.');
      } else {
        setError('회원가입 중 오류가 발생했습니다.');
      }
      console.error('Signup error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // 최종 제출 버튼 클릭 핸들러
  const handleFinalSubmit = () => {
    if (step === 3) {
      handleSubmit(null);
    }
  };

  // 폼에서 Enter 키 눌렀을 때 처리
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (step < 3) {
        handleNext();
      }
      // step 3에서는 Enter 키로 제출되지 않도록 함
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card signup-card">
        {/* Progress Indicator */}
        <div className="signup-progress">
          <div className={`progress-step ${step >= 1 ? 'active' : ''}`}>
            <div className="step-number">1</div>
            <div className="step-label">기본 정보</div>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step >= 2 ? 'active' : ''}`}>
            <div className="step-number">2</div>
            <div className="step-label">상세 정보</div>
          </div>
          <div className="progress-line"></div>
          <div className={`progress-step ${step >= 3 ? 'active' : ''}`}>
            <div className="step-number">3</div>
            <div className="step-label">투자 성향</div>
          </div>
        </div>

        <h1>회원가입</h1>
        <p className="subtitle">
          {step === 1 && 'Foresto Compass에 가입하세요'}
          {step === 2 && '추가 정보를 입력해주세요'}
          {step === 3 && '학습 성향을 알려주세요'}
        </p>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit} onKeyPress={handleKeyPress}>
          {/* Step 1: 기본 정보 */}
          {step === 1 && (
            <div className="form-step">
              <div className="form-group">
                <label htmlFor="name">이름 *</label>
                <input
                  type="text"
                  id="name"
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  placeholder="홍길동"
                  disabled={isLoading}
                />
              </div>

              <div className="form-group">
                <label htmlFor="email">이메일 *</label>
                <input
                  type="email"
                  id="email"
                  value={formData.email}
                  onChange={(e) => handleChange('email', e.target.value)}
                  placeholder="example@email.com"
                  disabled={isLoading}
                />
              </div>

              <div className="form-group">
                <label htmlFor="password">비밀번호 *</label>
                <input
                  type="password"
                  id="password"
                  value={formData.password}
                  onChange={(e) => handleChange('password', e.target.value)}
                  placeholder="••••••••"
                  disabled={isLoading}
                />
                <small>8자 이상의 비밀번호를 입력하세요.</small>
              </div>

              <div className="form-group">
                <label htmlFor="passwordConfirm">비밀번호 확인 *</label>
                <input
                  type="password"
                  id="passwordConfirm"
                  value={formData.passwordConfirm}
                  onChange={(e) => handleChange('passwordConfirm', e.target.value)}
                  placeholder="••••••••"
                  disabled={isLoading}
                />
              </div>
            </div>
          )}

          {/* Step 2: 상세 정보 */}
          {step === 2 && (
            <div className="form-step">
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="phone">전화번호</label>
                  <input
                    type="tel"
                    id="phone"
                    value={formData.phone}
                    onChange={(e) => handleChange('phone', e.target.value)}
                    placeholder="010-1234-5678"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="birthDate">생년월일</label>
                  <input
                    type="date"
                    id="birthDate"
                    value={formData.birthDate}
                    onChange={(e) => handleChange('birthDate', e.target.value)}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="occupation">직업</label>
                  <input
                    type="text"
                    id="occupation"
                    value={formData.occupation}
                    onChange={(e) => handleChange('occupation', e.target.value)}
                    placeholder="예: 소프트웨어 엔지니어"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="company">회사명</label>
                  <input
                    type="text"
                    id="company"
                    value={formData.company}
                    onChange={(e) => handleChange('company', e.target.value)}
                    placeholder="예: 테크컴퍼니"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="annualIncome">연봉 (만원)</label>
                  <input
                    type="number"
                    id="annualIncome"
                    value={formData.annualIncome}
                    onChange={(e) => handleChange('annualIncome', e.target.value)}
                    placeholder="예: 5000"
                    min="0"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="totalAssets">총 자산 (만원)</label>
                  <input
                    type="number"
                    id="totalAssets"
                    value={formData.totalAssets}
                    onChange={(e) => handleChange('totalAssets', e.target.value)}
                    placeholder="예: 10000"
                    min="0"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="city">거주 도시</label>
                  <input
                    type="text"
                    id="city"
                    value={formData.city}
                    onChange={(e) => handleChange('city', e.target.value)}
                    placeholder="예: 서울"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="district">구/군</label>
                  <input
                    type="text"
                    id="district"
                    value={formData.district}
                    onChange={(e) => handleChange('district', e.target.value)}
                    placeholder="예: 강남구"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 3: 투자 성향 */}
          {step === 3 && (
            <div className="form-step">
              <div className="form-group">
                <label htmlFor="investmentExperience">투자 경험</label>
                <select
                  id="investmentExperience"
                  value={formData.investmentExperience}
                  onChange={(e) => handleChange('investmentExperience', e.target.value)}
                >
                  <option value="초보">초보 - 투자 경험이 거의 없음</option>
                  <option value="중급">중급 - 1~3년 정도 투자 경험</option>
                  <option value="고급">고급 - 3년 이상 투자 경험</option>
                  <option value="전문가">전문가 - 전문적인 투자 지식 보유</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="investmentGoal">투자 목표</label>
                <input
                  type="text"
                  id="investmentGoal"
                  value={formData.investmentGoal}
                  onChange={(e) => handleChange('investmentGoal', e.target.value)}
                  placeholder="예: 노후 준비, 주택 구입, 자녀 교육비 등"
                />
              </div>

              <div className="form-group">
                <label htmlFor="riskTolerance">위험 감수 성향</label>
                <select
                  id="riskTolerance"
                  value={formData.riskTolerance}
                  onChange={(e) => handleChange('riskTolerance', e.target.value)}
                >
                  <option value="보수적">보수적 - 안정적인 수익을 선호</option>
                  <option value="중립적">중립적 - 균형잡힌 투자 선호</option>
                  <option value="공격적">공격적 - 높은 수익을 위해 위험 감수 가능</option>
                </select>
              </div>

              <div className="info-box">
                <p><strong>선택사항 안내</strong></p>
                <p>2단계의 상세 정보는 선택사항이며, 나중에 프로필에서 수정할 수 있습니다.</p>
              </div>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="form-actions">
            {step > 1 && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleBack}
                disabled={isLoading}
              >
                이전
              </button>
            )}

            {step < 3 ? (
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleNext}
                disabled={isLoading}
              >
                다음
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleFinalSubmit}
                disabled={isLoading}
              >
                {isLoading ? '가입 중...' : '회원가입 완료'}
              </button>
            )}
          </div>
        </form>

        <div className="auth-footer">
          <p>
            이미 계정이 있으신가요?{' '}
            <Link to="/login" className="link">
              로그인
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default SignupPage;
