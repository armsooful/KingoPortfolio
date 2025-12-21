#!/bin/bash

echo "=========================================="
echo "  🚀 KingoPortfolio 서버 시작"
echo "=========================================="
echo ""

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. 백엔드 시작
echo -e "${BLUE}1️⃣  백엔드 서버 시작 중...${NC}"
cd /Users/changrim/KingoPortfolio/backend

# 기존 백엔드 프로세스 종료
pkill -f "uvicorn app.main:app" 2>/dev/null
sleep 1

# 백엔드 시작 (백그라운드)
/Users/changrim/KingoPortfolio/venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

# 백엔드 시작 대기
echo "   ⏳ 백엔드 로딩 중..."
sleep 5

# 백엔드 상태 확인
if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ 백엔드 정상 작동 (http://127.0.0.1:8000)${NC}"
    echo "   PID: $BACKEND_PID"
else
    echo -e "   ${RED}❌ 백엔드 시작 실패${NC}"
    echo "   로그: tail -f /tmp/backend.log"
    exit 1
fi

echo ""

# 2. 프론트엔드 시작 안내
echo -e "${BLUE}2️⃣  프론트엔드 서버 시작${NC}"
echo ""
echo -e "${YELLOW}다음 명령어를 새 터미널에서 실행하세요:${NC}"
echo ""
echo "   cd /Users/changrim/KingoPortfolio/frontend"
echo "   npm run dev"
echo ""
echo -e "${YELLOW}또는 이 스크립트를 Ctrl+C로 종료하지 말고,${NC}"
echo -e "${YELLOW}새 터미널을 열어서 위 명령어를 실행하세요.${NC}"
echo ""

# 3. 상태 모니터링
echo "=========================================="
echo -e "${GREEN}  ✅ 백엔드 서버 실행 중${NC}"
echo "=========================================="
echo ""
echo "📊 서버 정보:"
echo "   • 백엔드: http://127.0.0.1:8000"
echo "   • 프론트엔드: http://localhost:5173 (수동 시작 필요)"
echo "   • 로그: /tmp/backend.log"
echo ""
echo "📝 다음 단계:"
echo "   1. 새 터미널에서 프론트엔드 시작 (위 명령어)"
echo "   2. 브라우저에서 http://localhost:5173 접속"
echo "   3. 로그인 후 '🔧 관리자' 클릭"
echo ""
echo "🛑 서버 종료:"
echo "   Ctrl+C (이 터미널에서)"
echo ""
echo "=========================================="
echo ""

# 백엔드 로그 실시간 표시
echo -e "${BLUE}📋 백엔드 로그 (실시간):${NC}"
echo "=========================================="
tail -f /tmp/backend.log
