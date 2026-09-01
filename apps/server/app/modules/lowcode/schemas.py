"""低代码模块 schemas (re-export + 模块专属)。"""

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.lowcode import (
    LowCodePageCreate,
    LowCodePageResponse,
    LowCodePageUpdate,
)


class DataSourceTestRequest(BaseSchema):
    """数据源测试请求。"""

    url: str = Field(..., description="请求 URL")
    method: str = Field("GET", description="请求方法: GET/POST/PUT/DELETE")
    headers: dict[str, str] | None = Field(None, description="请求头")
    params: dict[str, Any] | None = Field(None, description="请求参数/查询参数")
    body: dict[str, Any] | None = Field(None, description="请求体 (POST/PUT 时使用)")
    response_path: str | None = Field(
        None,
        description="响应数据提取路径，如 data.list，为空则取整个响应",
    )


class DataSourceFieldSuggestion(BaseSchema):
    """字段建议项。"""

    path: str = Field(..., description="字段路径，如 data.list[0].name")
    type: str = Field(..., description="字段类型: string/number/boolean/array/object")
    sample: Any | None = Field(None, description="示例值")


class DataSourceTestResponse(BaseSchema):
    """数据源测试响应。"""

    success: bool = Field(..., description="请求是否成功")
    status_code: int | None = Field(None, description="HTTP 状态码")
    sample_data: Any | None = Field(None, description="响应样本数据 (截取前 5 条)")
    fields: list[DataSourceFieldSuggestion] = Field(
        default_factory=list, description="字段建议列表"
    )
    error: str | None = Field(None, description="错误信息")
    elapsed_ms: int = Field(..., description="请求耗时 (毫秒)")


class DataPreviewField(BaseSchema):
    """数据预览字段。"""

    name: str = Field(..., description="字段名")
    type: str = Field(..., description="字段类型")
    sample: Any | None = Field(None, description="示例值")


class DataPreviewItem(BaseSchema):
    """单个数据源的预览结果。"""

    source_id: str = Field(..., description="数据源 ID")
    url: str = Field(..., description="数据源 URL")
    method: str = Field(..., description="请求方法")
    mock_data: Any = Field(..., description="模拟数据结构")
    fields: list[DataPreviewField] = Field(
        default_factory=list, description="字段列表"
    )


class DataPreviewResponse(BaseSchema):
    """页面数据预览响应。"""

    page_id: str = Field(..., description="页面 ID")
    page_name: str = Field(..., description="页面名称")
    data_sources: list[DataPreviewItem] = Field(
        default_factory=list, description="各数据源预览"
    )


# ---------------------------------------------------------------------------
# Version history schemas
# ---------------------------------------------------------------------------


class VersionItem(BaseSchema):
    """版本历史列表项。"""

    id: str = Field(..., description="版本记录 ID")
    version: int = Field(..., description="版本号")
    snapshot_label: str | None = Field(None, description="版本标签")
    created_at: datetime | None = Field(None, description="创建时间")
    created_by: str | None = Field(None, description="创建人 ID")


class VersionListResponse(BaseSchema):
    """版本历史列表响应。"""

    current_version: int = Field(0, description="页面当前版本号")
    versions: list[VersionItem] = Field(default_factory=list, description="版本列表 (降序)")


class RollbackRequest(BaseSchema):
    """回滚到指定版本请求。"""

    version_id: str = Field(..., description="目标版本记录 ID")


class PublishToMarketplaceRequest(BaseSchema):
    """从页面发布模板到市场的兼容请求。"""

    name: str = Field(..., min_length=1, max_length=200, description="模板名称")
    category: str = Field(..., min_length=1, max_length=50, description="模板分类")
    short_description: str | None = Field(None, max_length=100, description="简短描述")
    description: str | None = Field(None, max_length=1000, description="模板描述")
    thumbnail_url: str | None = Field(None, description="缩略图 URL")
    thumbnail_key: str | None = Field(None, description="缩略图存储 Key（兼容前端上传响应）")
    tags: list[str] | None = Field(None, description="标签列表")
    is_public: bool = Field(True, description="是否公开到市场")


# ---------------------------------------------------------------------------
# Deploy schemas
# ---------------------------------------------------------------------------


class DeployRollbackRequest(BaseSchema):
    """部署回滚请求。"""

    target_version: str | None = Field(
        None,
        description="目标版本号，为空时自动选择上一个已发布版本",
    )


class DeployResultResponse(BaseSchema):
    """部署触发结果。"""

    build_job_id: str = Field(..., description="构建任务 ID")
    audit_id: str | None = Field(None, description="微信审核 ID")
    deploy_status: str = Field(..., description="部署状态")
    artifact_url: str | None = Field(None, description="构建产物 URL")


