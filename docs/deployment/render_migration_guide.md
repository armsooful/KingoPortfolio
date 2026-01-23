# Render 배포 후 마이그레이션 가이드
최초작성일자: 2026-01-12
최종수정일자: 2026-01-18

## 이메일 인증 자동 활성화 마이그레이션

교육용 플랫폼으로 전환하면서 이메일 인증 절차를 생략하기로 결정했습니다.
이미 가입한 사용자들의 이메일 인증을 활성화하려면 아래 마이그레이션을 실행하세요.

### Render에서 실행 방법

1. **Render 대시보드에서 Shell 접속**
   - Render.com 대시보드에 로그인
   - 해당 웹 서비스 선택
   - 오른쪽 상단 "Shell" 버튼 클릭

2. **마이그레이션 스크립트 실행**
   ```bash
   python backend/scripts/migrate_auto_verify_emails.py
   ```

3. **결과 확인**
   - 스크립트가 성공적으로 완료되면 모든 사용자의 `is_email_verified`가 `True`로 설정됩니다
   - 이제 모든 사용자가 로그인할 수 있습니다

### 로컬에서 실행 방법

```bash
# 가상환경 활성화
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows

# 마이그레이션 실행
python backend/scripts/migrate_auto_verify_emails.py
```

### 마이그레이션이 하는 일

- 모든 사용자의 `is_email_verified` 필드를 `True`로 설정
- 기존 사용자들이 이메일 인증 없이 로그인할 수 있도록 함
- 신규 사용자는 회원가입 시 자동으로 인증됨 (코드 변경으로 처리)

### 문제 해결

**Q: 마이그레이션 실행 후에도 로그인이 안 돼요**
- 브라우저 캐시를 지우고 다시 시도하세요
- 로그아웃 후 다시 로그인해보세요
- 개발자 도구의 Console 탭에서 에러 메시지를 확인하세요

**Q: 스크립트 실행 시 "No module named 'app'" 에러가 발생해요**
- 프로젝트 루트 디렉토리에서 실행하고 있는지 확인하세요
- 가상환경이 활성화되어 있는지 확인하세요

**Q: 데이터베이스 연결 에러가 발생해요**
- Render에서 실행 중인지 확인하세요 (Shell을 통해 접속)
- 로컬에서 실행 시 `kingo.db` 파일이 있는지 확인하세요

### 관련 파일

- 마이그레이션 스크립트: `backend/scripts/migrate_auto_verify_emails.py`
- 회원가입 로직: `backend/app/routes/auth.py` (line 181-183)
- 사용자 모델: `backend/app/models/user.py`
