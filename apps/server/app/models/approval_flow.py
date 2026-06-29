"""
通用审批流引擎数据模型

包含:
- ApprovalFlowDefinition: 审批流定义
- ApprovalFlowNode: 流程节点
- ApprovalFlowCondition: 条件规则
- ApprovalInstance: 审批实例
- ApprovalRecord: 审批记录
"""
import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class ApprovalFlowDefinition(Base, AuditMixin):
    """审批流定义表 - 一个业务类型对应一个流程模板"""
    __tablename__ = "approval_flow_definitions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    name = Column(String(200), nullable=False, comment="流程名称")
    business_type = Column(String(100), nullable=False, comment="业务类型标识")
    description = Column(Text, comment="流程描述")
    version = Column(Integer, nullable=False, default=1, comment="版本号")
    status = Column(String(20), nullable=False, default="draft", comment="状态: draft/active/archived")
    form_schema = Column(JSON, comment="表单字段定义 (JSON Schema)")
    callback_config = Column(JSON, comment="回调配置")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, comment="门店级流程")
    snapshot_json = Column(JSON, comment="发布时的流程快照（节点+条件的完整 JSON）")
    edges = Column(JSON, comment="流程连线 [{source, target, sourceHandle, targetHandle}]")
    global_listeners = Column(JSON, nullable=True, comment="全局监听器列表")

    # 关系
    nodes = relationship("ApprovalFlowNode", back_populates="flow_def", cascade="all, delete-orphan", lazy="selectin")
    conditions = relationship("ApprovalFlowCondition", back_populates="flow_def", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        Index("idx_flow_def_tenant_biz", "tenant_id", "business_type"),
    )


class ApprovalFlowNode(Base):
    """审批流节点表"""
    __tablename__ = "approval_flow_nodes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flow_def_id = Column(String(36), ForeignKey("approval_flow_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    node_key = Column(String(100), nullable=False, comment="节点标识")
    node_name = Column(String(200), nullable=False, comment="节点名称")
    node_type = Column(String(30), nullable=False, comment="start/approval/cc/condition/end")
    approval_mode = Column(String(20), comment="会签(and)/或签(or)/依次审批(sequential)")
    assignee_type = Column(String(30), comment="审批人方式: role/user/department/dynamic")
    assignee_config = Column(JSON, comment="审批人配置")
    timeout_hours = Column(Integer, comment="超时时间(小时)")
    timeout_action = Column(String(20), comment="超时动作: remind/auto_approve/auto_reject/transfer")
    sort_order = Column(Integer, nullable=False, default=0, comment="节点排序")
    position_x = Column(Float, comment="设计器X坐标")
    position_y = Column(Float, comment="设计器Y坐标")
    listeners = Column(JSON, nullable=True, comment="执行监听器列表")
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.utcnow())
    updated_at = Column(DateTime, default=lambda: __import__('datetime').datetime.utcnow(),
                        onupdate=lambda: __import__('datetime').datetime.utcnow())

    # 关系
    flow_def = relationship("ApprovalFlowDefinition", back_populates="nodes")
    conditions = relationship("ApprovalFlowCondition", back_populates="node", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        {"comment": "审批流节点表"},
    )