class DeployStatusResponse(BaseSchema):
    """部署状态查询响应。"""

    page_id: str = Field(..., description="页面 ID")
    deploy_status: str = Field(..., description="部署状态")
    last_deploy_at: str | None = Field(None, description="最近部署时间")
    miniapp_instance_id: str | None = Field(None, description="关联小程序实例 ID")
    build_job: dict[str, Any] | None = Field(
        None, description="最近构建任务信息"
    )


class DeployRollbackResponse(BaseSchema):
    """部署回滚结果。"""

    page_id: str = Field(..., description="页面 ID")
    rollback_to_version: str | None = Field(None, description="回滚到的版本")
    deploy_status: str = Field(..., description="部署状态")
    release_job_id: str = Field(..., description="发布任务 ID")


class PreviewDeployResponse(BaseSchema):
    """预览部署结果。"""

    page_id: str = Field(..., description="页面 ID")
    qr_code_url: str = Field(..., description="预览二维码 URL")
    expires_at: str | None = Field(None, description="二维码过期时间")
    message: str | None = Field(None, description="附加消息")


class WeChatAuditCallbackRequest(BaseSchema):
    """微信审核状态回调请求。"""

    auditid: str = Field(..., description="审核 ID")
    status: int = Field(..., description="审核状态: 0=通过, 其他=失败")
    reason: str | None = Field(None, description="审核失败原因")


class WeChatAuditCallbackResponse(BaseSchema):
    """微信审核回调处理结果。"""

    page_id: str = Field(..., description="页面 ID")
    deploy_status: str = Field(..., description="部署状态")
    audit_status: str = Field(..., description="审核状态: passed / failed")
    reason: str | None = Field(None, description="审核失败原因")


# ---------------------------------------------------------------------------
# Codegen schemas
# ---------------------------------------------------------------------------


class GeneratedFileSchema(BaseSchema):
    """生成的文件。"""

    path: str = Field(..., description="文件路径，如 pages/home/index.tsx")
    content: str = Field(..., description="文件内容")
    type: str = Field(..., description="文件类型: tsx/css/json/wxml/wxss/js")


class CodegenResultSchema(BaseSchema):
    """代码生成结果。"""

    files: list[GeneratedFileSchema] = Field(
        default_factory=list, description="生成的文件列表"
    )
    warnings: list[dict[str, Any]] = Field(
        default_factory=list, description="分析警告列表"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="外部依赖列表 (npm 包名)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="生成元数据 (目标平台、时间戳等)"
    )


class CodegenPreviewRequest(BaseSchema):
    """代码生成预览请求。"""

    schema_data: dict[str, Any] = Field(
        ..., description="页面 schema JSON"
    )
    data_sources: list[dict[str, Any]] = Field(
        default_factory=list, description="数据源列表"
    )
    target: str = Field(
        "taro",
        description="目标平台: taro / native",
    )


# ---------------------------------------------------------------------------
# Audit log schemas
# ---------------------------------------------------------------------------


class AuditLogItem(BaseSchema):
    """审计日志列表项。"""

    id: str = Field(..., description="日志 ID")
    page_id: str = Field(..., description="页面 ID")
    operator_id: str = Field(..., description="操作人 ID")
    action: str = Field(..., description="操作类型")
    detail: dict[str, Any] | None = Field(None, description="操作详情")
    created_at: datetime | None = Field(None, description="操作时间")


class AuditLogListResponse(BaseSchema):
    """审计日志列表响应。"""

    current_version: int = Field(0, description="当前版本号（兼容）")
    items: list[AuditLogItem] = Field(default_factory=list, description="审计日志列表")
    total: int = Field(0, description="总条数")


__all__ = [
    "AuditLogItem",
    "AuditLogListResponse",
    "CodegenPreviewRequest",
    "CodegenResultSchema",
    "DataSourceFieldSuggestion",
    "DataSourceTestRequest",
    "DataSourceTestResponse",
    "DataPreviewField",
    "DataPreviewItem",
    "DataPreviewResponse",
    "DeployResultResponse",
    "DeployRollbackRequest",
    "DeployRollbackResponse",
    "DeployStatusResponse",
    "GeneratedFileSchema",
    "LowCodePageCreate",
    "LowCodePageResponse",
    "LowCodePageUpdate",
    "PublishToMarketplaceRequest",
    "PreviewDeployResponse",
    "RollbackRequest",
    "VersionItem",
    "VersionListResponse",
    "WeChatAuditCallbackRequest",
    "WeChatAuditCallbackResponse",
]
