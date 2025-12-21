#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
KingoPortfolio 데이터 분류 테스트
수집한 데이터의 분류 로직 테스트
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.data_collector import DataClassifier
from datetime import datetime

def test_risk_classification():
    """위험도 분류 테스트"""
    print("\n" + "="*60)
    print("📊 위험도 분류 테스트")
    print("="*60)
    
    test_cases = [
        {
            "pe": 8.0,
            "div": 6.5,
            "expected": "low",
            "desc": "PE 낮음 + 배당 높음 → 보수형"
        },
        {
            "pe": 25.0,
            "div": 2.0,
            "expected": "medium",
            "desc": "PE 중간 + 배당 중간 → 중립형"
        },
        {
            "pe": 50.0,
            "div": 0.5,
            "expected": "high",
            "desc": "PE 높음 + 배당 낮음 → 적극형"
        },
        {
            "pe": 5.0,
            "div": None,
            "expected": "low",
            "desc": "PE 극히 낮음 → 보수형"
        },
        {
            "pe": None,
            "div": 7.0,
            "expected": "low",
            "desc": "배당 매우 높음 → 보수형"
        },
    ]
    
    print("\n테스트 케이스:")
    for i, case in enumerate(test_cases, 1):
        result = DataClassifier.classify_risk(case['pe'], case['div'])
        status = "✅" if result == case['expected'] else "❌"
        
        print(f"\n{i}. {case['desc']}")
        print(f"   PE: {case['pe']}, 배당: {case['div']}")
        print(f"   결과: {result} | 예상: {case['expected']} {status}")


def test_investment_type_classification():
    """투자성향 분류 테스트"""
    print("\n" + "="*60)
    print("🎯 투자성향 분류 테스트")
    print("="*60)
    
    test_cases = [
        {
            "risk": "low",
            "expected_include": "conservative",
            "desc": "저위험도 → 보수형 포함"
        },
        {
            "risk": "medium",
            "expected_include": "moderate",
            "desc": "중위험도 → 중립형 포함"
        },
        {
            "risk": "high",
            "expected_include": "aggressive",
            "desc": "고위험도 → 적극형 포함"
        },
    ]
    
    print("\n테스트 케이스:")
    for i, case in enumerate(test_cases, 1):
        result = DataClassifier.classify_investment_type(case['risk'])
        has_expected = case['expected_include'] in result
        status = "✅" if has_expected else "❌"
        
        print(f"\n{i}. {case['desc']}")
        print(f"   위험도: {case['risk']}")
        print(f"   결과: {', '.join(result)}")
        print(f"   {case['expected_include']} 포함: {status}")


def test_category_classification():
    """범주 분류 테스트"""
    print("\n" + "="*60)
    print("🏢 범주 분류 테스트")
    print("="*60)
    
    test_cases = [
        {
            "name": "삼성전자",
            "sector": "전자",
            "expected": "기술주",
            "desc": "삼성전자 → 기술주"
        },
        {
            "name": "카카오",
            "sector": "정보기술",
            "expected": "기술주",
            "desc": "카카오 → 기술주"
        },
        {
            "name": "삼성물산",
            "sector": None,
            "expected": None,
            "desc": "삼성물산 → 기타주"
        },
        {
            "name": "SK텔레콤",
            "sector": "통신",
            "expected": "기타주",
            "desc": "SK텔레콤 → 기타주 (또는 금융)"
        },
        {
            "name": "기아",
            "sector": "자동차",
            "expected": None,
            "desc": "기아 → 자동차주"
        },
    ]
    
    print("\n테스트 케이스:")
    for i, case in enumerate(test_cases, 1):
        result = DataClassifier.classify_category(case['name'], case['sector'])
        
        print(f"\n{i}. {case['desc']}")
        print(f"   회사: {case['name']}, 섹터: {case['sector']}")
        print(f"   결과: {result}")


def test_comprehensive():
    """통합 테스트: 실제 데이터 기반"""
    print("\n" + "="*60)
    print("🔄 통합 분류 테스트")
    print("="*60)
    
    sample_stocks = [
        {
            "name": "삼성전자",
            "ticker": "005930",
            "pe_ratio": 12.5,
            "pb_ratio": 1.2,
            "dividend_yield": 3.5,
            "sector": "전자"
        },
        {
            "name": "카카오",
            "ticker": "035720",
            "pe_ratio": 45.3,
            "pb_ratio": 8.5,
            "dividend_yield": 0.5,
            "sector": "정보기술"
        },
        {
            "name": "POSCO홀딩스",
            "ticker": "005490",
            "pe_ratio": 5.2,
            "pb_ratio": 0.6,
            "dividend_yield": 6.5,
            "sector": "철강"
        },
    ]
    
    print("\n샘플 주식 분류 결과:")
    print("-" * 60)
    
    for stock in sample_stocks:
        print(f"\n📈 {stock['name']} ({stock['ticker']})")
        
        # 위험도 분류
        risk = DataClassifier.classify_risk(
            stock['pe_ratio'],
            stock['dividend_yield']
        )
        
        # 투자성향 분류
        inv_types = DataClassifier.classify_investment_type(
            risk,
            stock['dividend_yield']
        )
        
        # 범주 분류
        category = DataClassifier.classify_category(
            stock['name'],
            stock['sector']
        )
        
        print(f"   PE: {stock['pe_ratio']:.1f}, PB: {stock['pb_ratio']:.1f}")
        print(f"   배당수익률: {stock['dividend_yield']:.1f}%")
        print(f"   위험도: {risk}")
        print(f"   투자성향: {', '.join(inv_types)}")
        print(f"   범주: {category}")


def main():
    """메인 테스트 함수"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "KingoPortfolio 데이터 분류 테스트" + " "*16 + "║")
    print("╚" + "="*58 + "╝")
    
    print(f"\n⏰ 테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 위험도 분류
        test_risk_classification()
        
        # 2. 투자성향 분류
        test_investment_type_classification()
        
        # 3. 범주 분류
        test_category_classification()
        
        # 4. 통합 테스트
        test_comprehensive()
        
        print("\n" + "="*60)
        print("✅ 모든 분류 테스트 완료!")
        print("="*60)
        print("\n")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()