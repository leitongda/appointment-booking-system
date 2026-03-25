#!/usr/bin/env python3
"""
核心业务表租户数据迁移脚本

执行步骤:
1. 全量备份数据库
2. 按依赖顺序回填 tenant_id:
   - Store (已有 tenant_id)
   - Doctor (store_id -> tenant_id)
   - Department (store_id -> tenant_id)
   - Schedule / ScheduleTemplate (store_id -> tenant_id)
   - Appointment (schedule_id -> tenant_id)
   - Patient (store_id -> tenant_id)
   - User (按租户拆分)
3. 验证数据完整性

使用方法:
    # 预览模式（不执行修改）
    python scripts/migrate_core_tenant_data.py --dry-run

    # 执行迁移
    python scripts/migrate_core_tenant_data.py --execute

    # 验证迁移结果
    python scripts/migrate_core_tenant_data.py --verify
"""
import sys
import os
import argparse
import uuid
from datetime import datetime
from collections import defaultdict

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, select, update, insert
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.models.tenant import Tenant
from app.models.store import Store
from app.models.doctor import Doctor
from app.models.department import Department
from app.models.schedule import Schedule
from app.models.schedule_template import ScheduleTemplate
from app.models.appointment import Appointment
from app.models.user import Patient
from app.models.user import User


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
            'errors': []
        }

    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        prefix = "[DRY-RUN] " if self.dry_run else ""
        print(f"{prefix}[{level}] {message}")

    def get_default_tenant(self) -> str:
        """获取默认租户ID"""
        tenant = self.db.execute(
            select(Tenant).where(Tenant.tenant_code == "default")
        ).scalar_one_or_none()

        if not tenant:
            # 如果没有默认租户，获取第一个租户
            tenant = self.db.execute(
                select(Tenant).limit(1)
            ).scalar_one_or_none()

        if not tenant:
            raise ValueError("没有找到任何租户，请先运行 init_subscription_plans.py 创建默认租户")

        return tenant.id

    def build_store_tenant_map(self) -> dict:
        """构建 store_id -> tenant_id 映射"""
        result = self.db.execute(
            select(Store.id, Store.tenant_id)
        ).all()
        return {row[0]: row[1] for row in result if row[1]}

    def migrate_doctors(self, store_tenant_map: dict):
        """迁移医生表"""
        self.log("开始迁移 doctors 表...")

        # 获取默认租户ID
        default_tenant_id = self.get_default_tenant()

        # 获取所有没有 tenant_id 的医生
        doctors = self.db.execute(
            select(Doctor).where(Doctor.tenant_id == None)
        ).scalars().all()

        for doctor in doctors:
            if doctor.store_id and doctor.store_id in store_tenant_map:
                tenant_id = store_tenant_map[doctor.store_id]
            else:
                # 如果没有 store_id，使用默认租户
                tenant_id = default_tenant_id
                self.log(f"  Doctor {doctor.id} ({doctor.name}) 无 store_id，使用默认租户", "WARN")

            if not self.dry_run:
                doctor.tenant_id = tenant_id
            self.stats['doctors_updated'] += 1
            self.log(f"  Doctor {doctor.id} ({doctor.name}) -> tenant {tenant_id}")

        if not self.dry_run:
            self.db.commit()
        self.log(f"医生表迁移完成，更新 {self.stats['doctors_updated']} 条记录")

    def migrate_departments(self, store_tenant_map: dict):
        """迁移科室表"""
        self.log("开始迁移 departments 表...")

        # 获取默认租户ID
        default_tenant_id = self.get_default_tenant()

        departments = self.db.execute(
            select(Department).where(Department.tenant_id == None)
        ).scalars().all()

        for dept in departments:
            if dept.store_id and dept.store_id in store_tenant_map:
                tenant_id = store_tenant_map[dept.store_id]
            else:
                # 如果没有 store_id，使用默认租户
                tenant_id = default_tenant_id
                self.log(f"  Department {dept.id} ({dept.name}) 无 store_id，使用默认租户", "WARN")

            if not self.dry_run:
                dept.tenant_id = tenant_id
            self.stats['departments_updated'] += 1
            self.log(f"  Department {dept.id} ({dept.name}) -> tenant {tenant_id}")

        if not self.dry_run:
            self.db.commit()
        self.log(f"科室表迁移完成，更新 {self.stats['departments_updated']} 条记录")

    def migrate_schedules(self, store_tenant_map: dict):
        """迁移排班表"""
        self.log("开始迁移 schedules 表...")

        schedules = self.db.execute(
            select(Schedule).where(Schedule.tenant_id == None)
        ).scalars().all()

        for schedule in schedules:
            if schedule.store_id and schedule.store_id in store_tenant_map:
                tenant_id = store_tenant_map[schedule.store_id]
                if not self.dry_run:
                    schedule.tenant_id = tenant_id
                self.stats['schedules_updated'] += 1
            else:
                self.log(f"  Schedule {schedule.id} 无法确定租户", "WARN")

        if not self.dry_run:
            self.db.commit()
        self.log(f"排班表迁移完成，更新 {self.stats['schedules_updated']} 条记录")

    def migrate_schedule_templates(self, store_tenant_map: dict):
        """迁移排班模板表"""
        self.log("开始迁移 schedule_templates 表...")

        templates = self.db.execute(
            select(ScheduleTemplate).where(ScheduleTemplate.tenant_id == None)
        ).scalars().all()

        for template in templates:
            if template.store_id and template.store_id in store_tenant_map:
                tenant_id = store_tenant_map[template.store_id]
                if not self.dry_run:
                    template.tenant_id = tenant_id
                self.stats['schedule_templates_updated'] += 1
            else:
                self.log(f"  ScheduleTemplate {template.id} 无法确定租户", "WARN")

        if not self.dry_run:
            self.db.commit()
        self.log(f"排班模板表迁移完成，更新 {self.stats['schedule_templates_updated']} 条记录")

    def migrate_appointments(self):
        """迁移预约表（通过 schedule 关联）"""
        self.log("开始迁移 appointments 表...")

        # PostgreSQL 不支持 UPDATE JOIN，使用子查询
        query = text("""
            UPDATE appointments
            SET tenant_id = s.tenant_id
            FROM schedules s
            WHERE appointments.schedule_id = s.id
            AND appointments.tenant_id IS NULL
            AND s.tenant_id IS NOT NULL
        """)

        if not self.dry_run:
            result = self.db.execute(query)
            self.stats['appointments_updated'] = result.rowcount
            self.db.commit()
        else:
            # 预览模式：统计需要更新的数量
            count_query = text("""
                SELECT COUNT(*) FROM appointments a
                JOIN schedules s ON a.schedule_id = s.id
                WHERE a.tenant_id IS NULL AND s.tenant_id IS NOT NULL
            """)
            result = self.db.execute(count_query).scalar()
            self.stats['appointments_updated'] = result or 0

        self.log(f"预约表迁移完成，更新 {self.stats['appointments_updated']} 条记录")

    def migrate_patients(self, store_tenant_map: dict):
        """迁移患者表"""
        self.log("开始迁移 patients 表...")

        patients = self.db.execute(
            select(Patient).where(Patient.tenant_id == None)
        ).scalars().all()

        for patient in patients:
            tenant_id = None

            # 优先使用 store_id 获取 tenant_id
            if patient.store_id and patient.store_id in store_tenant_map:
                tenant_id = store_tenant_map[patient.store_id]
            else:
                # 备选：通过最近的预约获取 tenant_id
                recent_appointment = self.db.execute(
                    select(Appointment)
                    .where(Appointment.patient_id == patient.id)
                    .where(Appointment.tenant_id != None)
                    .order_by(Appointment.created_at.desc())
                    .limit(1)
                ).scalar_one_or_none()

                if recent_appointment:
                    tenant_id = recent_appointment.tenant_id

            if tenant_id:
                if not self.dry_run:
                    patient.tenant_id = tenant_id
                self.stats['patients_updated'] += 1
                self.log(f"  Patient {patient.id} ({patient.name}) -> tenant {tenant_id}")
            else:
                self.log(f"  Patient {patient.id} ({patient.name}) 无法确定租户", "WARN")

        if not self.dry_run:
            self.db.commit()
        self.log(f"患者表迁移完成，更新 {self.stats['patients_updated']} 条记录")

    def migrate_users(self, store_tenant_map: dict):
        """
        迁移用户表（核心：按租户拆分）

        策略：
        1. 获取用户所有患者及其租户归属
        2. 如果只属于一个租户，直接更新 tenant_id
        3. 如果跨多租户，需要拆分 User
        """
        self.log("开始迁移 users 表（可能需要拆分）...")

        # 获取所有没有 tenant_id 的用户
        users = self.db.execute(
            select(User).where(User.tenant_id == None)
        ).scalars().all()

        for user in users:
            # 获取该用户所有患者及其租户归属
            patients_query = text("""
                SELECT DISTINCT p.tenant_id, p.id as patient_id
                FROM patients p
                WHERE p.user_id = :user_id AND p.tenant_id IS NOT NULL
            """)
            result = self.db.execute(patients_query, {"user_id": user.id}).fetchall()

            tenant_ids = list(set([row[0] for row in result]))

            if len(tenant_ids) == 0:
                # 没有患者，无法确定租户，跳过或使用默认租户
                self.log(f"  User {user.id} ({user.phone or user.nickname}) 没有患者记录，跳过", "WARN")
                continue

            if len(tenant_ids) == 1:
                # 只属于一个租户，直接更新
                tenant_id = tenant_ids[0]
                if not self.dry_run:
                    user.tenant_id = tenant_id
                self.stats['users_updated'] += 1
                self.log(f"  User {user.id} ({user.phone or user.nickname}) -> tenant {tenant_id}")
            else:
                # 跨多租户，需要拆分
                self.log(f"  User {user.id} ({user.phone or user.nickname}) 跨 {len(tenant_ids)} 个租户，需要拆分")

                for i, tenant_id in enumerate(tenant_ids):
                    if i == 0:
                        # 第一个租户复用原 User
                        if not self.dry_run:
                            user.tenant_id = tenant_id
                        self.stats['users_updated'] += 1
                        self.log(f"    -> 原 User 保留，tenant_id = {tenant_id}")
                    else:
                        # 其他租户创建新 User
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

                            # 更新相关 Patient 的 user_id
                            patient_ids = [row[1] for row in result if row[0] == tenant_id]
                            self.db.execute(
                                update(Patient)
                                .where(Patient.id.in_(patient_ids))
                                .values(user_id=new_user.id, tenant_id=tenant_id)
                            )

                            # 更新相关 Appointment 的 user_id
                            self.db.execute(
                                update(Appointment)
                                .where(Appointment.patient_id.in_(patient_ids))
                                .values(user_id=new_user.id)
                            )

                        self.stats['users_created'] += 1
                        self.log(f"    -> 创建新 User，tenant_id = {tenant_id}")

        if not self.dry_run:
            self.db.commit()
        self.log(f"用户表迁移完成，更新 {self.stats['users_updated']} 条，新建 {self.stats['users_created']} 条")

    def run_migration(self):
        """执行完整迁移流程"""
        self.log("=" * 60)
        self.log("开始核心业务表租户数据迁移")
        self.log("=" * 60)

        # 构建映射表
        store_tenant_map = self.build_store_tenant_map()
        self.log(f"已加载 {len(store_tenant_map)} 个门店的租户映射")

        # 按依赖顺序执行迁移
        self.migrate_doctors(store_tenant_map)
        self.migrate_departments(store_tenant_map)
        self.migrate_schedule_templates(store_tenant_map)
        self.migrate_schedules(store_tenant_map)
        self.migrate_appointments()  # 不需要 store_tenant_map
        self.migrate_patients(store_tenant_map)
        self.migrate_users(store_tenant_map)

        self.log("=" * 60)
        self.log("迁移完成！统计信息：")
        for key, value in self.stats.items():
            if key != 'errors':
                self.log(f"  {key}: {value}")

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
