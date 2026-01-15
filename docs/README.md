# Foresto Compass 문서 목록

**최종 업데이트**: 2026-01-15

---

## 폴더 구조

```
docs/
├── architecture/     # 설계 및 아키텍처 문서
├── changelogs/       # 변경 이력 및 릴리스 노트
├── compliance/       # 법적 준수 및 면책 조항
├── deployment/       # 배포 및 인프라 가이드
├── development/      # 개발 가이드 및 백로그
├── legacy/           # 과거 문서 아카이브
├── manuals/          # 운영 매뉴얼
└── phase1/           # Phase 1 관련 문서
```

---

## Phase 1 (시뮬레이션 인프라)

| 파일명 | 설명 |
|--------|------|
| [20260115_phase1_completion_report.md](phase1/20260115_phase1_completion_report.md) | Phase 1 완료 보고서 |
| [20260115_phase1_backlog_tickets.md](phase1/20260115_phase1_backlog_tickets.md) | Phase 1 작업 티켓 백로그 |
| [20260115_phase1_postgresql_ddl_with_partitioning.sql](phase1/20260115_phase1_postgresql_ddl_with_partitioning.sql) | PostgreSQL DDL (파티셔닝 포함) |

---

## Architecture (설계)

| 파일명 | 설명 |
|--------|------|
| [20260115_phase0_implementation_scope.md](architecture/20260115_phase0_implementation_scope.md) | Phase 0 현재 구현 코드 범위 |
| [20260114_code_analysis_consistency_guide.md](architecture/20260114_code_analysis_consistency_guide.md) | 코드 분석 정합성 가이드 |
| [20260110_portfolio_simulation_algorithm.md](architecture/20260110_portfolio_simulation_algorithm.md) | 포트폴리오 시뮬레이션 알고리즘 |
| [20251221_project_structure.md](architecture/20251221_project_structure.md) | 프로젝트 구조 |

---

## Compliance (법적 준수)

| 파일명 | 설명 |
|--------|------|
| [20260115_forbidden_terms_scan_log.md](compliance/20260115_forbidden_terms_scan_log.md) | 금지 용어 스캔 로그 |
| [20260114_forbidden_terms_list.md](compliance/20260114_forbidden_terms_list.md) | 금지 용어 목록 |
| [20260110_survey_legal_review.md](compliance/20260110_survey_legal_review.md) | 설문 문항 법적 검토 수정안 |
| [20260105_terminology_guide.md](compliance/20260105_terminology_guide.md) | 용어 가이드 |
| [20260105_disclaimer_terminology_summary.md](compliance/20260105_disclaimer_terminology_summary.md) | 면책 조항 및 용어 요약 |

---

## Deployment (배포)

| 파일명 | 설명 |
|--------|------|
| [20260112_vercel_environment_setup.md](deployment/20260112_vercel_environment_setup.md) | Vercel 환경 변수 설정 가이드 |
| [20260112_render_migration_guide.md](deployment/20260112_render_migration_guide.md) | Render 마이그레이션 가이드 |
| [20260110_cloudflare_forwarding_manual.md](deployment/20260110_cloudflare_forwarding_manual.md) | Cloudflare 포워딩 매뉴얼 |

---

## Development (개발)

| 파일명 | 설명 |
|--------|------|
| [20260115_database_setup_guide.md](development/20260115_database_setup_guide.md) | 데이터베이스 설정 가이드 |
| [20260115_data_quality_policy.md](development/20260115_data_quality_policy.md) | 데이터 품질 정책 |
| [20260115_api_snapshot_simulation.md](development/20260115_api_snapshot_simulation.md) | API 스냅샷 시뮬레이션 |
| [20260114_detailed_backlog_tickets.md](development/20260114_detailed_backlog_tickets.md) | 상세 백로그 티켓 |
| [20260113_developer_manual.md](development/20260113_developer_manual.md) | 개발자 매뉴얼 |
| [20251229_future_roadmap.md](development/20251229_future_roadmap.md) | 향후 로드맵 |

