# Vercel 배포 및 환경변수 설정 가이드
최초작성일자: 2026-01-12
최종수정일자: 2026-01-18

## 문제 상황

Vercel에 배포된 프론트엔드가 `http://localhost:8000`으로 API 요청을 보내는 문제가 발생합니다.
이는 빌드 시점에 환경변수가 올바르게 주입되지 않았기 때문입니다.

## 해결 방법

### 1. Vercel 대시보드에서 환경변수 설정

1. **Vercel 대시보드 접속**
   - https://vercel.com 로그인
   - 프로젝트 선택

2. **Settings → Environment Variables 이동**

3. **환경변수 추가**
   - **Key**: `VITE_API_URL`
   - **Value**: `https://kingo-backend.onrender.com`
   - **Environment**: `Production`, `Preview`, `Development` 모두 선택

4. **Redeploy**
   - Deployments 탭으로 이동
   - 최신 배포 옆 점 3개 클릭
   - "Redeploy" 선택
   - "Use existing Build Cache" 체크 해제 (중요!)
   - "Redeploy" 버튼 클릭

### 2. 환경변수 확인

배포 완료 후 브라우저 개발자 도구에서 확인:
```javascript
// 콘솔에서 확인
console.log(import.meta.env.VITE_API_URL)
// 출력: https://kingo-backend.onrender.com
```

또는 Network 탭에서 API 요청이 `https://kingo-backend.onrender.com`으로 가는지 확인

### 3. 추가 환경변수 (필요시)

프로덕션 환경에서 추가 설정이 필요한 경우:

| Key | Value | Description |
|-----|-------|-------------|
| `VITE_API_URL` | `https://kingo-backend.onrender.com` | 백엔드 API URL (필수) |
| `NODE_ENV` | `production` | Node 환경 (자동 설정됨) |

## 문제 해결

### Q1: 환경변수를 설정했는데도 localhost로 요청이 감

**원인**: 빌드 캐시가 남아있어서 이전 빌드를 사용함

**해결**:
1. Vercel 대시보드에서 Settings → General → Build & Development Settings
2. "Clear Build Cache" 버튼 클릭
3. 또는 Redeploy 시 "Use existing Build Cache" 체크 해제

### Q2: CORS 에러가 발생함

**원인**: 백엔드에서 Vercel 프론트엔드 도메인을 허용하지 않음

**해결**:
1. Render 대시보드에서 백엔드 서비스 선택
2. Environment Variables에서 `ALLOWED_ORIGINS` 확인
3. Vercel 배포 URL 추가 (예: `https://your-app.vercel.app`)

현재 설정된 CORS origins:
```
https://kingo-portfolio-d0je2u1t8-changrims-projects.vercel.app,http://localhost:3000
```

### Q3: 빌드는 성공하는데 런타임에 에러 발생

**원인**: Vite는 빌드 시점에 환경변수를 번들에 포함시킴

**해결**:
- 환경변수 변경 후 반드시 **새로운 빌드** 필요
- "Redeploy" 만으로는 부족, 캐시 제거 후 빌드

## Vite 환경변수 작동 방식

Vite는 `VITE_` 접두사가 붙은 환경변수만 클라이언트에 노출합니다:

```javascript
// ✅ 작동함
const apiUrl = import.meta.env.VITE_API_URL

// ❌ 작동하지 않음 (보안상 클라이언트에 노출 안 됨)
const secret = import.meta.env.SECRET_KEY
```

## 로컬 개발 환경

로컬에서는 `.env.development` 또는 `.env.local` 사용:

```bash
# frontend/.env.local (gitignore됨)
VITE_API_URL=http://localhost:8000
```

## 프로덕션 빌드 테스트

로컬에서 프로덕션 빌드 테스트:

```bash
cd frontend

# 프로덕션 빌드
npm run build

# 빌드된 파일 미리보기
npm run preview
```

## 참고 자료

- [Vite 환경변수 가이드](https://vitejs.dev/guide/env-and-mode.html)
- [Vercel 환경변수 문서](https://vercel.com/docs/projects/environment-variables)
- [Render 환경변수 문서](https://render.com/docs/environment-variables)
