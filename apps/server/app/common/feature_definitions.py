"""功能开关定义

TenantFeatures 定义所有租户功能开关的字段和默认值。
从 app.modules.tenants.schemas 移至此处，消除 common -> modules 的反向依赖。
功能开关定义属于通用层（common），不属于 tenants 业务模块。
"""
from pydantic import BaseModel, ConfigDict, Field


class TenantFeatures(BaseModel):
    """租户/订阅计划 功能开关配置

    所有功能开关均为布尔值，默认 False（关闭）。
    允许额外字段以保持向前兼容——新功能可由业务方自由添加，
    老数据中缺少的字段会自动补 False。
    """
    # 预约与排班
    basic_appointment: bool = Field(default=False, description="基础预约功能")
    basic_schedule: bool = Field(default=False, description="基础排班功能")

    # 统计
    basic_statistics: bool = Field(default=False, description="基础统计")
    advanced_statistics: bool = Field(default=False, description="高级数据分析")

    # 集成
    wechat_integration: bool = Field(default=False, description="微信集成")
    sms_notification: bool = Field(default=False, description="短信通知")

    # 数据
    export_data: bool = Field(default=False, description="数据导出")

    # 高级
    api_access: bool = Field(default=False, description="API 开放接口")
    custom_branding: bool = Field(default=False, description="自定义品牌")
    priority_support: bool = Field(default=False, description="优先技术支持")
    sso: bool = Field(default=False, description="单点登录(SSO)")
    online_payment: bool = Field(default=False, description="在线支付")

    # 灰度 / 实验性
    beta_features: bool = Field(default=False, description="灰度功能总开关")
    beta_ai_assistant: bool = Field(default=False, description="AI 辅助（实验性）")
    beta_analytics_v2: bool = Field(default=False, description="新版数据分析（实验性）")
    # beta_unified_message 已退役：统一消息系统已全量启用

    # 低代码平台
    lowcode_basic: bool = Field(default=True, description="低代码基础功能（默认开启，向后兼容）")
    lowcode_advanced_components: bool = Field(default=False, description="低代码高级组件")
    lowcode_custom_components: bool = Field(default=False, description="低代码自定义组件")
    lowcode_data_binding: bool = Field(default=False, description="低代码数据绑定")
    lowcode_codegen: bool = Field(default=False, description="低代码代码生成")
    lowcode_marketplace: bool = Field(default=False, description="低代码组件市场")
    lowcode_publish_miniapp: bool = Field(default=False, description="低代码发布小程序")
    # deprecated: 将合并到 lowcode_codegen，不再作为独立功能开关
    lowcode_export_code: bool = Field(default=False, description="低代码导出代码（deprecated，将合并到 lowcode_codegen）")
    lowcode_max_pages: int = Field(default=5, ge=0, description="低代码最大页面数（0表示不限制）")

    model_config = ConfigDict(extra="allow")
