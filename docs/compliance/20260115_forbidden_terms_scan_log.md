# 금지어 스캔 결과 로그
최초작성일자: 2026-01-15
최종수정일자: 2026-01-20

## 마지막 검사 정보

| 항목 | 값 |
|------|-----|
| **검사 시점** | 2026-01-20 (Phase 6 금지어 v2 반영) |
| **검사 결과** | ✅ 통과 |
| **발견된 금지어** | 0건 |
| **검사 대상** | `frontend/src`, `backend/app` |

---

## 검사 실행 로그

```
=== Foresto Compass 금지어 검사 ===
검사 대상: /Users/changrim/KingoPortfolio/frontend/src /Users/changrim/KingoPortfolio/backend/app

=== 검사 완료 ===
[통과] 금지어가 발견되지 않았습니다.
```

---

## 금지어 목록 (검사 대상)

### HIGH 위험도 (즉시 수정 필요)
| 카테고리 | 금지어 |
|----------|--------|
| 추천/권유 | 추천, 권유, 투자하세요, 사세요, 파세요 |
| 수익 보장 | 보장, 확실한 수익, 손실 없음, 무위험, 안전한 투자 |
| 전문가/자문 | 전문가 조언, 투자 자문, 투자 상담 |

### MEDIUM 위험도 (수정 권장)
| 카테고리 | 금지어 |
|----------|--------|
| 예측/전망 | 기대수익률, 예상수익, 기대, 전망, 향후, 가능성, 유효할 |
| 평가/비교/우열 | 최적, 우수, 효율, 승자, Top, 랭킹, 더 낫다, 불리하다, 안정적, 공격적 |

---

## 예외 처리 패턴

다음 패턴이 포함된 라인은 자동 필터링됨:

### 부정문/제거 문맥
- `아닙니다`, `않습니다`, `제공하지`, `아님`, `제거`

### 문서/테스트 파일
- `forbidden_terms`, `금지어`, `test`, `Test`, `spec`, `Spec`
- `.test.`, `.spec.`, `__tests__`, `disclaimer`, `Disclaimer`

### 금융 용어 (허용)
- `무위험 수익률`, `무위험 자산`, `risk_free`, `risk-free`

### 바이너리/기타
- `Binary file`, `.pyc`

---

## 제외 디렉토리/파일

- `*.test.*`, `*.spec.*`, `__tests__`
- `node_modules`, `.git`, `dist`, `build`
- `*.md`, `forbidden_terms_check.sh`

---

## Phase 0 수정 이력

### 수정된 금지어 (2026-01-15)

| 파일 | 변경 전 | 변경 후 |
|------|---------|---------|
| `export.py:265-266` | 추천 자산 배분 | 학습 시나리오 자산 배분 |
| `securities.py:174` | 상품 추천 규칙 | 상품 매칭 규칙 |
| `securities.py:184` | 추천 이유 | 매칭 사유 |
| `admin_portfolio.py:204` | 추천될 가능성이 높은 | 매칭 점수가 높은 |
| `admin.py:1223` | 투자 추천 포함 | 가치 평가 참고치 포함 |
| `portfolio_engine.py:825,851` | 포트폴리오 추천 결과 | 포트폴리오 시뮬레이션 결과 |
| `claude_service.py:123` | 추천 자산 배분 | 학습용 예시 자산 배분 |
| `claude_service.py:187` | 추천합니다 | 학습해보세요 |
| `qualitative_analyzer.py:267` | 관망 추천 | 관망 고려 |

### 예외 패턴 추가
- `제거`: 부정문/제거 문맥 예외 처리 (valuation.py:670 대응)

### 스캔 로그 업데이트 (2026-01-20)
- Phase 6 금지어 v2 반영, frontend/src + backend/app 스캔 통과

---

## 검사 스크립트 사용법

```bash
# 전체 검사
./scripts/forbidden_terms_check.sh

# 특정 디렉토리만 검사
./scripts/forbidden_terms_check.sh frontend/src

# CI/pre-commit 연동
./scripts/forbidden_terms_check.sh && echo "통과" || exit 1
```

---

## pre-commit 훅 설정 (선택)

```bash
# .git/hooks/pre-commit 파일 생성
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
./scripts/forbidden_terms_check.sh
EOF
chmod +x .git/hooks/pre-commit
```

---

## 관련 문서

- [금지어 목록 상세](./20260114_forbidden_terms_list.md)
- [Phase 0 변경 로그](../changelogs/20260115_changelog_phase0.md)

---

**검증 담당**: Claude Code
**마지막 업데이트**: 2026-01-20
