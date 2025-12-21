# 🔐 로그인 문제 디버그 가이드

## 현재 상황

**증상**: 회원가입 후 로그아웃하고 다시 로그인하면 비밀번호가 맞는데도 로그인이 안 됨

## 🔍 디버그 로그 활성화 완료

백엔드에 상세 디버그 로그가 추가되었습니다:
- 회원가입 시: 비밀번호 길이, 바이트 수, 16진수 출력
- 로그인 시: 입력 비밀번호, 해시 비교 결과 출력

## 📝 테스트 방법

### 1. 백엔드 로그 확인 준비

**터미널 1 (백엔드 로그 보기)**:
```bash
# 백엔드 실행 중인 터미널에서 로그 확인
# 또는
tail -f /tmp/backend.log
```

### 2. 회원가입 테스트

1. 브라우저에서 http://localhost:5173/signup 접속
2. 새 계정 생성:
   - 이메일: test@debug.com
   - 비밀번호: test1234
   - 이름: Test User

3. **백엔드 로그 확인** - 다음과 같은 출력이 나와야 함:
```
============================================================
📨 SIGNUP 요청 받음
이메일: test@debug.com
이름: Test User
비밀번호 (표시): test1234
비밀번호 길이 (글자): 8
비밀번호 길이 (바이트): 8
비밀번호 16진수: 74657374313233343
============================================================

🔐 hash_password 호출됨
   입력 비밀번호: test1234
   글자 수: 8
   바이트: 8
   ✅ 검증 통과, 해싱 중...
   ✅ 해싱 완료

✅ 회원가입 성공: test@debug.com
```

### 3. 로그아웃 후 로그인 테스트

1. 로그아웃 버튼 클릭
2. 로그인 페이지로 이동
3. 동일한 정보로 로그인:
   - 이메일: test@debug.com
   - 비밀번호: test1234

4. **백엔드 로그 확인**:
```
============================================================
🔐 authenticate_user 호출됨
이메일: test@debug.com
입력 비밀번호: test1234
비밀번호 길이: 8
비밀번호 바이트: 8
✅ 사용자 발견: test@debug.com
DB 해시: $2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxx...
비밀번호 검증 결과: True
============================================================
```

**검증 결과가 False이면 문제 발생!**

## 🐛 예상되는 문제점

### 문제 1: 비밀번호에 공백이 추가됨

**증상**: 프론트엔드에서 비밀번호 앞뒤에 공백이 추가
**로그**:
```
입력 비밀번호:  test1234  (앞뒤 공백 있음)
비밀번호 길이: 10
```

**해결**: 프론트엔드에서 trim() 추가

### 문제 2: 비밀번호 인코딩 문제

**증상**: 회원가입과 로그인 시 비밀번호 인코딩이 다름
**로그**:
```
회원가입: 74657374313233343  (정상 UTF-8)
로그인:   74657374313233343d (끝에 이상한 바이트)
```

**해결**: 인코딩 방식 통일

### 문제 3: 비밀번호 해시 검증 실패

**증상**: bcrypt 검증이 실패
**로그**:
```
비밀번호 검증 결과: False
```

**가능한 원인**:
- 회원가입 시와 로그인 시 비밀번호가 다름
- 해시가 잘못 저장됨
- bcrypt 버전 문제

## 🔧 즉시 확인할 사항

### 1. 데이터베이스에 저장된 해시 확인

```bash
sqlite3 /Users/changrim/KingoPortfolio/backend/kingo.db << 'EOF'
SELECT
  email,
  hashed_password
FROM users
WHERE email = 'test@debug.com';
EOF
```

**정상적인 bcrypt 해시**:
- 항상 `$2b$12$`로 시작
- 총 길이: 60자
- 예: `$2b$12$AbCdEfGhIjKlMnOpQrStUvWxYz0123456789...`

### 2. 수동 비밀번호 검증 테스트

