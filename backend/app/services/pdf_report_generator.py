"""
PDF 투자 리포트 생성 서비스
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from datetime import datetime
from io import BytesIO
import matplotlib
matplotlib.use('Agg')  # Non-GUI backend
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm


class PDFReportGenerator:
    """투자 리포트 PDF 생성기"""

    def __init__(self):
        self.width, self.height = A4
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """스타일 설정"""
        # 제목 스타일
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # 부제목 스타일
        self.styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))

        # 본문 스타일
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            leading=14,
            spaceAfter=10,
            fontName='Helvetica'
        ))

        # 강조 스타일
        self.styles.add(ParagraphStyle(
            name='Highlight',
            parent=self.styles['BodyText'],
            fontSize=12,
            textColor=colors.HexColor('#667eea'),
            fontName='Helvetica-Bold',
            spaceAfter=10
        ))

    def generate_portfolio_report(self, portfolio_data, user_data, output_path=None):
        """
        포트폴리오 투자 리포트 생성

        Args:
            portfolio_data: 포트폴리오 데이터
            user_data: 사용자 데이터
            output_path: 출력 파일 경로 (None이면 BytesIO 반환)

        Returns:
            BytesIO or file path
        """
        # PDF 문서 생성
        if output_path:
            doc = SimpleDocTemplate(output_path, pagesize=A4)
        else:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)

        # 스토리 (페이지 내용) 구성
        story = []

        # 1. 표지 페이지
        story.extend(self._create_cover_page(user_data, portfolio_data))
        story.append(PageBreak())

        # 2. 투자 성향 분석
        story.extend(self._create_investment_profile_section(portfolio_data))
        story.append(Spacer(1, 0.3*inch))

        # 3. 포트폴리오 구성
        story.extend(self._create_portfolio_composition_section(portfolio_data))
        story.append(Spacer(1, 0.3*inch))

        # 4. 자산 배분 차트
        story.extend(self._create_asset_allocation_section(portfolio_data))
        story.append(PageBreak())

        # 5. 보유 종목 상세
        story.extend(self._create_holdings_detail_section(portfolio_data))
        story.append(PageBreak())

        # 6. 리스크 분석
        story.extend(self._create_risk_analysis_section(portfolio_data))
        story.append(Spacer(1, 0.3*inch))

        # 7. 기대 성과
        story.extend(self._create_expected_performance_section(portfolio_data))
        story.append(PageBreak())

        # 8. 면책 조항
        story.extend(self._create_disclaimer_section())

        # PDF 빌드
        doc.build(story)

        if output_path:
            return output_path
        else:
            buffer.seek(0)
            return buffer

    def _create_cover_page(self, user_data, portfolio_data):
        """표지 페이지 생성"""
        elements = []

        # 로고/제목
        elements.append(Spacer(1, 2*inch))
        title = Paragraph("Investment Portfolio Report", self.styles['CustomTitle'])
        elements.append(title)

        subtitle = Paragraph("Personal Investment Analysis", self.styles['CustomHeading1'])
        elements.append(subtitle)
        elements.append(Spacer(1, 1*inch))

        # 사용자 정보
        user_info = f"""
        <para align=center>
        <b>Prepared for:</b> {user_data.get('email', 'N/A')}<br/>
        <b>Report Date:</b> {datetime.now().strftime('%Y-%m-%d')}<br/>
        <b>Investment Type:</b> {self._format_investment_type(portfolio_data.get('investment_type', 'moderate'))}
        </para>
        """
        elements.append(Paragraph(user_info, self.styles['CustomBody']))
        elements.append(Spacer(1, 2*inch))

        # 하단 문구
        footer = Paragraph(
            "<para align=center><i>Powered by Foresto Compass</i></para>",
            self.styles['CustomBody']
        )
        elements.append(footer)

        return elements

    def _create_investment_profile_section(self, portfolio_data):
        """투자 성향 분석 섹션"""
        elements = []

        elements.append(Paragraph("1. Investment Profile", self.styles['CustomHeading1']))

        investment_type = portfolio_data.get('investment_type', 'moderate')
        type_descriptions = {
            'conservative': 'Conservative - Focus on capital preservation with stable returns',
            'moderate': 'Moderate - Balanced approach between stability and growth',
            'aggressive': 'Aggressive - Growth-oriented with higher risk tolerance'
        }

        desc = type_descriptions.get(investment_type, 'Moderate')
        elements.append(Paragraph(f"<b>Investment Type:</b> {desc}", self.styles['CustomBody']))

        # 투자 성향 특징
        if 'statistics' in portfolio_data:
            stats = portfolio_data['statistics']

            profile_text = f"""
            <b>Expected Annual Return:</b> {stats.get('expected_annual_return', 0):.2f}%<br/>
            <b>Portfolio Risk Level:</b> {stats.get('portfolio_risk', 'Medium')}<br/>
            <b>Diversification Score:</b> {stats.get('diversification_score', 0):.2f}
            """
            elements.append(Paragraph(profile_text, self.styles['CustomBody']))

        return elements

    def _create_portfolio_composition_section(self, portfolio_data):
        """포트폴리오 구성 섹션"""
        elements = []

        elements.append(Paragraph("2. Portfolio Composition", self.styles['CustomHeading1']))

        # 자산 배분 테이블
        if 'allocation' in portfolio_data:
            allocation = portfolio_data['allocation']

            data = [
                ['Asset Class', 'Allocation (%)', 'Amount (KRW)'],
                ['Stocks', f"{allocation.get('stocks', 0):.1f}%", f"{self._format_currency(allocation.get('stocks_amount', 0))}"],
                ['ETFs', f"{allocation.get('etfs', 0):.1f}%", f"{self._format_currency(allocation.get('etfs_amount', 0))}"],
                ['Bonds', f"{allocation.get('bonds', 0):.1f}%", f"{self._format_currency(allocation.get('bonds_amount', 0))}"],
                ['Deposits', f"{allocation.get('deposits', 0):.1f}%", f"{self._format_currency(allocation.get('deposits_amount', 0))}"],
            ]

            table = Table(data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ]))

            elements.append(table)

        return elements

    def _create_asset_allocation_section(self, portfolio_data):
        """자산 배분 차트 섹션"""
        elements = []

        elements.append(Paragraph("3. Asset Allocation Chart", self.styles['CustomHeading1']))

        if 'allocation' in portfolio_data:
            allocation = portfolio_data['allocation']

            # 파이 차트 생성
            labels = []
            sizes = []
            colors_list = []

            if allocation.get('stocks', 0) > 0:
                labels.append(f"Stocks\n{allocation['stocks']:.1f}%")
                sizes.append(allocation['stocks'])
                colors_list.append('#667eea')

            if allocation.get('etfs', 0) > 0:
                labels.append(f"ETFs\n{allocation['etfs']:.1f}%")
                sizes.append(allocation['etfs'])
                colors_list.append('#4caf50')

            if allocation.get('bonds', 0) > 0:
                labels.append(f"Bonds\n{allocation['bonds']:.1f}%")
                sizes.append(allocation['bonds'])
                colors_list.append('#ff9800')

            if allocation.get('deposits', 0) > 0:
                labels.append(f"Deposits\n{allocation['deposits']:.1f}%")
                sizes.append(allocation['deposits'])
                colors_list.append('#2196f3')

            if sizes:
                fig, ax = plt.subplots(figsize=(6, 6))
                ax.pie(sizes, labels=labels, colors=colors_list, autopct='%1.1f%%', startangle=90)
                ax.axis('equal')
                plt.title('Asset Allocation Distribution', fontsize=14, fontweight='bold')

                # 이미지로 저장
                img_buffer = BytesIO()
                plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
                img_buffer.seek(0)
                plt.close()

                # PDF에 추가
                img = Image(img_buffer, width=5*inch, height=5*inch)
                elements.append(img)

        return elements

    def _create_holdings_detail_section(self, portfolio_data):
        """보유 종목 상세 섹션"""
        elements = []

        elements.append(Paragraph("4. Holdings Detail", self.styles['CustomHeading1']))

        # 주식
        if 'portfolio' in portfolio_data and 'stocks' in portfolio_data['portfolio']:
            stocks = portfolio_data['portfolio']['stocks']
            if stocks:
                elements.append(Paragraph("<b>Stocks:</b>", self.styles['Highlight']))

                stock_data = [['Ticker', 'Name', 'Quantity', 'Price', 'Total Value']]
                for stock in stocks[:10]:  # 최대 10개만 표시
                    stock_data.append([
                        stock.get('ticker', 'N/A'),
                        stock.get('name', 'N/A')[:20],  # 이름 길이 제한
                        str(stock.get('quantity', 0)),
                        f"{stock.get('price', 0):,.0f}",
                        f"{stock.get('total_value', 0):,.0f}"
                    ])

                table = Table(stock_data, colWidths=[1*inch, 2*inch, 1*inch, 1.2*inch, 1.3*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
                ]))

                elements.append(table)
                elements.append(Spacer(1, 0.3*inch))

        # ETF
        if 'portfolio' in portfolio_data and 'etfs' in portfolio_data['portfolio']:
            etfs = portfolio_data['portfolio']['etfs']
            if etfs:
                elements.append(Paragraph("<b>ETFs:</b>", self.styles['Highlight']))

                etf_data = [['Ticker', 'Name', 'Quantity', 'Price', 'Total Value']]
                for etf in etfs[:10]:
                    etf_data.append([
                        etf.get('ticker', 'N/A'),
                        etf.get('name', 'N/A')[:20],
                        str(etf.get('quantity', 0)),
                        f"{etf.get('price', 0):,.0f}",
                        f"{etf.get('total_value', 0):,.0f}"
                    ])

                table = Table(etf_data, colWidths=[1*inch, 2*inch, 1*inch, 1.2*inch, 1.3*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4caf50')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
                ]))

                elements.append(table)

        return elements

    def _create_risk_analysis_section(self, portfolio_data):
        """리스크 분석 섹션"""
        elements = []

        elements.append(Paragraph("5. Risk Analysis", self.styles['CustomHeading1']))

        if 'statistics' in portfolio_data:
            stats = portfolio_data['statistics']

            risk_text = f"""
            <b>Portfolio Risk Level:</b> {stats.get('portfolio_risk', 'Medium')}<br/>
            <b>Diversification Score:</b> {stats.get('diversification_score', 0):.2f}<br/>
            <b>Risk Assessment:</b> This portfolio is designed to match your risk tolerance and investment objectives.
            """

            elements.append(Paragraph(risk_text, self.styles['CustomBody']))

            # 리스크 설명
            risk_desc = """
            <b>Key Risk Factors:</b><br/>
            • Market volatility may affect short-term returns<br/>
            • Individual stock performance varies<br/>
            • Economic conditions impact all asset classes<br/>
            • Past performance does not guarantee future results
            """
            elements.append(Paragraph(risk_desc, self.styles['CustomBody']))

        return elements

    def _create_expected_performance_section(self, portfolio_data):
        """기대 성과 섹션"""
        elements = []

        elements.append(Paragraph("6. Expected Performance", self.styles['CustomHeading1']))

        if 'statistics' in portfolio_data:
            stats = portfolio_data['statistics']

            perf_text = f"""
            <b>Expected Annual Return:</b> {stats.get('expected_annual_return', 0):.2f}%<br/>
            <b>Investment Horizon:</b> Long-term (3+ years suggested for learning)<br/>
            <b>Rebalancing Frequency:</b> Quarterly or semi-annually
            """

            elements.append(Paragraph(perf_text, self.styles['CustomBody']))

            # 학습 참고사항
            learning_notes = """
            <b>Learning Notes:</b><br/>
            • This simulation is for educational purposes only<br/>
            • Understand portfolio diversification concepts<br/>
            • Learn about market conditions and their effects<br/>
            • Consult with financial advisors for actual investment decisions
            """
            elements.append(Paragraph(learning_notes, self.styles['CustomBody']))

        return elements

    def _create_disclaimer_section(self):
        """면책 조항 섹션"""
        elements = []

        elements.append(Paragraph("Disclaimer", self.styles['CustomHeading1']))

        disclaimer_text = """
        <b>Important Legal Notice:</b><br/><br/>

        This investment portfolio report is provided for educational and informational purposes only and does not constitute
        investment advice or a suggestion to buy or sell any securities.<br/><br/>

        <b>Key Points:</b><br/>
        • All investment decisions are made at your own risk and discretion<br/>
        • Past performance is not indicative of future results<br/>
        • Portfolio returns are estimates based on historical data and may vary significantly<br/>
        • We are not responsible for any investment losses<br/>
        • Consult with a licensed financial advisor before making investment decisions<br/><br/>

        <b>Data Sources:</b><br/>
        Portfolio simulations are generated using algorithmic analysis based on publicly available data.
        Data accuracy and timeliness are not guaranteed.<br/><br/>

        <i>© 2025 Foresto Compass. All rights reserved.</i>
        """

        elements.append(Paragraph(disclaimer_text, self.styles['CustomBody']))

        return elements

    def _format_investment_type(self, inv_type):
        """투자 성향 포맷팅"""
        type_map = {
            'conservative': 'Conservative (Stable)',
            'moderate': 'Moderate (Balanced)',
            'aggressive': 'Aggressive (Growth)'
        }
        return type_map.get(inv_type, 'Moderate')

    def _format_currency(self, amount):
        """통화 포맷팅"""
        if amount >= 100000000:  # 1억 이상
            return f"{amount/100000000:.1f}억원"
        elif amount >= 10000:  # 1만 이상
            return f"{amount/10000:.0f}만원"
        else:
            return f"{amount:,.0f}원"

    # ========================================================================
    # Phase 3-B: 성과 해석 리포트 PDF 생성
    # ========================================================================

    def generate_explanation_report(self, explanation_data: dict, output_path=None):
        """
        성과 해석 리포트 PDF 생성

        Args:
            explanation_data: 성과 해석 데이터 (ExplanationResult dict)
            output_path: 출력 파일 경로 (None이면 BytesIO 반환)

        Returns:
            BytesIO or file path
        """
        if output_path:
            doc = SimpleDocTemplate(output_path, pagesize=A4)
        else:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)

        story = []

        # 1. 표지
        story.extend(self._create_explanation_cover())
        story.append(PageBreak())

        # 2. 요약 섹션
        story.extend(self._create_summary_section(explanation_data))
        story.append(Spacer(1, 0.3*inch))

        # 3. 성과 지표 해석 섹션
        story.extend(self._create_performance_explanation_section(explanation_data))
        story.append(PageBreak())

        # 4. 위험 분석 섹션
        story.extend(self._create_risk_explanation_section(explanation_data))
        story.append(Spacer(1, 0.3*inch))

        # 5. 비교 맥락 섹션 (있는 경우)
        if explanation_data.get('comparison'):
            story.extend(self._create_comparison_section(explanation_data))
            story.append(Spacer(1, 0.3*inch))

        # 6. 면책 조항
        story.extend(self._create_explanation_disclaimer_section(explanation_data))

        doc.build(story)

        if output_path:
            return output_path
        else:
            buffer.seek(0)
            return buffer

    def _create_explanation_cover(self):
        """성과 해석 리포트 표지"""
        elements = []

        elements.append(Spacer(1, 2*inch))

        title = Paragraph(
            "Portfolio Performance Analysis Report",
            self.styles['CustomTitle']
        )
        elements.append(title)

        subtitle = Paragraph(
            "Understanding Your Investment Journey",
            self.styles['CustomHeading1']
        )
        elements.append(subtitle)
        elements.append(Spacer(1, 1*inch))

        # 리포트 정보
        report_info = f"""
        <para align=center>
        <b>Report Date:</b> {datetime.now().strftime('%Y-%m-%d')}<br/>
        <b>Report Type:</b> Performance Explanation Report<br/>
        <b>Purpose:</b> Educational Analysis (Not Investment Advice)
        </para>
        """
        elements.append(Paragraph(report_info, self.styles['CustomBody']))
        elements.append(Spacer(1, 2*inch))

        footer = Paragraph(
            "<para align=center><i>Powered by Kingo Portfolio</i></para>",
            self.styles['CustomBody']
        )
        elements.append(footer)

        return elements

    def _create_summary_section(self, explanation_data: dict):
        """요약 섹션"""
        elements = []

        elements.append(Paragraph("1. Performance Summary", self.styles['CustomHeading1']))

        summary = explanation_data.get('summary', 'No summary available.')
        elements.append(Paragraph(summary, self.styles['CustomBody']))

        return elements

    def _create_performance_explanation_section(self, explanation_data: dict):
        """성과 지표 해석 섹션"""
        elements = []

        elements.append(Paragraph("2. Key Metrics Explained", self.styles['CustomHeading1']))

        explanations = explanation_data.get('performance_explanation', [])

        for exp in explanations:
            metric_name = exp.get('metric', 'Unknown')
            formatted_value = exp.get('formatted_value', 'N/A')
            description = exp.get('description', '')
            context = exp.get('context', '')

            # 지표명과 값
            metric_header = f"<b>{self._get_metric_korean_name(metric_name)}</b> ({formatted_value})"
            elements.append(Paragraph(metric_header, self.styles['Highlight']))

            # 설명
            elements.append(Paragraph(description, self.styles['CustomBody']))

            # 맥락 (박스 스타일)
            if context:
                context_text = f"<i>💡 {context}</i>"
                elements.append(Paragraph(context_text, self.styles['CustomBody']))

            elements.append(Spacer(1, 0.2*inch))

        return elements

    def _create_risk_explanation_section(self, explanation_data: dict):
        """위험 분석 섹션"""
        elements = []

        elements.append(Paragraph("3. Risk Analysis", self.styles['CustomHeading1']))

        risk_explanation = explanation_data.get('risk_explanation', '')
        elements.append(Paragraph(risk_explanation, self.styles['CustomBody']))

        # 위험 구간 표시
        risk_periods = explanation_data.get('risk_periods', [])
        if risk_periods:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Notable Risk Periods:</b>", self.styles['CustomBody']))

            for rp in risk_periods:
                period_desc = rp.get('description', '')
                start_date = rp.get('start_date', '')
                end_date = rp.get('end_date', '')
                severity = rp.get('severity', 'moderate')

                severity_color = {
                    'mild': '#4caf50',
                    'moderate': '#ff9800',
                    'severe': '#f44336'
                }.get(severity, '#ff9800')

                period_text = f"• {period_desc}"
                if start_date and end_date:
                    period_text += f" ({start_date} ~ {end_date})"

                elements.append(Paragraph(period_text, self.styles['CustomBody']))

        return elements

    def _create_comparison_section(self, explanation_data: dict):
        """비교 맥락 섹션"""
        elements = []

        elements.append(Paragraph("4. Market Comparison", self.styles['CustomHeading1']))

        comparison = explanation_data.get('comparison', {})
        benchmark_name = comparison.get('benchmark_name', 'Market Index')
        relative_performance = comparison.get('relative_performance', '')
        note = comparison.get('note', '')

        elements.append(Paragraph(f"<b>Compared to:</b> {benchmark_name}", self.styles['CustomBody']))
        elements.append(Paragraph(relative_performance, self.styles['CustomBody']))

        if note:
            note_text = f"<i>Note: {note}</i>"
            elements.append(Paragraph(note_text, self.styles['CustomBody']))

        return elements

    def _create_explanation_disclaimer_section(self, explanation_data: dict):
        """면책 조항 섹션"""
        elements = []

        elements.append(Paragraph("Important Disclaimer", self.styles['CustomHeading1']))

        disclaimer = explanation_data.get('disclaimer', '')

        # 기본 면책 조항
        disclaimer_text = f"""
        <b>Legal Notice:</b><br/><br/>

        {disclaimer}<br/><br/>

        <b>Key Points:</b><br/>
        • This report is for educational and informational purposes only<br/>
        • Past performance does not guarantee future results<br/>
        • This is NOT investment advice or recommendation<br/>
        • All investment decisions are your own responsibility<br/>
        • Consult a licensed financial advisor for investment decisions<br/><br/>

        <b>Data Disclaimer:</b><br/>
        Analysis is based on historical data. Data accuracy is not guaranteed.
        Market conditions change and past patterns may not repeat.<br/><br/>

        <i>© 2025 Kingo Portfolio. All rights reserved.</i>
        """

        elements.append(Paragraph(disclaimer_text, self.styles['CustomBody']))

        return elements

    def _get_metric_korean_name(self, metric: str) -> str:
        """지표명 한글 변환"""
        metric_names = {
            'CAGR': '연평균 수익률 (CAGR)',
            'Volatility': '변동성',
            'MDD': '최대 낙폭 (MDD)',
            'Sharpe Ratio': '샤프 비율'
        }
        return metric_names.get(metric, metric)

    # ========================================================================
    # Phase 3-B 프리미엄 리포트: 아웃라인 기반 고도화
    # ========================================================================

    def generate_premium_report(
        self,
        explanation_data: dict,
        report_title: str = None,
        period_start: str = None,
        period_end: str = None,
        total_return: float = None,
        output_path=None
    ):
        """
        프리미엄 성과 해석 리포트 PDF 생성

        Phase3B_Premium_Report_Outline.md 구성안에 따른 고도화 리포트

        Args:
            explanation_data: 성과 해석 데이터
            report_title: 리포트 제목 (선택)
            period_start: 분석 시작일 (YYYY-MM-DD)
            period_end: 분석 종료일 (YYYY-MM-DD)
            total_return: 누적 수익률 (선택)
            output_path: 출력 파일 경로

        Returns:
            BytesIO or file path
        """
        if output_path:
            doc = SimpleDocTemplate(
                output_path, pagesize=A4,
                topMargin=0.75*inch, bottomMargin=0.75*inch,
                leftMargin=0.75*inch, rightMargin=0.75*inch
            )
        else:
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer, pagesize=A4,
                topMargin=0.75*inch, bottomMargin=0.75*inch,
                leftMargin=0.75*inch, rightMargin=0.75*inch
            )

        story = []

        # 1. 표지 (Cover)
        story.extend(self._create_premium_cover(
            report_title=report_title,
            period_start=period_start,
            period_end=period_end
        ))
        story.append(PageBreak())

        # 2. 요약 페이지 (Executive Summary)
        story.extend(self._create_executive_summary(
            explanation_data=explanation_data,
            total_return=total_return
        ))
        story.append(PageBreak())

        # 3. 성과 해석 섹션
        story.extend(self._create_premium_performance_section(explanation_data))
        story.append(PageBreak())

        # 4. 위험 구간 분석
        story.extend(self._create_premium_risk_section(explanation_data))
        story.append(Spacer(1, 0.3*inch))

        # 5. 맥락 비교 섹션
        if explanation_data.get('comparison'):
            story.extend(self._create_premium_comparison_section(explanation_data))
            story.append(PageBreak())

        # 6. 종합 해석
        story.extend(self._create_comprehensive_interpretation(explanation_data))
        story.append(Spacer(1, 0.3*inch))

        # 7. 참고 및 고지
        story.extend(self._create_premium_disclaimer_section(explanation_data))

        doc.build(story)

        if output_path:
            return output_path
        else:
            buffer.seek(0)
            return buffer

    def _create_premium_cover(
        self,
        report_title: str = None,
        period_start: str = None,
        period_end: str = None
    ):
        """프리미엄 리포트 표지"""
        elements = []

        elements.append(Spacer(1, 1.5*inch))

        # 메인 타이틀
        title_text = report_title or "나의 포트폴리오 해석 리포트"
        title = Paragraph(
            f"<para align=center><font size=28><b>{title_text}</b></font></para>",
            self.styles['CustomTitle']
        )
        elements.append(title)

        elements.append(Spacer(1, 0.5*inch))

        # 서브타이틀
        subtitle = Paragraph(
            "<para align=center><font size=14 color='#666666'>"
            "My Portfolio Interpretation Report"
            "</font></para>",
            self.styles['CustomBody']
        )
        elements.append(subtitle)

        elements.append(Spacer(1, 1.5*inch))

        # 리포트 메타 정보
        period_text = ""
        if period_start and period_end:
            period_text = f"{period_start} ~ {period_end}"
        else:
            period_text = "전체 기간"

        meta_info = f"""
        <para align=center>
        <font size=12>
        <b>분석 기간:</b> {period_text}<br/><br/>
        <b>생성일자:</b> {datetime.now().strftime('%Y년 %m월 %d일')}<br/><br/>
        </font>
        </para>
        """
        elements.append(Paragraph(meta_info, self.styles['CustomBody']))

        elements.append(Spacer(1, 1*inch))

        # 고지 문구 박스
        notice_text = """
        <para align=center>
        <font size=9 color='#666666'>
        ⚠️ 본 리포트는 과거 데이터를 기반으로 한 설명 자료이며,<br/>
        투자 판단이나 자문을 제공하지 않습니다.
        </font>
        </para>
        """
        elements.append(Paragraph(notice_text, self.styles['CustomBody']))

        elements.append(Spacer(1, 1.5*inch))

        # 푸터
        footer = Paragraph(
            "<para align=center><i>Powered by Kingo Portfolio</i></para>",
            self.styles['CustomBody']
        )
        elements.append(footer)

        return elements

    def _create_executive_summary(
        self,
        explanation_data: dict,
        total_return: float = None
    ):
        """요약 페이지 (Executive Summary)"""
        elements = []

        elements.append(Paragraph(
            "<b>Executive Summary</b>",
            self.styles['CustomTitle']
        ))
        elements.append(Spacer(1, 0.3*inch))

        # 한 문장 요약
        elements.append(Paragraph(
            "<b>📋 한 문장 요약</b>",
            self.styles['CustomHeading1']
        ))

        summary = explanation_data.get('summary', '')
        if summary:
            elements.append(Paragraph(summary, self.styles['CustomBody']))
        else:
            elements.append(Paragraph(
                "이 포트폴리오는 안정성과 변동성 사이의 균형을 중시한 결과로 해석할 수 있습니다.",
                self.styles['CustomBody']
            ))

        elements.append(Spacer(1, 0.4*inch))

        # 핵심 지표 요약 테이블
        elements.append(Paragraph(
            "<b>📊 핵심 지표 요약</b>",
            self.styles['CustomHeading1']
        ))

        # 지표 데이터 추출
        perf_exp = explanation_data.get('performance_explanation', [])

        cagr_value = "N/A"
        vol_level = "N/A"
        mdd_value = "N/A"
        sharpe_value = "N/A"

        for exp in perf_exp:
            metric = exp.get('metric', '')
            formatted = exp.get('formatted_value', 'N/A')
            level = exp.get('level', '')

            if metric == 'CAGR':
                cagr_value = formatted
            elif metric == 'Volatility':
                vol_level = self._get_level_korean(level) or formatted
            elif metric == 'MDD':
                mdd_value = formatted
            elif metric == 'Sharpe Ratio':
                sharpe_value = formatted

        # 누적 수익률
        total_return_text = f"{total_return*100:.1f}%" if total_return else "N/A"

        # 테이블 데이터
        table_data = [
            ['지표', '값', '해석'],
            ['누적 수익률', total_return_text, '전체 기간 총 수익'],
            ['연평균 수익률 (CAGR)', cagr_value, '연간 복리 기준'],
            ['변동성', vol_level, '가격 변동 폭'],
            ['최대 낙폭 (MDD)', mdd_value, '최대 하락 구간'],
            ['샤프 비율', sharpe_value, '위험 대비 수익'],
        ]

        table = Table(table_data, colWidths=[2*inch, 1.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
        ]))

        elements.append(table)

        return elements

    def _create_premium_performance_section(self, explanation_data: dict):
        """성과 해석 섹션 (고도화)"""
        elements = []

        elements.append(Paragraph(
            "<b>성과 해석</b>",
            self.styles['CustomTitle']
        ))
        elements.append(Spacer(1, 0.3*inch))

        perf_exp = explanation_data.get('performance_explanation', [])

        for exp in perf_exp:
            metric = exp.get('metric', '')
            formatted_value = exp.get('formatted_value', 'N/A')
            description = exp.get('description', '')
            context = exp.get('context', '')

            # 섹션 제목
            korean_name = self._get_metric_korean_name(metric)
            elements.append(Paragraph(
                f"<b>📈 {korean_name}</b> <font color='#667eea'>({formatted_value})</font>",
                self.styles['CustomHeading1']
            ))

            # 설명
            elements.append(Paragraph(description, self.styles['CustomBody']))

            # 맥락 박스
            if context:
                context_box = f"""
                <para backColor='#f0f4ff' borderPadding='10'>
                <font size=9 color='#4a5568'>💡 {context}</font>
                </para>
                """
                elements.append(Paragraph(context_box, self.styles['CustomBody']))

            elements.append(Spacer(1, 0.25*inch))

        return elements

    def _create_premium_risk_section(self, explanation_data: dict):
        """위험 구간 분석 섹션 (고도화)"""
        elements = []

        elements.append(Paragraph(
            "<b>위험 구간 분석</b>",
            self.styles['CustomTitle']
        ))
        elements.append(Spacer(1, 0.3*inch))

        # 5.1 최대 낙폭 구간 설명
        elements.append(Paragraph(
            "<b>⚠️ 최대 낙폭 구간</b>",
            self.styles['CustomHeading1']
        ))

        risk_explanation = explanation_data.get('risk_explanation', '')
        if risk_explanation:
            elements.append(Paragraph(risk_explanation, self.styles['CustomBody']))

        risk_periods = explanation_data.get('risk_periods', [])
        if risk_periods:
            elements.append(Spacer(1, 0.2*inch))

            for rp in risk_periods:
                period_desc = rp.get('description', '')
                start_date = rp.get('start_date', '')
                end_date = rp.get('end_date', '')
                severity = rp.get('severity', 'moderate')

                severity_label = {
                    'mild': '경미',
                    'moderate': '보통',
                    'severe': '심각'
                }.get(severity, '보통')

                severity_color = {
                    'mild': '#28a745',
                    'moderate': '#ffc107',
                    'severe': '#dc3545'
                }.get(severity, '#ffc107')

                period_text = f"""
                <para>
                <font color='{severity_color}'><b>[{severity_label}]</b></font> {period_desc}
                """
                if start_date and end_date:
                    period_text += f"<br/><font size=9 color='#666666'>기간: {start_date} ~ {end_date}</font>"
                period_text += "</para>"

                elements.append(Paragraph(period_text, self.styles['CustomBody']))
                elements.append(Spacer(1, 0.1*inch))

        elements.append(Spacer(1, 0.3*inch))

        # 5.2 회복 과정 설명
        elements.append(Paragraph(
            "<b>📈 회복 과정</b>",
            self.styles['CustomHeading1']
        ))

        recovery_text = """
        하락 이후 회복에는 일정 시간이 소요되었으며,
        이는 시장 환경의 영향을 받은 결과로 볼 수 있습니다.
        회복 기간은 하락 폭과 시장 상황에 따라 달라질 수 있습니다.
        """
        elements.append(Paragraph(recovery_text, self.styles['CustomBody']))

        return elements

    def _create_premium_comparison_section(self, explanation_data: dict):
        """맥락 비교 섹션 (고도화)"""
        elements = []

        elements.append(Paragraph(
            "<b>맥락 비교</b>",
            self.styles['CustomTitle']
        ))
        elements.append(Spacer(1, 0.3*inch))

        comparison = explanation_data.get('comparison', {})

        # 6.1 시장 대비 비교
        elements.append(Paragraph(
            "<b>📊 시장 대비 비교</b>",
            self.styles['CustomHeading1']
        ))

        benchmark_name = comparison.get('benchmark_name', '시장 지수')
        relative_performance = comparison.get('relative_performance', '')

        if relative_performance:
            elements.append(Paragraph(
                f"<b>비교 대상:</b> {benchmark_name}",
                self.styles['CustomBody']
            ))
            elements.append(Paragraph(relative_performance, self.styles['CustomBody']))

        elements.append(Spacer(1, 0.2*inch))

        # 추가 맥락 설명
        market_context = """
        동일 기간 시장 대비 변동성은 포트폴리오 구성에 따라 다르게 나타납니다.
        급등 구간에서의 수익과 급락 구간에서의 방어력은
        서로 상충되는 특성일 수 있습니다.
        """
        elements.append(Paragraph(market_context, self.styles['CustomBody']))

        # 비교 노트
        note = comparison.get('note', '')
        if note:
            elements.append(Spacer(1, 0.2*inch))
            note_text = f"<i><font color='#666666'>참고: {note}</font></i>"
            elements.append(Paragraph(note_text, self.styles['CustomBody']))

        return elements

    def _create_comprehensive_interpretation(self, explanation_data: dict):
        """종합 해석 섹션"""
        elements = []

        elements.append(Paragraph(
            "<b>종합 해석</b>",
            self.styles['CustomTitle']
        ))
        elements.append(Spacer(1, 0.3*inch))

        # 종합 해석 문구
        summary = explanation_data.get('summary', '')

        # 포트폴리오 특성 해석
        perf_exp = explanation_data.get('performance_explanation', [])

        # 변동성 수준 확인
        vol_level = None
        mdd_level = None
        for exp in perf_exp:
            if exp.get('metric') == 'Volatility':
                vol_level = exp.get('level', '')
            if exp.get('metric') == 'MDD':
                mdd_level = exp.get('level', '')

        # 종합 해석 생성
        if vol_level in ['low', 'very_low'] or mdd_level in ['low', 'very_low']:
            interpretation = """
            본 포트폴리오는 수익 극대화보다는 예측 가능한 흐름을 중시한 선택의 결과로 해석할 수 있습니다.
            이러한 특성은 장기 보유를 선호하는 투자자에게 심리적 안정감을 제공할 수 있습니다.
            """
        elif vol_level in ['high', 'very_high'] or mdd_level in ['high', 'very_high']:
            interpretation = """
            본 포트폴리오는 높은 성장 가능성을 추구한 선택의 결과로 해석할 수 있습니다.
            이러한 특성은 변동성을 감내할 수 있는 투자자에게 적합할 수 있으나,
            단기적으로 큰 폭의 가치 변동을 경험할 수 있습니다.
            """
        else:
            interpretation = """
            본 포트폴리오는 안정성과 성장성 사이의 균형을 추구한 선택의 결과로 해석할 수 있습니다.
            이러한 특성은 중장기 관점의 투자자에게 적합할 수 있습니다.
            """

        elements.append(Paragraph(interpretation, self.styles['CustomBody']))

        elements.append(Spacer(1, 0.2*inch))

        # 결론 박스
        conclusion_box = """
        <para backColor='#e8f4fd' borderPadding='15'>
        <b>💡 핵심 포인트</b><br/><br/>
        • 포트폴리오의 특성을 이해하는 것이 중요합니다<br/>
        • 과거 성과는 미래를 보장하지 않습니다<br/>
        • 자신의 투자 목표와 위험 감내 수준을 고려하세요
        </para>
        """
        elements.append(Paragraph(conclusion_box, self.styles['CustomBody']))

        return elements

    def _create_premium_disclaimer_section(self, explanation_data: dict):
        """참고 및 고지 섹션 (고도화)"""
        elements = []

        elements.append(Paragraph(
            "<b>참고 및 고지</b>",
            self.styles['CustomTitle']
        ))
        elements.append(Spacer(1, 0.3*inch))

        disclaimer = explanation_data.get('disclaimer', '')

        disclaimer_content = f"""
        <para>
        <b>⚠️ 중요 고지사항</b><br/><br/>

        {disclaimer}<br/><br/>

        <b>본 리포트에 대하여:</b><br/>
        • 본 리포트는 과거 데이터 기반 설명 자료입니다<br/>
        • 미래 성과를 보장하지 않습니다<br/>
        • 투자 권유, 추천, 자문이 아닙니다<br/>
        • 모든 투자 판단의 책임은 본인에게 있습니다<br/><br/>

        <b>데이터 정확성:</b><br/>
        본 분석에 사용된 데이터는 신뢰할 수 있는 출처에서 수집되었으나,
        데이터의 정확성을 100% 보장하지 않습니다.
        시장 상황은 변하며, 과거 패턴이 반복된다는 보장은 없습니다.<br/><br/>

        <b>전문가 상담:</b><br/>
        실제 투자 결정 전에는 반드시 공인된 금융 전문가와 상담하시기 바랍니다.<br/><br/>

        <font size=8 color='#999999'>
        © {datetime.now().year} Kingo Portfolio. All rights reserved.<br/>
        본 리포트의 무단 복제 및 배포를 금합니다.
        </font>
        </para>
        """

        elements.append(Paragraph(disclaimer_content, self.styles['CustomBody']))

        return elements

    def _get_level_korean(self, level: str) -> str:
        """수준 한글 변환"""
        level_map = {
            'very_low': '매우 낮음',
            'low': '낮음',
            'moderate': '보통',
            'high': '높음',
            'very_high': '매우 높음'
        }
        return level_map.get(level, '')
