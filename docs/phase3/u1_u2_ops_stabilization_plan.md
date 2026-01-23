# U-1/U-2 운영 안정화 계획

## 목적
- U-1/U-2 사용자 기능 운영 안정화를 위해 핵심 이벤트/메트릭 고정, 알림 임계치 설정, 롤백/핫픽스 절차를 명문화한다.

## 1) 사용자 행동 이벤트/메트릭 고정

### 이벤트 정의
- `u1_view_summary`: 사용자 요약 화면 진입
- `u1_view_performance`: 성과 요약/지표 상세 진입
- `u2_view_history`: 성과 히스토리 조회
- `u2_compare_period`: 기간 비교 조회
- `u2_metric_detail`: 지표 상세 조회
- `u2_bookmark_add`: 북마크 추가
- `u2_bookmark_remove`: 북마크 삭제

### 메트릭 정의(산식)
- 이탈률: `bounced_sessions / total_sessions`
  - 기준: 요약/성과 화면 진입 후 10초 내 추가 액션 없이 종료
- 재시도율: `retry_requests / total_requests`
  - 기준: 동일 사용자·동일 API에 60초 내 2회 이상 요청
- 실패율: `failed_requests / total_requests`
  - 기준: 4xx/5xx 포함, 분모는 전체 요청

### 로그 스키마 고정(공통 필드)
- `event_name` (string)
- `user_id` (string, hash)
- `portfolio_id` (string)
- `request_id` (string)
- `status` (string: success|failure)
- `error_code` (string, optional)
- `latency_ms` (number)
- `timestamp` (ISO8601)

## 2) 알림 임계치 설정

### SLA/오류율
- API 95p 응답시간 > 1.5s (5분 윈도우) → 경고
- API 99p 응답시간 > 3.0s (5분 윈도우) → 긴급
- 오류율(5xx) > 1.0% (5분 윈도우) → 경고
- 오류율(5xx) > 2.0% (5분 윈도우) → 긴급
- 4xx 오류율 > 10% (15분 윈도우) → 경고(클라이언트 품질 점검)

### 지연/타임아웃
- 외부 의존성 타임아웃 > 0.5% (5분 윈도우) → 경고
- 외부 의존성 타임아웃 > 1.0% (5분 윈도우) → 긴급

### 알림 채널
- 경고: Slack #ops-alerts
- 긴급: Slack #ops-alerts + 온콜 SMS

## 3) 롤백 및 핫픽스 절차

### 롤백 트리거
- 긴급 알림 2회 연속 발생
- 핵심 API 실패율(5xx) 2% 이상 10분 지속
- 사용자 결함(데이터 누락/왜곡) 신고 3건 이상

### 롤백 단계
1. 문제 버전 확인 및 배포 중지
2. 이전 안정 버전으로 즉시 롤백
3. 모니터링에서 오류율/지연 정상화 확인
4. 롤백 사유/영향 범위 기록

### 핫픽스 절차
1. 영향 범위 최소화한 패치 브랜치 생성
2. 핵심 회귀 테스트 및 U-1/U-2 통합 테스트 실행
3. 릴리즈 노트/변경사항 기록
4. 배포 후 1시간 집중 모니터링

## 운영 체크리스트
- 이벤트/메트릭 정의 변경 시 문서 갱신
- 임계치 변경 시 알림 룰 및 이유 기록
- 롤백/핫픽스 이력은 월간 리포트에 포함

## 참고 문서
- `docs/changelogs/20260118_u2_release_notes.md`
