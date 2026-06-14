"""生成平台经营看板演示数据（DEMO 标记，便于清理）

仅在空开发库用于演示。生成：
- 近 30 天排班（Schedule.store_id 轮询 4 个门店，time_slot='DEMO' 标记）
- 基于排班的预约（appointment_no 前缀 'DEMO-'，状态加权分布）
- 优先用有诊费配置的医生，保证营收可计算

清理：见脚本末尾 print 的清理命令。

用法：python scripts/seed_demo_metrics.py
"""
import random
import uuid
from datetime import date, time, timedelta

from sqlalchemy import select, func, delete

from app.db.session import get_sync_db
from app.models.tenant import Tenant
from app.models.store import Store
from app.models.doctor import Doctor
from app.models.user import Patient
from app.models.schedule import Schedule
from app.models.appointment import Appointment
from app.models.consultation_fee import DoctorConsultationFee

random.seed(42)  # 可复现

# 预约状态加权分布（让看板好看：多已完成 + 一定爽约/取消）
STATUS_WEIGHTS = [
    (5, 40),   # 已完成
    (2, 15),   # 已签到
    (1, 12),   # 已预约
    (8, 12),   # 爽约
    (6, 10),   # 取消
    (4, 6),    # 就诊中
    (3, 5),    # 历史候诊
]
_STATUS_POOL = [s for s, w in STATUS_WEIGHTS for _ in range(w)]


def _weighted_status() -> int:
    return random.choice(_STATUS_POOL)


def main():
    today = date.today()
    # 就诊日：近 30 天、不含今天（让状态都已确定）
    target_dates = [today - timedelta(days=i) for i in range(1, 30)]

    with get_sync_db() as db:
        tenant_id = db.scalar(select(Tenant.id).limit(1))
        stores = db.execute(
            select(Store.id, Store.name, Store.tenant_id)
            .where(Store.tenant_id == tenant_id, Store.status == 1)
        ).all()
        if not stores:
            print("无可用门店，退出"); return
        patients = db.execute(
            select(Patient.id, Patient.user_id).where(Patient.tenant_id == tenant_id)
        ).all()
        if not patients:
            print("无可用患者，退出"); return

        # 优先用有诊费配置的医生（保证营收可算），不足则补未删除医生
        fee_doc_ids = set(db.execute(
            select(DoctorConsultationFee.doctor_id).distinct()
        ).scalars().all())
        doctors = db.execute(
            select(Doctor.id).where(Doctor.deleted_at.is_(None))
        ).scalars().all()
        with_fee = [d for d in doctors if d in fee_doc_ids]
        without_fee = [d for d in doctors if d not in fee_doc_ids]
        chosen = (with_fee + without_fee)[:12]  # 最多 12 个医生
        if not chosen:
            print("无可用医生，退出"); return

        print(f"门店 {len(stores)} 家 / 医生 {len(chosen)} 名（其中 {len(with_fee)} 有诊费）/ 患者 {len(patients)} 名")
        print(f"就诊日范围: {target_dates[-1]} ~ {target_dates[0]}（{len(target_dates)} 天）")

        # 清理旧 DEMO 数据（幂等可重跑）
        db.execute(delete(Appointment).where(Appointment.appointment_no.like("DEMO-%")))
        db.execute(delete(Schedule).where(Schedule.time_slot == "DEMO"))

        sched_count = 0
        appt_count = 0
        for d_idx, d in enumerate(target_dates):
            for doc_idx, doc in enumerate(chosen):
                store = stores[(doc_idx + d_idx) % len(stores)]  # 轮询门店
                sched = Schedule(
                    id=str(uuid.uuid4()),
                    doctor_id=doc,
                    store_id=store.id,
                    tenant_id=tenant_id,
                    schedule_date=d,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                    time_slot="DEMO",
                    appointment_type="normal",
                    total_slots=20,
                    timezone="Asia/Shanghai",
                )
                db.add(sched)
                db.flush()
                sched_count += 1

                n = random.randint(1, 6)
                for _ in range(n):
                    p = random.choice(patients)
                    appt = Appointment(
                        id=str(uuid.uuid4()),
                        appointment_no=f"DEMO-{uuid.uuid4().hex[:12]}",
                        user_id=p.user_id,
                        patient_id=p.id,
                        doctor_id=doc,
                        schedule_id=sched.id,
                        tenant_id=tenant_id,
                        status=_weighted_status(),
                    )
                    db.add(appt)
                    appt_count += 1
        # get_sync_db 退出时自动 commit

    print(f"生成排班 {sched_count} 条 / 预约 {appt_count} 条（已提交）")

    # 跑回填聚合
    from app.tasks.store_metric_task import aggregate_store_daily_metrics
    result = aggregate_store_daily_metrics(backfill_days=30)
    print(f"回填聚合完成: {result}")

    print("\n清理演示数据：python scripts/clean_demo_metrics.py")


if __name__ == "__main__":
    main()
