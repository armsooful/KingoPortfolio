"""
이메일 발송 유틸리티
"""
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template

# 환경 변수에서 SMTP 설정 가져오기
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER)
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Foresto Compass")

# 프론트엔드 URL (이메일 인증 링크에 사용)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def generate_verification_token() -> str:
    """이메일 인증 토큰 생성 (보안 랜덤 문자열)"""
    return secrets.token_urlsafe(32)


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> bool:
    """
    이메일 발송 함수

    Args:
        to_email: 수신자 이메일
        subject: 이메일 제목
        html_content: HTML 본문
        text_content: 텍스트 본문 (선택사항)

    Returns:
        bool: 발송 성공 여부
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print("⚠️ SMTP credentials not configured. Email not sent.")
        return False

    try:
        # 이메일 메시지 생성
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        message["To"] = to_email

        # 텍스트 버전 추가
        if text_content:
            part1 = MIMEText(text_content, "plain")
            message.attach(part1)

        # HTML 버전 추가
        part2 = MIMEText(html_content, "html")
        message.attach(part2)

        # SMTP 서버에 연결하여 이메일 발송
        # 포트 465: implicit TLS (use_tls), 포트 587: STARTTLS
        if SMTP_PORT == 465:
            await aiosmtplib.send(
                message,
                hostname=SMTP_HOST,
                port=SMTP_PORT,
                username=SMTP_USER,
                password=SMTP_PASSWORD,
                use_tls=True,
            )
        else:
            await aiosmtplib.send(
                message,
                hostname=SMTP_HOST,
                port=SMTP_PORT,
                username=SMTP_USER,
                password=SMTP_PASSWORD,
                start_tls=True,
            )

        print(f"✅ Email sent successfully to {to_email}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {str(e)}")
        return False


async def send_verification_email(to_email: str, verification_token: str) -> bool:
    """
    이메일 인증 메일 발송

    Args:
        to_email: 수신자 이메일
        verification_token: 인증 토큰

    Returns:
        bool: 발송 성공 여부
    """
    # 인증 링크 생성
    verification_url = f"{FRONTEND_URL}/verify-email?token={verification_token}"

    # HTML 템플릿
    html_template = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 600px;
            margin: 20px auto;
            background: #ffffff;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 28px;
        }
        .content {
            padding: 40px 30px;
        }
        .content h2 {
            color: #667eea;
            margin-top: 0;
        }
        .button {
            display: inline-block;
            padding: 15px 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            margin: 20px 0;
        }
        .button:hover {
            opacity: 0.9;
        }
        .footer {
            background: #f8f9fa;
            padding: 20px 30px;
            text-align: center;
            font-size: 12px;
            color: #666;
        }
        .warning {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌲 Foresto Compass</h1>
        </div>
        <div class="content">
            <h2>이메일 인증</h2>
            <p>안녕하세요!</p>
            <p>Foresto Compass 회원가입을 환영합니다. 아래 버튼을 클릭하여 이메일 주소를 인증해주세요.</p>

            <div style="text-align: center;">
                <a href="{{ verification_url }}" class="button">이메일 인증하기</a>
            </div>

            <p>버튼이 작동하지 않는 경우, 아래 링크를 복사하여 브라우저에 붙여넣으세요:</p>
            <p style="word-break: break-all; color: #667eea;">{{ verification_url }}</p>

            <div class="warning">
                <strong>⚠️ 중요:</strong> 이 인증 링크는 24시간 동안만 유효합니다.
                본인이 요청하지 않았다면 이 이메일을 무시하셔도 됩니다.
            </div>
        </div>
        <div class="footer">
            <p>&copy; 2025 Foresto Compass. All rights reserved.</p>
            <p>이 이메일은 발신 전용입니다. 회신하지 마세요.</p>
        </div>
    </div>
</body>
</html>
    """)

    # 텍스트 템플릿 (HTML을 지원하지 않는 이메일 클라이언트용)
    text_template = Template("""
Foresto Compass 이메일 인증

안녕하세요!

Foresto Compass 회원가입을 환영합니다.
아래 링크를 클릭하여 이메일 주소를 인증해주세요.

인증 링크: {{ verification_url }}

이 인증 링크는 24시간 동안만 유효합니다.
본인이 요청하지 않았다면 이 이메일을 무시하셔도 됩니다.

© 2025 Foresto Compass. All rights reserved.
    """)

    html_content = html_template.render(verification_url=verification_url)
    text_content = text_template.render(verification_url=verification_url)

    return await send_email(
        to_email=to_email,
        subject="[Foresto Compass] 이메일 주소를 인증해주세요",
        html_content=html_content,
        text_content=text_content
    )


def is_verification_token_expired(sent_at: datetime, hours: int = 24) -> bool:
    """
    인증 토큰이 만료되었는지 확인

    Args:
        sent_at: 이메일 발송 시간
        hours: 유효 시간 (기본 24시간)

    Returns:
        bool: 만료 여부
    """
    if not sent_at:
        return True

    expiry_time = sent_at + timedelta(hours=hours)
    return datetime.utcnow() > expiry_time
