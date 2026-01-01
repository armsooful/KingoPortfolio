# 이메일 인증 기능 설정 가이드

KingoPortfolio의 이메일 인증 기능을 설정하는 방법을 안내합니다.

## 📋 목차

1. [기능 개요](#기능-개요)
2. [SMTP 설정](#smtp-설정)
3. [Gmail 설정 예시](#gmail-설정-예시)
4. [환경 변수 설정](#환경-변수-설정)
5. [테스트](#테스트)
6. [문제 해결](#문제-해결)

## 기능 개요

이메일 인증 기능은 사용자가 입력한 이메일 주소가 실제로 소유하고 있는 이메일인지 확인하는 기능입니다.

### 주요 기능

- ✅ 회원가입 시 자동으로 인증 이메일 발송
- ✅ 이메일 인증 링크 클릭으로 간편하게 인증
- ✅ 인증 이메일 재발송 기능
- ✅ 24시간 유효한 인증 토큰
- ✅ 프로필 페이지에서 인증 상태 확인

### 인증 플로우

1. 사용자가 회원가입 완료
2. 시스템이 자동으로 인증 이메일 발송
3. 사용자가 이메일에서 인증 링크 클릭
4. 이메일 인증 완료
5. 프로필 페이지에서 "✓ 인증 완료" 표시

## SMTP 설정

이메일 발송을 위해서는 SMTP 서버 설정이 필요합니다.

### 지원 SMTP 서비스

- Gmail (권장)
- Outlook/Hotmail
- SendGrid
- AWS SES
- 기타 SMTP 서버

## Gmail 설정 예시

Gmail을 SMTP 서버로 사용하는 경우 다음 단계를 따라주세요.

### 1. Google 계정 2단계 인증 활성화

1. [Google 계정 설정](https://myaccount.google.com/) 접속
2. **보안** 메뉴 선택
3. **2단계 인증** 활성화

### 2. 앱 비밀번호 생성

1. [앱 비밀번호 페이지](https://myaccount.google.com/apppasswords) 접속
2. 앱 선택: **기타(맞춤 이름)**
3. 이름 입력: `KingoPortfolio` (또는 원하는 이름)
4. **생성** 클릭
5. 생성된 16자리 앱 비밀번호 복사 (공백 제거)

### 3. 환경 변수 설정

생성된 앱 비밀번호를 `.env` 파일에 입력합니다.

## 환경 변수 설정

### 1. .env 파일 생성

```bash
cd backend
cp .env.example .env
```

### 2. SMTP 설정 입력

`.env` 파일을 열고 다음 항목을 수정합니다:

```bash
# SMTP 이메일 설정
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com           # 실제 Gmail 주소로 변경
SMTP_PASSWORD=your-app-password-here      # Gmail 앱 비밀번호로 변경
SMTP_FROM_EMAIL=your-email@gmail.com      # 발신자 이메일
SMTP_FROM_NAME=KingoPortfolio             # 발신자 이름

# 프론트엔드 URL (인증 링크에 사용)
FRONTEND_URL=http://localhost:5173        # 프론트엔드 URL
```

### 3. 설정 확인

모든 설정이 완료되면 서버를 재시작합니다:

```bash
# 백엔드 서버 재시작
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload
```

## 테스트

### 1. 회원가입 테스트

1. 프론트엔드 접속: http://localhost:5173/signup
2. 회원가입 양식 작성
3. 회원가입 완료 후 이메일 확인
4. 이메일에서 "이메일 인증하기" 버튼 클릭
5. 인증 완료 확인

### 2. API 테스트

#### 인증 이메일 발송 (로그인 필요)

```bash
curl -X POST http://localhost:8000/auth/send-verification-email \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 인증 이메일 재발송 (로그인 불필요)

```bash
curl -X POST http://localhost:8000/auth/resend-verification-email \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

#### 이메일 인증 확인

```bash
curl -X GET "http://localhost:8000/auth/verify-email?token=YOUR_TOKEN"
```

## 문제 해결

### SMTP 인증 실패

**문제**: `❌ Failed to send email: Authentication failed`

**해결 방법**:
1. Gmail 앱 비밀번호가 정확한지 확인
2. 2단계 인증이 활성화되어 있는지 확인
3. `.env` 파일에 공백이나 특수문자가 잘못 입력되지 않았는지 확인

### 이메일이 발송되지 않음

**문제**: 이메일이 전송되지 않거나 스팸 폴더에 들어감

**해결 방법**:
1. 백엔드 콘솔에서 에러 로그 확인
2. SMTP 서버 주소와 포트가 정확한지 확인
3. 방화벽이 587 포트를 차단하지 않는지 확인
4. 스팸 폴더 확인

### 인증 링크 만료

**문제**: `인증 링크가 만료되었습니다`

**해결 방법**:
1. 프로필 페이지에서 "인증 이메일 발송" 버튼 클릭
2. 또는 `/auth/resend-verification-email` API 호출
3. 새로 발송된 이메일에서 인증 진행

### 환경 변수가 로드되지 않음

**문제**: SMTP 설정이 적용되지 않음

**해결 방법**:
1. `.env` 파일이 `backend/` 디렉토리에 있는지 확인
2. `.env` 파일 인코딩이 UTF-8인지 확인
3. 서버 재시작 (`Ctrl+C` 후 다시 실행)

## 보안 고려사항

### 앱 비밀번호 관리

- ⚠️ 앱 비밀번호는 절대 Git에 커밋하지 마세요
- ⚠️ `.env` 파일은 `.gitignore`에 포함되어야 합니다
- ⚠️ 프로덕션 환경에서는 환경 변수로 설정하세요

### 토큰 보안

- ✅ 인증 토큰은 24시간 후 자동 만료
- ✅ 토큰은 URL-safe 랜덤 문자열로 생성
- ✅ 인증 완료 후 토큰 자동 삭제

## API 문서

### POST `/auth/send-verification-email`

로그인한 사용자의 이메일로 인증 메일 발송

- **인증 필요**: Yes
- **Rate Limit**: 3회/시간

### GET `/auth/verify-email`

이메일 인증 토큰 확인 및 인증 처리

- **인증 필요**: No
- **Parameters**: `token` (query parameter)

### POST `/auth/resend-verification-email`

이메일 인증 메일 재발송

- **인증 필요**: No
- **Rate Limit**: 3회/시간
- **Body**: `{"email": "user@example.com"}`

## 추가 지원

문제가 해결되지 않으면 GitHub Issues에 문의해주세요.
