"""兼职费用相关枚举"""
from enum import Enum


class FreelanceTaskStatus(str, Enum):
    """兼职任务状态"""
    PENDING = "pending"           # 待发布
    PUBLISHED = "published"       # 已发布
    INDEXED = "indexed"           # 已收录
    NEED_MODIFY = "need_modify"   # 需修改
    REJECTED = "rejected"         # 已拒绝


class FreelanceSettlementStatus(str, Enum):
    """结算状态"""
    PENDING = "pending"       # 待确认
    CONFIRMED = "confirmed"   # 已确认
    PAID = "paid"             # 已支付
    CANCELLED = "cancelled"   # 已驳回


class FreelanceInteractionType(str, Enum):
    """互动类型"""
    COMMENT = "comment"   # 评论
    DM = "dm"             # 私信


class FreelanceAccountPlatform(str, Enum):
    """社交媒体平台"""
    XIAOHONGSHU = "xiaohongshu"   # 小红书
    DOUYIN = "douyin"             # 抖音
    WEIBO = "weibo"               # 微博
    WECHAT = "wechat"             # 微信
    OTHER = "other"               # 其他


class FreelanceAccountType(str, Enum):
    """账号类型"""
    OLD = "old"   # 老账号
    NEW = "new"   # 新账号
