#!/usr/bin/env python3
"""
统一消息中心数据迁移脚本

将旧表数据迁移到新表：
- messages → notification_groups + notification_recipients
- notification_logs → notification_deliveries
- message_templates + email_templates → unified_templates

使用方法:
    # 预览模式（不执行修改）
    python scripts/migrate_unified_message.py --dry-run

    # 执行迁移
    python scripts/migrate_unified_message.py --execute

    # 验证迁移结果
    python scripts/migrate_unified_message.py --verify
"""
import sys
import os
import argparse
import uuid
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, select, func
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine


class UnifiedMessageMigrator:
    """统一消息数据迁移器"""

    def __init__(self, db: Session, dry_run: bool = True):
        self.db = db
        self.dry_run = dry_run
        self.stats = {
            "groups_created": 0,
            "recipients_created": 0,
            "deliveries_created": 0,
            "templates_created": 0,
            "messages_processed": 0,
            "logs_processed": 0,
            "errors": [],
        }

    def run(self):
        """执行迁移"""
        print(f"{'[DRY RUN] ' if self.dry_run else ''}开始统一消息数据迁移...")
        print(f"时间: {datetime.now().isoformat()}")

        try:
            # Step 1: 迁移模板
            self._migrate_templates()

            # Step 2: 迁移消息 → 通知组 + 接收人
            self._migrate_messages()

            # Step 3: 迁移通知日志 → 投递记录
            self._migrate_notification_logs()

            if not self.dry_run:
                self.db.commit()
                print("\n迁移已提交。")
            else:
                self.db.rollback()
                print("\n[DRY RUN] 迁移已回滚（预览模式）。")

        except Exception as e:
            self.db.rollback()
            print(f"\n迁移失败: {e}")
            self.stats["errors"].append(str(e))
            raise

        self._print_stats()

    def _migrate_templates(self):
        """迁移 message_templates + email_templates → unified_templates"""
        print("\n--- 迁移模板 ---")

        # 迁移 message_templates
        result = self.db.execute(text(
            "SELECT id, tenant_id, code, name, message_type, title_template, content_template, status "
            "FROM message_templates"
        ))
        msg_templates = result.fetchall()
        print(f"message_templates: {len(msg_templates)} 条")

        for row in msg_templates:
            template_id = str(uuid.uuid4())
            if not self.dry_run:
                self.db.execute(text(
                    "INSERT INTO unified_templates "
                    "(id, tenant_id, code, name, message_type, text_template, status, created_at) "
                    "VALUES (:id, :tenant_id, :code, :name, :message_type, :text_template, :status, :now)"
                ), {
                    "id": template_id,
                    "tenant_id": row[1],
                    "code": row[2],
                    "name": row[3],
                    "message_type": row[4],
                    "text_template": f"{row[5]}\n{row[6]}" if row[5] and row[6] else (row[6] or row[5]),
                    "status": row[7],
                    "now": datetime.utcnow(),
                })
            self.stats["templates_created"] += 1

        # 迁移 email_templates
        result = self.db.execute(text(
            "SELECT id, tenant_id, code, name, template_type, subject_template, content_template, status "
            "FROM email_templates"
        ))
        email_templates = result.fetchall()
        print(f"email_templates: {len(email_templates)} 条")

        for row in email_templates:
            # 检查是否已存在同 code 的模板（避免冲突）
            existing = self.db.execute(text(
                "SELECT id FROM unified_templates WHERE tenant_id = :tid AND code = :code"
            ), {"tid": row[1], "code": row[2]}).fetchone()

            if existing:
                print(f"  跳过重复模板: tenant={row[1]}, code={row[2]}")
                continue

            template_id = str(uuid.uuid4())
            if not self.dry_run:
                self.db.execute(text(
                    "INSERT INTO unified_templates "
                    "(id, tenant_id, code, name, message_type, event_type, subject_template, html_template, status, created_at) "
                    "VALUES (:id, :tenant_id, :code, :name, :message_type, :event_type, :subject_template, :html_template, :status, :now)"
                ), {
                    "id": template_id,
                    "tenant_id": row[1],
                    "code": row[2],
                    "name": row[3],
                    "message_type": row[4] or "system",
                    "event_type": row[4],
                    "subject_template": row[5],
                    "html_template": row[6],
                    "status": row[7],
                    "now": datetime.utcnow(),
                })
            self.stats["templates_created"] += 1

        print(f"  模板迁移完成: {self.stats['templates_created']} 条")

    def _migrate_messages(self):
        """迁移 messages → notification_groups + notification_recipients"""
        print("\n--- 迁移消息 ---")

        # 按 (tenant_id, related_id, message_type) 分组
        result = self.db.execute(text(
            "SELECT id, tenant_id, store_id, user_id, user_type, title, content, "
            "message_type, related_id, is_read, read_at, created_at, extra_data "
            "FROM messages ORDER BY created_at"
        ))
        messages = result.fetchall()
        print(f"messages: {len(messages)} 条")

        # 分组
        groups = defaultdict(list)
        for msg in messages:
            tenant_id = msg[1] or ""
            related_id = msg[8] or ""
            msg_type = msg[7] or "system"
            group_key = (tenant_id, related_id, msg_type)
            groups[group_key].append(msg)

        print(f"  分组后: {len(groups)} 个通知组")

        for group_key, group_messages in groups.items():
            tenant_id, related_id, msg_type = group_key
            first_msg = group_messages[0]

            # 创建通知组
            group_id = str(uuid.uuid4())
            dedup_key = f"{tenant_id}:{related_id}:{msg_type}:{first_msg[0]}"

            if not self.dry_run:
                self.db.execute(text(
                    "INSERT INTO notification_groups "
                    "(id, tenant_id, store_id, event_type, message_type, related_id, dedup_key, status, "
                    "legacy_message_id, created_at, updated_at) "
                    "VALUES (:id, :tenant_id, :store_id, :event_type, :message_type, :related_id, "
                    ":dedup_key, :status, :legacy_message_id, :created_at, :updated_at)"
                ), {
                    "id": group_id,
                    "tenant_id": tenant_id or None,
                    "store_id": first_msg[2],
                    "event_type": msg_type,
                    "message_type": msg_type,
                    "related_id": related_id or None,
                    "dedup_key": dedup_key,
                    "status": "sent",
                    "legacy_message_id": first_msg[0],
                    "created_at": first_msg[11],
                    "updated_at": first_msg[11],
                })
            self.stats["groups_created"] += 1

            # 创建接收人记录
            for msg in group_messages:
                recipient_id = str(uuid.uuid4())
                if not self.dry_run:
                    self.db.execute(text(
                        "INSERT INTO notification_recipients "
                        "(id, group_id, tenant_id, user_id, user_type, title, content, "
                        "is_read, read_at, status, created_at, updated_at) "
                        "VALUES (:id, :group_id, :tenant_id, :user_id, :user_type, :title, :content, "
                        ":is_read, :read_at, :status, :created_at, :updated_at)"
                    ), {
                        "id": recipient_id,
                        "group_id": group_id,
                        "tenant_id": tenant_id or None,
                        "user_id": msg[3],
                        "user_type": msg[4],
                        "title": msg[5],
                        "content": msg[6],
                        "is_read": msg[9],
                        "read_at": msg[10],
                        "status": "sent",
                        "created_at": msg[11],
                        "updated_at": msg[11],
                    })
                self.stats["recipients_created"] += 1
                self.stats["messages_processed"] += 1

        print(f"  消息迁移完成: {self.stats['messages_processed']} 条")

    def _migrate_notification_logs(self):
        """迁移 notification_logs → notification_deliveries"""
        print("\n--- 迁移通知日志 ---")

        result = self.db.execute(text(
            "SELECT id, tenant_id, store_id, user_id, user_type, channel, message_type, "
            "title, content, status, error_message, recipient, related_id, "
            "retry_count, max_retries, next_retry_at, sent_at, created_at, extra_data "
            "FROM notification_logs"
        ))
        logs = result.fetchall()
        print(f"notification_logs: {len(logs)} 条")

        for log in logs:
            # 尝试找到关联的通知组
            tenant_id = log[1] or ""
            related_id = log[12] or ""
            msg_type = log[6] or "system"

            group_result = self.db.execute(text(
                "SELECT id FROM notification_groups "
                "WHERE (tenant_id = :tenant_id OR (tenant_id IS NULL AND :tenant_id = '')) "
                "AND (related_id = :related_id OR (related_id IS NULL AND :related_id = '')) "
                "AND message_type = :message_type "
                "LIMIT 1"
            ), {"tenant_id": tenant_id, "related_id": related_id, "message_type": msg_type})
            group_row = group_result.fetchone()

            if not group_row:
                # 没有找到关联组，跳过
                continue

            group_id = group_row[0]

            # 查找对应的接收人
            user_id = log[3]
            recipient_result = self.db.execute(text(
                "SELECT id FROM notification_recipients "
                "WHERE group_id = :group_id AND user_id = :user_id "
                "LIMIT 1"
            ), {"group_id": group_id, "user_id": user_id})
            recipient_row = recipient_result.fetchone()

            recipient_id = recipient_row[0] if recipient_row else None

            delivery_id = str(uuid.uuid4())
            if not self.dry_run:
                self.db.execute(text(
                    "INSERT INTO notification_deliveries "
                    "(id, group_id, recipient_id, tenant_id, channel, status, recipient_address, "
                    "error_message, retry_count, max_retries, next_retry_at, sent_at, "
                    "extra_data, legacy_log_id, created_at) "
                    "VALUES (:id, :group_id, :recipient_id, :tenant_id, :channel, :status, "
                    ":recipient_address, :error_message, :retry_count, :max_retries, "
                    ":next_retry_at, :sent_at, :extra_data, :legacy_log_id, :created_at)"
                ), {
                    "id": delivery_id,
                    "group_id": group_id,
                    "recipient_id": recipient_id,
                    "tenant_id": log[1] or None,
                    "channel": log[5],
                    "status": log[9],
                    "recipient_address": log[11],
                    "error_message": log[10],
                    "retry_count": log[13],
                    "max_retries": log[14],
                    "next_retry_at": log[15],
                    "sent_at": log[16],
                    "extra_data": log[18],
                    "legacy_log_id": log[0],
                    "created_at": log[17],
                })
            self.stats["deliveries_created"] += 1
            self.stats["logs_processed"] += 1

        print(f"  投递记录迁移完成: {self.stats['deliveries_created']} 条")

    def _print_stats(self):
        """打印统计信息"""
        print("\n" + "=" * 50)
        print("迁移统计:")
        print(f"  模板: {self.stats['templates_created']} 条")
        print(f"  通知组: {self.stats['groups_created']} 条")
        print(f"  接收人: {self.stats['recipients_created']} 条")
        print(f"  投递记录: {self.stats['deliveries_created']} 条")
        print(f"  处理消息: {self.stats['messages_processed']} 条")
        print(f"  处理日志: {self.stats['logs_processed']} 条")
        if self.stats["errors"]:
            print(f"  错误: {len(self.stats['errors'])} 条")
            for err in self.stats["errors"]:
                print(f"    - {err}")
        print("=" * 50)

    def verify(self):
        """验证迁移结果"""
        print("\n--- 验证迁移结果 ---")

        # 统计旧表
        msg_count = self.db.execute(text("SELECT COUNT(*) FROM messages")).scalar()
        log_count = self.db.execute(text("SELECT COUNT(*) FROM notification_logs")).scalar()
        msg_tpl_count = self.db.execute(text("SELECT COUNT(*) FROM message_templates")).scalar()
        email_tpl_count = self.db.execute(text("SELECT COUNT(*) FROM email_templates")).scalar()

        # 统计新表
        group_count = self.db.execute(text("SELECT COUNT(*) FROM notification_groups")).scalar()
        recipient_count = self.db.execute(text("SELECT COUNT(*) FROM notification_recipients")).scalar()
        delivery_count = self.db.execute(text("SELECT COUNT(*) FROM notification_deliveries")).scalar()
        unified_tpl_count = self.db.execute(text("SELECT COUNT(*) FROM unified_templates")).scalar()

        print(f"\n旧表统计:")
        print(f"  messages: {msg_count}")
        print(f"  notification_logs: {log_count}")
        print(f"  message_templates: {msg_tpl_count}")
        print(f"  email_templates: {email_tpl_count}")

        print(f"\n新表统计:")
        print(f"  notification_groups: {group_count}")
        print(f"  notification_recipients: {recipient_count}")
        print(f"  notification_deliveries: {delivery_count}")
        print(f"  unified_templates: {unified_tpl_count}")

        # 基本验证
        issues = []
        if recipient_count < msg_count:
            issues.append(f"接收人({recipient_count}) < 消息({msg_count})")
        if group_count == 0 and msg_count > 0:
            issues.append("有消息但无通知组")

        if issues:
            print(f"\n潜在问题:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"\n验证通过。")


def main():
    parser = argparse.ArgumentParser(description="统一消息数据迁移")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不执行修改")
    parser.add_argument("--execute", action="store_true", help="执行迁移")
    parser.add_argument("--verify", action="store_true", help="验证迁移结果")
    args = parser.parse_args()

    if not args.execute and not args.verify:
        args.dry_run = True

    db = SessionLocal()
    try:
        migrator = UnifiedMessageMigrator(db, dry_run=args.dry_run)

        if args.verify:
            migrator.verify()
        else:
            migrator.run()
    finally:
        db.close()


if __name__ == "__main__":
    main()
