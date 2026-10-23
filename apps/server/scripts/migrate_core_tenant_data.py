#!/usr/bin/env python3
"""
核心业务表租户数据迁移脚本

执行步骤:
1. 全量备份数据库
2. 按依赖顺序回填 tenant_id（只做“可推导”的回填）:
   - Doctor / Department / Schedule / ScheduleTemplate (store_id -> stores.tenant_id)
   - Appointment (schedule_id -> schedules.tenant_id)
   - Patient (store_id -> stores.tenant_id，回退最近一次预约)
   - User (按患者所属租户拆分)
   - MedicalRecord / ExaminationReport (appointment/store/patient/doctor -> tenant_id)
   - FollowUpPlan (department_id -> departments.tenant_id)
   - FollowUpTask / FollowUpRecord (appointment/patient/doctor/plan -> tenant_id)
   - FollowUpSelfReport (patient_id -> patients.tenant_id)
   - Message (store/user/admin -> tenant_id)
   - WaitlistEntry (schedule/patient -> tenant_id)
3. 验证数据完整性

原则（R4-14）:
- **禁止默认租户兜底**：无法从业务关系推导的行保持 tenant_id=NULL 并计入
  “不可推导(NULL)”统计，交由人工核对；不得写入 default 租户。
- --dry-run 输出各表“可推导”与“不可推导(NULL)”数量，以及合计；
  --execute 只回填可推导行，并重新统计剩余不可推导行；
  --verify 检查业务表 NULL 是否为 0（follow_up_plans 中 department_id 为
  NULL 的平台级模板除外）。

使用方法:
    # 预览模式（不执行修改）
    python scripts/migrate_core_tenant_data.py --dry-run

    # 执行迁移
    python scripts/migrate_core_tenant_data.py --execute

    # 验证迁移结果
    python scripts/migrate_core_tenant_data.py --verify
"""
import argparse
import os
import sys
import uuid

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.appointment import Appointment
from app.models.user import Patient, User


