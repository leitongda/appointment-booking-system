#!/usr/bin/env python
"""验证旧表（admins / doctors / users）与新表（accounts + 扩展表）的数据一致性。

用法:
    cd apps/server
    python scripts/verify_account_sync.py [--limit N] [--type admin|doctor|user] [--json]

退出码:
    0 — 数据一致
    1 — 发现差异
    2 — 运行出错
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# 确保能 import app 包
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, select

from app.common.account_sync import (
    ConsistencyReport,
    SyncDiff,
    check_admin_consistency,
    check_doctor_consistency,
    check_user_consistency,
    check_account_sync_consistency,
)
from app.db.session import AsyncSessionLocal
from app.models.account import Account, AccountAdmin, AccountDoctor, AccountUser
from app.models.admin import Admin
from app.models.doctor import Doctor
from app.models.user import User


def _print_text_report(report: ConsistencyReport, limit: int | None = None) -> None:
    """以可读文本格式输出差异报告"""

    print("=" * 70)
    print("  账户双写一致性校验报告")
    print("=" * 70)

    # --- 统计概览 ---
    print(f"\n[概览]")
    print(f"  旧表缺失（新表有、旧表无）: {len(report.extra_in_new)} 条")
    print(f"  新表缺失（旧表有、新表无）: {len(report.missing_in_new)} 条")
    print(f"  字段差异记录数:             {len(report.field_diffs)} 条")
    print(f"  总问题数:                   {report.total_issues} 条")

    if report.is_consistent:
        print("\n[结果] 数据一致性校验通过，未发现差异。")
        return

    # --- 新表缺失 ---
    if report.missing_in_new:
        items = report.missing_in_new if limit is None else report.missing_in_new[:limit]
        print(f"\n[新表缺失] 旧表有、新表无（共 {len(report.missing_in_new)} 条，显示 {len(items)} 条）:")
        for rtype, rid in items:
            print(f"  - [{rtype}] id={rid}")

    # --- 旧表缺失 ---
    if report.extra_in_new:
        items = report.extra_in_new if limit is None else report.extra_in_new[:limit]
        print(f"\n[旧表缺失] 新表有、旧表无（共 {len(report.extra_in_new)} 条，显示 {len(items)} 条）:")
        for rtype, rid in items:
            print(f"  - [{rtype}] id={rid}")

    # --- 字段差异 ---
    if report.field_diffs:
        items = report.field_diffs if limit is None else report.field_diffs[:limit]
        print(f"\n[字段差异] 共 {len(report.field_diffs)} 条，显示 {len(items)} 条:")
        for diff in items:
            print(f"\n  [{diff.record_type}] id={diff.record_id}")
            for fname, old_val, new_val in diff.field_diffs:
                # 避免打印 password_hash 等敏感字段的完整值
                display_old = _mask_sensitive(fname, old_val)
                display_new = _mask_sensitive(fname, new_val)
                print(f"    {fname}: old={display_old} -> new={display_new}")

    print("\n" + "=" * 70)


def _mask_sensitive(field_name: str, value) -> str:
    """对敏感字段做脱敏显示"""
    if value is None:
        return "<None>"
    if field_name == "password_hash":
        return "<masked>" if value else "<empty>"
    s = str(value)
    if len(s) > 50:
        return s[:50] + "..."
    return s


def _to_json_report(report: ConsistencyReport) -> dict:
    """将报告转为 JSON 可序列化的 dict"""
    return {
        "summary": {
            "missing_in_new": len(report.missing_in_new),
            "extra_in_new": len(report.extra_in_new),
            "field_diffs": len(report.field_diffs),
            "total_issues": report.total_issues,
            "is_consistent": report.is_consistent,
        },
        "missing_in_new": [
            {"type": t, "id": rid} for t, rid in report.missing_in_new
        ],
        "extra_in_new": [
            {"type": t, "id": rid} for t, rid in report.extra_in_new
        ],
        "field_diffs": [
            {
                "type": d.record_type,
                "id": d.record_id,
                "diffs": [
                    {"field": f, "old": _safe_json(old), "new": _safe_json(new)}
                    for f, old, new in d.field_diffs
                ],
            }
            for d in report.field_diffs
        ],
    }


def _safe_json(value):
    """将值转为 JSON 安全类型"""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


async def main():
    parser = argparse.ArgumentParser(description="验证账户双写数据一致性")
    parser.add_argument(
        "--limit", type=int, default=20,
        help="每类差异最多显示条数（默认 20）",
    )
    parser.add_argument(
        "--type", choices=["admin", "doctor", "user"], default=None,
        help="仅校验指定类型",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="以 JSON 格式输出",
    )
    args = parser.parse_args()

    try:
        async with AsyncSessionLocal() as db:
            if args.type:
                report = ConsistencyReport()
                checker = {
                    "admin": check_admin_consistency,
                    "doctor": check_doctor_consistency,
                    "user": check_user_consistency,
                }[args.type]
                await checker(db, report)
            else:
                report = await check_account_sync_consistency(db)

        if args.json:
            print(json.dumps(_to_json_report(report), ensure_ascii=False, indent=2))
        else:
            _print_text_report(report, limit=args.limit)

        sys.exit(0 if report.is_consistent else 1)

    except Exception as exc:
        print(f"校验运行出错: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
