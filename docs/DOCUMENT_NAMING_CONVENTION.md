# 문서 네이밍 규칙 (Document Naming Convention)

이 문서는 `docs/` 폴더 내 문서들의 네이밍 규칙을 정의합니다.

## 기본 형식

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
- 날짜는 파일명에 포함하지 않음 (Git 히스토리로 관리)
- 한글 파일명 금지 (호환성 문제)

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

## 버전 관리

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
