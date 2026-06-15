"""兼职费用 — 公开接口（兼职人员自助查看，无需登录）"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.freelance import (
    FreelanceInteraction,
    Freelancer,
    FreelanceSettlement,
    FreelanceTask,
)

router = APIRouter()


@router.get("/portal/{access_token}", summary="兼职人员自助查看")
async def get_freelancer_portal(
    access_token: str,
    db: AsyncSession = Depends(get_db),
):
    """兼职人员通过访问令牌查看自己的任务和收入"""
    # 查找兼职人员
    stmt = select(Freelancer).where(
        and_(Freelancer.access_token == access_token, Freelancer.status == 1)
    )
    result = await db.execute(stmt)
    freelancer = result.scalar_one_or_none()
    if not freelancer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="无效的访问链接")

    # 查询任务列表
    task_stmt = (
        select(FreelanceTask)
        .where(FreelanceTask.freelancer_id == freelancer.id)
        .order_by(FreelanceTask.created_at.desc())
    )
    tasks = (await db.execute(task_stmt)).scalars().all()

    # 查询结算列表
    settle_stmt = (
        select(FreelanceSettlement)
        .where(FreelanceSettlement.freelancer_id == freelancer.id)
        .order_by(FreelanceSettlement.created_at.desc())
    )
    settlements = (await db.execute(settle_stmt)).scalars().all()

    # 统计
    total_earned = sum(float(s.actual_amount) for s in settlements if s.status in ("confirmed", "paid"))
    total_pending = sum(float(s.actual_amount) for s in settlements if s.status == "pending")
    total_tasks = len(tasks)

    return {
        "freelancer": {
            "name": freelancer.name,
            "accountName": freelancer.account_name,
            "accountPlatform": freelancer.account_platform,
        },
        "summary": {
            "totalTasks": total_tasks,
            "totalEarned": total_earned,
            "totalPending": total_pending,
        },
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "publishedAt": t.published_at.isoformat() if t.published_at else None,
                "likesCount": t.likes_count,
                "commentsCount": t.comments_count,
                "baseAmount": float(t.base_amount or 0),
                "bonusAmount": float(t.bonus_amount or 0),
                "likesBonusAmount": float(t.likes_bonus_amount or 0),
            }
            for t in tasks
        ],
        "settlements": [
            {
                "id": s.id,
                "settlementNo": s.settlement_no,
                "totalAmount": float(s.total_amount or 0),
                "actualAmount": float(s.actual_amount or 0),
                "status": s.status,
                "createdAt": s.created_at.isoformat() if s.created_at else None,
            }
            for s in settlements
        ],
    }


@router.get("/portal/{access_token}/interactions/{task_id}", summary="查看任务互动记录")
async def get_task_interactions_public(
    access_token: str,
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """兼职人员查看自己某个任务的互动记录"""
    # 验证访问令牌
    freelancer_stmt = select(Freelancer).where(
        and_(Freelancer.access_token == access_token, Freelancer.status == 1)
    )
    freelancer = (await db.execute(freelancer_stmt)).scalar_one_or_none()
    if not freelancer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="无效的访问链接")

    # 验证任务归属
    task_stmt = select(FreelanceTask).where(
        and_(FreelanceTask.id == task_id, FreelanceTask.freelancer_id == freelancer.id)
    )
    task = (await db.execute(task_stmt)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    # 查询互动记录
    interaction_stmt = (
        select(FreelanceInteraction)
        .where(FreelanceInteraction.task_id == task_id)
        .order_by(FreelanceInteraction.created_at.desc())
    )
    interactions = (await db.execute(interaction_stmt)).scalars().all()

    return [
        {
            "id": i.id,
            "interactionType": i.interaction_type,
            "content": i.content,
            "amount": float(i.amount or 0.5),
            "interactedAt": i.interacted_at.isoformat() if i.interacted_at else None,
        }
        for i in interactions
    ]
