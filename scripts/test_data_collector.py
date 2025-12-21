#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
KingoPortfolio 데이터 수집 테스트
yfinance API를 통해 실시간 주식/ETF 데이터 수집 테스트
"""

import sys
import os

# 프로젝트 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.data_collector import DataCollector, DataClassifier
from datetime import datetime

def test_stock_collection():
    """주식 데이터 수집 테스트"""
    print("\n" + "="*60)
    print("🔴 주식 데이터 수집 테스트")
    print("="*60)
    
    test_stocks = [
        ("005930", "삼성전자"),
        ("000660", "LG전자"),
        ("035720", "카카오"),
    ]
    
    for ticker, name in test_stocks:
        print(f"\n📊 {name} ({ticker}) 수집 중...")
        
        try:
            data = DataCollector.fetch_stock_data(ticker, name)
            
            if data:
                print(f"✅ 수집 완료!")
                print(f"   현재가: {data['current_price']:>10,.0f}원")
                print(f"   PE비율: {str(data['pe_ratio']) if data['pe_ratio'] else 'N/A':>10}")
                print(f"   PB비율: {str(data['pb_ratio']) if data['pb_ratio'] else 'N/A':>10}")
                
                div_yield = data['dividend_yield']
                if div_yield:
                    print(f"   배당수익률: {div_yield:>8.2f}%")
                else:
                    print(f"   배당수익률: {'N/A':>10}")
                
                print(f"   YTD 수익률: {data['ytd_return']:>8.2f}%")
                print(f"   1년 수익률: {data['one_year_return']:>8.2f}%")
                
                # 분류
                risk = DataClassifier.classify_risk(data['pe_ratio'], data['dividend_yield'])
                inv_type = DataClassifier.classify_investment_type(risk, data['dividend_yield'])
                category = DataClassifier.classify_category(name, data.get('sector'))
                
                print(f"   위험도: {risk}")
                print(f"   투자성향: {', '.join(inv_type)}")
                print(f"   범주: {category}")
            else:
                print(f"❌ 수집 실패")
        
        except Exception as e:
            print(f"❌ 오류: {str(e)}")


def test_etf_collection():
    """ETF 데이터 수집 테스트"""
    print("\n" + "="*60)
    print("📊 ETF 데이터 수집 테스트")
    print("="*60)
    
    test_etfs = [
        ("102110", "KODEX 배당성장"),
        ("133690", "TIGER 200"),
    ]
    
    for ticker, name in test_etfs:
        print(f"\n📈 {name} ({ticker}) 수집 중...")
        
        try:
            data = DataCollector.fetch_etf_data(ticker, name)
            
            if data:
                print(f"✅ 수집 완료!")
                print(f"   현재가: {data['current_price']:>10,.0f}원")
                print(f"   운용자산: {data['aum']:>10,.0f}")
                print(f"   수수료율: {data['expense_ratio']:>10.2f}%")
                print(f"   YTD 수익률: {data['ytd_return']:>8.2f}%")
                print(f"   1년 수익률: {data['one_year_return']:>8.2f}%")
            else:
                print(f"❌ 수집 실패")
        
        except Exception as e:
            print(f"❌ 오류: {str(e)}")


def test_classification():
    """데이터 분류 테스트"""
    print("\n" + "="*60)
    print("🏷️ 데이터 분류 테스트")
    print("="*60)
    
    test_cases = [
        {"pe": 8.0, "div": 6.5, "name": "삼성전자 (배당주)"},
        {"pe": 25.0, "div": 2.0, "name": "LG전자 (중간)"},
        {"pe": 50.0, "div": 0.5, "name": "카카오 (성장주)"},
    ]
    
    print("\n📊 위험도 분류:")
    for case in test_cases:
        risk = DataClassifier.classify_risk(case['pe'], case['div'])
        print(f"  {case['name']:20} → {risk}")
    
    print("\n📊 투자성향 분류:")
    for risk_level in ["low", "medium", "high"]:
        inv_types = DataClassifier.classify_investment_type(risk_level)
        print(f"  {risk_level:10} → {', '.join(inv_types)}")
    
    print("\n📊 범주 분류:")
    test_names = [
        ("삼성전자", "전자"),
        ("카카오", "정보기술"),
        ("현대금융", None),
    ]
    
    for name, sector in test_names:
        category = DataClassifier.classify_category(name, sector)
        print(f"  {name:15} → {category}")


def main():
    """메인 테스트 함수"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "KingoPortfolio 데이터 수집 테스트" + " "*16 + "║")
    print("╚" + "="*58 + "╝")
    
    print(f"\n⏰ 테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📍 Python 버전: {sys.version.split()[0]}")
    
    try:
        # 1. 주식 수집
        test_stock_collection()
        
        # 2. ETF 수집
        test_etf_collection()
        
        # 3. 분류
        test_classification()
        
        print("\n" + "="*60)
        print("✅ 모든 테스트 완료!")
        print("="*60)
        print("\n✅ 다음 단계:")
        print("   1. 백엔드 서버 실행: python -m uvicorn app.main:app --reload")
        print("   2. 프론트엔드 실행: npm run dev")
        print("   3. 관리자 콘솔에서 데이터 적재: POST /admin/load-data")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()