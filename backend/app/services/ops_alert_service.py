"""
Phase 3-C / Epic C-1: 운영 알림 서비스
생성일: 2026-01-18
목적: 배치 실패, 재처리 등 운영 이벤트 발생 시 알림 발송
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from sqlalchemy.orm import Session
import logging

from app.models.ops import OpsAlert, ErrorCodeMaster
from app.services.error_code_service import ErrorCodeService
from app.config import settings

logger = logging.getLogger(__name__)


class AlertType(str, Enum):
    """알림 유형"""
    BATCH_FAILED = "BATCH_FAILED"
    BATCH_STOPPED = "BATCH_STOPPED"
    REPLAY_EXECUTED = "REPLAY_EXECUTED"
    MANUAL_START = "MANUAL_START"
    DATA_CORRECTION = "DATA_CORRECTION"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class AlertLevel(str, Enum):
    """알림 레벨"""
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertChannel(str, Enum):
    """알림 채널"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"


class AlertError(Exception):
    """알림 관련 예외"""
    def __init__(self, message: str, error_code: str = "C1-ALT-001"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class OpsAlertService:
    """운영 알림 서비스"""

    def __init__(self, db: Session):
        self.db = db
        self.error_service = ErrorCodeService(db)
        self._email_enabled = settings.ops_alert_email_enabled
        self._slack_enabled = settings.ops_alert_slack_enabled
        self._webhook_url: Optional[str] = settings.ops_alert_webhook_url or None

    def configure(
        self,
        email_enabled: bool = True,
        slack_enabled: bool = False,
        webhook_url: Optional[str] = None,
    ) -> None:
        """알림 설정"""
        self._email_enabled = email_enabled
        self._slack_enabled = slack_enabled
        self._webhook_url = webhook_url

    def _resolve_alert_level(
        self,
        level: Optional[str],
        default: AlertLevel = AlertLevel.ERROR,
    ) -> AlertLevel:
        """문자열/Enum 입력을 AlertLevel로 정규화"""
        if isinstance(level, AlertLevel):
            return level
        if isinstance(level, str):
            try:
                return AlertLevel(level)
            except ValueError:
                return default
        return default

    def send_alert(
        self,
        alert_type: AlertType,
        alert_level: AlertLevel,
        title: str,
        message: str,
        execution_id: Optional[str] = None,
        error_code: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
        channels: Optional[List[AlertChannel]] = None,
    ) -> OpsAlert:
        """
        알림 발송

        Args:
            alert_type: 알림 유형
            alert_level: 알림 레벨
            title: 알림 제목
            message: 알림 메시지
            execution_id: 관련 배치 실행 ID
            error_code: 관련 오류 코드
            detail: 상세 정보
            channels: 발송 채널 (None이면 기본 채널)

        Returns:
            OpsAlert: 생성된 알림 레코드
        """
        # 기본 채널 설정
        if channels is None:
            channels = self._get_default_channels(alert_level)

        # 알림 레코드 생성
        alert = OpsAlert(
            alert_type=alert_type.value,
            alert_level=alert_level.value,
            execution_id=execution_id,
            related_error_code=error_code,
            alert_title=title,
            alert_message=message,
            alert_detail=detail,
            channels_sent=[c.value for c in channels],
            sent_at=datetime.utcnow(),
        )

        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        # 실제 발송
        self._dispatch_alert(alert, channels)

        return alert

    def send_batch_failed_alert(
        self,
        execution_id: str,
        job_id: str,
        error_code: str,
        error_message: str,
    ) -> OpsAlert:
        """배치 실패 알림"""
        error_info = self.error_service.get_full_info(error_code)
        alert_level = self._resolve_alert_level(
            error_info.get("alert_level"),
            default=AlertLevel.ERROR,
        )

        return self.send_alert(
            alert_type=AlertType.BATCH_FAILED,
            alert_level=alert_level,
            title=f"[BATCH FAILED] {job_id}",
            message=f"배치 실행 실패: {error_message}",
            execution_id=execution_id,
            error_code=error_code,
            detail={
                "job_id": job_id,
                "error_code": error_code,
                "ops_message": error_info.get("ops_message"),
                "action_guide": error_info.get("action_guide"),
            },
        )

    def send_batch_stopped_alert(
        self,
        execution_id: str,
        job_id: str,
        operator_id: str,
        reason: str,
    ) -> OpsAlert:
        """배치 수동 중단 알림"""
        return self.send_alert(
            alert_type=AlertType.BATCH_STOPPED,
            alert_level=AlertLevel.WARN,
            title=f"[BATCH STOPPED] {job_id}",
            message=f"배치 실행이 {operator_id}에 의해 중단되었습니다: {reason}",
            execution_id=execution_id,
            error_code="C1-BAT-002",
            detail={
                "job_id": job_id,
                "operator_id": operator_id,
                "reason": reason,
            },
        )

    def send_replay_alert(
        self,
        execution_id: str,
        job_id: str,
        operator_id: str,
        replay_reason: str,
        replay_type: str,
    ) -> OpsAlert:
        """재처리 실행 알림"""
        return self.send_alert(
            alert_type=AlertType.REPLAY_EXECUTED,
            alert_level=AlertLevel.INFO,
            title=f"[REPLAY] {job_id}",
            message=f"{operator_id}에 의해 {replay_type} 재처리가 실행되었습니다",
            execution_id=execution_id,
            detail={
                "job_id": job_id,
                "operator_id": operator_id,
                "replay_type": replay_type,
                "reason": replay_reason,
            },
        )

    def send_manual_start_alert(
        self,
        execution_id: str,
        job_id: str,
        operator_id: str,
        reason: str,
    ) -> OpsAlert:
        """배치 수동 시작/재개 알림"""
        return self.send_alert(
            alert_type=AlertType.MANUAL_START,
            alert_level=AlertLevel.INFO,
            title=f"[MANUAL START] {job_id}",
            message=f"배치 실행이 {operator_id}에 의해 시작/재개되었습니다: {reason}",
            execution_id=execution_id,
            detail={
                "job_id": job_id,
                "operator_id": operator_id,
                "reason": reason,
            },
        )

    def send_data_correction_alert(
        self,
        target_type: str,
        target_id: str,
        operator_id: str,
        reason: str,
    ) -> OpsAlert:
        """데이터 보정 알림"""
        return self.send_alert(
            alert_type=AlertType.DATA_CORRECTION,
            alert_level=AlertLevel.WARN,
            title=f"[DATA CORRECTION] {target_type}:{target_id}",
            message=f"{operator_id}에 의해 데이터 보정이 수행되었습니다: {reason}",
            detail={
                "target_type": target_type,
                "target_id": target_id,
                "operator_id": operator_id,
                "reason": reason,
            },
        )

    def send_auto_alert_by_error_code(
        self,
        execution_id: str,
        error_code: str,
        additional_message: Optional[str] = None,
    ) -> Optional[OpsAlert]:
        """
        오류 코드 기반 자동 알림

        auto_alert=True인 오류 코드에 대해 자동 알림 발송

        Args:
            execution_id: 배치 실행 ID
            error_code: 오류 코드
            additional_message: 추가 메시지

        Returns:
            OpsAlert: 생성된 알림 (auto_alert=False면 None)
        """
        if not self.error_service.should_auto_alert(error_code):
            return None

        error_info = self.error_service.get_full_info(error_code)
        alert_level = self._resolve_alert_level(
            error_info.get("alert_level"),
            default=AlertLevel.ERROR,
        )

        message = error_info.get("ops_message", "")
        if additional_message:
            message = f"{message}\n\n{additional_message}"

        return self.send_alert(
            alert_type=AlertType.SYSTEM_ERROR,
            alert_level=alert_level,
            title=f"[{error_code}] {error_info.get('category', 'SYS')} Error",
            message=message,
            execution_id=execution_id,
            error_code=error_code,
            detail={
                "severity": error_info.get("severity"),
                "action_guide": error_info.get("action_guide"),
            },
        )

    def acknowledge_alert(
        self,
        alert_id: int,
        acknowledged_by: str,
    ) -> OpsAlert:
        """
        알림 확인 처리

        Args:
            alert_id: 알림 ID
            acknowledged_by: 확인자 ID

        Returns:
            OpsAlert: 업데이트된 알림
        """
        alert = self.db.query(OpsAlert).filter_by(alert_id=alert_id).first()
        if not alert:
            raise AlertError(f"Alert not found: {alert_id}", "C1-ALT-002")

        if alert.acknowledged_by:
            raise AlertError(
                f"Alert already acknowledged by {alert.acknowledged_by}",
                "C1-ALT-003"
            )

        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(alert)

        return alert

    def get_alerts(
        self,
        alert_type: Optional[str] = None,
        alert_level: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[OpsAlert]:
        """알림 목록 조회"""
        query = self.db.query(OpsAlert)

        if alert_type:
            query = query.filter(OpsAlert.alert_type == alert_type)
        if alert_level:
            query = query.filter(OpsAlert.alert_level == alert_level)
        if acknowledged is not None:
            if acknowledged:
                query = query.filter(OpsAlert.acknowledged_by.isnot(None))
            else:
                query = query.filter(OpsAlert.acknowledged_by.is_(None))
        if start_date:
            query = query.filter(OpsAlert.created_at >= start_date)
        if end_date:
            query = query.filter(OpsAlert.created_at <= end_date)

        return (
            query
            .order_by(OpsAlert.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_alert(self, alert_id: int) -> Optional[OpsAlert]:
        """단일 알림 조회"""
        return self.db.query(OpsAlert).filter_by(alert_id=alert_id).first()

    def get_unacknowledged_alerts(
        self,
        alert_level: Optional[str] = None,
        limit: int = 50,
    ) -> List[OpsAlert]:
        """미확인 알림 조회"""
        query = self.db.query(OpsAlert).filter(
            OpsAlert.acknowledged_by.is_(None)
        )

        if alert_level:
            query = query.filter(OpsAlert.alert_level == alert_level)

        return query.order_by(OpsAlert.created_at.desc()).limit(limit).all()

    def get_alerts_by_execution(
        self,
        execution_id: str,
    ) -> List[OpsAlert]:
        """배치 실행별 알림 조회"""
        return self.db.query(OpsAlert).filter(
            OpsAlert.execution_id == execution_id
        ).order_by(OpsAlert.created_at.desc()).all()

    def count_unacknowledged(
        self,
        alert_level: Optional[str] = None,
    ) -> int:
        """미확인 알림 건수"""
        query = self.db.query(OpsAlert).filter(
            OpsAlert.acknowledged_by.is_(None)
        )

        if alert_level:
            query = query.filter(OpsAlert.alert_level == alert_level)

        return query.count()

    def _get_default_channels(
        self,
        alert_level: AlertLevel,
    ) -> List[AlertChannel]:
        """레벨별 기본 발송 채널"""
        channels = []

        if self._email_enabled:
            channels.append(AlertChannel.EMAIL)

        if self._slack_enabled and alert_level in [AlertLevel.ERROR, AlertLevel.CRITICAL]:
            channels.append(AlertChannel.SLACK)

        if self._webhook_url and alert_level == AlertLevel.CRITICAL:
            channels.append(AlertChannel.WEBHOOK)

        return channels if channels else [AlertChannel.EMAIL]

    def _dispatch_alert(
        self,
        alert: OpsAlert,
        channels: List[AlertChannel],
    ) -> None:
        """실제 알림 발송"""
        for channel in channels:
            try:
                if channel == AlertChannel.EMAIL:
                    self._send_email(alert)
                elif channel == AlertChannel.SLACK:
                    self._send_slack(alert)
                elif channel == AlertChannel.WEBHOOK:
                    self._send_webhook(alert)
            except Exception as e:
                logger.error(f"Failed to send alert via {channel}: {e}")

    def _send_email(self, alert: OpsAlert) -> bool:
        """이메일 발송 (async send_email 호출)"""
        alert_email = settings.alert_email
        if not alert_email:
            logger.info("[EMAIL] alert_email 미설정 — skip")
            return False

        import asyncio
        from app.utils.email import send_email

        level_colors = {
            "CRITICAL": "#dc2626",
            "ERROR": "#ea580c",
            "WARN": "#d97706",
            "INFO": "#2563eb",
        }
        color = level_colors.get(alert.alert_level, "#6b7280")

        detail_html = ""
        if alert.alert_detail:
            import json
            detail_html = (
                f'<pre style="background:#f1f5f9;padding:12px;border-radius:6px;'
                f'font-size:13px;overflow-x:auto;">'
                f'{json.dumps(alert.alert_detail, ensure_ascii=False, indent=2)}</pre>'
            )

        html = (
            f'<div style="font-family:sans-serif;max-width:600px;margin:0 auto;">'
            f'<div style="background:{color};color:#fff;padding:16px 20px;border-radius:8px 8px 0 0;">'
            f'<h2 style="margin:0;font-size:18px;">[{alert.alert_level}] {alert.alert_title}</h2>'
            f'</div>'
            f'<div style="padding:20px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 8px 8px;">'
            f'<p style="margin:0 0 12px;color:#374151;">{alert.alert_message}</p>'
            f'{detail_html}'
            f'<p style="margin:12px 0 0;font-size:12px;color:#9ca3af;">Foresto Compass Ops Alert</p>'
            f'</div></div>'
        )

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(send_email(
                    to_email=alert_email,
                    subject=f"[Ops {alert.alert_level}] {alert.alert_title}",
                    html_content=html,
                ))
            else:
                loop.run_until_complete(send_email(
                    to_email=alert_email,
                    subject=f"[Ops {alert.alert_level}] {alert.alert_title}",
                    html_content=html,
                ))
            logger.info("[EMAIL] Alert sent to %s: %s", alert_email, alert.alert_title)
            return True
        except Exception as e:
            logger.error("[EMAIL] Failed to send alert: %s", e)
            return False

    def _send_slack(self, alert: OpsAlert) -> bool:
        """Slack Incoming Webhook 발송"""
        webhook_url = settings.slack_webhook_url
        if not webhook_url:
            logger.info("[SLACK] slack_webhook_url 미설정 — skip")
            return False

        import json
        import requests

        level_colors = {
            "CRITICAL": "#dc2626",
            "ERROR": "#ea580c",
            "WARN": "#d97706",
            "INFO": "#2563eb",
        }
        color = level_colors.get(alert.alert_level, "#6b7280")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"[{alert.alert_level}] {alert.alert_title}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": alert.alert_message},
            },
        ]

        if alert.alert_detail:
            detail_text = json.dumps(alert.alert_detail, ensure_ascii=False, indent=2)
            if len(detail_text) > 2900:
                detail_text = detail_text[:2900] + "\n..."
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"```{detail_text}```"},
            })

        payload = {
            "attachments": [{
                "color": color,
                "blocks": blocks,
            }]
        }

        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info("[SLACK] Alert sent: %s", alert.alert_title)
            return True
        except Exception as e:
            logger.error("[SLACK] Failed to send alert: %s", e)
            return False

    def _send_webhook(self, alert: OpsAlert) -> bool:
        """Webhook 발송"""
        if not self._webhook_url:
            return False

        import json
        import requests

        payload = {
            "alert_id": alert.alert_id,
            "alert_type": alert.alert_type,
            "alert_level": alert.alert_level,
            "title": alert.alert_title,
            "message": alert.alert_message,
            "detail": alert.alert_detail,
            "sent_at": str(alert.sent_at),
        }

        try:
            resp = requests.post(self._webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info("[WEBHOOK] Alert sent: %s", alert.alert_title)
            return True
        except Exception as e:
            logger.error("[WEBHOOK] Failed to send alert: %s", e)
            return False
