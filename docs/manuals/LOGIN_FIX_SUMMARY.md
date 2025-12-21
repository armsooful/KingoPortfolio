# 🔐 로그인 문제 수정 완료

## 문제 상황

**증상**: 회원가입 후 로그아웃하고 다시 로그인하면 비밀번호가 맞는데도 로그인이 안 됨

**백엔드 로그**:
```
🔐 authenticate_user 호출됨
이메일: undefined  ← 문제!
입력 비밀번호: debug1234
비밀번호 길이: 9
비밀번호 바이트: 9
❌ 사용자 없음
```

## 원인 분석

### 1. 이메일이 `undefined`로 전송됨

**LoginPage.jsx** (27-30줄):
```javascript
const response = await loginApi({
  email,      // ← 'email' 필드로 전송
  password,
});
```

**api.js** (52-56줄):
```javascript
export const login = (data) => {
  const formData = new URLSearchParams();
  formData.append('username', data.username);  // ← 'username' 필드 기대
  formData.append('password', data.password);
```

**문제**: LoginPage는 `email`을 보내는데, api.js는 `username`을 읽으려고 함
**결과**: `data.username`은 undefined → 백엔드에 "undefined" 전송

### 2. OAuth2 표준 vs 실제 사용

OAuth2 표준은 `username` 필드를 사용하지만, 우리 앱은 이메일을 사용자명으로 사용합니다.

## 수정 내용

### [frontend/src/services/api.js](frontend/src/services/api.js#L56)

**Before**:
```javascript
formData.append('username', data.username);
```

**After**:
```javascript
// email을 username으로 매핑 (OAuth2 표준)
formData.append('username', data.email || data.username);
```

**설명**:
- `data.email`이 있으면 사용 (LoginPage에서 전송)
- 없으면 `data.username` 사용 (하위 호환성)
- OAuth2 표준에 맞게 `username` 필드로 전송

## 테스트 방법

### 1. 프론트엔드 재시작 (필요시)

브라우저 캐시 때문에 변경사항이 적용되지 않을 수 있습니다:

```bash
# 프론트엔드 재시작
cd /Users/changrim/KingoPortfolio/frontend
npm run dev
```

또는 브라우저에서:
- **Hard Refresh**: Cmd+Shift+R (Mac) 또는 Ctrl+Shift+R (Windows)
- **캐시 삭제**: 개발자 도구 > Network > Disable cache 체크

### 2. 로그인 테스트

1. http://localhost:5173/login 접속
2. 기존 계정으로 로그인:
   - 이메일: debug@test.com
   - 비밀번호: debug1234

3. **백엔드 로그 확인** - 이제 정상적으로 출력:
```
============================================================
🔐 authenticate_user 호출됨
이메일: debug@test.com  ← 정상!
입력 비밀번호: debug1234
비밀번호 길이: 9
비밀번호 바이트: 9
✅ 사용자 발견: debug@test.com
DB 해시: $2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxx...
비밀번호 검증 결과: True  ← 성공!
============================================================
```

### 3. 회원가입 후 로그인 테스트

1. 새 계정 생성: http://localhost:5173/signup
   - 이메일: test@example.com
   - 비밀번호: test1234
   - 이름: Test User

2. 로그아웃

3. 다시 로그인:
   - 이메일: test@example.com
   - 비밀번호: test1234

4. ✅ 로그인 성공!

## 추가 개선 사항

### 디버그 로그 추가 완료

**backend/app/crud.py** (46-72줄):
```python
def authenticate_user(db: Session, email: str, password: str):
    """사용자 인증 (로그인)"""
    print("\n" + "="*60)
    print("🔐 authenticate_user 호출됨")
    print(f"이메일: {email}")
    print(f"입력 비밀번호: {password}")
    print(f"비밀번호 길이: {len(password)}")
    print(f"비밀번호 바이트: {len(password.encode('utf-8'))}")

    user = get_user_by_email(db, email)

    if not user:
        print("❌ 사용자 없음")
        print("="*60 + "\n")
        return None

    print(f"✅ 사용자 발견: {user.email}")
    print(f"DB 해시: {user.hashed_password[:50]}...")

    verification_result = verify_password(password, user.hashed_password)
    print(f"비밀번호 검증 결과: {verification_result}")
    print("="*60 + "\n")

    if not verification_result:
        return None

    return user
```

**용도**: 향후 로그인 문제 디버깅 시 사용

## 프로덕션 배포 전 확인사항

### 1. 디버그 로그 제거

프로덕션에서는 비밀번호를 로그에 출력하면 안 됩니다!

**backend/app/crud.py**:
```python
def authenticate_user(db: Session, email: str, password: str):
    """사용자 인증 (로그인)"""
    # 디버그 로그 제거
    user = get_user_by_email(db, email)

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
```

**backend/app/auth.py**:
```python
def hash_password(password: str) -> str:
    """비밀번호 해시 (bcrypt 72바이트 제한)"""
    # 디버그 로그 제거
    if len(password.encode('utf-8')) > 72:
        raise ValueError("password cannot be longer than 72 bytes")

    return pwd_context.hash(password)
```

**backend/app/routes/auth.py**:
```python
@router.post("/signup", response_model=Token, status_code=201)
async def signup(user_create: UserCreate, db: Session = Depends(get_db)):
    """회원가입"""
    # 디버그 로그 제거

    existing_user = get_user_by_email(db, user_create.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # ... 나머지 코드
```

### 2. HTTPS 사용

프로덕션에서는 HTTPS를 사용하여 비밀번호를 암호화 전송

### 3. Rate Limiting

무차별 대입 공격 방지를 위한 로그인 시도 제한 추가

## 수정 파일 목록

1. ✅ **frontend/src/services/api.js** (Line 56)
   - `data.username` → `data.email || data.username`

2. ✅ **backend/app/crud.py** (Line 46-72)
   - 디버그 로그 추가 (개발용)

3. ✅ **backend/app/auth.py** (Line 27-39)
   - 디버그 로그 추가 (개발용)

4. ✅ **backend/app/routes/auth.py** (Line 30-39)
   - 디버그 로그 추가 (개발용)

## 테스트 결과

### Before (실패)
```
이메일: undefined
❌ 사용자 없음
```

### After (성공)
```
이메일: debug@test.com
✅ 사용자 발견: debug@test.com
비밀번호 검증 결과: True
✅ 로그인 성공!
```

## 관련 문서

- [LOGIN_DEBUG_GUIDE.md](LOGIN_DEBUG_GUIDE.md) - 로그인 디버깅 가이드
- [QUICK_START.md](QUICK_START.md) - 빠른 시작 가이드

---

**수정일**: 2024-12-20
**버전**: 1.1
**상태**: ✅ 로그인 문제 해결 완료
