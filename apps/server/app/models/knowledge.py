"""知识库模型：知识库 / 目录 / 文档 / 切片（向量） / 共享授权

向量列固定 1024 维（与 kb01 迁移一致）；embedding 模型切换 = 整库重建，禁止同库混维。
"""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.db.base import AuditMixin, Base
from app.enums.knowledge import KnowledgeDocStatus, KnowledgeVisibility

KB_EMBEDDING_DIMS = 1024


class KnowledgeBase(Base, AuditMixin):
    """知识库"""
    __tablename__ = "knowledge_bases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    name = Column(String(100), nullable=False, comment="名称")
    description = Column(Text, nullable=True, comment="描述")
    owner_admin_id = Column(String(36), ForeignKey("admins.id"), nullable=False, index=True, comment="拥有者管理员ID")
    visibility = Column(
        String(20), nullable=False, default=KnowledgeVisibility.PRIVATE.value, comment="可见性: private/tenant"
    )
    embedding_model = Column(String(100), nullable=False, comment="创建时使用的 embedding 模型")
    embedding_dims = Column(Integer, nullable=False, default=KB_EMBEDDING_DIMS, comment="向量维度")
    doc_count = Column(Integer, nullable=False, default=0, comment="文档数")
    chunk_count = Column(Integer, nullable=False, default=0, comment="切片数")


class KnowledgeFolder(Base, AuditMixin):
    """知识库目录（任意层级）"""
    __tablename__ = "knowledge_folders"
    __table_args__ = (
        UniqueConstraint("kb_id", "parent_id", "name", name="uq_knowledge_folders_kb_parent_name"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    kb_id = Column(
        String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True, comment="知识库ID"
    )
    parent_id = Column(
        String(36),
        ForeignKey("knowledge_folders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="父目录ID",
    )
    name = Column(String(100), nullable=False, comment="目录名")
    sort_order = Column(Integer, nullable=False, default=0, comment="排序")


class KnowledgeDocument(Base, AuditMixin):
    """知识库文档（原件元数据 + 处理状态）"""
    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    kb_id = Column(
        String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True, comment="知识库ID"
    )
    folder_id = Column(
        String(36), ForeignKey("knowledge_folders.id", ondelete="SET NULL"), nullable=True, index=True, comment="目录ID"
    )
    title = Column(String(200), nullable=False, comment="标题")
    file_name = Column(String(255), nullable=False, comment="原始文件名")
    file_key = Column(String(500), nullable=False, comment="存储 key（不对外暴露）")
    mime_type = Column(String(100), nullable=False, comment="MIME 类型")
    size_bytes = Column(BigInteger, nullable=False, default=0, comment="文件大小（字节）")
    status = Column(
        String(20), nullable=False, default=KnowledgeDocStatus.PENDING.value, index=True, comment="处理状态"
    )
    failed_stage = Column(String(20), nullable=True, comment="失败阶段: parsing/embedding")
    error_message = Column(Text, nullable=True, comment="用户可读的失败原因")
    page_count = Column(Integer, nullable=True, comment="页数（PDF）")
    chunk_count = Column(Integer, nullable=False, default=0, comment="切片数")
    uploaded_by = Column(String(36), nullable=True, comment="上传人管理员ID")
    processed_at = Column(DateTime, nullable=True, comment="最近一次处理完成时间")


class KnowledgeChunk(Base):
    """文档切片（含向量）；page_no/section/seq 是引用来源定位的依据"""
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index("ix_knowledge_chunks_doc_seq", "doc_id", "seq"),
        Index(
            "ix_knowledge_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    kb_id = Column(
        String(36),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="知识库ID（冗余，供检索过滤）",
    )
    doc_id = Column(
        String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, comment="文档ID"
    )
    seq = Column(Integer, nullable=False, comment="切片序号")
    content = Column(Text, nullable=False, comment="切片原文")
    page_no = Column(Integer, nullable=True, comment="页码（PDF）")
    section = Column(String(200), nullable=True, comment="章节/标题")
    token_count = Column(Integer, nullable=False, default=0, comment="估算 token 数")
    embedding = Column(Vector(KB_EMBEDDING_DIMS), nullable=False, comment="向量")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")


class KnowledgeShare(Base, AuditMixin):
    """知识库共享授权（按同事或按角色）"""
    __tablename__ = "knowledge_shares"
    __table_args__ = (
        UniqueConstraint("kb_id", "grantee_type", "grantee_id", name="uq_knowledge_shares_kb_grantee"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    kb_id = Column(
        String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True, comment="知识库ID"
    )
    grantee_type = Column(String(10), nullable=False, comment="授权对象类型: admin/role")
    grantee_id = Column(String(36), nullable=False, index=True, comment="管理员ID 或 角色ID")
    permission = Column(String(10), nullable=False, comment="权限: read/edit")
    granted_by = Column(String(36), nullable=True, comment="授权人管理员ID")
