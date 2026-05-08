"""
邮箱数据清洗脚本

在邮箱认证功能上线前运行，检查并修复 accounts / users 表中的邮箱数据问题：
1. 格式校验：清除不合法的邮箱格式
2. 空白清理：trim 空格、转小写
3. 重复检测：同一租户内重复邮箱报告
4. 跨表一致性：accounts 与 users 表的 email 是否同步

用法：
    cd apps/server
    python -m scripts.cleanup_email_data [--dry-run]

    --dry-run   仅报告问题，不执行修复（默认）
    --fix       执行修复
"""

import re
import sys
import asyncio
from collections import defaultdict
from sqlalchemy import select, update, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.account import Account
from app.models.user import User

# 严格邮箱正则（RFC 5322 简化版）
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

# 常见拼写错误域名修正映射
DOMAIN_FIXES = {
    "gmial.com": "gmail.com",
    "gamil.com": "gmail.com",
    "gmal.com": "gmail.com",
    "hotmal.com": "hotmail.com",
    "hotmial.com": "hotmail.com",
    "yaho.com": "yahoo.com",
    "163.comm": "163.com",
    "qq.comm": "qq.com",
    "qq.con": "qq.com",
}


def validate_email(email: str) -> tuple[bool, str]:
    """
    校验邮箱格式

    Returns:
        (is_valid, reason)
    """
    if not email:
        return True, "空邮箱，跳过"

    email = email.strip()
    if not email:
        return True, "空白邮箱，跳过"

    if len(email) > 100:
        return False, f"长度超限({len(email)} > 100)"

    if not EMAIL_REGEX.match(email):
        return False, "格式不合法"

    # 检查常见拼写错误
    domain = email.split("@")[1].lower()
    if domain in DOMAIN_FIXES:
        return False, f"疑似域名拼写错误: {domain} -> {DOMAIN_FIXES[domain]}"

    return True, "OK"


def normalize_email(email: str) -> str | None:
    """
    规范化邮箱：trim、小写、修复常见拼写错误

    Returns:
        规范化后的邮箱，如果为空则返回 None
    """
    if not email:
        return None

    email = email.strip().lower()
    if not email:
        return None

    # 修复常见域名拼写错误
    parts = email.split("@")
    if len(parts) == 2:
        domain = parts[1]
        if domain in DOMAIN_FIXES:
            email = f"{parts[0]}@{DOMAIN_FIXES[domain]}"

    return email


async def check_accounts(db: AsyncSession, fix: bool) -> dict:
    """检查 accounts 表的邮箱数据"""
    report = {
        "total": 0,
        "with_email": 0,
        "empty_trimmed": 0,
        "normalized": 0,
        "invalid_format": 0,
        "duplicates": [],
        "fixed": 0,
    }

    try:
        result = await db.execute(select(Account))
        accounts = result.scalars().all()
    except Exception as e:
        await db.rollback()
        if "email" in str(e) and "does not exist" in str(e):
            print("  [SKIP] accounts 表尚未执行 email 迁移 (080)，跳过")
            return report
        raise
    report["total"] = len(accounts)

    # 按 (tenant_id, email) 分组检测重复
    email_groups: dict[tuple, list] = defaultdict(list)
    fixes = []

    for acc in accounts:
        original = acc.email
        if not original or not original.strip():
            continue

        report["with_email"] += 1
        normalized = normalize_email(original)

        if normalized is None:
            report["empty_trimmed"] += 1
            fixes.append((acc.id, None))
            continue

        is_valid, reason = validate_email(normalized)
        if not is_valid:
            report["invalid_format"] += 1
            print(f"  [INVALID] account={acc.id} email='{original}' reason={reason}")
            if "域名拼写错误" in reason:
                # 自动修复常见拼写错误
                fixed_email = normalize_email(normalized)
                if fixed_email and fixed_email != original:
                    report["normalized"] += 1
                    fixes.append((acc.id, fixed_email))
                    print(f"    -> 自动修正为: {fixed_email}")
            continue

        if normalized != original:
            report["normalized"] += 1
            fixes.append((acc.id, normalized))

        key = (acc.tenant_id, normalized)
        email_groups[key].append(acc.id)

    # 检测重复
    for (tenant_id, email), ids in email_groups.items():
        if len(ids) > 1:
            report["duplicates"].append({
                "tenant_id": tenant_id,
                "email": email,
                "account_ids": ids,
            })
            print(f"  [DUP] tenant={tenant_id} email='{email}' accounts={ids}")

    # 执行修复
    if fix and fixes:
        for acc_id, new_email in fixes:
            await db.execute(
                update(Account).where(Account.id == acc_id).values(email=new_email)
            )
        report["fixed"] = len(fixes)
        await db.commit()
        print(f"  已修复 {len(fixes)} 条 accounts 记录")

    return report


