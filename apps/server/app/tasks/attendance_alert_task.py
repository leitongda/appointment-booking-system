"""考勤异常告警 Celery 任务"""
import logging
from collections import Counter
from datetime import date, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.enums.message import MessageType
from app.models.account import Account
from app.models.attendance import AttendanceStatDaily
from app.models.message import Message
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

# 严重迟到阈值（分钟）
SEVERE_LATE_MINUTES = 30
# 严重早退阈值（分钟）
SEVERE_EARLY_MINUTES = 30
# 连续异常检测天数窗口
CONSECUTIVE_WINDOW_DAYS = 3
# 连续异常最小触发次数
CONSECUTIVE_THRESHOLD = 2


@celery_app.task(
    name="attendance_alert",
    queue="scheduled",
    max_retries=3,
    default_retry_delay=60,
)
def attendance_alert(target_date_str: str | None = None):
    """检测考勤异常并发送告警

    检测以下异常：
    1. 缺勤：有排班但无打卡记录
    2. 严重迟到（>30分钟）
    3. 严重早退（>30分钟）
    4. 连续异常（最近3天中2天以上异常）
    """
    if target_date_str:
        target_date = date.fromisoformat(target_date_str)
    else:
        target_date = date.today() - timedelta(days=1)

    logger.info("开始考勤异常检测: %s", target_date)

    with get_sync_db() as db:
        tenants = db.execute(
            select(Tenant).where(Tenant.status == 1)
        ).scalars().all()

        total_alerts = 0
        for tenant in tenants:
            alerts = _detect_anomalies(db, tenant.id, target_date)
            if alerts:
                _send_alerts(db, tenant.id, alerts)
                total_alerts += len(alerts)

        db.commit()
        logger.info("考勤异常检测完成: %s, 发现 %d 条异常", target_date, total_alerts)

    return {"date": str(target_date), "alerts": total_alerts}


def _detect_anomalies(db: Session, tenant_id: str, target_date: date) -> list[dict]:
    """检测单个租户的考勤异常"""
    anomalies = []

    # 获取当日统计记录
    stats = db.execute(
        select(AttendanceStatDaily).where(
            and_(
                AttendanceStatDaily.tenant_id == tenant_id,
                AttendanceStatDaily.date == target_date,
            )
        )
    ).scalars().all()

    for stat in stats:
        if stat.status == "absent":
            anomalies.append({
                "account_id": stat.account_id,
                "type": "absent",
                "message": "缺勤",
                "date": target_date,
            })
        elif stat.status == "late" and stat.late_minutes > SEVERE_LATE_MINUTES:
            anomalies.append({
                "account_id": stat.account_id,
                "type": "severe_late",
                "message": f"严重迟到 {stat.late_minutes} 分钟",
                "date": target_date,
            })
        elif stat.status == "early" and stat.early_minutes > SEVERE_EARLY_MINUTES:
            anomalies.append({
                "account_id": stat.account_id,
                "type": "severe_early",
                "message": f"严重早退 {stat.early_minutes} 分钟",
                "date": target_date,
            })

    # 检测连续异常（最近 N 天有 >= 阈值天数异常）
    window_start = target_date - timedelta(days=CONSECUTIVE_WINDOW_DAYS - 1)
    recent_stats = db.execute(
        select(AttendanceStatDaily).where(
            and_(
                AttendanceStatDaily.tenant_id == tenant_id,
                AttendanceStatDaily.date >= window_start,
                AttendanceStatDaily.date <= target_date,
                AttendanceStatDaily.status.in_(["late", "early", "absent"]),
            )
        )
    ).scalars().all()

    anomaly_counts = Counter(s.account_id for s in recent_stats)
    # 去重：已添加的严重异常不重复追加连续异常
    existing_types = {(a["account_id"], a["type"]) for a in anomalies}
    for account_id, count in anomaly_counts.items():
        if count >= CONSECUTIVE_THRESHOLD:
            if (account_id, "consecutive") not in existing_types:
                anomalies.append({
                    "account_id": account_id,
                    "type": "consecutive",
                    "message": f"连续 {count} 天考勤异常",
                    "date": target_date,
                })

    return anomalies


def _send_alerts(db: Session, tenant_id: str, alerts: list[dict]):
    """发送考勤异常告警（站内信）"""
    account_ids = {a["account_id"] for a in alerts}
    accounts = db.execute(
        select(Account).where(Account.id.in_(account_ids))
    ).scalars().all()
    account_map = {a.id: a for a in accounts}

    for alert in alerts:
        account = account_map.get(alert["account_id"])
        if not account:
            continue

        display_name = account.name or account.username or account.phone or "未知用户"
        logger.info(
            "考勤异常告警: %s - %s (%s)",
            display_name, alert["message"], alert["date"],
        )

        try:
            message = Message(
                tenant_id=tenant_id,
                user_id=alert["account_id"],
                user_type="doctor",
                title="考勤异常提醒",
                content=f"您在 {alert['date']} 的考勤存在异常：{alert['message']}",
                message_type=MessageType.SYSTEM.value,
            )
            db.add(message)
        except Exception as e:
            logger.warning("发送考勤告警通知失败: %s", e)
