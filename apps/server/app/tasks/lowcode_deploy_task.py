"""
低代码小程序部署流水线 Celery 任务

流水线阶段:
1. build_lowcode_page_task  — 代码生成 + Taro 构建 + 产物存储
2. upload_to_wechat_task    — 上传代码到微信平台
3. submit_audit_task        — 提交微信审核
4. publish_release_task     — 发布已审核通过的版本
5. rollback_task            — 回滚到上一个已发布版本
"""
import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.models.miniapp_platform import (
    BuildJob,
    MiniappInstance,
    ReleaseArtifact,
    ReleaseJob,
)
from app.models.lowcode_page import LowCodePage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _run_async(coro):
    """在同步 Celery 上下文中运行异步协程。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _get_instance_secrets(db, instance: MiniappInstance) -> dict:
    """从实例配置中解析 app_id / app_secret。

    app_secret_ref 支持 ``env:XXX`` 格式，优先从环境变量读取，
    回退到 ref 字符串本身。
    """
    app_secret = instance.app_secret_ref or ""
    if app_secret.upper().startswith("ENV:"):
        env_key = app_secret[4:]
        app_secret = os.environ.get(env_key, "")

    return {
        "app_id": instance.app_id,
        "app_secret": app_secret,
    }


def _save_build_log(db, job: BuildJob, log_text: str):
    """追加构建日志到 BuildJob。"""
    existing = job.build_log or ""
    separator = "\n---\n" if existing else ""
    job.build_log = existing + separator + log_text
    db.flush()


def _create_release_artifact(db, job: BuildJob, file_path: str) -> ReleaseArtifact:
    """为构建产物创建 ReleaseArtifact 记录。"""
    checksum = ""
    if os.path.isfile(file_path):
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        checksum = h.hexdigest()

    artifact = ReleaseArtifact(
        build_job_id=job.id,
        file_path=file_path,
        checksum=checksum,
    )
    db.add(artifact)
    db.flush()
    return artifact


def _update_page_deploy_status(db, page_id: str, status: str):
    """更新低代码页面的部署状态。"""
    page = db.execute(
        select(LowCodePage).where(LowCodePage.id == page_id)
    ).scalar_one_or_none()
    if page:
        page.deploy_status = status
        page.last_deploy_at = datetime.now()
        db.flush()


# ---------------------------------------------------------------------------
# 1. 构建低代码页面
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.tasks.lowcode_deploy_task.build_lowcode_page_task",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    time_limit=1800,
    soft_time_limit=1500,
)
def build_lowcode_page_task(self, page_id: str, tenant_id: str):
    """构建低代码页面：codegen 生成 Taro 代码 + Taro 构建 + 产物存储。

    流程:
    1. 从数据库加载 LowCodePage 和关联的 MiniappInstance
    2. 调用 CodegenService.generate_taro 生成页面源码
    3. 将生成的文件写入临时目录，执行 ``taro build`` 构建小程序包
    4. 创建 BuildJob 记录并关联产物 (ReleaseArtifact)
    5. 更新 LowCodePage 的 deploy_status

    Args:
        page_id: 低代码页面 ID
        tenant_id: 租户 ID

    Returns:
        dict: {"success": bool, "build_job_id": str, "artifact_id": str | None, ...}
    """
    logger.info("[构建任务] 开始: page_id=%s, tenant_id=%s", page_id, tenant_id)

    with get_sync_db() as db:
        # ---------- 加载页面和实例 ----------
        page = db.execute(
            select(LowCodePage).where(
                LowCodePage.id == page_id,
                LowCodePage.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()

        if not page:
            logger.error("[构建任务] 页面不存在: page_id=%s", page_id)
            return {"success": False, "reason": "页面不存在"}

        if not page.miniapp_instance_id:
            logger.error("[构建任务] 页面未关联小程序实例: page_id=%s", page_id)
            _update_page_deploy_status(db, page_id, "failed")
            db.commit()
            return {"success": False, "reason": "页面未关联小程序实例"}

        instance = db.execute(
            select(MiniappInstance).where(
                MiniappInstance.id == page.miniapp_instance_id,
            )
        ).scalar_one_or_none()

        if not instance:
            logger.error("[构建任务] 小程序实例不存在: instance_id=%s", page.miniapp_instance_id)
            _update_page_deploy_status(db, page_id, "failed")
            db.commit()
            return {"success": False, "reason": "小程序实例不存在"}

        # ---------- 创建 BuildJob (pending -> running) ----------
        build_job = BuildJob(
            tenant_id=tenant_id,
            miniapp_instance_id=instance.id,
            lowcode_page_id=page_id,
            trigger_source="celery_deploy",
            build_params=json.dumps({"page_id": page_id}),
            status="running",
            started_at=datetime.now(),
        )
        db.add(build_job)
        db.flush()
        build_job_id = build_job.id

        _update_page_deploy_status(db, page_id, "building")
        db.commit()

        # ---------- Codegen 生成 Taro 源码 ----------
        try:
            from app.modules.lowcode.codegen_service import CodegenService, CodegenError

            async def _run_codegen():
                codegen = CodegenService(db)
                return await codegen.generate_taro(page_id, tenant_id)

            codegen_result = _run_async(_run_codegen())

            _save_build_log(
                db,
                db.get(BuildJob, build_job_id),
                f"Codegen 完成: 生成 {len(codegen_result.files)} 个文件, "
                f"警告 {len(codegen_result.warnings)} 条",
            )
            db.commit()

        except Exception as exc:
            error_msg = f"代码生成失败: {exc}"
            logger.error("[构建任务] %s", error_msg, exc_info=True)
            _fail_build_job(db, build_job_id, page_id, error_msg)
            return {"success": False, "reason": error_msg, "build_job_id": build_job_id}

        # ---------- 写入临时目录并执行 Taro 构建 ----------
        project_dir = None
        try:
            project_dir = tempfile.mkdtemp(prefix="lowcode_build_")
            _write_codegen_files(project_dir, codegen_result)

            taro_output = _run_taro_build(project_dir)

            _save_build_log(
                db,
                db.get(BuildJob, build_job_id),
                f"Taro 构建完成: {taro_output}",
            )
            db.commit()

        except Exception as exc:
            error_msg = f"Taro 构建失败: {exc}"
            logger.error("[构建任务] %s", error_msg, exc_info=True)
            _fail_build_job(db, build_job_id, page_id, error_msg)
            return {"success": False, "reason": error_msg, "build_job_id": build_job_id}
        finally:
            if project_dir:
                shutil.rmtree(project_dir, ignore_errors=True)

        # ---------- 存储构建产物 ----------
        try:
            artifact_dir = _get_artifact_dir(tenant_id, page_id)
            os.makedirs(artifact_dir, exist_ok=True)
            dist_path = os.path.join(project_dir, "dist")
            artifact_path = os.path.join(artifact_dir, f"build_{build_job_id}.tar.gz")

            _create_tarball(dist_path, artifact_path)

            artifact = _create_release_artifact(
                db, db.get(BuildJob, build_job_id), artifact_path
            )

            # 更新 BuildJob 状态
            job = db.get(BuildJob, build_job_id)
            job.status = "success"
            job.finished_at = datetime.now()
            job.artifact_url = artifact_path

            _update_page_deploy_status(db, page_id, "built")
            db.commit()

            logger.info(
                "[构建任务] 成功: page_id=%s, build_job_id=%s, artifact_id=%s",
                page_id,
                build_job_id,
                artifact.id,
            )
            return {
                "success": True,
                "build_job_id": build_job_id,
                "artifact_id": artifact.id,
                "artifact_path": artifact_path,
            }

        except Exception as exc:
            error_msg = f"产物存储失败: {exc}"
            logger.error("[构建任务] %s", error_msg, exc_info=True)
            _fail_build_job(db, build_job_id, page_id, error_msg)
            return {"success": False, "reason": error_msg, "build_job_id": build_job_id}


# ---------------------------------------------------------------------------
# 2. 上传代码到微信平台
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.tasks.lowcode_deploy_task.upload_to_wechat_task",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=480,
)
def upload_to_wechat_task(self, build_job_id: str, instance_id: str):
    """将构建产物上传到微信小程序平台。

    流程:
    1. 加载 BuildJob 和关联的 ReleaseArtifact
    2. 解压制品到临时目录
    3. 调用 MiniappPublisher.upload_code 上传
    4. 创建 ReleaseJob (action=upload) 记录

    Args:
        build_job_id: 构建任务 ID
        instance_id: 小程序实例 ID

    Returns:
        dict: {"success": bool, "release_job_id": str, ...}
    """
    logger.info(
        "[上传任务] 开始: build_job_id=%s, instance_id=%s",
        build_job_id,
        instance_id,
    )

    with get_sync_db() as db:
        # ---------- 加载构建任务和制品 ----------
        build_job = db.execute(
            select(BuildJob).where(BuildJob.id == build_job_id)
        ).scalar_one_or_none()

        if not build_job:
            logger.error("[上传任务] 构建任务不存在: build_job_id=%s", build_job_id)
            return {"success": False, "reason": "构建任务不存在"}

        if build_job.status != "success":
            logger.error(
                "[上传任务] 构建任务未成功: build_job_id=%s, status=%s",
                build_job_id,
                build_job.status,
            )
            return {"success": False, "reason": f"构建任务状态异常: {build_job.status}"}

        artifact = db.execute(
            select(ReleaseArtifact).where(ReleaseArtifact.build_job_id == build_job_id)
        ).scalar_one_or_none()

        if not artifact:
            logger.error(
                "[上传任务] 构建产物不存在: build_job_id=%s", build_job_id
            )
            return {"success": False, "reason": "构建产物不存在"}

        # ---------- 加载小程序实例 ----------
        instance = db.execute(
            select(MiniappInstance).where(MiniappInstance.id == instance_id)
        ).scalar_one_or_none()

        if not instance:
            logger.error("[上传任务] 小程序实例不存在: instance_id=%s", instance_id)
            return {"success": False, "reason": "小程序实例不存在"}

        secrets = _get_instance_secrets(db, instance)
        if not secrets["app_secret"]:
            logger.error("[上传任务] 小程序 app_secret 为空: instance_id=%s", instance_id)
            return {"success": False, "reason": "小程序 app_secret 未配置"}

        # ---------- 创建 ReleaseJob (upload) ----------
        release_job = ReleaseJob(
            miniapp_instance_id=instance_id,
            artifact_id=artifact.id,
            action="upload",
            target_version=build_job.build_params and json.loads(build_job.build_params).get("version", "1.0.0"),
            status="running",
        )
        db.add(release_job)
        db.flush()
        release_job_id = release_job.id

        # 更新页面部署状态
        if build_job.lowcode_page_id:
            _update_page_deploy_status(db, build_job.lowcode_page_id, "uploading")

        db.commit()

        # ---------- 解压制品并上传 ----------
        extract_dir = None
        try:
            extract_dir = _extract_artifact(artifact.file_path)
            version = release_job.target_version or "1.0.0"

            from app.infrastructure.wechat.miniapp_publisher import MiniappPublisher

            publisher = MiniappPublisher(
                app_id=secrets["app_id"],
                app_secret=secrets["app_secret"],
            )

            upload_result = _run_async(
                publisher.upload_code(
                    project_path=extract_dir,
                    version=version,
                    desc=f"低代码页面构建 {build_job_id[:8]}",
                )
            )

            if not upload_result.get("success"):
                error_msg = upload_result.get("error", "未知上传错误")
                _fail_release_job(db, release_job_id, build_job, error_msg)
                return {
                    "success": False,
                    "reason": error_msg,
                    "release_job_id": release_job_id,
                }

            # 上传成功
            rj = db.get(ReleaseJob, release_job_id)
            rj.status = "success"
            rj.result = json.dumps(upload_result)

            if build_job.lowcode_page_id:
                _update_page_deploy_status(db, build_job.lowcode_page_id, "uploaded")

            db.commit()

            logger.info(
                "[上传任务] 成功: release_job_id=%s", release_job_id
            )
            return {
                "success": True,
                "release_job_id": release_job_id,
                "upload_output": upload_result.get("output", ""),
            }

        except Exception as exc:
            error_msg = f"上传失败: {exc}"
            logger.error("[上传任务] %s", error_msg, exc_info=True)
            _fail_release_job(db, release_job_id, build_job, error_msg)
            return {
                "success": False,
                "reason": error_msg,
                "release_job_id": release_job_id,
            }
        finally:
            if extract_dir:
                shutil.rmtree(extract_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 3. 提交微信审核
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.tasks.lowcode_deploy_task.submit_audit_task",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=300,
    soft_time_limit=240,
)
def submit_audit_task(self, release_job_id: str):
    """提交小程序代码到微信审核。

    Args:
        release_job_id: 发布任务 ID (action=upload 的 ReleaseJob)

    Returns:
        dict: {"success": bool, "audit_release_job_id": str, ...}
    """
    logger.info("[审核任务] 开始: release_job_id=%s", release_job_id)

    with get_sync_db() as db:
        # ---------- 加载上传任务 ----------
        upload_job = db.execute(
            select(ReleaseJob).where(ReleaseJob.id == release_job_id)
        ).scalar_one_or_none()

        if not upload_job:
            logger.error("[审核任务] 发布任务不存在: release_job_id=%s", release_job_id)
            return {"success": False, "reason": "发布任务不存在"}

        if upload_job.status != "success":
            logger.error(
                "[审核任务] 上传任务未成功: release_job_id=%s, status=%s",
                release_job_id,
                upload_job.status,
            )
            return {"success": False, "reason": f"上传任务状态异常: {upload_job.status}"}

        # ---------- 加载小程序实例 ----------
        instance = db.execute(
            select(MiniappInstance).where(
                MiniappInstance.id == upload_job.miniapp_instance_id
            )
        ).scalar_one_or_none()

        if not instance:
            return {"success": False, "reason": "小程序实例不存在"}

        secrets = _get_instance_secrets(db, instance)
        if not secrets["app_secret"]:
            return {"success": False, "reason": "小程序 app_secret 未配置"}

        # ---------- 创建 ReleaseJob (submit_audit) ----------
        audit_job = ReleaseJob(
            miniapp_instance_id=instance.id,
            artifact_id=upload_job.artifact_id,
            action="submit_audit",
            status="running",
        )
        db.add(audit_job)
        db.flush()
        audit_job_id = audit_job.id
        db.commit()

        # ---------- 调用微信提交审核 ----------
        try:
            from app.infrastructure.wechat.miniapp_publisher import MiniappPublisher

            publisher = MiniappPublisher(
                app_id=secrets["app_id"],
                app_secret=secrets["app_secret"],
            )

            result = _run_async(publisher.submit_audit())

            errcode = result.get("errcode", -1)
            if errcode != 0:
                error_msg = result.get("errmsg", "提交审核失败")
                _fail_audit_job(db, audit_job_id, error_msg)
                return {
                    "success": False,
                    "reason": error_msg,
                    "audit_release_job_id": audit_job_id,
                }

            # 审核提交成功
            aj = db.get(ReleaseJob, audit_job_id)
            aj.status = "success"
            aj.result = json.dumps(result)
            db.commit()

            logger.info(
                "[审核任务] 成功: audit_release_job_id=%s, auditid=%s",
                audit_job_id,
                result.get("auditid"),
            )
            return {
                "success": True,
                "audit_release_job_id": audit_job_id,
                "auditid": result.get("auditid"),
            }

        except Exception as exc:
            error_msg = f"提交审核异常: {exc}"
            logger.error("[审核任务] %s", error_msg, exc_info=True)
            _fail_audit_job(db, audit_job_id, error_msg)
            return {
                "success": False,
                "reason": error_msg,
                "audit_release_job_id": audit_job_id,
            }


# ---------------------------------------------------------------------------
# 4. 发布已审核通过的版本
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.tasks.lowcode_deploy_task.publish_release_task",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    time_limit=300,
    soft_time_limit=240,
)
def publish_release_task(self, release_job_id: str):
    """发布已审核通过的小程序版本。

    流程:
    1. 加载审核通过的 ReleaseJob (action=submit_audit)
    2. 调用 MiniappPublisher.release 发布
    3. 创建 ReleaseJob (action=publish) 记录
    4. 创建版本快照 (更新 LowCodePage.current_version / publish_count)

    Args:
        release_job_id: 审核任务 ID (action=submit_audit 的 ReleaseJob)

    Returns:
        dict: {"success": bool, "publish_release_job_id": str, ...}
    """
    logger.info("[发布任务] 开始: release_job_id=%s", release_job_id)

    with get_sync_db() as db:
        # ---------- 加载审核任务 ----------
        audit_job = db.execute(
            select(ReleaseJob).where(ReleaseJob.id == release_job_id)
        ).scalar_one_or_none()

        if not audit_job:
            logger.error("[发布任务] 审核任务不存在: release_job_id=%s", release_job_id)
            return {"success": False, "reason": "审核任务不存在"}

        if audit_job.status != "success":
            logger.error(
                "[发布任务] 审核任务未成功: release_job_id=%s, status=%s",
                release_job_id,
                audit_job.status,
            )
            return {"success": False, "reason": f"审核任务状态异常: {audit_job.status}"}

        # ---------- 加载小程序实例 ----------
        instance = db.execute(
            select(MiniappInstance).where(
                MiniappInstance.id == audit_job.miniapp_instance_id
            )
        ).scalar_one_or_none()

        if not instance:
            return {"success": False, "reason": "小程序实例不存在"}

        secrets = _get_instance_secrets(db, instance)
        if not secrets["app_secret"]:
            return {"success": False, "reason": "小程序 app_secret 未配置"}

        # ---------- 创建 ReleaseJob (publish) ----------
        publish_job = ReleaseJob(
            miniapp_instance_id=instance.id,
            artifact_id=audit_job.artifact_id,
            action="publish",
            status="running",
        )
        db.add(publish_job)
        db.flush()
        publish_job_id = publish_job.id
        db.commit()

        # ---------- 调用微信发布 ----------
        try:
            from app.infrastructure.wechat.miniapp_publisher import MiniappPublisher

            publisher = MiniappPublisher(
                app_id=secrets["app_id"],
                app_secret=secrets["app_secret"],
            )

            result = _run_async(publisher.release())

            errcode = result.get("errcode", -1)
            if errcode != 0:
                error_msg = result.get("errmsg", "发布失败")
                _fail_publish_job(db, publish_job_id, error_msg)
                return {
                    "success": False,
                    "reason": error_msg,
                    "publish_release_job_id": publish_job_id,
                }

            # 发布成功
            pj = db.get(ReleaseJob, publish_job_id)
            pj.status = "success"
            pj.result = json.dumps(result)

            # ---------- 创建版本快照 ----------
            _create_version_snapshot(db, audit_job)

            db.commit()

            logger.info(
                "[发布任务] 成功: publish_release_job_id=%s", publish_job_id
            )
            return {
                "success": True,
                "publish_release_job_id": publish_job_id,
            }

        except Exception as exc:
            error_msg = f"发布异常: {exc}"
            logger.error("[发布任务] %s", error_msg, exc_info=True)
            _fail_publish_job(db, publish_job_id, error_msg)
            return {
                "success": False,
                "reason": error_msg,
                "publish_release_job_id": publish_job_id,
            }


# ---------------------------------------------------------------------------
# 5. 版本回滚
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.tasks.lowcode_deploy_task.rollback_task",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    time_limit=300,
    soft_time_limit=240,
)
def rollback_task(self, release_job_id: str, target_version: Optional[str] = None):
    """回滚小程序到指定版本或上一个已发布的版本。

    如果提供了 target_version，重新上传该版本的构建产物并发布；
    否则使用微信 revertcoderelease API 回退到上一个已发布版本。

    Args:
        release_job_id: 当前发布任务 ID (用于关联实例)
        target_version: 目标版本号 (可选，不传则回退到上一版本)

    Returns:
        dict: {"success": bool, "rollback_release_job_id": str, ...}
    """
    logger.info(
        "[回滚任务] 开始: release_job_id=%s, target_version=%s",
        release_job_id,
        target_version,
    )

    with get_sync_db() as db:
        # ---------- 加载关联的发布任务 ----------
        source_job = db.execute(
            select(ReleaseJob).where(ReleaseJob.id == release_job_id)
        ).scalar_one_or_none()

        if not source_job:
            logger.error("[回滚任务] 发布任务不存在: release_job_id=%s", release_job_id)
            return {"success": False, "reason": "发布任务不存在"}

        # ---------- 加载小程序实例 ----------
        instance = db.execute(
            select(MiniappInstance).where(
                MiniappInstance.id == source_job.miniapp_instance_id
            )
        ).scalar_one_or_none()

        if not instance:
            return {"success": False, "reason": "小程序实例不存在"}

        secrets = _get_instance_secrets(db, instance)
        if not secrets["app_secret"]:
            return {"success": False, "reason": "小程序 app_secret 未配置"}

        # ---------- 创建 ReleaseJob (rollback) ----------
        rollback_job = ReleaseJob(
            miniapp_instance_id=instance.id,
            artifact_id=source_job.artifact_id,
            action="rollback",
            target_version=target_version,
            status="running",
        )
        db.add(rollback_job)
        db.flush()
        rollback_job_id = rollback_job.id
        db.commit()

        # ---------- 调用微信回滚 ----------
        try:
            from app.infrastructure.wechat.miniapp_publisher import MiniappPublisher

            publisher = MiniappPublisher(
                app_id=secrets["app_id"],
                app_secret=secrets["app_secret"],
            )

            if target_version:
                # 回滚到指定版本：查找该版本对应的构建产物并重新上传发布
                target_artifact = _find_artifact_by_version(
                    db, instance.id, target_version
                )
                if not target_artifact:
                    error_msg = f"未找到版本 {target_version} 的构建产物"
                    _fail_rollback_job(db, rollback_job_id, error_msg)
                    return {
                        "success": False,
                        "reason": error_msg,
                        "rollback_release_job_id": rollback_job_id,
                    }

                extract_dir = None
                try:
                    extract_dir = _extract_artifact(target_artifact.file_path)
                    upload_result = _run_async(
                        publisher.upload_code(
                            project_path=extract_dir,
                            version=target_version,
                            desc=f"回滚到版本 {target_version}",
                        )
                    )
                    if not upload_result.get("success"):
                        error_msg = upload_result.get("error", "回滚上传失败")
                        _fail_rollback_job(db, rollback_job_id, error_msg)
                        return {
                            "success": False,
                            "reason": error_msg,
                            "rollback_release_job_id": rollback_job_id,
                        }

                    # 上传成功后提交审核并发布
                    audit_result = _run_async(publisher.submit_audit())
                    if audit_result.get("errcode", -1) != 0:
                        error_msg = audit_result.get("errmsg", "回滚审核提交失败")
                        _fail_rollback_job(db, rollback_job_id, error_msg)
                        return {
                            "success": False,
                            "reason": error_msg,
                            "rollback_release_job_id": rollback_job_id,
                        }

                    release_result = _run_async(publisher.release())
                    if release_result.get("errcode", -1) != 0:
                        error_msg = release_result.get("errmsg", "回滚发布失败")
                        _fail_rollback_job(db, rollback_job_id, error_msg)
                        return {
                            "success": False,
                            "reason": error_msg,
                            "rollback_release_job_id": rollback_job_id,
                        }

                    result = release_result
                finally:
                    if extract_dir:
                        shutil.rmtree(extract_dir, ignore_errors=True)
            else:
                # 无指定版本，使用微信 revert API 回退到上一版本
                result = _run_async(publisher.rollback())

            errcode = result.get("errcode", -1)
            if errcode != 0:
                error_msg = result.get("errmsg", "回滚失败")
                _fail_rollback_job(db, rollback_job_id, error_msg)
                return {
                    "success": False,
                    "reason": error_msg,
                    "rollback_release_job_id": rollback_job_id,
                }

            # 回滚成功
            rj = db.get(ReleaseJob, rollback_job_id)
            rj.status = "success"
            rj.result = json.dumps(result)
            db.commit()

            logger.info(
                "[回滚任务] 成功: rollback_release_job_id=%s", rollback_job_id
            )
            return {
                "success": True,
                "rollback_release_job_id": rollback_job_id,
            }

        except Exception as exc:
            error_msg = f"回滚异常: {exc}"
            logger.error("[回滚任务] %s", error_msg, exc_info=True)
            _fail_rollback_job(db, rollback_job_id, error_msg)
            return {
                "success": False,
                "reason": error_msg,
                "rollback_release_job_id": rollback_job_id,
            }


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------


def _find_artifact_by_version(db, instance_id: str, version: str):
    """根据版本号查找对应的构建产物。

    查找该小程序实例最近一次成功的 upload ReleaseJob，其关联的 artifact
    中 build_job 的 version 匹配。
    """
    # 查找所有成功的 upload 任务，关联到该实例
    upload_jobs = db.execute(
        select(ReleaseJob).where(
            ReleaseJob.miniapp_instance_id == instance_id,
            ReleaseJob.action == "upload",
            ReleaseJob.status == "success",
        ).order_by(ReleaseJob.created_at.desc())
    ).scalars().all()

    for job in upload_jobs:
        if not job.target_version or job.target_version != version:
            continue
        if not job.artifact_id:
            continue
        artifact = db.execute(
            select(ReleaseArtifact).where(ReleaseArtifact.id == job.artifact_id)
        ).scalar_one_or_none()
        if artifact and os.path.isfile(artifact.file_path):
            return artifact

    return None


def _write_codegen_files(project_dir: str, codegen_result) -> None:
    """将 CodegenResult 中的文件写入项目目录。"""
    for f in codegen_result.files:
        file_path = os.path.join(project_dir, f.path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(f.content)


def _run_taro_build(project_dir: str) -> str:
    """在项目目录执行 ``taro build --type weapp``。

    Returns:
        构建输出日志

    Raises:
        RuntimeError: 构建失败时抛出
    """
    env = os.environ.copy()
    # 确保 node / npm 在 PATH 中
    result = subprocess.run(
        ["npx", "taro", "build", "--type", "weapp"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
    )

    stdout = result.stdout or ""
    stderr = result.stderr or ""
    output = stdout + "\n" + stderr

    if result.returncode != 0:
        raise RuntimeError(
            f"taro build 退出码 {result.returncode}:\n{output[-2000:]}"
        )

    return output[-2000:]  # 截断过长日志


def _get_artifact_dir(tenant_id: str, page_id: str) -> str:
    """获取构建产物存储目录。"""
    base = os.environ.get("ARTIFACT_DIR", "/tmp/lowcode_artifacts")
    return os.path.join(base, tenant_id, page_id)


def _create_tarball(source_dir: str, output_path: str) -> None:
    """将目录打包为 tar.gz。"""
    import tarfile

    with tarfile.open(output_path, "w:gz") as tar:
        for item in os.listdir(source_dir):
            tar.add(
                os.path.join(source_dir, item),
                arcname=item,
            )


def _extract_artifact(artifact_path: str) -> str:
    """解压 tar.gz 产物到临时目录，返回解压后的路径。"""
    import tarfile

    extract_dir = tempfile.mkdtemp(prefix="lowcode_upload_")
    with tarfile.open(artifact_path, "r:gz") as tar:
        tar.extractall(path=extract_dir, filter="data")
    return extract_dir


def _create_version_snapshot(db, audit_job: ReleaseJob):
    """发布成功后，更新关联 LowCodePage 的版本快照。

    - current_version += 1
    - publish_count += 1
    - deploy_status = published
    """
    if not audit_job.artifact_id:
        return

    artifact = db.execute(
        select(ReleaseArtifact).where(ReleaseArtifact.id == audit_job.artifact_id)
    ).scalar_one_or_none()

    if not artifact or not artifact.build_job_id:
        return

    build_job = db.execute(
        select(BuildJob).where(BuildJob.id == artifact.build_job_id)
    ).scalar_one_or_none()

    if not build_job or not build_job.lowcode_page_id:
        return

    page = db.execute(
        select(LowCodePage).where(LowCodePage.id == build_job.lowcode_page_id)
    ).scalar_one_or_none()

    if page:
        page.current_version = (page.current_version or 0) + 1
        page.publish_count = (page.publish_count or 0) + 1
        page.deploy_status = "published"
        page.status = 1  # 标记为已发布
        db.flush()
        logger.info(
            "[版本快照] page_id=%s, version=%s", page.id, page.current_version
        )


def _fail_build_job(db, build_job_id: str, page_id: str, error_msg: str):
    """将 BuildJob 标记为失败并更新页面部署状态。"""
    try:
        job = db.get(BuildJob, build_job_id)
        if job:
            job.status = "failed"
            job.finished_at = datetime.now()
            _save_build_log(db, job, f"FAILED: {error_msg}")
        _update_page_deploy_status(db, page_id, "failed")
        db.commit()
    except Exception as e:
        logger.error("[构建任务] 更新失败状态异常: %s", e)
        db.rollback()


def _fail_release_job(db, release_job_id: str, build_job: BuildJob, error_msg: str):
    """将 ReleaseJob (upload) 标记为失败并更新页面部署状态。"""
    try:
        rj = db.get(ReleaseJob, release_job_id)
        if rj:
            rj.status = "failed"
            rj.result = json.dumps({"error": error_msg})
        if build_job and build_job.lowcode_page_id:
            _update_page_deploy_status(db, build_job.lowcode_page_id, "failed")
        db.commit()
    except Exception as e:
        logger.error("[上传任务] 更新失败状态异常: %s", e)
        db.rollback()


def _fail_audit_job(db, audit_job_id: str, error_msg: str):
    """将 ReleaseJob (submit_audit) 标记为失败。"""
    try:
        aj = db.get(ReleaseJob, audit_job_id)
        if aj:
            aj.status = "failed"
            aj.result = json.dumps({"error": error_msg})
        db.commit()
    except Exception as e:
        logger.error("[审核任务] 更新失败状态异常: %s", e)
        db.rollback()


def _fail_publish_job(db, publish_job_id: str, error_msg: str):
    """将 ReleaseJob (publish) 标记为失败。"""
    try:
        pj = db.get(ReleaseJob, publish_job_id)
        if pj:
            pj.status = "failed"
            pj.result = json.dumps({"error": error_msg})
        db.commit()
    except Exception as e:
        logger.error("[发布任务] 更新失败状态异常: %s", e)
        db.rollback()


def _fail_rollback_job(db, rollback_job_id: str, error_msg: str):
    """将 ReleaseJob (rollback) 标记为失败。"""
    try:
        rj = db.get(ReleaseJob, rollback_job_id)
        if rj:
            rj.status = "failed"
            rj.result = json.dumps({"error": error_msg})
        db.commit()
    except Exception as e:
        logger.error("[回滚任务] 更新失败状态异常: %s", e)
        db.rollback()
