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
