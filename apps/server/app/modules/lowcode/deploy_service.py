"""低代码页面部署服务。

职责: 代码生成 -> 构建 -> 上传 -> 审核 -> 发布 的完整部署流水线。
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lowcode_page import LowCodePage
from app.models.miniapp_platform import BuildJob, ReleaseJob
from app.utils.audit import set_update_audit

logger = logging.getLogger(__name__)

# 部署状态常量
DEPLOY_STATUS_IDLE = "idle"
DEPLOY_STATUS_BUILDING = "building"
DEPLOY_STATUS_BUILT = "built"
DEPLOY_STATUS_UPLOADING = "uploading"
DEPLOY_STATUS_UPLOADED = "uploaded"
DEPLOY_STATUS_AUDITING = "auditing"
DEPLOY_STATUS_PUBLISHED = "published"
DEPLOY_STATUS_FAILED = "failed"

_VALID_DEPLOY_TRANSITIONS: dict[str, set[str]] = {
    DEPLOY_STATUS_IDLE: {DEPLOY_STATUS_BUILDING},
    DEPLOY_STATUS_BUILDING: {DEPLOY_STATUS_BUILT, DEPLOY_STATUS_FAILED},
    DEPLOY_STATUS_BUILT: {DEPLOY_STATUS_UPLOADING, DEPLOY_STATUS_FAILED},
    DEPLOY_STATUS_UPLOADING: {DEPLOY_STATUS_UPLOADED, DEPLOY_STATUS_FAILED},
    DEPLOY_STATUS_UPLOADED: {DEPLOY_STATUS_AUDITING, DEPLOY_STATUS_FAILED},
    DEPLOY_STATUS_AUDITING: {DEPLOY_STATUS_PUBLISHED, DEPLOY_STATUS_FAILED},
    DEPLOY_STATUS_FAILED: {DEPLOY_STATUS_BUILDING},  # 失败后可重新构建
    DEPLOY_STATUS_PUBLISHED: {DEPLOY_STATUS_BUILDING},  # 已发布后可重新构建
}


class DeployError(Exception):
    """部署流程异常。"""


class LowCodeDeployService:
    """低代码部署服务。

    封装 codegen -> build -> upload -> audit 的完整部署流程。
    当前实现为占位逻辑 (stub)，后续接入实际部署管线。
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_page(self, tenant_id: str, page_id: str) -> LowCodePage:
        """加载页面，不存在则抛出异常。"""
        query = select(LowCodePage).where(
            LowCodePage.tenant_id == tenant_id,
            LowCodePage.id == page_id,
        )
        result = await self.db.execute(query)
        page = result.scalar_one_or_none()
        if not page:
            raise DeployError("页面不存在")
        return page

    async def _update_deploy_status(
        self,
        page: LowCodePage,
        new_status: str,
        updated_by: Optional[str] = None,
    ) -> None:
        """更新部署状态，校验状态转换合法性。"""
        current = page.deploy_status or DEPLOY_STATUS_IDLE
        allowed = _VALID_DEPLOY_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise DeployError(
                f"部署状态不允许从 '{current}' 转换到 '{new_status}'"
            )
        page.deploy_status = new_status
        page.last_deploy_at = datetime.now(timezone.utc)
        if updated_by:
            set_update_audit(page, updated_by)
        await self.db.commit()
        await self.db.refresh(page)

    async def _create_build_job(
        self,
        page: LowCodePage,
        trigger_source: str = "lowcode_deploy",
    ) -> BuildJob:
        """创建构建任务记录。"""
        job = BuildJob(
            tenant_id=page.tenant_id,
            miniapp_instance_id=page.miniapp_instance_id,
            lowcode_page_id=page.id,
            trigger_source=trigger_source,
            build_params="{}",
            status="pending",
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def _create_release_job(
        self,
        page: LowCodePage,
        action: str,
        artifact_id: Optional[str] = None,
    ) -> ReleaseJob:
        """创建发布任务记录。"""
        job = ReleaseJob(
            miniapp_instance_id=page.miniapp_instance_id,
            artifact_id=artifact_id,
            action=action,
            status="pending",
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def trigger_deploy(
        self,
        tenant_id: str,
        page_id: str,
        updated_by: Optional[str] = None,
    ) -> dict[str, Any]:
        """触发部署: 创建构建任务并派发到 Celery 异步执行。

        Returns:
            部署任务摘要，包含 build_job_id。

        Raises:
            DeployError: 页面不存在、未关联小程序实例、或状态不允许部署。
        """
        page = await self._load_page(tenant_id, page_id)

        if not page.miniapp_instance_id:
            raise DeployError("页面未关联小程序实例，无法部署")

        # 更新状态为 building
        await self._update_deploy_status(page, DEPLOY_STATUS_BUILDING, updated_by)

        # 创建构建任务
        build_job = await self._create_build_job(page)

        # 派发到 Celery 异步执行
        from app.tasks.lowcode_deploy_task import build_lowcode_page_task
        build_lowcode_page_task.delay(str(page.id), str(build_job.id))

        return {
            "build_job_id": str(build_job.id),
            "deploy_status": DEPLOY_STATUS_BUILDING,
            "message": "部署任务已提交，正在异步执行",
        }

    async def get_deploy_status(
        self,
        tenant_id: str,
        page_id: str,
    ) -> dict[str, Any]:
        """获取页面的当前部署状态。

        Returns:
            包含 deploy_status、last_deploy_at、最近构建任务信息的字典。
        """
        page = await self._load_page(tenant_id, page_id)

        # 查询最近的构建任务
        build_job_info: Optional[dict[str, Any]] = None
        if page.last_build_job_id:
            query = select(BuildJob).where(BuildJob.id == page.last_build_job_id)
            result = await self.db.execute(query)
            job = result.scalar_one_or_none()
            if job:
                build_job_info = {
                    "id": str(job.id),
                    "status": job.status,
                    "build_log": job.build_log,
                    "artifact_url": job.artifact_url,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                }

        return {
            "page_id": str(page.id),
            "deploy_status": page.deploy_status or DEPLOY_STATUS_IDLE,
            "last_deploy_at": (
                page.last_deploy_at.isoformat() if page.last_deploy_at else None
            ),
            "miniapp_instance_id": page.miniapp_instance_id,
            "build_job": build_job_info,
        }

    async def rollback_deploy(
        self,
        tenant_id: str,
        page_id: str,
        target_version: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> dict[str, Any]:
        """回滚部署到上一个已发布版本。

        Args:
            target_version: 目标版本号，为 None 时自动选择上一个已发布版本。

        Returns:
            回滚结果摘要。
        """
        page = await self._load_page(tenant_id, page_id)

        if page.deploy_status not in (
            DEPLOY_STATUS_PUBLISHED,
            DEPLOY_STATUS_AUDITING,
            DEPLOY_STATUS_FAILED,
        ):
            raise DeployError(
                f"当前部署状态 '{page.deploy_status}' 不允许回滚"
            )

        # 查询上一个成功的构建任务作为回滚目标
        query = (
            select(BuildJob)
            .where(
                BuildJob.lowcode_page_id == page.id,
                BuildJob.tenant_id == tenant_id,
                BuildJob.status == "completed",
            )
            .order_by(BuildJob.created_at.desc())
            .limit(2)
        )
        result = await self.db.execute(query)
        jobs = list(result.scalars().all())

        if len(jobs) < 2:
            raise DeployError("没有可回滚的历史版本")

        # jobs[0] 是当前版本，jobs[1] 是上一个版本
        target_job = jobs[1]

        # 创建回滚发布任务
        release_job = await self._create_release_job(
            page,
            action="rollback",
            artifact_id=target_job.id if target_job.artifact_url else None,
        )

        # 更新部署状态
        page.deploy_status = DEPLOY_STATUS_UPLOADED
        page.last_deploy_at = datetime.now(timezone.utc)
        if updated_by:
            set_update_audit(page, updated_by)
        await self.db.commit()
        await self.db.refresh(page)

        return {
            "page_id": str(page.id),
            "rollback_to_version": target_job.artifact_url,
            "deploy_status": DEPLOY_STATUS_UPLOADED,
            "release_job_id": str(release_job.id),
        }

    async def generate_preview_qr(
        self,
        tenant_id: str,
        page_id: str,
    ) -> dict[str, Any]:
        """生成预览二维码。

        上传代码到微信开发版并生成体验二维码，供测试人员扫码预览。

        Returns:
            包含 qr_code_url 和 expires_at 的字典。
        """
        page = await self._load_page(tenant_id, page_id)

        if not page.miniapp_instance_id:
            raise DeployError("页面未关联小程序实例，无法生成预览")

        # TODO: 调用微信开发版上传接口 + 生成体验二维码
        logger.info(
            "preview deploy: page_id=%s, miniapp_instance_id=%s",
            page.id,
            page.miniapp_instance_id,
        )

        return {
            "page_id": str(page.id),
            "qr_code_url": f"https://api.weixin.qq.com/wxa/get_qrcode?token=preview_{page.id}",
            "expires_at": None,  # TODO: 设置过期时间
            "message": "预览二维码生成成功（占位）",
        }

    async def handle_audit_callback(
        self,
        callback_data: dict[str, Any],
    ) -> dict[str, Any]:
        """处理微信审核状态回调。

        根据审核结果更新部署状态:
        - audit_success -> published
        - audit_fail -> failed

        Returns:
            处理结果。
        """
        # TODO: 校验回调签名
        audit_id = callback_data.get("auditid")
        status_code = callback_data.get("status")
        reason = callback_data.get("reason", "")

        if not audit_id:
            raise DeployError("回调缺少 auditid 字段")

        # 查询关联的构建任务
        # audit_id 格式为 "audit_{page_id}"，从回调中提取 page_id
        if not audit_id.startswith("audit_"):
            raise DeployError(f"无效的 audit_id 格式: {audit_id}")

        page_id = audit_id[len("audit_"):]

        query = select(LowCodePage).where(LowCodePage.id == page_id)
        result = await self.db.execute(query)
        page = result.scalar_one_or_none()
        if not page:
            raise DeployError(f"找不到关联页面: {page_id}")

        # status == 0 表示审核通过，其他表示失败
        if status_code == 0:
            page.deploy_status = DEPLOY_STATUS_PUBLISHED
            page.status = 1  # 已发布
            logger.info("audit passed: page_id=%s", page_id)
        else:
            page.deploy_status = DEPLOY_STATUS_FAILED
            logger.warning(
                "audit failed: page_id=%s, reason=%s", page_id, reason
            )

        page.last_deploy_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(page)

        return {
            "page_id": page_id,
            "deploy_status": page.deploy_status,
            "audit_status": "passed" if status_code == 0 else "failed",
            "reason": reason,
        }