class TenantDataMigrator:
    """租户数据迁移器"""

    def __init__(self, db: Session, dry_run: bool = True):
        self.db = db
        self.dry_run = dry_run
        self.stats = {
            'doctors_updated': 0,
            'departments_updated': 0,
            'schedules_updated': 0,
            'schedule_templates_updated': 0,
            'appointments_updated': 0,
            'patients_updated': 0,
            'users_updated': 0,
            'users_created': 0,
            'medical_records_updated': 0,
            'examination_reports_updated': 0,
            'follow_up_plans_updated': 0,
            'follow_up_tasks_updated': 0,
            'follow_up_records_updated': 0,
            'follow_up_self_reports_updated': 0,
            'messages_updated': 0,
            'waitlist_entries_updated': 0,
            'resolvable_pending': 0,
            'unresolved': {},
            'errors': [],
        }

    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        prefix = "[DRY-RUN] " if self.dry_run else ""
        print(f"{prefix}[{level}] {message}")

    # ------------------------------------------------------------------ 基础工具
    def _count(self, sql: str, params: dict | None = None) -> int:
        return int(self.db.execute(text(sql), params or {}).scalar() or 0)

    def _mark_unresolved(self, label: str, count: int) -> None:
        self.stats['unresolved'][label] = count

    def _run_backfill(
        self,
        key: str,
        label: str,
        update_sql: str,
        resolvable_sql: str,
        unresolved_sql: str,
    ) -> None:
        """执行一条“可推导”回填。

        dry-run：只统计可推导 / 不可推导(NULL) 数量，不写库；
        execute：先回填，再统计剩余不可推导行。
        任何情况下都不使用默认租户兜底。
        """
        if self.dry_run:
            resolvable = self._count(resolvable_sql)
            unresolved = self._count(unresolved_sql)
            self.stats[key] = resolvable
            self.stats['resolvable_pending'] += resolvable
            self._mark_unresolved(label, unresolved)
            self.log(f"{label}: 可推导 {resolvable} 条，不可推导(NULL) {unresolved} 条")
            return

        result = self.db.execute(text(update_sql))
        updated = max(result.rowcount or 0, 0)
        self.stats[key] = updated
        self.db.commit()
        remaining = self._count(unresolved_sql)
        self._mark_unresolved(label, remaining)
        self.log(f"{label}: 已回填 {updated} 条，仍不可推导(NULL) {remaining} 条")

    # ------------------------------------------------------------------ 各表回填
    def migrate_doctors(self):
        """医生表：store_id -> tenant_id（无门店保持 NULL，不使用默认租户）"""
        self.log("开始迁移 doctors 表...")
        self._run_backfill(
            key='doctors_updated',
            label='doctors',
            update_sql="""
                UPDATE doctors d
                SET tenant_id = s.tenant_id
                FROM stores s
                WHERE d.store_id = s.id
                  AND d.tenant_id IS NULL
                  AND s.tenant_id IS NOT NULL
            """,
            resolvable_sql="""
                SELECT count(*) FROM doctors d
                JOIN stores s ON s.id = d.store_id
                WHERE d.tenant_id IS NULL AND s.tenant_id IS NOT NULL
            """,
            unresolved_sql="""
                SELECT count(*) FROM doctors d
                LEFT JOIN stores s ON s.id = d.store_id
                WHERE d.tenant_id IS NULL AND (s.id IS NULL OR s.tenant_id IS NULL)
            """,
        )
        self.log(f"医生表迁移完成，更新 {self.stats['doctors_updated']} 条记录")

    def migrate_departments(self):
        """科室表：store_id -> tenant_id（无门店保持 NULL，不使用默认租户）"""
        self.log("开始迁移 departments 表...")
        self._run_backfill(
            key='departments_updated',
            label='departments',
            update_sql="""
                UPDATE departments d
                SET tenant_id = s.tenant_id
                FROM stores s
                WHERE d.store_id = s.id
                  AND d.tenant_id IS NULL
                  AND s.tenant_id IS NOT NULL
            """,
            resolvable_sql="""
                SELECT count(*) FROM departments d
                JOIN stores s ON s.id = d.store_id
                WHERE d.tenant_id IS NULL AND s.tenant_id IS NOT NULL
            """,
            unresolved_sql="""
                SELECT count(*) FROM departments d
                LEFT JOIN stores s ON s.id = d.store_id
                WHERE d.tenant_id IS NULL AND (s.id IS NULL OR s.tenant_id IS NULL)
            """,
        )
        self.log(f"科室表迁移完成，更新 {self.stats['departments_updated']} 条记录")

    def migrate_schedules(self):
        """排班表：store_id -> tenant_id"""
        self.log("开始迁移 schedules 表...")
        self._run_backfill(
            key='schedules_updated',
            label='schedules',
            update_sql="""
                UPDATE schedules s
                SET tenant_id = st.tenant_id
                FROM stores st
                WHERE s.store_id = st.id
                  AND s.tenant_id IS NULL
                  AND st.tenant_id IS NOT NULL
            """,
            resolvable_sql="""
                SELECT count(*) FROM schedules s
                JOIN stores st ON st.id = s.store_id
                WHERE s.tenant_id IS NULL AND st.tenant_id IS NOT NULL
            """,
            unresolved_sql="""
                SELECT count(*) FROM schedules s
                LEFT JOIN stores st ON st.id = s.store_id
                WHERE s.tenant_id IS NULL AND (st.id IS NULL OR st.tenant_id IS NULL)
            """,
        )
        self.log(f"排班表迁移完成，更新 {self.stats['schedules_updated']} 条记录")

    def migrate_schedule_templates(self):
        """排班模板表：store_id -> tenant_id"""
        self.log("开始迁移 schedule_templates 表...")
        self._run_backfill(
            key='schedule_templates_updated',
            label='schedule_templates',
            update_sql="""
                UPDATE schedule_templates st
                SET tenant_id = s.tenant_id
                FROM stores s
                WHERE st.store_id = s.id
                  AND st.tenant_id IS NULL
                  AND s.tenant_id IS NOT NULL
            """,
            resolvable_sql="""
                SELECT count(*) FROM schedule_templates st
                JOIN stores s ON s.id = st.store_id
                WHERE st.tenant_id IS NULL AND s.tenant_id IS NOT NULL
            """,
            unresolved_sql="""
                SELECT count(*) FROM schedule_templates st
                LEFT JOIN stores s ON s.id = st.store_id
                WHERE st.tenant_id IS NULL AND (s.id IS NULL OR s.tenant_id IS NULL)
            """,
        )
        self.log(f"排班模板表迁移完成，更新 {self.stats['schedule_templates_updated']} 条记录")

    def migrate_appointments(self):
        """预约表：schedule_id -> schedules.tenant_id"""
        self.log("开始迁移 appointments 表...")
        self._run_backfill(
            key='appointments_updated',
            label='appointments',
            update_sql="""
                UPDATE appointments a
                SET tenant_id = s.tenant_id
                FROM schedules s
                WHERE a.schedule_id = s.id
                  AND a.tenant_id IS NULL
                  AND s.tenant_id IS NOT NULL
            """,
            resolvable_sql="""
                SELECT count(*) FROM appointments a
                JOIN schedules s ON a.schedule_id = s.id
                WHERE a.tenant_id IS NULL AND s.tenant_id IS NOT NULL
            """,
            unresolved_sql="""
                SELECT count(*) FROM appointments a
                LEFT JOIN schedules s ON a.schedule_id = s.id
                WHERE a.tenant_id IS NULL AND (s.id IS NULL OR s.tenant_id IS NULL)
            """,
        )
        self.log(f"预约表迁移完成，更新 {self.stats['appointments_updated']} 条记录")

    def migrate_patients(self):
        """患者表：store_id -> tenant_id，回退到最近一次带租户的预约"""
        self.log("开始迁移 patients 表...")

        def derived(x: str) -> str:
            """按给定别名生成可推导的 tenant_id 表达式。"""
            return f"""
                COALESCE(
                    (SELECT s.tenant_id FROM stores s WHERE s.id = {x}.store_id),
                    (SELECT a.tenant_id FROM appointments a
                      WHERE a.patient_id = {x}.id AND a.tenant_id IS NOT NULL
                      ORDER BY a.created_at DESC LIMIT 1)
                )
            """

        self._run_backfill(
            key='patients_updated',
            label='patients',
            update_sql=f"""
                UPDATE patients p
                SET tenant_id = src.tenant_id
                FROM (
                    SELECT p2.id, {derived('p2')} AS tenant_id
                    FROM patients p2
                    WHERE p2.tenant_id IS NULL
                ) src
                WHERE p.id = src.id AND src.tenant_id IS NOT NULL
            """,
            resolvable_sql=f"""
                SELECT count(*) FROM patients p
                WHERE p.tenant_id IS NULL AND {derived('p')} IS NOT NULL
            """,
            unresolved_sql=f"""
                SELECT count(*) FROM patients p
                WHERE p.tenant_id IS NULL AND {derived('p')} IS NULL
            """,
        )
        self.log(f"患者表迁移完成，更新 {self.stats['patients_updated']} 条记录")

    def migrate_users(self):
        """
        迁移用户表（核心：按租户拆分）

        策略：
        1. 获取用户所有患者及其租户归属
        2. 如果只属于一个租户，直接更新 tenant_id
        3. 如果跨多租户，需要拆分 User
        4. 没有任何患者记录的用户无法推导租户，保持 NULL（不落默认租户）
        """
        self.log("开始迁移 users 表（可能需要拆分）...")

        users = self.db.execute(
            select(User).where(User.tenant_id == None)
        ).scalars().all()

        no_patient_users = 0
        for user in users:
            patients_query = text("""
                SELECT DISTINCT p.tenant_id, p.id as patient_id
                FROM patients p
                WHERE p.user_id = :user_id AND p.tenant_id IS NOT NULL
            """)
            result = self.db.execute(patients_query, {"user_id": user.id}).fetchall()

            tenant_ids = list(set([row[0] for row in result]))

            if len(tenant_ids) == 0:
                # 没有可推导的租户：保持 NULL，禁止默认租户兜底
                no_patient_users += 1
                self.log(f"  User {user.id} ({user.phone or user.nickname}) 无可推导租户，保持 NULL", "WARN")
                continue

            if len(tenant_ids) == 1:
                tenant_id = tenant_ids[0]
                if not self.dry_run:
                    user.tenant_id = tenant_id
                self.stats['users_updated'] += 1
                self.log(f"  User {user.id} ({user.phone or user.nickname}) -> tenant {tenant_id}")
            else:
                self.log(f"  User {user.id} ({user.phone or user.nickname}) 跨 {len(tenant_ids)} 个租户，需要拆分")

                for i, tenant_id in enumerate(tenant_ids):
                    if i == 0:
                        if not self.dry_run:
                            user.tenant_id = tenant_id
                        self.stats['users_updated'] += 1
                        self.log(f"    -> 原 User 保留，tenant_id = {tenant_id}")
                    else:
                        if not self.dry_run:
                            new_user = User(
                                id=str(uuid.uuid4()),
                                tenant_id=tenant_id,
                                phone=user.phone,
                                password_hash=user.password_hash,
                                nickname=user.nickname,
                                avatar=user.avatar,
                                gender=user.gender,
                                openid=None,  # 新用户的 openid 需要重新绑定
                                status=user.status,
                                points=0,  # 新用户积分从 0 开始
                                unionid=None,
                                wechat_nickname=user.wechat_nickname,
                                wechat_avatar=user.wechat_avatar,
                            )
                            self.db.add(new_user)
                            self.db.flush()  # 获取 new_user.id

                            patient_ids = [row[1] for row in result if row[0] == tenant_id]
                            self.db.execute(
                                update(Patient)
                                .where(Patient.id.in_(patient_ids))
                                .values(user_id=new_user.id, tenant_id=tenant_id)
                            )
                            self.db.execute(
                                update(Appointment)
                                .where(Appointment.patient_id.in_(patient_ids))
                                .values(user_id=new_user.id)
                            )

                        self.stats['users_created'] += 1
                        self.log(f"    -> 创建新 User，tenant_id = {tenant_id}")

        self._mark_unresolved('users(无可推导患者)', no_patient_users)

        if not self.dry_run:
            self.db.commit()
        self.log(f"用户表迁移完成，更新 {self.stats['users_updated']} 条，新建 {self.stats['users_created']} 条")

    # ------------------------------------------------ R4-14 新增：业务从属表回填
    def migrate_medical_records(self):
        """病历：appointment / patient / doctor -> tenant_id"""
        self.log("开始迁移 medical_records 表...")

        def derived(x: str) -> str:
            return f"""
                COALESCE(
                    (SELECT a.tenant_id FROM appointments a WHERE a.id = {x}.appointment_id),
                    (SELECT p.tenant_id FROM patients p WHERE p.id = {x}.patient_id),
                    (SELECT d.tenant_id FROM doctors d WHERE d.id = {x}.doctor_id)
                )
            """

        self._run_backfill(
            key='medical_records_updated',
            label='medical_records',
            update_sql=f"""
                UPDATE medical_records m
                SET tenant_id = src.tenant_id
                FROM (
                    SELECT m2.id, {derived('m2')} AS tenant_id
                    FROM medical_records m2
                    WHERE m2.tenant_id IS NULL
                ) src
                WHERE m.id = src.id AND src.tenant_id IS NOT NULL
            """,
            resolvable_sql=f"SELECT count(*) FROM medical_records m WHERE m.tenant_id IS NULL AND {derived('m')} IS NOT NULL",
            unresolved_sql=f"SELECT count(*) FROM medical_records m WHERE m.tenant_id IS NULL AND {derived('m')} IS NULL",
        )
        self.log(f"病历表迁移完成，更新 {self.stats['medical_records_updated']} 条记录")

    def migrate_examination_reports(self):
        """检查报告：appointment / store / patient / doctor -> tenant_id"""
        self.log("开始迁移 examination_reports 表...")

        def derived(x: str) -> str:
            return f"""
                COALESCE(
                    (SELECT a.tenant_id FROM appointments a WHERE a.id = {x}.appointment_id),
                    (SELECT s.tenant_id FROM stores s WHERE s.id = {x}.store_id),
                    (SELECT p.tenant_id FROM patients p WHERE p.id = {x}.patient_id),
                    (SELECT d.tenant_id FROM doctors d WHERE d.id = {x}.doctor_id)
                )
            """

        self._run_backfill(
            key='examination_reports_updated',
            label='examination_reports',
            update_sql=f"""
                UPDATE examination_reports e
                SET tenant_id = src.tenant_id
                FROM (
                    SELECT e2.id, {derived('e2')} AS tenant_id
                    FROM examination_reports e2
                    WHERE e2.tenant_id IS NULL
                ) src
                WHERE e.id = src.id AND src.tenant_id IS NOT NULL
            """,
            resolvable_sql=f"SELECT count(*) FROM examination_reports e WHERE e.tenant_id IS NULL AND {derived('e')} IS NOT NULL",
            unresolved_sql=f"SELECT count(*) FROM examination_reports e WHERE e.tenant_id IS NULL AND {derived('e')} IS NULL",
        )
        self.log(f"检查报告表迁移完成，更新 {self.stats['examination_reports_updated']} 条记录")

    def migrate_follow_up_plans(self):
        """随访计划：department_id -> departments.tenant_id。

        department_id 为 NULL 的是平台级全局模板，tenant_id=NULL 属预期语义，
        既不计入可推导，也不计入不可推导。
        """
        self.log("开始迁移 follow_up_plans 表...")
        self._run_backfill(
            key='follow_up_plans_updated',
            label='follow_up_plans',
            update_sql="""
                UPDATE follow_up_plans fp
                SET tenant_id = d.tenant_id
                FROM departments d
                WHERE fp.department_id = d.id
                  AND fp.tenant_id IS NULL
                  AND d.tenant_id IS NOT NULL
            """,
            resolvable_sql="""
                SELECT count(*) FROM follow_up_plans fp
                JOIN departments d ON d.id = fp.department_id
                WHERE fp.tenant_id IS NULL AND d.tenant_id IS NOT NULL
            """,
            unresolved_sql="""
                SELECT count(*) FROM follow_up_plans fp
                LEFT JOIN departments d ON d.id = fp.department_id
                WHERE fp.tenant_id IS NULL
                  AND fp.department_id IS NOT NULL
                  AND (d.id IS NULL OR d.tenant_id IS NULL)
            """,
        )
        self.log(f"随访计划表迁移完成，更新 {self.stats['follow_up_plans_updated']} 条记录")

    def migrate_follow_up_tasks(self):
        """随访任务：appointment / patient / doctor / plan -> tenant_id"""
        self.log("开始迁移 follow_up_tasks 表...")

        def derived(x: str) -> str:
            return f"""
                COALESCE(
                    (SELECT a.tenant_id FROM appointments a WHERE a.id = {x}.appointment_id),
                    (SELECT p.tenant_id FROM patients p WHERE p.id = {x}.patient_id),
                    (SELECT d.tenant_id FROM doctors d WHERE d.id = {x}.doctor_id),
                    (SELECT fp.tenant_id FROM follow_up_plans fp WHERE fp.id = {x}.plan_id)
                )
            """

        self._run_backfill(
            key='follow_up_tasks_updated',
            label='follow_up_tasks',
            update_sql=f"""
                UPDATE follow_up_tasks t
                SET tenant_id = src.tenant_id
                FROM (
                    SELECT t2.id, {derived('t2')} AS tenant_id
                    FROM follow_up_tasks t2
                    WHERE t2.tenant_id IS NULL
                ) src
                WHERE t.id = src.id AND src.tenant_id IS NOT NULL
            """,
            resolvable_sql=f"SELECT count(*) FROM follow_up_tasks t WHERE t.tenant_id IS NULL AND {derived('t')} IS NOT NULL",
            unresolved_sql=f"SELECT count(*) FROM follow_up_tasks t WHERE t.tenant_id IS NULL AND {derived('t')} IS NULL",
        )
        self.log(f"随访任务表迁移完成，更新 {self.stats['follow_up_tasks_updated']} 条记录")

    def migrate_follow_up_records(self):
        """随访记录：appointment / patient / doctor -> tenant_id"""
        self.log("开始迁移 follow_up_records 表...")

        def derived(x: str) -> str:
            return f"""
                COALESCE(
                    (SELECT a.tenant_id FROM appointments a WHERE a.id = {x}.appointment_id),
                    (SELECT p.tenant_id FROM patients p WHERE p.id = {x}.patient_id),
                    (SELECT d.tenant_id FROM doctors d WHERE d.id = {x}.doctor_id)
                )
            """

        self._run_backfill(
            key='follow_up_records_updated',
            label='follow_up_records',
            update_sql=f"""
                UPDATE follow_up_records r
                SET tenant_id = src.tenant_id
                FROM (
                    SELECT r2.id, {derived('r2')} AS tenant_id
                    FROM follow_up_records r2
                    WHERE r2.tenant_id IS NULL
                ) src
                WHERE r.id = src.id AND src.tenant_id IS NOT NULL
            """,
            resolvable_sql=f"SELECT count(*) FROM follow_up_records r WHERE r.tenant_id IS NULL AND {derived('r')} IS NOT NULL",
            unresolved_sql=f"SELECT count(*) FROM follow_up_records r WHERE r.tenant_id IS NULL AND {derived('r')} IS NULL",
        )
        self.log(f"随访记录表迁移完成，更新 {self.stats['follow_up_records_updated']} 条记录")

    def migrate_follow_up_self_reports(self):
        """随访自报：patient_id -> patients.tenant_id"""
        self.log("开始迁移 follow_up_self_reports 表...")
        self._run_backfill(
            key='follow_up_self_reports_updated',
            label='follow_up_self_reports',
            update_sql="""
                UPDATE follow_up_self_reports r
                SET tenant_id = p.tenant_id
                FROM patients p
                WHERE r.patient_id = p.id
                  AND r.tenant_id IS NULL
                  AND p.tenant_id IS NOT NULL
            """,
            resolvable_sql="""
                SELECT count(*) FROM follow_up_self_reports r
                JOIN patients p ON p.id = r.patient_id
                WHERE r.tenant_id IS NULL AND p.tenant_id IS NOT NULL
            """,
            unresolved_sql="""
                SELECT count(*) FROM follow_up_self_reports r
                LEFT JOIN patients p ON p.id = r.patient_id
                WHERE r.tenant_id IS NULL AND (p.id IS NULL OR p.tenant_id IS NULL)
            """,
        )
        self.log(f"随访自报表迁移完成，更新 {self.stats['follow_up_self_reports_updated']} 条记录")

    def migrate_messages(self):
        """站内消息：store / user / admin -> tenant_id"""
        self.log("开始迁移 messages 表...")

        def derived(x: str) -> str:
            return f"""
                COALESCE(
                    (SELECT s.tenant_id FROM stores s WHERE s.id = {x}.store_id),
                    (SELECT u.tenant_id FROM users u WHERE u.id = {x}.user_id),
                    (SELECT d.tenant_id FROM doctors d WHERE d.id = {x}.user_id),
                    (SELECT ad.tenant_id FROM admins ad WHERE ad.id = {x}.user_id)
                )
            """

        self._run_backfill(
            key='messages_updated',
            label='messages',
            update_sql=f"""
                UPDATE messages m
                SET tenant_id = src.tenant_id
                FROM (
                    SELECT m2.id, {derived('m2')} AS tenant_id
                    FROM messages m2
                    WHERE m2.tenant_id IS NULL
                ) src
                WHERE m.id = src.id AND src.tenant_id IS NOT NULL
            """,
            resolvable_sql=f"SELECT count(*) FROM messages m WHERE m.tenant_id IS NULL AND {derived('m')} IS NOT NULL",
            unresolved_sql=f"SELECT count(*) FROM messages m WHERE m.tenant_id IS NULL AND {derived('m')} IS NULL",
        )
        self.log(f"消息表迁移完成，更新 {self.stats['messages_updated']} 条记录")

    def migrate_waitlist_entries(self):
        """候补：schedule / patient -> tenant_id"""
        self.log("开始迁移 waitlist_entries 表...")

        def derived(x: str) -> str:
            return f"""
                COALESCE(
                    (SELECT s.tenant_id FROM schedules s WHERE s.id = {x}.schedule_id),
                    (SELECT p.tenant_id FROM patients p WHERE p.id = {x}.patient_id)
                )
            """

        self._run_backfill(
            key='waitlist_entries_updated',
            label='waitlist_entries',
            update_sql=f"""
                UPDATE waitlist_entries w
                SET tenant_id = src.tenant_id
                FROM (
                    SELECT w2.id, {derived('w2')} AS tenant_id
                    FROM waitlist_entries w2
                    WHERE w2.tenant_id IS NULL
                ) src
                WHERE w.id = src.id AND src.tenant_id IS NOT NULL
            """,
            resolvable_sql=f"SELECT count(*) FROM waitlist_entries w WHERE w.tenant_id IS NULL AND {derived('w')} IS NOT NULL",
            unresolved_sql=f"SELECT count(*) FROM waitlist_entries w WHERE w.tenant_id IS NULL AND {derived('w')} IS NULL",
        )
        self.log(f"候补表迁移完成，更新 {self.stats['waitlist_entries_updated']} 条记录")

    # ------------------------------------------------------------------ 执行/验证
    def run_migration(self):
        """执行完整迁移流程"""
        self.log("=" * 60)
        self.log("开始核心业务表租户数据迁移（禁止默认租户兜底）")
        self.log("=" * 60)

        # 按依赖顺序执行：父表在前，业务从属表在后
        self.migrate_doctors()
        self.migrate_departments()
        self.migrate_schedule_templates()
        self.migrate_schedules()
        self.migrate_appointments()
        self.migrate_patients()
        self.migrate_users()
        # R4-14：业务从属表
        self.migrate_medical_records()
        self.migrate_examination_reports()
        self.migrate_follow_up_plans()
        self.migrate_follow_up_tasks()
        self.migrate_follow_up_records()
        self.migrate_follow_up_self_reports()
        self.migrate_messages()
        self.migrate_waitlist_entries()

        self.log("=" * 60)
        self.log("迁移完成！统计信息：")
        for key, value in self.stats.items():
            if key in ('errors', 'unresolved'):
                continue
            self.log(f"  {key}: {value}")

        total_unresolved = sum(self.stats['unresolved'].values())
        if self.dry_run:
            self.log(
                f"  可推导合计: {self.stats['resolvable_pending']}，"
                f"不可推导(NULL)合计: {total_unresolved}"
            )
        else:
            self.log(f"  不可推导(NULL)合计: {total_unresolved}")

        if self.stats['unresolved']:
            self.log("不可推导（保持 NULL，需人工核对）统计：", "WARN")
            for name, count in sorted(self.stats['unresolved'].items()):
                self.log(f"  - {name}: {count}")

        if self.stats['errors']:
            self.log("错误信息：", "ERROR")
            for error in self.stats['errors']:
                self.log(f"  - {error}", "ERROR")

        return self.stats

    def verify_migration(self):
        """验证迁移结果"""
        self.log("=" * 60)
        self.log("验证迁移结果")
        self.log("=" * 60)

        checks = [
            ("doctors", "SELECT COUNT(*) FROM doctors WHERE tenant_id IS NULL"),
            ("departments", "SELECT COUNT(*) FROM departments WHERE tenant_id IS NULL"),
            ("schedules", "SELECT COUNT(*) FROM schedules WHERE tenant_id IS NULL"),
            ("schedule_templates", "SELECT COUNT(*) FROM schedule_templates WHERE tenant_id IS NULL"),
            ("appointments", "SELECT COUNT(*) FROM appointments WHERE tenant_id IS NULL"),
            ("patients", "SELECT COUNT(*) FROM patients WHERE tenant_id IS NULL"),
            ("users", "SELECT COUNT(*) FROM users WHERE tenant_id IS NULL"),
            ("medical_records", "SELECT COUNT(*) FROM medical_records WHERE tenant_id IS NULL"),
            ("examination_reports", "SELECT COUNT(*) FROM examination_reports WHERE tenant_id IS NULL"),
            (
                "follow_up_plans(部门级)",
                "SELECT COUNT(*) FROM follow_up_plans WHERE tenant_id IS NULL AND department_id IS NOT NULL",
            ),
            ("follow_up_tasks", "SELECT COUNT(*) FROM follow_up_tasks WHERE tenant_id IS NULL"),
            ("follow_up_records", "SELECT COUNT(*) FROM follow_up_records WHERE tenant_id IS NULL"),
            ("follow_up_self_reports", "SELECT COUNT(*) FROM follow_up_self_reports WHERE tenant_id IS NULL"),
            ("messages", "SELECT COUNT(*) FROM messages WHERE tenant_id IS NULL"),
            ("waitlist_entries", "SELECT COUNT(*) FROM waitlist_entries WHERE tenant_id IS NULL"),
        ]

        all_passed = True
        for table, query in checks:
            result = self.db.execute(text(query)).scalar()
            status = "PASS" if result == 0 else "FAIL"
            if result > 0:
                all_passed = False
            self.log(f"  {table}: {result} 条记录无 tenant_id [{status}]")

        # 检查租户一致性
        consistency_checks = [
            # 医生的 tenant_id 应该等于其门店的 tenant_id
            ("doctors-stores", """
                SELECT COUNT(*) FROM doctors d
                JOIN stores s ON d.store_id = s.id
                WHERE d.tenant_id != s.tenant_id OR (d.tenant_id IS NULL AND s.tenant_id IS NOT NULL)
            """),
            # 预约的 tenant_id 应该等于其排班的 tenant_id
            ("appointments-schedules", """
                SELECT COUNT(*) FROM appointments a
                JOIN schedules s ON a.schedule_id = s.id
                WHERE a.tenant_id != s.tenant_id OR (a.tenant_id IS NULL AND s.tenant_id IS NOT NULL)
            """),
            # 病历的 tenant_id 应该等于其预约的 tenant_id
            ("medical_records-appointments", """
                SELECT COUNT(*) FROM medical_records m
                JOIN appointments a ON m.appointment_id = a.id
                WHERE m.tenant_id != a.tenant_id OR (m.tenant_id IS NULL AND a.tenant_id IS NOT NULL)
            """),
            # 候补的 tenant_id 应该等于其排班的 tenant_id
            ("waitlist-schedules", """
                SELECT COUNT(*) FROM waitlist_entries w
                JOIN schedules s ON w.schedule_id = s.id
                WHERE w.tenant_id != s.tenant_id OR (w.tenant_id IS NULL AND s.tenant_id IS NOT NULL)
            """),
        ]

        for name, query in consistency_checks:
            result = self.db.execute(text(query)).scalar()
            status = "PASS" if result == 0 else "FAIL"
            if result > 0:
                all_passed = False
            self.log(f"  一致性检查 {name}: {result} 条不一致 [{status}]")

        if all_passed:
            self.log("所有检查通过！")
        else:
            self.log("存在未通过的检查，请审查数据", "WARN")

        return all_passed


def main():
    parser = argparse.ArgumentParser(description="核心业务表租户数据迁移脚本")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不执行修改")
    parser.add_argument("--execute", action="store_true", help="执行迁移")
    parser.add_argument("--verify", action="store_true", help="验证迁移结果")

    args = parser.parse_args()

    if not (args.dry_run or args.execute or args.verify):
        parser.print_help()
        print("\n请指定一个操作模式: --dry-run, --execute 或 --verify")
        sys.exit(1)

    db = SessionLocal()
    try:
        migrator = TenantDataMigrator(db, dry_run=args.dry_run)

        if args.verify:
            migrator.verify_migration()
        else:
            migrator.run_migration()

    except Exception as e:
        print(f"[ERROR] 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
