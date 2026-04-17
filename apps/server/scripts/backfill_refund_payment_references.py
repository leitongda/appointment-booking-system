"""批量修复历史退款记录中的支付引用字段。"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import AsyncSessionLocal
from app.modules.refunds.service import RefundService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="修复 refund_records 中遗留的 out_trade_no / wx_transaction_id / payment_profile_id"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="实际写入数据库；默认仅 dry-run 预览",
    )
    parser.add_argument(
        "--tenant-id",
        help="仅处理指定租户的退款记录",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="最多处理多少条退款记录",
    )
    return parser


async def main():
    parser = build_parser()
    args = parser.parse_args()

    dry_run = not args.apply

    print("=" * 72)
    print("退款支付引用回填")
    print("=" * 72)
    print(f"模式: {'DRY RUN' if dry_run else 'APPLY'}")
    print(f"租户: {args.tenant_id or '全部'}")
    print(f"限制: {args.limit or '不限制'}")
    print()

    async with AsyncSessionLocal() as db:
        service = RefundService(db)

        try:
            summary = await service.backfill_refund_payment_references(
                tenant_id=args.tenant_id,
                limit=args.limit,
                dry_run=dry_run,
            )

            if dry_run:
                await db.rollback()
            else:
                await db.commit()

            print("统计结果")
            print(f"  扫描记录: {summary['scanned']}")
            print(f"  待更新: {summary['would_update']}")
            print(f"  已更新: {summary['updated']}")
            print(f"  无需变更: {summary['unchanged']}")
            print(f"  无法修复: {summary['unrepairable']}")

            if summary["details"]:
                print()
                print("明细")
                for item in summary["details"]:
                    print(
                        f"- refund_no={item['refund_no']} "
                        f"appointment_id={item['appointment_id']} "
                        f"changes={item['changes']} issues={item['issues']}"
                    )

            print()
            print("完成")
        except Exception as exc:
            await db.rollback()
            print(f"执行失败: {exc}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
