#!/usr/bin/env python3
"""
KingoPortfolio API 전체 테스트 스크립트
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

def print_test(test_name, success, response=None):
    """테스트 결과 출력"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"\n{status} | {test_name}")
    if response:
        print(f"   Status: {response.status_code}")
        try:
            print(f"   Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        except:
            print(f"   Response: {response.text}")

def test_health():
    """Health Check 테스트"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        success = response.status_code == 200
        print_test("Health Check", success, response)
        return success
    except Exception as e:
        print_test("Health Check", False)
        print(f"   Error: {e}")
        return False

def test_root():
    """Root 엔드포인트 테스트"""
    try:
        response = requests.get(f"{BASE_URL}/")
        success = response.status_code == 200
        print_test("Root Endpoint", success, response)
        return success
    except Exception as e:
        print_test("Root Endpoint", False)
        print(f"   Error: {e}")
        return False

def test_register():
    """회원가입 테스트"""
    try:
        test_user = {
            "email": f"test_{datetime.now().timestamp()}@example.com",
            "password": "testpass123",
            "name": "테스트유저"
        }
        response = requests.post(f"{BASE_URL}/auth/signup", json=test_user)
        success = response.status_code in [200, 201]
        print_test("회원가입", success, response)
        return success, test_user if success else None
    except Exception as e:
        print_test("회원가입", False)
        print(f"   Error: {e}")
        return False, None

def test_login(user):
    """로그인 테스트"""
    try:
        login_data = {
            "username": user["email"],
            "password": user["password"]
        }
        response = requests.post(
            f"{BASE_URL}/token",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        success = response.status_code == 200
        print_test("로그인", success, response)
        
        if success:
            token = response.json().get("access_token")
            return success, token
        return False, None
    except Exception as e:
        print_test("로그인", False)
        print(f"   Error: {e}")
        return False, None

def test_get_questions(token):
    """설문 질문 조회 테스트"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/survey/questions", headers=headers)
        success = response.status_code == 200
        
        if success:
            data = response.json()
            success = success and data.get("total") == 15
        
        print_test("설문 질문 조회", success, response)
        return success, response.json() if success else None
    except Exception as e:
        print_test("설문 질문 조회", False)
        print(f"   Error: {e}")
        return False, None

def test_submit_survey(token):
    """설문 제출 테스트"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        # 샘플 답변 (모든 질문에 B 선택)
        survey_data = {
            "answers": [{"question_id": i, "answer": "B"} for i in range(1, 16)]
        }
        response = requests.post(
            f"{BASE_URL}/survey/submit",
            json=survey_data,
            headers=headers
        )
        success = response.status_code == 200
        print_test("설문 제출", success, response)
        return success
    except Exception as e:
        print_test("설문 제출", False)
        print(f"   Error: {e}")
        return False

def test_diagnosis(token):
    """진단 결과 조회 테스트"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        # 샘플 답변으로 진단 요청 (DiagnosisSubmitRequest 형식)
        diagnosis_data = {
            "answers": [
                {"question_id": i, "answer_value": 3} for i in range(1, 16)
            ],
            "monthly_investment": 100  # 월 100만원
        }
        response = requests.post(
            f"{BASE_URL}/diagnosis/submit",
            json=diagnosis_data,
            headers=headers
        )
        success = response.status_code in [200, 201]
        print_test("진단 제출", success, response)
        return success
    except Exception as e:
        print_test("진단 제출", False)
        print(f"   Error: {e}")
        return False

def test_get_latest_diagnosis(token):
    """최근 진단 결과 조회 테스트"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/diagnosis/me", headers=headers)
        success = response.status_code == 200
        print_test("최근 진단 조회", success, response)
        return success
    except Exception as e:
        print_test("최근 진단 조회", False)
        print(f"   Error: {e}")
        return False

def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("🧪 KingoPortfolio API 전체 테스트 시작")
    print("=" * 60)
    
    # 1. 기본 엔드포인트 테스트
    print("\n📍 1단계: 기본 엔드포인트")
    print("-" * 60)
    if not test_health():
        print("\n❌ 서버가 실행되지 않았습니다. uvicorn app.main:app --reload 실행 필요")
        return
    test_root()
    
    # 2. 인증 테스트
    print("\n📍 2단계: 인증 시스템")
    print("-" * 60)
    register_success, user = test_register()
    if not register_success:
        print("\n⚠️ 회원가입 실패. 기존 테스트 계정으로 시도합니다.")
        user = {"email": "test@example.com", "password": "testpass123"}
    
    login_success, token = test_login(user)
    if not login_success:
        print("\n❌ 로그인 실패. 테스트를 중단합니다.")
        return
    
    # 3. 설문 시스템 테스트
    print("\n📍 3단계: 설문 시스템")
    print("-" * 60)
    questions_success, questions = test_get_questions(token)
    if questions_success:
        test_submit_survey(token)
    
    # 4. 진단 시스템 테스트
    print("\n📍 4단계: 진단 시스템")
    print("-" * 60)
    diagnosis_success = test_diagnosis(token)
    if diagnosis_success:
        test_get_latest_diagnosis(token)
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("✅ 테스트 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()