---

## Changelogs (변경 이력)

| 파일명 | 설명 |
|--------|------|
| [20260115_changelog_phase0.md](changelogs/20260115_changelog_phase0.md) | Phase 0 변경 이력 |
| [20260112_changelog.md](changelogs/20260112_changelog.md) | 2026-01-12 변경 이력 |
| [20260107_development_progress.md](changelogs/20260107_development_progress.md) | 개발 진행 상황 |
| [20260105_implementation_summary.md](changelogs/20260105_implementation_summary.md) | 구현 요약 |
| [20260105_pdf_report_implementation.md](changelogs/20260105_pdf_report_implementation.md) | PDF 리포트 구현 요약 |

---

## Manuals (운영 매뉴얼)

| 파일명 | 설명 |
|--------|------|
| [QUICK_START.md](manuals/QUICK_START.md) | 빠른 시작 가이드 |
| [DATABASE_GUIDE.md](manuals/DATABASE_GUIDE.md) | 데이터베이스 가이드 |
| [DATABASE_RESET_GUIDE.md](manuals/DATABASE_RESET_GUIDE.md) | 데이터베이스 초기화 가이드 |
| [CLAUDE_API_SETUP.md](manuals/CLAUDE_API_SETUP.md) | Claude API 설정 |
| [ALPHA_VANTAGE_GUIDE.md](manuals/ALPHA_VANTAGE_GUIDE.md) | Alpha Vantage 가이드 |
| [DATA_COLLECTION_GUIDE.md](manuals/DATA_COLLECTION_GUIDE.md) | 데이터 수집 가이드 |
| [TEST_GUIDE.md](manuals/TEST_GUIDE.md) | 테스트 가이드 |
| [VERIFICATION_GUIDE.md](manuals/VERIFICATION_GUIDE.md) | 검증 가이드 |
| [LOGIN_DEBUG_GUIDE.md](manuals/LOGIN_DEBUG_GUIDE.md) | 로그인 디버그 가이드 |
| [LOGIN_FIX_SUMMARY.md](manuals/LOGIN_FIX_SUMMARY.md) | 로그인 수정 요약 |
| [YFINANCE_FIX_SUMMARY.md](manuals/YFINANCE_FIX_SUMMARY.md) | yfinance 수정 요약 |
| [PROGRESS_MONITORING_GUIDE.md](manuals/PROGRESS_MONITORING_GUIDE.md) | 진행 모니터링 가이드 |
| [ADMIN_TROUBLESHOOTING.md](manuals/ADMIN_TROUBLESHOOTING.md) | 관리자 문제 해결 |

---

## Legacy (과거 문서)

| 파일명 | 설명 |
|--------|------|
| [20260103_project_report.md](legacy/20260103_project_report.md) | 프로젝트 보고서 |
| [20251216_project_plan.md](legacy/20251216_project_plan.md) | 프로젝트 계획 |
| [20251216_investment_diagnosis_spec.md](legacy/20251216_investment_diagnosis_spec.md) | 투자 진단 명세 |
| [20251216_progress_status.md](legacy/20251216_progress_status.md) | 진행 상황 |
| [20251214_summary.md](legacy/20251214_summary.md) | 2025-12-14 요약 |
| [20251213_summary.md](legacy/20251213_summary.md) | 2025-12-13 요약 |
| [20251217/](legacy/20251217/) | 2025-12-17 문서 아카이브 |

---

## 파일명 규칙

```
YYYYMMDD_descriptive_name.md
```

- **YYYYMMDD**: 작성일 또는 최종 수정일
- **descriptive_name**: 문서 내용을 유추할 수 있는 영문 소문자 이름 (단어는 underscore로 구분)

---

## 관련 링크

- [README.md](../README.md) - 프로젝트 메인 README
- [scripts/](../scripts/) - 운영 스크립트
