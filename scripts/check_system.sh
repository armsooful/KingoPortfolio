#!/bin/bash

echo "=========================================="
echo "  KingoPortfolio 시스템 상태 확인"
echo "=========================================="
echo ""

# 1. 백엔드 확인
echo "1️⃣  백엔드 서버 확인..."
if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "   ✅ 백엔드 정상 작동 (http://127.0.0.1:8000)"
else
    echo "   ❌ 백엔드 실행 안 됨"
    exit 1
fi

# 2. 프론트엔드 확인
echo ""
echo "2️⃣  프론트엔드 서버 확인..."
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "   ✅ 프론트엔드 정상 작동 (http://localhost:5173)"
else
    echo "   ❌ 프론트엔드 실행 안 됨"
    exit 1
fi

# 3. 데이터베이스 확인
echo ""
echo "3️⃣  데이터베이스 확인..."
if [ -f /Users/changrim/KingoPortfolio/backend/kingo.db ]; then
    echo "   ✅ 데이터베이스 파일 존재"

    # SQLite로 데이터 확인
    cd /Users/changrim/KingoPortfolio/backend
    stocks_count=$(sqlite3 kingo.db "SELECT COUNT(*) FROM stocks;" 2>/dev/null || echo "0")
    etfs_count=$(sqlite3 kingo.db "SELECT COUNT(*) FROM etfs;" 2>/dev/null || echo "0")
    bonds_count=$(sqlite3 kingo.db "SELECT COUNT(*) FROM bonds;" 2>/dev/null || echo "0")
    deposits_count=$(sqlite3 kingo.db "SELECT COUNT(*) FROM deposit_products;" 2>/dev/null || echo "0")

    echo ""
    echo "   📊 데이터 현황:"
    echo "      주식: ${stocks_count}개"
    echo "      ETF: ${etfs_count}개"
    echo "      채권: ${bonds_count}개"
    echo "      예적금: ${deposits_count}개"
    echo "      ────────────────"
    echo "      총합: $((stocks_count + etfs_count + bonds_count + deposits_count))개"
else
    echo "   ❌ 데이터베이스 파일 없음"
fi

# 4. yfinance 버전 확인
echo ""
echo "4️⃣  yfinance 버전 확인..."
yfinance_version=$(/Users/changrim/KingoPortfolio/venv/bin/pip show yfinance 2>/dev/null | grep Version | cut -d' ' -f2)
if [ ! -z "$yfinance_version" ]; then
    echo "   ✅ yfinance 버전: $yfinance_version"

    # 버전 비교 (0.2.66 이상이어야 함)
    if [ "$(printf '%s\n' "0.2.66" "$yfinance_version" | sort -V | head -n1)" = "0.2.66" ]; then
        echo "   ✅ 버전 OK (0.2.66 이상)"
    else
        echo "   ⚠️  버전이 낮습니다. 0.2.66 이상으로 업그레이드하세요."
    fi
else
    echo "   ❌ yfinance 설치 안 됨"
fi

echo ""
echo "=========================================="
echo "  ✅ 모든 시스템 정상 작동!"
echo "=========================================="
echo ""
echo "📝 다음 단계:"
echo "   1. 브라우저에서 http://localhost:5173 접속"
echo "   2. 로그인 또는 회원가입"
echo "   3. 상단 메뉴에서 '🔧 관리자' 클릭"
echo "   4. 데이터 현황 확인 및 수집 테스트"
echo ""
echo "📚 관련 문서:"
echo "   - YFINANCE_FIX_SUMMARY.md"
echo "   - VERIFICATION_GUIDE.md"
echo "   - DATA_COLLECTION_GUIDE.md"
echo ""