class ApprovalFlowCondition(Base):
    """审批流条件规则表 - 挂在条件节点上，决定分支路由"""
    __tablename__ = "approval_flow_conditions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    node_id = Column(String(36), ForeignKey("approval_flow_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    flow_def_id = Column(String(36), ForeignKey("approval_flow_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_key = Column(String(100), nullable=False, comment="满足条件时跳转到的节点 key")
    field_name = Column(String(200), nullable=False, comment="条件字段名")
    operator = Column(String(20), nullable=False, comment="操作符: eq/neq/gt/gte/lt/lte/in/contains")
    value = Column(Text, nullable=False, comment="条件值 (JSON 字符串)")
    priority = Column(Integer, nullable=False, default=0, comment="优先级，越小越先匹配")
    group_id = Column(String(50), nullable=True, comment="条件组 ID: 同组 AND，不同组 OR。None 表示独立条件")
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.utcnow())

    # 关系
    node = relationship("ApprovalFlowNode", back_populates="conditions")
    flow_def = relationship("ApprovalFlowDefinition", back_populates="conditions")

    __table_args__ = (
        {"comment": "审批流条件规则表"},
    )


class ApprovalInstance(Base, AuditMixin):
    """审批实例表 - 每次发起审批生成一条"""
    __tablename__ = "approval_instances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    flow_def_id = Column(String(36), ForeignKey("approval_flow_definitions.id"), nullable=False, index=True)
    business_type = Column(String(100), nullable=False, comment="业务类型")
    business_id = Column(String(36), nullable=False, comment="关联的业务记录 ID")
    title = Column(String(500), nullable=False, comment="审批标题")
    form_data = Column(JSON, nullable=False, comment="表单数据快照")
    status = Column(String(30), nullable=False, default="pending",
                    comment="pending/approved/rejected/cancelled/withdrawn")
    current_node_key = Column(String(100), comment="当前所在节点 key")
    applicant_id = Column(String(36), nullable=False, comment="申请人 ID")
    applicant_name = Column(String(100), comment="申请人姓名")
    approved_at = Column(DateTime, comment="通过时间")
    rejected_at = Column(DateTime, comment="拒绝时间")
    cancelled_at = Column(DateTime, comment="取消/撤回时间")
    completed_reason = Column(String(50), comment="完成原因: normal/timeout/auto_approved")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True)

    # 关系
    flow_def = relationship("ApprovalFlowDefinition")
    records = relationship("ApprovalRecord", back_populates="instance", cascade="all, delete-orphan",
                           order_by="ApprovalRecord.created_at", lazy="selectin")
    tasks = relationship("ApprovalTask", back_populates="instance", cascade="all, delete-orphan",
                         order_by="ApprovalTask.created_at", lazy="selectin")

    __table_args__ = (
        Index("idx_appr_inst_biz", "business_type", "business_id"),
        Index("idx_appr_inst_applicant", "applicant_id"),
        Index("idx_appr_inst_status", "status"),
        Index("idx_appr_inst_store_status", "store_id", "status"),
        {"comment": "审批实例表"},
    )


class ApprovalRecord(Base):
    """审批记录表 - 每个节点每个审批人的操作"""
    __tablename__ = "approval_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    instance_id = Column(String(36), ForeignKey("approval_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    node_key = Column(String(100), nullable=False, comment="节点 key")
    node_name = Column(String(200), comment="节点名称")
    approver_id = Column(String(36), nullable=False, comment="审批人 ID")
    approver_name = Column(String(100), comment="审批人姓名")
    action = Column(String(30), nullable=False, comment="approve/reject/delegate/comment/withdraw")
    comment = Column(Text, comment="审批意见")
    delegate_to = Column(String(36), comment="转交目标人 ID")
    attachments = Column(JSON, comment="附件列表")
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.utcnow())

    # 关系
    instance = relationship("ApprovalInstance", back_populates="records")

    __table_args__ = (
        Index("idx_appr_rec_approver", "approver_id"),
        Index("idx_appr_rec_instance_node", "instance_id", "node_key"),
        {"comment": "审批记录表"},
    )


class ApprovalTask(Base):
    """审批任务表 - 每个审批节点每个审批人一条待办"""
    __tablename__ = "approval_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True)
    instance_id = Column(String(36), ForeignKey("approval_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    node_key = Column(String(100), nullable=False, comment="节点 key")
    node_name = Column(String(200), comment="节点名称")
    task_type = Column(String(30), nullable=False, default="approval", comment="approval/cc")
    status = Column(String(20), nullable=False, default="pending",
                    comment="pending/completed/cancelled/transferred/expired")
    assignee_id = Column(String(36), nullable=False, comment="审批人 ID")
    assignee_name = Column(String(100), comment="审批人姓名")
    candidate_user_ids = Column(JSON, comment="候选人 ID 列表（或签/会签时）")
    assignee_snapshot = Column(JSON, comment="审批人解析快照")
    completed_at = Column(DateTime, comment="完成时间")
    completed_by = Column(String(36), comment="完成操作人（审批人或 system）")
    timeout_at = Column(DateTime, comment="超时时间")
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.utcnow())

    # 关系
    instance = relationship("ApprovalInstance", back_populates="tasks")

    __table_args__ = (
        Index("idx_appr_task_tenant_status", "tenant_id", "status"),
        Index("idx_appr_task_assignee_status", "assignee_id", "status"),
        Index("idx_appr_task_instance_node", "instance_id", "node_key"),
        {"comment": "审批任务表"},
    )
