"""知识库（RAG）：knowledge_bases / folders / documents / chunks(pgvector) / shares

Revision ID: kb01_knowledge_base
Revises: 20261025_merge_three_heads
Create Date: 2026-10-26

openspec: add-knowledge-base-rag
- CREATE EXTENSION IF NOT EXISTS vector：生产 PG 18.0 已于 2026-10-26 安装 pgvector 0.8.7，此处幂等；
  CI / 本地测试库需用 pgvector/pgvector 镜像或已装扩展的 PG
- knowledge_chunks.embedding vector(1024) + HNSW 余弦索引；建索引前会话级提高 maintenance_work_mem
  （生产默认仅 64MB，HNSW 图放不进会非常慢）
- downgrade 只删表，不卸载扩展
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "kb01_knowledge_base"
down_revision = "20261025_merge_three_heads"
branch_labels = None
depends_on = None

EMBEDDING_DIMS = 1024


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间"),
        sa.Column("created_by", sa.String(36), nullable=True, comment="创建人ID"),
        sa.Column("updated_by", sa.String(36), nullable=True, comment="更新人ID"),
    ]


def _ensure_vector_extension() -> None:
    """pgvector 不是 trusted 扩展，CREATE EXTENSION 需要超级用户；应用账号（hospital）通常没有。

    已存在 → 直接跳过（生产 PG 18 已于 2026-10-26 以 postgres 账号安装 0.8.7）；
    不存在 → 尝试创建，无权时给出可操作的指引而不是裸的 InsufficientPrivilegeError。
    """
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).scalar():
        return
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except Exception as exc:
        raise RuntimeError(
            "pgvector 扩展未安装，且当前数据库用户无权创建。请先用超级用户在本库执行：\n"
            "    CREATE EXTENSION IF NOT EXISTS vector;\n"
            "（本地 Homebrew PG 需先 make install pgvector；CI 请使用 pgvector/pgvector 镜像）"
        ) from exc


def upgrade() -> None:
    _ensure_vector_extension()

    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=True, comment="租户ID"),
        sa.Column("name", sa.String(100), nullable=False, comment="名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="描述"),
        sa.Column(
            "owner_admin_id", sa.String(36), sa.ForeignKey("admins.id"), nullable=False, comment="拥有者管理员ID"
        ),
        sa.Column(
            "visibility", sa.String(20), nullable=False, server_default="private", comment="可见性: private/tenant"
        ),
        sa.Column("embedding_model", sa.String(100), nullable=False, comment="创建时使用的 embedding 模型"),
        sa.Column(
            "embedding_dims", sa.Integer(), nullable=False, server_default=str(EMBEDDING_DIMS), comment="向量维度"
        ),
        sa.Column("doc_count", sa.Integer(), nullable=False, server_default="0", comment="文档数"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0", comment="切片数"),
        *_audit_columns(),
    )
    op.create_index("ix_knowledge_bases_tenant_id", "knowledge_bases", ["tenant_id"])
    op.create_index("ix_knowledge_bases_owner_admin_id", "knowledge_bases", ["owner_admin_id"])

    op.create_table(
        "knowledge_folders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=True, comment="租户ID"),
        sa.Column(
            "kb_id",
            sa.String(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
            comment="知识库ID",
        ),
        sa.Column(
            "parent_id",
            sa.String(36),
            sa.ForeignKey("knowledge_folders.id", ondelete="CASCADE"),
            nullable=True,
            comment="父目录ID",
        ),
        sa.Column("name", sa.String(100), nullable=False, comment="目录名"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0", comment="排序"),
        *_audit_columns(),
        sa.UniqueConstraint("kb_id", "parent_id", "name", name="uq_knowledge_folders_kb_parent_name"),
    )
    op.create_index("ix_knowledge_folders_tenant_id", "knowledge_folders", ["tenant_id"])
    op.create_index("ix_knowledge_folders_kb_id", "knowledge_folders", ["kb_id"])
    op.create_index("ix_knowledge_folders_parent_id", "knowledge_folders", ["parent_id"])

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=True, comment="租户ID"),
        sa.Column(
            "kb_id",
            sa.String(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
            comment="知识库ID",
        ),
        sa.Column(
            "folder_id",
            sa.String(36),
            sa.ForeignKey("knowledge_folders.id", ondelete="SET NULL"),
            nullable=True,
            comment="目录ID",
        ),
        sa.Column("title", sa.String(200), nullable=False, comment="标题"),
        sa.Column("file_name", sa.String(255), nullable=False, comment="原始文件名"),
        sa.Column("file_key", sa.String(500), nullable=False, comment="存储 key（不对外暴露）"),
        sa.Column("mime_type", sa.String(100), nullable=False, comment="MIME 类型"),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0", comment="文件大小（字节）"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", comment="处理状态"),
        sa.Column("failed_stage", sa.String(20), nullable=True, comment="失败阶段: parsing/embedding"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="用户可读的失败原因"),
        sa.Column("page_count", sa.Integer(), nullable=True, comment="页数（PDF）"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0", comment="切片数"),
        sa.Column("uploaded_by", sa.String(36), nullable=True, comment="上传人管理员ID"),
        sa.Column("processed_at", sa.DateTime(), nullable=True, comment="最近一次处理完成时间"),
        *_audit_columns(),
    )
    op.create_index("ix_knowledge_documents_tenant_id", "knowledge_documents", ["tenant_id"])
    op.create_index("ix_knowledge_documents_kb_id", "knowledge_documents", ["kb_id"])
    op.create_index("ix_knowledge_documents_folder_id", "knowledge_documents", ["folder_id"])
    op.create_index("ix_knowledge_documents_status", "knowledge_documents", ["status"])

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=True, comment="租户ID"),
        sa.Column(
            "kb_id",
            sa.String(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
            comment="知识库ID（冗余，供检索过滤）",
        ),
        sa.Column(
            "doc_id",
            sa.String(36),
            sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
            nullable=False,
            comment="文档ID",
        ),
        sa.Column("seq", sa.Integer(), nullable=False, comment="切片序号"),
        sa.Column("content", sa.Text(), nullable=False, comment="切片原文"),
        sa.Column("page_no", sa.Integer(), nullable=True, comment="页码（PDF）"),
        sa.Column("section", sa.String(200), nullable=True, comment="章节/标题"),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0", comment="估算 token 数"),
        sa.Column("embedding", Vector(EMBEDDING_DIMS), nullable=False, comment="向量"),
        sa.Column("created_at", sa.DateTime(), nullable=True, comment="创建时间"),
    )
    op.create_index("ix_knowledge_chunks_tenant_id", "knowledge_chunks", ["tenant_id"])
    op.create_index("ix_knowledge_chunks_kb_id", "knowledge_chunks", ["kb_id"])
    op.create_index("ix_knowledge_chunks_doc_seq", "knowledge_chunks", ["doc_id", "seq"])
    # HNSW 图构建受 maintenance_work_mem 限制；SET LOCAL 只影响本事务
    op.execute("SET LOCAL maintenance_work_mem = '256MB'")
    op.create_index(
        "ix_knowledge_chunks_embedding_hnsw",
        "knowledge_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "knowledge_shares",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=True, comment="租户ID"),
        sa.Column(
            "kb_id",
            sa.String(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
            comment="知识库ID",
        ),
        sa.Column("grantee_type", sa.String(10), nullable=False, comment="授权对象类型: admin/role"),
        sa.Column("grantee_id", sa.String(36), nullable=False, comment="管理员ID 或 角色ID"),
        sa.Column("permission", sa.String(10), nullable=False, comment="权限: read/edit"),
        sa.Column("granted_by", sa.String(36), nullable=True, comment="授权人管理员ID"),
        *_audit_columns(),
        sa.UniqueConstraint("kb_id", "grantee_type", "grantee_id", name="uq_knowledge_shares_kb_grantee"),
    )
    op.create_index("ix_knowledge_shares_tenant_id", "knowledge_shares", ["tenant_id"])
    op.create_index("ix_knowledge_shares_kb_id", "knowledge_shares", ["kb_id"])
    op.create_index("ix_knowledge_shares_grantee_id", "knowledge_shares", ["grantee_id"])


def downgrade() -> None:
    op.drop_table("knowledge_shares")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
    op.drop_table("knowledge_folders")
    op.drop_table("knowledge_bases")
