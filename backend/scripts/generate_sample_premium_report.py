#!/usr/bin/env python3
"""
Phase 3-B: 프리미엄 리포트 샘플 PDF 생성 스크립트

이 스크립트는 프리미엄 성과 해석 리포트의 샘플 PDF를 생성합니다.
실제 데이터 없이도 리포트 형식을 확인할 수 있습니다.

사용법:
    python scripts/generate_sample_premium_report.py

출력:
    output/sample_premium_report_YYYYMMDD.pdf
"""

import sys
import os
from datetime import date, datetime
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.explanation_engine import (
    explain_performance,
    explanation_result_to_dict
)
from app.services.pdf_report_generator import PDFReportGenerator


def generate_sample_data():
    """샘플 성과 데이터 생성"""
    return {
        # 성과 지표
        "cagr": 0.082,           # 연 8.2% 수익률
        "volatility": 0.145,     # 14.5% 변동성
        "mdd": -0.123,           # -12.3% 최대 낙폭
        "sharpe": 0.56,          # 샤프 비율 0.56

        # 분석 기간
        "period_start": date(2022, 1, 1),
        "period_end": date(2024, 12, 31),

        # 기타 설정
        "rf_annual": 0.035,      # 무위험 수익률 3.5%
        "benchmark_name": "KOSPI",
        "benchmark_return": 0.045,  # 벤치마크 4.5% 수익률

        # 리포트 설정
        "report_title": "나의 포트폴리오 해석 리포트 (샘플)",
        "total_return": 0.268,   # 누적 26.8% 수익률 (3년)
    }


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("Phase 3-B: 프리미엄 리포트 샘플 PDF 생성")
    print("=" * 60)

    # 1. 샘플 데이터 로드
    print("\n[1/4] 샘플 데이터 준비 중...")
    sample_data = generate_sample_data()
    print(f"  - CAGR: {sample_data['cagr']*100:.1f}%")
    print(f"  - 변동성: {sample_data['volatility']*100:.1f}%")
    print(f"  - MDD: {sample_data['mdd']*100:.1f}%")
    print(f"  - 샤프 비율: {sample_data['sharpe']:.2f}")
    print(f"  - 분석 기간: {sample_data['period_start']} ~ {sample_data['period_end']}")

    # 2. 성과 해석 생성
    print("\n[2/4] 성과 해석 생성 중...")
    explanation_result = explain_performance(
        cagr=sample_data["cagr"],
        volatility=sample_data["volatility"],
        mdd=sample_data["mdd"],
        sharpe=sample_data["sharpe"],
        period_start=sample_data["period_start"],
        period_end=sample_data["period_end"],
        rf_annual=sample_data["rf_annual"],
        benchmark_name=sample_data["benchmark_name"],
        benchmark_return=sample_data["benchmark_return"],
    )

    explanation_data = explanation_result_to_dict(explanation_result)
    print(f"  - 요약: {explanation_data.get('summary', '')[:50]}...")
    print(f"  - 지표 해석: {len(explanation_data.get('performance_explanation', []))}개")

    # 3. 출력 디렉토리 생성
    output_dir = project_root / "output"
    output_dir.mkdir(exist_ok=True)

    # 4. PDF 생성
    print("\n[3/4] 프리미엄 PDF 생성 중...")
    pdf_generator = PDFReportGenerator()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"sample_premium_report_{timestamp}.pdf"
    output_path = output_dir / output_filename

    pdf_generator.generate_premium_report(
        explanation_data=explanation_data,
        report_title=sample_data["report_title"],
        period_start=sample_data["period_start"].isoformat(),
        period_end=sample_data["period_end"].isoformat(),
        total_return=sample_data["total_return"],
        output_path=str(output_path)
    )

    print(f"  - 출력 경로: {output_path}")

    # 5. 기본 PDF도 생성 (비교용)
    print("\n[4/4] 기본 PDF 생성 중 (비교용)...")
    basic_filename = f"sample_basic_report_{timestamp}.pdf"
    basic_path = output_dir / basic_filename

    pdf_generator.generate_explanation_report(
        explanation_data=explanation_data,
        output_path=str(basic_path)
    )
    print(f"  - 출력 경로: {basic_path}")

    # 완료 메시지
    print("\n" + "=" * 60)
    print("PDF 생성 완료!")
    print("=" * 60)
    print(f"\n생성된 파일:")
    print(f"  1. 프리미엄 리포트: {output_path}")
    print(f"  2. 기본 리포트: {basic_path}")
    print(f"\n파일 크기:")
    print(f"  1. 프리미엄: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"  2. 기본: {basic_path.stat().st_size / 1024:.1f} KB")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