```bash
cd /Users/changrim/KingoPortfolio/backend
/Users/changrim/KingoPortfolio/venv/bin/python3 << 'EOF'
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 테스트 비밀번호
password = "test1234"

# 해시 생성
hashed = pwd_context.hash(password)
print(f"해시: {hashed}")

# 검증
result = pwd_context.verify(password, hashed)
print(f"검증 결과: {result}")

# 다른 비밀번호로 검증
wrong = pwd_context.verify("wrong", hashed)
print(f"잘못된 비밀번호: {wrong}")
EOF
```

**예상 출력**:
```
해시: $2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxx...
검증 결과: True
잘못된 비밀번호: False
```

## 🔍 실제 문제 진단 방법

### 단계 1: 회원가입 테스트

1. 새 계정으로 회원가입
2. 백엔드 로그에서 다음 확인:
   - 비밀번호 길이
   - 바이트 수
   - 16진수 값

### 단계 2: 즉시 로그인 테스트 (로그아웃 없이)

1. 회원가입 직후 자동 로그인된 상태
2. 다른 페이지로 이동 (예: 관리자 페이지)
3. 정상 작동 확인

### 단계 3: 로그아웃 후 로그인 테스트

1. 로그아웃 버튼 클릭
2. 로그인 페이지로 이동
3. **정확히 같은 비밀번호** 입력
4. 백엔드 로그 확인:
   - 입력 비밀번호와 회원가입 시 비밀번호 비교
   - 검증 결과 확인

### 단계 4: 프론트엔드 확인

**브라우저 개발자 도구 > Console**:
```javascript
// 로그인 요청 전에 비밀번호 확인
console.log("입력한 비밀번호:", document.querySelector('input[type="password"]').value);
console.log("길이:", document.querySelector('input[type="password"]').value.length);
```

## 📱 프론트엔드 체크리스트

### LoginPage.jsx 확인 사항

1. **비밀번호 trim 확인**:
```javascript
const password = formData.password.trim(); // ✅ trim 있어야 함
```

2. **API 요청 확인**:
```javascript
const response = await login({
  username: email,    // ✅ OAuth2 형식
  password: password  // ✅ trim된 비밀번호
});
```

3. **에러 처리 확인**:
```javascript
catch (error) {
  console.error('로그인 에러:', error.response?.data);
  // 상세 에러 메시지 출력
}
```

## 🛠️ 임시 해결책

### 방법 1: 비밀번호 재설정 기능 (향후 추가)

현재는 없지만, 필요시 추가 가능

### 방법 2: DB에서 직접 비밀번호 변경

**주의**: 임시 방편이므로 프로덕션에서는 사용 금지

```bash
cd /Users/changrim/KingoPortfolio/backend
/Users/changrim/KingoPortfolio/venv/bin/python3 << 'EOF'
from app.database import SessionLocal
from app.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()

# 사용자 찾기
user = db.query(User).filter(User.email == "test@debug.com").first()

if user:
    # 새 비밀번호 설정
    new_password = "test1234"
    user.hashed_password = pwd_context.hash(new_password)
    db.commit()
    print(f"✅ {user.email}의 비밀번호 변경 완료")
else:
    print("❌ 사용자 없음")

db.close()
EOF
```

## 📊 로그 분석 결과 보고

다음 정보를 수집해주세요:

1. **회원가입 로그**:
   - 비밀번호 길이
   - 바이트 수
   - 16진수 값

2. **로그인 로그**:
   - 입력 비밀번호 길이
   - 바이트 수
   - 검증 결과 (True/False)

3. **브라우저 Console**:
   - 에러 메시지
   - Network 탭의 응답

4. **데이터베이스**:
   - 저장된 해시의 첫 10글자

이 정보가 있으면 정확한 문제를 파악할 수 있습니다!

---

**작성일**: 2024-12-20
**버전**: 1.0
**목적**: 로그인 문제 디버깅
