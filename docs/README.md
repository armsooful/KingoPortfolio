# Foresto Compass 문서 디렉토리

> 마지막 정리: 2026-02-15

## 구조

```
docs/
├── PRD.md                          # 제품 요구사항 정의서
├── ui-theme-guide.md               # CSS 테마 시스템 가이드 (다크/라이트 모드)
│
├── strategy/                       # 사업 전략 & 경쟁 분석
│   ├── foresto-business-consulting-report.md/pdf  # 사업 컨설팅 보고서
│   ├── foresto-competitive-strategy-report.md     # 경쟁사 분석 & 차별화 전략
│   ├── compass-score-project-report.md            # Compass Score 구현 보고서
│   ├── investor_partner_deck.md                   # 투자자/파트너 소개 자료
│   ├── stockmatrix-indicator-analysis.md          # StockMatrix 30개 지표 분석
│   └── stockmatrix-email-analysis-report.md       # StockMatrix 이메일 분석
│
├── compliance/                     # 규제 준수 (자본시장법)
│   ├── forbidden_terms_list.md     # 금지 용어 목록
│   ├── terminology_guide.md        # 용어 변환 가이드
│   ├── disclaimer_terminology_summary.md  # 면책 조항 요약
│   ├── survey_legal_review.md      # 설문 법률 검토
│   └── forbidden_terms_scan_log.md # 금지 용어 스캔 로그
│
├── deployment/                     # 배포 가이드
│   ├── render_migration_guide.md   # Render 백엔드 배포
│   ├── vercel_environment_setup.md # Vercel 프론트엔드 배포
│   └── cloudflare_forwarding_manual.md  # Cloudflare 설정
│
├── architecture/                   # 시스템 설계
│   ├── system_overview.md          # 시스템 아키텍처 개요
│   ├── technical_specification.md  # 기술 스펙
│   ├── portfolio_simulation_algorithm.md  # 포트폴리오 시뮬레이션 알고리즘
│   ├── bond_data_integration_design.md    # 채권 데이터 통합 설계
│   └── regulatory_compliance.md    # 규제 준수 아키텍처
│
├── guides/                         # 개발자 & 운영 가이드
│   ├── quick_start.md              # 빠른 시작 가이드
│   ├── database_guide.md           # 데이터베이스 가이드
│   ├── database_setup_guide.md     # DB 설정 가이드
│   ├── data_collection_guide.md    # 데이터 수집 가이드
│   ├── stock_bond_load_guide.md    # 주식/채권 데이터 로딩
│   ├── test_guide.md               # 테스트 가이드
│   ├── admin_troubleshooting.md    # 관리자 트러블슈팅
│   ├── claude_api_setup.md         # Claude API 설정
│   ├── alpha_vantage_guide.md      # Alpha Vantage 가이드
│   ├── finlife_open_api.md         # FSS Finlife API 레퍼런스
│   ├── fss_finlife_api_implementation_guide.md  # FSS 구현 가이드
│   ├── bonds_consolidation_impl.md # 채권 통합 구현
│   ├── batch_upsert_optimization.md # 배치 Upsert 최적화
│   ├── progress_monitoring_guide.md # 진행률 모니터링
│   ├── verification_guide.md       # 검증 가이드
│   ├── login_debug_guide.md        # 로그인 디버깅
│   ├── table_consolidation_design.md # 테이블 통합 설계
│   ├── table_catalog.md            # 테이블 카탈로그
│   ├── data_quality_policy.md      # 데이터 품질 정책
│   └── admin_data_page_api_map.md  # 관리자 페이지 API 맵
│
├── ui-mockup/                      # UI 목업
│   └── dashboard-redesign.html     # 대시보드 리디자인 목업
│
└── archive/                        # 아카이브 (개발 이력)
    ├── phase1~11/                  # 페이즈별 개발 문서 (168파일)
    ├── changelogs/                 # 릴리즈 노트
    ├── reports/                    # 완료 보고서
    ├── development/                # 개발 과정 문서
    ├── alpha_test/                 # 알파 테스트
    └── screenshots/                # 스크린샷
```

## 핵심 문서 바로가기

| 용도 | 문서 |
|------|------|
| 프로젝트 전체 이해 | [PRD.md](PRD.md) + 루트의 `CLAUDE.md` |
| 사업 전략 | [strategy/foresto-business-consulting-report.md](strategy/foresto-business-consulting-report.md) |
| 경쟁 분석 | [strategy/foresto-competitive-strategy-report.md](strategy/foresto-competitive-strategy-report.md) |
| 테마 시스템 | [ui-theme-guide.md](ui-theme-guide.md) |
| 규제 준수 | [compliance/](compliance/) |
| 빠른 시작 | [guides/quick_start.md](guides/quick_start.md) |
| 배포 | [deployment/](deployment/) |

## 정리 원칙

- **활성 문서 (44개)**: 현재 참조가 필요한 문서만 루트 레벨에 유지
- **아카이브 (221개)**: 개발 이력으로서 가치가 있으나 일상적으로 참조하지 않는 문서
- **삭제 기준**: 10줄 미만의 극소 파일, 완전 중복, CLAUDE.md가 대체한 메타 문서
