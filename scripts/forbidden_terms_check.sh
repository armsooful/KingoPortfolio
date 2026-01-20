#!/bin/bash
#
# 금지어 검사 스크립트
# Foresto Compass 서비스의 금지어 유입을 방지합니다.
#
# 사용법:
#   ./scripts/forbidden_terms_check.sh [검사 대상 디렉토리]
#
# 반환값:
#   0: 금지어 없음 (통과)
#   1: 금지어 발견 (실패)
#

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 스크립트 디렉토리 기준으로 프로젝트 루트 찾기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 검사 대상 디렉토리 (기본값: frontend/src, backend/app)
TARGET_DIRS="${1:-$PROJECT_ROOT/frontend/src $PROJECT_ROOT/backend/app}"

# 금지어 목록 (단일 소스)
# docs/compliance/20260114_forbidden_terms_list.md와 동기화 필요
FORBIDDEN_TERMS=(
    # 추천/권유 관련 (HIGH)
    "추천"
    "권유"
    "투자하세요"
    "사세요"
    "파세요"

    # 수익 보장 관련 (HIGH)
    "보장"
    "확실한 수익"
    "손실 없음"
    "무위험"
    "안전한 투자"

    # 예측/전망 관련 (MEDIUM)
    "기대수익률"
    "예상수익"
    "기대"
    "전망"
    "향후"
    "가능성"
    "유효할"

    # 평가/비교/우열 관련 (MEDIUM)
    "최적"
    "우수"
    "효율"
    "승자"
    "Top"
    "랭킹"
    "더 낫다"
    "불리하다"
    "안정적"
    "공격적"

    # 전문가/자문 관련 (HIGH)
    "전문가 조언"
    "투자 자문"
    "투자 상담"
)

# 예외 패턴 (이 패턴이 포함된 라인은 무시)
EXCEPTION_PATTERNS=(
    # 부정문/제거 문맥
    "아닙니다"
    "않습니다"
    "제공하지"
    "아님"
    "제거"

    # 문서/테스트
    "forbidden_terms"
    "금지어"
    "test"
    "Test"
    "spec"
    "Spec"
    ".test."
    ".spec."
    "__tests__"
    "disclaimer"
    "Disclaimer"

    # 금융 용어 (허용)
    "무위험 수익률"
    "무위험 자산"
    "risk_free"
    "risk-free"

    # 바이너리 파일
    "Binary file"
    ".pyc"

    # 부정문 추가 예외
    "보장은 없습니다"
)

# 제외할 파일/디렉토리 패턴
EXCLUDE_PATTERNS=(
    "*.test.*"
    "*.spec.*"
    "__tests__"
    "node_modules"
    ".git"
    "dist"
    "build"
    "*.md"
    "forbidden_terms_check.sh"
    "banned_words_v1.txt"
    "guard.py"
    "golden_report_sample.json"
)

echo -e "${YELLOW}=== Foresto Compass 금지어 검사 ===${NC}"
echo "검사 대상: $TARGET_DIRS"
echo ""

FOUND_ISSUES=0
TOTAL_MATCHES=0

# 각 금지어에 대해 검사
for term in "${FORBIDDEN_TERMS[@]}"; do
    # grep 옵션 구성
    GREP_EXCLUDES=""
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        GREP_EXCLUDES="$GREP_EXCLUDES --exclude=$pattern --exclude-dir=$pattern"
    done

    # 금지어 검색 (재귀적으로)
    MATCHES=$(grep -rn $GREP_EXCLUDES "$term" $TARGET_DIRS 2>/dev/null || true)

    if [ -n "$MATCHES" ]; then
        # 예외 패턴 필터링
        FILTERED_MATCHES=""
        while IFS= read -r line; do
            SKIP=false
            for exception in "${EXCEPTION_PATTERNS[@]}"; do
                if echo "$line" | grep -q "$exception"; then
                    SKIP=true
                    break
                fi
            done
            if [ "$SKIP" = false ]; then
                content="${line#*:}"
                content="${content#*:}"
                content="$(echo "$content" | sed -e 's/^[[:space:]]*//')"
                if [[ "$content" =~ ^(#|//|\\*|-) ]]; then
                    SKIP=true
                fi
            fi
            if [ "$SKIP" = false ]; then
                FILTERED_MATCHES="$FILTERED_MATCHES$line"$'\n'
            fi
        done <<< "$MATCHES"

        # 필터링 후 매치가 있으면 출력
        if [ -n "$(echo "$FILTERED_MATCHES" | tr -d '[:space:]')" ]; then
            echo -e "${RED}[금지어 발견] '$term'${NC}"
            echo "$FILTERED_MATCHES" | head -10
            MATCH_COUNT=$(echo "$FILTERED_MATCHES" | grep -c "$term" 2>/dev/null || echo "0")
            if [ "$MATCH_COUNT" -gt 10 ]; then
                echo "  ... 그 외 $((MATCH_COUNT - 10))건"
            fi
            echo ""
            FOUND_ISSUES=$((FOUND_ISSUES + 1))
            TOTAL_MATCHES=$((TOTAL_MATCHES + MATCH_COUNT))
        fi
    fi
done

echo "=== 검사 완료 ==="

if [ $FOUND_ISSUES -gt 0 ]; then
    echo -e "${RED}[실패] $FOUND_ISSUES종류의 금지어, 총 $TOTAL_MATCHES건 발견${NC}"
    echo ""
    echo "수정 방법:"
    echo "  1. docs/compliance/20260114_forbidden_terms_list.md에서 대체 표현 확인"
    echo "  2. 금지어를 허용된 표현으로 변경"
    echo "  3. 면책 조항(Disclaimer)에서 사용하는 경우 예외 처리됨"
    echo ""
    exit 1
else
    echo -e "${GREEN}[통과] 금지어가 발견되지 않았습니다.${NC}"
    exit 0
fi
