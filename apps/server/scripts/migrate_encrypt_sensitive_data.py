"""
敏感数据加密迁移脚本

将 patients 表中现有的 phone 和 id_card 明文数据加密填充到新加密列。
支持断点续传（按 ID 范围分批处理）。

用法：
    cd apps/server
    python scripts/migrate_encrypt_sensitive_data.py

注意事项：
1. 运行前确保已执行 Alembic 迁移（添加加密列）
2. 运行期间不影响正常业务（双写模式，新写入同时写明文+加密列）
3. 运行完成后需人工验证数据正确性，再执行删除明文列的迁移
"""
import argparse
import logging
import sys
import time
from pathlib import Path

# 将 apps/server 加入 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, select, update, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.encryption import encrypt, hash_value
from app.models.user import Patient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def migrate_batch(
    session: Session,
    batch_size: int,
    dry_run: bool = False,
) -> tuple[int, int]:
    """处理一批未加密的记录

    Args:
        session: 数据库会话
        batch_size: 批次大小
        dry_run: 试运行模式（不实际写入）

    Returns:
        (处理数, 跳过数)
    """
    # 查询未加密的记录（phone_encrypted 为 NULL 且 phone 不为 NULL）
    stmt = (
        select(Patient)
        .where(
            Patient.phone_encrypted.is_(None),
            Patient.phone.isnot(None),
        )
        .limit(batch_size)
    )

    results = session.execute(stmt).scalars().all()
    processed = 0
    skipped = 0

    for patient in results:
        try:
            # 加密 phone
            if patient.phone:
                patient.phone_encrypted = encrypt(patient.phone)
                patient.phone_hash = hash_value(patient.phone)

            # 加密 id_card
            if patient.id_card:
                patient.id_card_encrypted = encrypt(patient.id_card)
                patient.id_card_hash = hash_value(patient.id_card)

            processed += 1

            if processed % 100 == 0:
                logger.info(f"  已处理 {processed} 条...")

        except Exception as e:
            logger.error(f"  跳过 patient {patient.id}: {e}")
            skipped += 1

    if not dry_run and processed > 0:
        session.commit()
        logger.info(f"  提交 {processed} 条记录")
    elif dry_run:
        session.rollback()
        logger.info(f"  [试运行] 回滚 {processed} 条记录")

    return processed, skipped


def run_migration(
    batch_size: int = 1000,
    dry_run: bool = False,
    max_batches: int | None = None,
):
    """执行加密迁移

    Args:
        batch_size: 每批处理记录数
        dry_run: 试运行模式
        max_batches: 最大批次数（None 表示处理全部）
    """
    # 使用同步连接（迁移脚本不需要异步）
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(db_url, pool_pre_ping=True)

    logger.info("=" * 60)
    logger.info("敏感数据加密迁移")
    logger.info("=" * 60)
    logger.info(f"数据库: {db_url.split('@')[1] if '@' in db_url else 'local'}")
    logger.info(f"批次大小: {batch_size}")
    logger.info(f"试运行: {dry_run}")
    logger.info(f"最大批次: {max_batches or '无限'}")
    logger.info("-" * 60)

    # 统计待处理记录数
    with Session(engine) as session:
        total_stmt = select(func.count()).where(
            Patient.phone_encrypted.is_(None),
            Patient.phone.isnot(None),
        )
        total = session.execute(total_stmt).scalar() or 0
        logger.info(f"待处理记录数: {total}")

    if total == 0:
        logger.info("无需处理，退出")
        return

    # 分批处理
    start_time = time.time()
    total_processed = 0
    total_skipped = 0
    batch_num = 0

    while True:
        batch_num += 1
        if max_batches and batch_num > max_batches:
            logger.info(f"达到最大批次限制 ({max_batches})，停止")
            break

        with Session(engine) as session:
            processed, skipped = migrate_batch(session, batch_size, dry_run)

        total_processed += processed
        total_skipped += skipped

        if processed == 0:
            logger.info("所有记录已处理完毕")
            break

        elapsed = time.time() - start_time
        rate = total_processed / elapsed if elapsed > 0 else 0
        remaining = (total - total_processed) / rate if rate > 0 else 0

        logger.info(
            f"批次 {batch_num}: 处理 {processed}, 跳过 {skipped} | "
            f"累计 {total_processed}/{total} | "
            f"速率 {rate:.0f} 条/秒 | "
            f"预计剩余 {remaining:.0f} 秒"
        )

    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"迁移完成: 处理 {total_processed}, 跳过 {total_skipped}, 耗时 {elapsed:.1f} 秒")
    logger.info("=" * 60)

    if dry_run:
        logger.info("[试运行模式] 未实际写入数据库")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="敏感数据加密迁移")
    parser.add_argument("--batch-size", type=int, default=1000, help="每批处理记录数")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式（不实际写入）")
    parser.add_argument("--max-batches", type=int, default=None, help="最大批次数")
    args = parser.parse_args()

    try:
        run_migration(
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            max_batches=args.max_batches,
        )
    except KeyboardInterrupt:
        logger.info("\n用户中断，已安全停止")
    except Exception as e:
        logger.error(f"迁移失败: {e}", exc_info=True)
        sys.exit(1)
