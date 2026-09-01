"""统一消息服务

替代 MessageService + NotificationDispatcher，操作新表。

采用 Mixin 模式拆分：
- UnifiedMessageSendMixin  (service_send.py)  发送相关
- UnifiedMessageRulesMixin (service_rules.py) 规则/模板 CRUD
- UnifiedMessageInboxMixin (service_inbox.py) 消息读取/状态

对外仍只导出 ``UnifiedMessageService``，方法体逐字搬迁，行为保持不变。
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.notifications.registry import register_channels
from app.modules.unified_message.service_inbox import UnifiedMessageInboxMixin
from app.modules.unified_message.service_rules import UnifiedMessageRulesMixin
from app.modules.unified_message.service_send import UnifiedMessageSendMixin


class UnifiedMessageService(
    UnifiedMessageSendMixin,
    UnifiedMessageRulesMixin,
    UnifiedMessageInboxMixin,
):
    """统一消息服务

    多继承组合三个 Mixin，对外接口与拆分前完全一致。
    Mixin 间无私有状态冲突，共享 ``self.db``。
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        register_channels()
