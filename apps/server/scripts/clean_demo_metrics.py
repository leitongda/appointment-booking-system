"""清理 seed_demo_metrics.py 生成的演示数据

删除：
- appointment_no 前缀 'DEMO-' 的预约
- time_slot='DEMO' 的排班
- store_daily_metrics 全部预聚合行（可由聚合任务重算）

用法：python scripts/clean_demo_metrics.py
"""
from sqlalchemy import delete

from app.db.session import get_sync_db
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.store_metric import StoreDailyMetric


def main():
    with get_sync_db() as db:
        a = db.execute(delete(Appointment).where(Appointment.appointment_no.like("DEMO-%"))).rowcount
        s = db.execute(delete(Schedule).where(Schedule.time_slot == "DEMO")).rowcount
        m = db.execute(delete(StoreDailyMetric)).rowcount
    print(f"已删除：预约 {a} 条 / 排班 {s} 条 / 指标快照 {m} 条")


if __name__ == "__main__":
    main()