async def check_users(db: AsyncSession, fix: bool) -> dict:
    """检查 users 表的邮箱数据"""
    report = {
        "total": 0,
        "with_email": 0,
        "empty_trimmed": 0,
        "normalized": 0,
        "invalid_format": 0,
        "duplicates": [],
        "fixed": 0,
    }

    try:
        result = await db.execute(select(User))
        users = result.scalars().all()
    except Exception as e:
        await db.rollback()
        if "email" in str(e) and "does not exist" in str(e):
            print("  [SKIP] users 表尚未执行 email 迁移 (081)，跳过")
            return report
        raise
    report["total"] = len(users)

    email_groups: dict[tuple, list] = defaultdict(list)
    fixes = []

    for user in users:
        original = user.email
        if not original or not original.strip():
            continue

        report["with_email"] += 1
        normalized = normalize_email(original)

        if normalized is None:
            report["empty_trimmed"] += 1
            fixes.append((user.id, None))
            continue

        is_valid, reason = validate_email(normalized)
        if not is_valid:
            report["invalid_format"] += 1
            print(f"  [INVALID] user={user.id} email='{original}' reason={reason}")
            if "域名拼写错误" in reason:
                fixed_email = normalize_email(normalized)
                if fixed_email and fixed_email != original:
                    report["normalized"] += 1
                    fixes.append((user.id, fixed_email))
                    print(f"    -> 自动修正为: {fixed_email}")
            continue

        if normalized != original:
            report["normalized"] += 1
            fixes.append((user.id, normalized))

        key = (user.tenant_id, normalized)
        email_groups[key].append(user.id)

    for (tenant_id, email), ids in email_groups.items():
        if len(ids) > 1:
            report["duplicates"].append({
                "tenant_id": tenant_id,
                "email": email,
                "user_ids": ids,
            })
            print(f"  [DUP] tenant={tenant_id} email='{email}' users={ids}")

    if fix and fixes:
        for user_id, new_email in fixes:
            await db.execute(
                update(User).where(User.id == user_id).values(email=new_email)
            )
        report["fixed"] = len(fixes)
        await db.commit()
        print(f"  已修复 {len(fixes)} 条 users 记录")

    return report


async def check_cross_table_consistency(db: AsyncSession) -> dict:
    """检查 accounts 与 users 表的 email 一致性"""
    report = {
        "mismatches": [],
        "orphaned_accounts": 0,
    }

    try:
        # 通过 phone + tenant_id 匹配 Account 和 User
        stmt = text("""
            SELECT a.id AS account_id, a.email AS account_email,
                   u.id AS user_id, u.email AS user_email
            FROM accounts a
            INNER JOIN users u ON u.phone = a.phone AND (u.tenant_id = a.tenant_id OR (u.tenant_id IS NULL AND a.tenant_id IS NULL))
            WHERE (a.email IS NOT NULL AND a.email != '')
               OR (u.email IS NOT NULL AND u.email != '')
        """)

        result = await db.execute(stmt)
        rows = result.fetchall()

        for row in rows:
            acc_email = (row.account_email or "").strip().lower()
            user_email = (row.user_email or "").strip().lower()

            if acc_email and user_email and acc_email != user_email:
                report["mismatches"].append({
                    "account_id": row.account_id,
                    "user_id": row.user_id,
                    "account_email": acc_email,
                    "user_email": user_email,
                })
                print(f"  [MISMATCH] account={row.account_id} acc_email='{acc_email}' "
                      f"user={row.user_id} user_email='{user_email}'")
    except Exception as e:
        await db.rollback()
        if "does not exist" in str(e):
            print("  [SKIP] 跨表检查需要 email 迁移已完成，跳过")
        else:
            print(f"  [ERROR] 跨表检查失败: {e}")

    return report


async def main():
    fix = "--fix" in sys.argv
    mode = "修复模式" if fix else "仅检查（dry-run）"

    print(f"{'=' * 60}")
    print(f"邮箱数据清洗脚本 - {mode}")
    print(f"{'=' * 60}")

    async with async_session_maker() as db:
        print(f"\n[1/3] 检查 accounts 表...")
        acc_report = await check_accounts(db, fix)

        print(f"\n[2/3] 检查 users 表...")
        user_report = await check_users(db, fix)

        print(f"\n[3/3] 检查跨表一致性...")
        consistency = await check_cross_table_consistency(db)

    # 汇总报告
    print(f"\n{'=' * 60}")
    print("汇总报告")
    print(f"{'=' * 60}")
    print(f"accounts 表:")
    print(f"  总记录: {acc_report['total']}")
    print(f"  有邮箱: {acc_report['with_email']}")
    print(f"  空白清理: {acc_report['empty_trimmed']}")
    print(f"  格式规范化: {acc_report['normalized']}")
    print(f"  格式不合法: {acc_report['invalid_format']}")
    print(f"  重复邮箱组: {len(acc_report['duplicates'])}")

    print(f"\nusers 表:")
    print(f"  总记录: {user_report['total']}")
    print(f"  有邮箱: {user_report['with_email']}")
    print(f"  空白清理: {user_report['empty_trimmed']}")
    print(f"  格式规范化: {user_report['normalized']}")
    print(f"  格式不合法: {user_report['invalid_format']}")
    print(f"  重复邮箱组: {len(user_report['duplicates'])}")

    print(f"\n跨表一致性:")
    print(f"  邮箱不一致: {len(consistency['mismatches'])}")

    if fix:
        total_fixed = acc_report["fixed"] + user_report["fixed"]
        print(f"\n已修复: {total_fixed} 条记录")
    else:
        has_issues = (
            acc_report["invalid_format"] > 0
            or acc_report["normalized"] > 0
            or acc_report["duplicates"]
            or user_report["invalid_format"] > 0
            or user_report["normalized"] > 0
            or user_report["duplicates"]
            or consistency["mismatches"]
        )
        if has_issues:
            print(f"\n发现问题，运行 --fix 执行修复")
        else:
            print(f"\n数据质量良好，无需修复")


if __name__ == "__main__":
    asyncio.run(main())
