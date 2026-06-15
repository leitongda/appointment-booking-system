"""
微信相关定时任务
- 主动刷新微信 access_token
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.core.config import settings as app_settings
from app.db.session import get_sync_db
from app.infrastructure.wechat.token_manager import WechatTokenManager
from app.models.settings import SystemSetting as Settings

logger = logging.getLogger(__name__)


def _get_wechat_config(db: Session) -> dict:
    """从数据库获取微信配置"""
    try:
        result = db.execute(
            select(Settings).where(Settings.category == 'wechat')
        )
        settings_list = result.scalars().all()
        config = {}
        for s in settings_list:
            config[s.key] = s.value
        return config
    except Exception as e:
        logger.error(f"获取微信配置失败: {e}")
        return {}


@celery_app.task(
    name="app.tasks.wechat_task.refresh_wechat_token_task",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=120,
    soft_time_limit=90,
)
def refresh_wechat_token_task():
    """
    主动刷新微信 access_token
    每2小时执行一次
    
    好处：
    - 避免请求时才发现 Token 过期导致的延迟
    - 保证 Token 始终可用
    """
    logger.info("[定时任务] 开始执行：微信 Token 刷新")
    
    with get_sync_db() as db:
        try:
            # 获取微信配置
            wechat_config = _get_wechat_config(db)
            app_id = wechat_config.get('app_id') or app_settings.WECHAT_APP_ID
            app_secret = wechat_config.get('app_secret') or app_settings.WECHAT_APP_SECRET
            
            if not app_id or not app_secret:
                logger.warning("微信配置不完整，跳过 Token 刷新")
                return {
                    "success": False,
                    "reason": "微信配置不完整"
                }
            
            # 强制刷新 Token
            token = WechatTokenManager.get_access_token_sync(
                app_id,
                app_secret,
                force_refresh=True
            )
            
            logger.info(f"[定时任务] 微信 Token 刷新成功: app_id={app_id}")
            return {
                "success": True,
                "app_id": app_id,
                "token_preview": token[:10] + "..." if token else None
            }
            
        except Exception as e:
            logger.error(f"微信 Token 刷新失败: {e}")
            return {
                "success": False,
                "reason": str(e)
            }


@celery_app.task(
    name="app.tasks.wechat_task.refresh_wechat_token",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=120,
    soft_time_limit=90,
)
def refresh_wechat_token(app_id: str = None, app_secret: str = None):
    """
    刷新微信 Token（手动触发）
    
    Args:
        app_id: 小程序 AppID（可选，不传则从配置获取）
        app_secret: 小程序 AppSecret（可选，不传则从配置获取）
    """
    logger.info("[任务] 手动刷新微信 Token")
    
    with get_sync_db() as db:
        try:
            # 如果未传参数，从配置获取
            if not app_id or not app_secret:
                wechat_config = _get_wechat_config(db)
                app_id = app_id or wechat_config.get('app_id') or app_settings.WECHAT_APP_ID
                app_secret = app_secret or wechat_config.get('app_secret') or app_settings.WECHAT_APP_SECRET
            
            if not app_id or not app_secret:
                return {"success": False, "reason": "配置不完整"}
            
            token = WechatTokenManager.get_access_token_sync(
                app_id,
                app_secret,
                force_refresh=True
            )
            
            return {
                "success": True,
                "app_id": app_id,
                "token_preview": token[:10] + "..." if token else None
            }
            
        except Exception as e:
            logger.error(f"手动刷新 Token 失败: {e}")
            return {"success": False, "reason": str(e)}

