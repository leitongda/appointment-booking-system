#!/usr/bin/env python3
"""R4-12：回填租户 features.online_payment=True

背景（docs/tenant-remaining-plan.md §5.2 步骤 7 / §7 R4-12）：
`FEATURE_ENFORCEMENT_ENABLED` 翻 True 之前，必须保证活跃租户的
`online_payment` 已开通，否则存量租户支付下单全部 403。
功能读取优先级为 租户覆盖（`tenants.features`）> 订阅计划
（`subscription_plans.features`）> 系统默认（默认 False），
因此本脚本统一写入租户级覆盖，语义明确且不动计划默认。

原则：
- 只处理「活跃」租户：status=1 且未软删除（deleted_at IS NULL）；
- 保留 features JSON 中的其他键，仅设置/覆盖 online_payment；
- 默认 dry-run 只输出清单与计数；--execute 才落库；
- 幂等：已是 True 的租户跳过；重复执行结果一致。

使用方法:
    # 预览模式（不执行修改）
    python scripts/backfill_online_payment_feature.py

    # 执行回填
    python scripts/backfill_online_payment_feature.py --execute

    # 复核：回填后活跃租户中未开通数应为 0
    python scripts/backfill_online_payment_feature.py
"""
import argparse
import json
import logging
import sys
from pathlib import Path

# apps/server 加入 sys.path，支持在项目目录直接 python scripts/... 运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.db.session import get_sync_db_session
from app.models.tenant import Tenant

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("backfill_online_payment")

FEATURE_KEY = "online_payment"


def _effective_features(tenant: Tenant) -> dict:
    """解析租户 features JSON（损坏/为空视为空 dict，不猜测默认）。"""
    if not tenant.features:
        return {}
    try:
        data = json.loads(tenant.features)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def run(execute: bool) -> int:
    db = get_sync_db_session()
    try:
        tenants = (
            db.execute(
                select(Tenant).where(
                    Tenant.status == 1,
                    Tenant.deleted_at.is_(None),
                )
            )
            .scalars()
            .all()
        )

        to_backfill = []
        already = []
        for tenant in tenants:
            features = _effective_features(tenant)
            if features.get(FEATURE_KEY) is True:
                already.append(tenant)
            else:
                to_backfill.append((tenant, features))

        logger.info(
            "活跃租户共 %s 个：已开通 %s 个，待回填 %s 个（execute=%s）",
            len(tenants), len(already), len(to_backfill), execute,
        )
        for tenant, _ in to_backfill:
            logger.info(
                "  待回填: %s(%s) features=%s",
                tenant.name, tenant.tenant_code, tenant.features,
            )

        if not execute:
            logger.info("dry-run 结束，未修改任何数据")
            return 0

        for tenant, features in to_backfill:
            features[FEATURE_KEY] = True
            tenant.features = json.dumps(features, ensure_ascii=False)

        db.commit()
        logger.info("已回填 %s 个租户并提交", len(to_backfill))
        return 0
    except Exception:
        db.rollback()
        logger.exception("回填失败，已回滚")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute", action="store_true", help="执行回填（默认 dry-run）"
    )
    args = parser.parse_args()
    sys.exit(run(execute=args.execute))
