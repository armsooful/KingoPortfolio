# 사용 가이드 (Guides)

기능별 사용 방법 및 구현 가이드 모음

---

## 📚 문서 목록

### [PROFILE.md](PROFILE.md)
**사용자 프로필 관리 가이드**

- 프로필 조회/수정/삭제
- 비밀번호 변경
- 계정 삭제
- API 엔드포인트 상세
- 보안 고려사항

**대상**: 백엔드/프론트엔드 개발자
**관련 엔드포인트**: `/auth/profile`, `/auth/change-password`, `/auth/account`

---

### [PASSWORD_RESET.md](PASSWORD_RESET.md)
**비밀번호 재설정 가이드**

- 비밀번호 재설정 플로우
- 이메일 토큰 생성/검증
- API 엔드포인트
- 보안 모범 사례
- 프론트엔드 통합

**대상**: 백엔드/프론트엔드 개발자
**관련 엔드포인트**: `/auth/forgot-password`, `/auth/reset-password`

---

### [EXPORT.md](EXPORT.md)
**데이터 내보내기 가이드**

- CSV 내보내기
- Excel 내보내기 (스타일링)
- 진단 결과 내보내기
- 진단 이력 내보내기
- 커스텀 내보내기

**대상**: 백엔드 개발자
**관련 엔드포인트**: `/diagnosis/{id}/export/csv`, `/diagnosis/{id}/export/excel`

---

### [SEO.md](SEO.md)
**SEO 최적화 가이드**

- Meta 태그 설정
- Open Graph 태그
- JSON-LD 구조화 데이터
- robots.txt, sitemap.xml
- 모바일 최적화

**대상**: 프론트엔드 개발자, 마케팅 팀
**관련 엔드포인트**: `/`, `/robots.txt`, `/sitemap.xml`

---

### [RATE_LIMITING.md](RATE_LIMITING.md)
**API Rate Limiting 가이드**

- Rate Limiter 설정
- 클라이언트 식별
- 엔드포인트별 제한
- 429 에러 처리
- 프로덕션 설정 (Redis)

**대상**: 백엔드 개발자
**적용 엔드포인트**: 6개 (signup, login, forgot-password, diagnosis submit, export)

---

## 🎯 기능별 가이드 선택

### 인증 관련
- 프로필 관리 → [PROFILE.md](PROFILE.md)
- 비밀번호 재설정 → [PASSWORD_RESET.md](PASSWORD_RESET.md)
- API 보호 → [RATE_LIMITING.md](RATE_LIMITING.md)

### 데이터 관련
- 데이터 내보내기 → [EXPORT.md](EXPORT.md)

### 마케팅/SEO
- SEO 최적화 → [SEO.md](SEO.md)

---

## 🚀 빠른 시작

### 프론트엔드 개발자

```
1. PROFILE.md - 사용자 프로필 기능 이해
2. PASSWORD_RESET.md - 비밀번호 재설정 플로우
3. SEO.md - 랜딩 페이지 최적화
4. RATE_LIMITING.md - 429 에러 처리
```

### 백엔드 개발자

```
1. PROFILE.md - 프로필 API 구현
2. EXPORT.md - 데이터 내보내기 구현
3. RATE_LIMITING.md - Rate Limiter 설정
4. PASSWORD_RESET.md - 비밀번호 재설정 로직
```

### DevOps 엔지니어

```
1. RATE_LIMITING.md - Redis 설정
2. SEO.md - robots.txt, sitemap.xml 설정
```

---

## 📝 가이드 구조

모든 가이드 문서는 다음 구조를 따릅니다:

```
1. 개요 (Overview)
2. 주요 기능 (Features)
3. 사용 방법 (Usage)
   - API 엔드포인트
   - 요청/응답 예제
4. 예제 코드 (Examples)
5. 문제 해결 (Troubleshooting)
6. 보안 고려사항 (Security)
7. 관련 문서 (Related Docs)
```

---

## 🔍 자주 묻는 질문 (FAQ)

### Q: 프로필 수정 시 이메일 중복 에러가 발생해요
**A**: [PROFILE.md](PROFILE.md)의 "문제 해결" 섹션 참조

### Q: 비밀번호 재설정 이메일이 안 와요
**A**: [PASSWORD_RESET.md](PASSWORD_RESET.md)의 "이메일 전송 설정" 섹션 참조

### Q: CSV 파일에 한글이 깨져요
**A**: [EXPORT.md](EXPORT.md)의 "UTF-8 BOM 설정" 섹션 참조

### Q: Rate Limit을 초과했어요
**A**: [RATE_LIMITING.md](RATE_LIMITING.md)의 "429 에러 처리" 섹션 참조

### Q: 검색 엔진에 사이트가 안 나와요
**A**: [SEO.md](SEO.md)의 "sitemap.xml 제출" 섹션 참조

---

## 🛠️ 문제 해결 체크리스트

### 인증 문제
- [ ] JWT 토큰 만료 확인
- [ ] 권한 확인 (RBAC)
- [ ] Rate Limit 확인
- [ ] [PROFILE.md](PROFILE.md) 문제 해결 섹션 참조

### 데이터 내보내기 문제
- [ ] 파일 권한 확인
- [ ] 데이터 존재 여부 확인
- [ ] 인코딩 확인 (UTF-8)
- [ ] [EXPORT.md](EXPORT.md) 문제 해결 섹션 참조

### Rate Limit 문제
- [ ] 클라이언트 ID 확인
- [ ] Redis 연결 확인 (프로덕션)
- [ ] Rate Limit 설정 확인
- [ ] [RATE_LIMITING.md](RATE_LIMITING.md) 문제 해결 섹션 참조

---

## 📊 문서 통계

| 문서 | 라인 수 | 용량 | API 엔드포인트 수 |
|------|---------|------|-------------------|
| PROFILE.md | 632줄 | 29KB | 4개 |
| PASSWORD_RESET.md | 520줄 | 14KB | 2개 |
| EXPORT.md | 460줄 | 14KB | 3개 |
| SEO.md | 550줄 | 12KB | 3개 |
| RATE_LIMITING.md | 432줄 | 12KB | 6개 |

**총 API 엔드포인트**: 18개

---

## 🔄 가이드 업데이트 규칙

### 새 기능 추가 시
1. 새 가이드 문서 작성
2. 이 README에 추가
3. reference/API_DOCUMENTATION.md 업데이트
4. development/CHANGELOG.md에 기록

### 기존 기능 변경 시
1. 해당 가이드 업데이트
2. "마지막 업데이트" 날짜 변경
3. development/CHANGELOG.md에 기록

### API 변경 시
1. 가이드의 API 섹션 업데이트 (필수)
2. 요청/응답 예제 업데이트
3. reference/API_DOCUMENTATION.md 동기화

---

## 📞 문의 및 피드백

가이드 관련 문의나 개선 제안:
- GitHub Issues에 등록
- 문서 개선 PR 제출
- Backend Team에 문의

---

**마지막 업데이트**: 2025-12-29
**총 가이드 수**: 5개
