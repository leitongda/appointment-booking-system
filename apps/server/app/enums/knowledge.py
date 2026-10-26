"""知识库相关枚举"""
from enum import Enum


class KnowledgeDocStatus(str, Enum):
    """文档处理状态（界面上的"学习状态"）

    流转：pending → parsing → embedding → ready；任一阶段失败 → failed
    """
    PENDING = "pending"        # 待处理（已入库、已投递队列）
    PARSING = "parsing"        # 解析中（抽文本 + 切片）
    EMBEDDING = "embedding"    # 向量化中
    READY = "ready"            # 已就绪，可被检索
    FAILED = "failed"          # 失败，可重试


class KnowledgeFailedStage(str, Enum):
    """失败发生的阶段"""
    PARSING = "parsing"
    EMBEDDING = "embedding"


class KnowledgeVisibility(str, Enum):
    """知识库可见性"""
    PRIVATE = "private"  # 仅 owner 与持 knowledge:manage 者可见
    TENANT = "tenant"    # 租户内所有管理员可见（只读）


class KnowledgeShareGrantee(str, Enum):
    """共享对象类型"""
    ADMIN = "admin"  # 按同事（管理员）
    ROLE = "role"    # 按角色


class KnowledgeSharePermission(str, Enum):
    """共享权限级别

    edit 仅含上传/整理目录/重试/删文档，不含再分享与删库；read 仅含检索与预览。
    """
    READ = "read"
    EDIT = "edit"
