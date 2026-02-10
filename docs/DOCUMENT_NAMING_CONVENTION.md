# 문서 네이밍 규칙 (Document Naming Convention)

이 문서는 `docs/` 폴더 내 문서들의 네이밍 규칙을 정의합니다.

## 기본 형식 (날짜 접두어 제외)

```
[scope_][topic]_[type].md
```

| 구성요소 | 필수 | 설명 | 예시 |
|---------|------|------|------|
| `scope` | ❌ | Phase 또는 Epic 범위 | `phase7`, `c1`, `u2` |
| `topic` | ✅ | 문서 주제 | `implementation`, `api_design` |
| `type` | ❌ | 문서 유형 접미사 | `_tickets`, `_report`, `_spec` |

**규칙**
- 파일명은 **영문 소문자**와 **snake_case**만 사용
- 날짜(`YYYYMMDD`, `YYYY-MM-DD`) 접두어/접미어는 사용하지 않음 (Git 히스토리로 관리)
- 한글 파일명 금지 (호환성 문제)

## 링크 관리 규칙

- 문서 내 링크는 **상대경로 기준**으로 작성
- 동일 문서를 여러 위치에서 참조할 경우 파일명만 변경하지 말고 링크도 함께 갱신
- 날짜가 포함된 파일명/링크는 사용하지 않음 (접두어/접미어 모두 금지)

## 인덱스 설명 규칙 (documentation_index.md)

아래 규칙으로 `docs/documentation_index.md`의 설명(2열)을 자동 보정합니다.

### Phase 섹션
- `completion_report` → 완료 보고서
- `completion_statement` → 완료 진술서
- `implementation_tickets` → 구현 티켓
- `implementation_plan` → 구현 계획
- `implementation_summary` → 구현 요약
- `backlog_tickets` → 백로그 티켓
- `backlog` → 백로그
- `objectives` → 목표
- `specification` 또는 `_spec` → 명세서
- `design` → 설계
- `checklist` → 체크리스트
- `runbook` → 운영 Runbook
- `guide` → 가이드
- `schema` → 스키마
- `ddl` → DDL
- `api` → API
- `ux` → UX
- `ui` → UI
- `report` → 보고서
- 그 외 → Phase 문서

### Architecture
- `spec` → 명세서
- `design`/`architecture` → 설계
- 그 외 → 아키텍처

### Development
- `guide`/`manual` → 가이드
- `setup` → 설정
- `snapshot` → 스냅샷
- 그 외 → 개발 문서

### Compliance
- `policy` → 정책
- `terminology`/`terms` → 용어
- `disclaimer` → 면책
- 그 외 → 준수 문서

### Deployment
- `migration` → 마이그레이션
- `setup`/`environment` → 환경 설정
- `forwarding` → 포워딩
- 그 외 → 배포 문서

### Changelogs
- `release_notes` → 릴리즈 노트
- `changelog` → 변경 이력
- `progress` → 진행 상황
- `summary` → 요약
- 그 외 → 변경 기록

### Alpha Test
- `plan` → 계획
- `log` → 로그
- `issue` → 이슈 목록
- 그 외 → 테스트 문서

### Manuals
- 기본값 `매뉴얼`

### Reports
- `evidence` → 증적
- `baseline` → 기준선
- 그 외 → 보고서

### 예외 매핑 (파일명 고정)
- `documentation_index.md` → 문서 인덱스
- `DOCUMENT_NAMING_CONVENTION.md` → 네이밍 규칙
- `DATABASE_CONNECTION.md` / `database_connection.md` → DB 연결 가이드
- `feature_overview.md` → 기능 개요
- `table_catalog.md` → 테이블 카탈로그
- `manuals_index.md` → 매뉴얼 인덱스
- `link_fix_report.md` → 링크 점검 리포트

## 권장 형식

```
<scope>_<topic>_<type>.md
phase<phase><sub>_<topic>_<type>.md
phase3c_epic_c2_data_quality_design.md
```

**정렬/검색을 위한 순서 권장**
1. `scope` (phase/epic 등)
1. `topic`
1. `type` (보고서/티켓/명세 등)

## 폴더 구조 및 배치 기준

```
docs/
├── architecture/      # 시스템 아키텍처 설계 문서
├── changelogs/        # 변경 이력 로그
├── compliance/        # 규정 준수, 법적 검토 문서
├── deployment/        # 배포 가이드 및 설정
├── development/       # 개발 가이드, 백로그
├── manuals/           # 운영 매뉴얼, 트러블슈팅
├── phase{N}/          # Phase별 스펙, 설계, 티켓 (phase1 ~ phase9)
│   ├── specs/         # 스펙 문서
│   ├── guides/        # 가이드 문서
│   ├── checklists/    # 체크리스트
│   └── evidence/      # 검증 증적
├── reports/           # 완료/진행 보고서
└── legacy/            # 더 이상 사용하지 않는 구 문서
```

## Scope 식별자

### Phase 식별자
```
phase{N}{sub}   예: phase3a, phase7, phase9
```

### Epic 식별자 (Phase 3 이후)
| 접두사 | 의미 | 예시 |
|--------|------|------|
| `c{N}` | Core Epic (인프라/백엔드) | `c1`, `c2`, `c3`, `c4` |
| `u{N}` | User Epic (사용자 기능) | `u1`, `u2`, `u3` |

## 문서 유형 접미사

| 접미사 | 용도 | 예시 |
|--------|------|------|
| `_spec` | 기능/API 스펙 | `phase7_spec.md` |
| `_design` | 설계 문서 | `u2_bookmark_design.md` |
| `_detailed_design` | 상세 설계 | `c1_operations_detailed_design.md` |
| `_tickets` | 구현 티켓/백로그 | `c1_implementation_tickets.md` |
| `_report` | 보고서 | `project_progress_report.md` |
| `_completion_report` | 완료 보고서 | `phase3b_completion_report.md` |
| `_guide` | 가이드 문서 | `database_setup_guide.md` |
| `_manual` | 운영 매뉴얼 | `developer_manual.md` |
| `_checklist` | 체크리스트 | `c4_validation_checklist.md` |
| `_ddl` / `_schema` | DB 스키마 | `c2_ddl_schema.md` |
| `_api` | API 설계 | `u1_api_design.md` |
| `_policy` | 정책 문서 | `rate_limit_policy.md` |
| `_index` | 인덱스/목차 | `phase3_index.md` |

## 섹션별 예시

- Phase 문서: `phase3c_go_live_readiness_checklist.md`
- Epic 문서: `phase3c_epic_c2_data_quality_lineage_reproducibility_detailed_design.md`
- Phase 공통 티켓: `phase2_backlog.md`
- 운영/가이드: `phase4_operator_guide.md`, `database_setup_guide.md`
- 보고서: `project_progress_report.md`, `phase3b_completion_report.md`
- 체크리스트: `phase6_exit_criteria.md`, `c4_validation_checklist.md`

## 버전 관리
규칙에 따라 문서를 정리해줘
동일 주제의 문서가 메이저 변경되는 경우 `_v{N}` 접미사 사용:

```
disclaimer_v1.md → disclaimer_v2.md → disclaimer_v3.md
```

일반적인 변경 히스토리는 Git으로 관리합니다.

## 변환 예시

```
❌ phase_3_c_user_epic_u_1_사용자기능_검증체크리스트.md
✅ phase3c_u1_user_feature_validation_checklist.md

❌ Phase 9 개요.md
✅ phase9_overview.md

❌ 20260118_c1_implementation_tickets.md
✅ c1_implementation_tickets.md
```
