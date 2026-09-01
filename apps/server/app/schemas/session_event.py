"""会话回放与热力图 Schema

用于 rrweb 会话回放事件批量上报、会话列表、回放数据拼装、热力图查询。
- 请求体统一 camelCase（前端 rrweb recorder 上报字段）
- 响应类统一 alias_generator=to_camel + from_attributes（list 响应可直接从 ORM 聚合行构造）
- events 字段为 list[dict]，rrweb 事件结构动态，不做严格校验
"""
import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.base import BaseRequestSchema, BaseSchema
from app.schemas.response import to_camel

# 单批次上报 payload 序列化后的字节上限（2MB）。
# 防止恶意客户端用 500 条超大事件打爆对象存储配额；
# 正常 rrweb 100 条/批的事件量远小于此。
_MAX_PAYLOAD_BYTES = 2 * 1024 * 1024

# ========== 请求 Schema ==========

class SessionEventBatchRequest(BaseRequestSchema):
    """会话回放事件批量上报请求

    前端 rrweb recorder 每次批量上报一个会话段（segment），events 内为
    rrweb 原始事件对象数组，结构动态（snapshot/incremental/meta 等），
    因此不做严格 Pydantic 校验，仅约束列表长度 + 整体字节数。
    """

    session_id: str = Field(..., max_length=64, description="会话ID，与 behavior_log 共用")
    viewport_w: int | None = Field(None, ge=0, description="录制视口宽(px)，热力图分桶用")
    viewport_h: int | None = Field(None, ge=0, description="录制视口高(px)")
    page_path: str | None = Field(None, max_length=255, description="本批次主要页面路径")
    sequence: int | None = Field(None, ge=0, description="会话内批次序号")
    started_at: datetime | None = Field(None, description="本批次起始时间")
    ended_at: datetime | None = Field(None, description="本批次结束时间")
    events: list[dict] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="rrweb 原始事件对象数组（结构动态，不做严格校验）",
    )

    @model_validator(mode="after")
    def _validate_payload_size(self) -> "SessionEventBatchRequest":
        """校验整体 payload 序列化后不超过 _MAX_PAYLOAD_BYTES，防滥用。"""
        # 仅校验 events（占 payload 绝大部分体积），避免序列化整个对象
        serialized = json.dumps(self.events, ensure_ascii=False)
        if len(serialized.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
            raise ValueError(
                f"events 序列化后超过 {_MAX_PAYLOAD_BYTES // 1024 // 1024}MB 上限"
            )
        return self


# ========== 响应 Schema ==========

class SessionBatchResponse(BaseModel):
    """批量上报响应
    NOTE: 原 ConfigDict 为 {alias_generator, populate_by_name, by_alias=True}（3 字段，无 from_attributes），
    与 BaseSchema（4 字段）不一致，保留手写配置避免行为变化。
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    success: bool = True
    count: int = Field(0, description="本次入库事件数")
    segment_id: str = Field(..., description="本批次段ID")


class SessionSegmentResponse(BaseSchema):
    """会话单批次段响应（回放拼装用）"""

    segment_id: str = Field(..., description="批次段ID（SessionEvent.id）")
    sequence: int = Field(0, description="会话内批次序号")
    event_count: int = Field(0, description="本批次事件数")
    events_url: str | None = Field(None, description="rrweb 事件 JSON 的预签名下载地址")


class SessionListResponse(BaseSchema):
    """会话列表项（按 session_id 聚合）"""

    id: str = Field(..., description="代表行ID（最新批次段）")
    session_id: str = Field(..., description="会话ID")
    actor_id: str | None = Field(None, description="操作者ID（员工 account_id）")
    actor_name: str | None = Field(None, description="操作者姓名")
    page_path: str | None = Field(None, description="主要页面路径")
    viewport_w: int | None = Field(None, description="录制视口宽(px)")
    viewport_h: int | None = Field(None, description="录制视口高(px)")
    event_count: int = Field(0, description="会话事件总数（各批次求和）")
    sequence: int = Field(0, description="最大批次序号")
    started_at: datetime | None = Field(None, description="会话最早起始时间")
    ended_at: datetime | None = Field(None, description="会话最晚结束时间")
    created_at: datetime | None = Field(None, description="最近上报时间")


class SessionReplayResponse(BaseSchema):
    """会话回放数据响应（前端按顺序拼接 segments 的 eventsUrl 后喂给 rrweb-player）"""

    session_id: str = Field(..., description="会话ID")
    viewport_w: int | None = Field(None, description="录制视口宽(px)")
    viewport_h: int | None = Field(None, description="录制视口高(px)")
    segments: list[SessionSegmentResponse] = Field(
        default_factory=list,
        description="按 sequence/created_at 排序的批次段列表",
    )
    missing_count: int = Field(
        0,
        description="因 storage_key 缺失（孤儿/清理中）而被跳过的段数",
    )


# ========== 热力图 Schema ==========

class HeatmapPointItem(BaseSchema):
    """热力图单点"""

    x_ratio: float = Field(..., ge=0.0, le=1.0, description="x/视口宽，相对坐标（量化到 0.01）")
    y_ratio: float = Field(..., ge=0.0, le=1.0, description="y/视口高，相对坐标（量化到 0.01）")
    weight: int = Field(0, ge=0, description="聚合计数")


class HeatmapQueryResponse(BaseModel):
    """热力图查询响应
    NOTE: 原 ConfigDict 为 {alias_generator, populate_by_name, by_alias=True}（3 字段，无 from_attributes），
    与 BaseSchema（4 字段）不一致，保留手写配置避免行为变化。
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    page_path: str = Field(..., description="页面路径")
    viewport_bucket: str | None = Field(None, description="视口分桶: lg/md/sm")
    event_type: str = Field(..., description="事件类型: click/move")
    points: list[HeatmapPointItem] = Field(
        default_factory=list,
        description="热力图坐标点列表",
    )
