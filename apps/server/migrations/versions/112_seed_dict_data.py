"""seed dictionary data - first batch (11 display-only types)

Revision ID: 112
Revises: 111
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa
import uuid
from datetime import datetime

revision = '112'
down_revision = '111'
branch_labels = None
depends_on = None

# 字典类型定义：(code, name, description, items)
# items: list of (label, value, sort_order)
DICT_TYPES = [
    (
        "doctor_title",
        "医生职称",
        "医生的职称等级",
        [
            ("主任医师", "主任医师", 1),
            ("副主任医师", "副主任医师", 2),
            ("主治医师", "主治医师", 3),
            ("住院医师", "住院医师", 4),
        ],
    ),
    (
        "education",
        "学历",
        "学历层级",
        [
            ("专科", "专科", 1),
            ("本科", "本科", 2),
            ("硕士", "硕士", 3),
            ("博士", "博士", 4),
            ("博士后", "博士后", 5),
        ],
    ),
    (
        "id_card_type",
        "证件类型",
        "身份证件类型",
        [
            ("居民身份证", "1", 1),
            ("户口簿", "2", 2),
            ("护照", "3", 3),
        ],
    ),
    (
        "patient_relationship",
        "就诊人关系",
        "就诊人与挂号人的关系",
        [
            ("本人", "本人", 1),
            ("父母", "父母", 2),
            ("子女", "子女", 3),
            ("配偶", "配偶", 4),
            ("其他", "其他", 5),
        ],
    ),
    (
        "notice_type",
        "公告类型",
        "系统公告的分类",
        [
            ("系统公告", "1", 1),
            ("停诊通知", "2", 2),
            ("活动通知", "3", 3),
        ],
    ),
    (
        "news_type",
        "新闻类型",
        "新闻资讯的分类",
        [
            ("医院动态", "1", 1),
            ("健康知识", "2", 2),
            ("政策法规", "3", 3),
        ],
    ),
    (
        "banner_link_type",
        "轮播图链接类型",
        "轮播图点击后的跳转类型",
        [
            ("无链接", "0", 1),
            ("内部链接", "1", 2),
            ("外部链接", "2", 3),
        ],
    ),
    (
        "banner_position",
        "轮播图展示位置",
        "轮播图在前端的展示位置",
        [
            ("首页", "home", 1),
            ("我的", "mine", 2),
        ],
    ),
    (
        "booking_notice_type",
        "预约须知类型",
        "预约须知的分类",
        [
            ("预约须知", "BOOKING", 1),
            ("就诊须知", "VISIT", 2),
            ("退号须知", "REFUND", 3),
        ],
    ),
    (
        "doctor_page_style",
        "医生页面风格",
        "医生个人主页的展示风格",
        [
            ("风格1", "1", 1),
            ("风格2", "2", 2),
            ("风格3", "3", 3),
        ],
    ),
    (
        "processing_method",
        "停诊处置方式",
        "停诊后的处置方式",
        [
            ("自动退号退款", "auto_refund", 1),
            ("转约其他医生", "reschedule", 2),
            ("改期其他时间", "change_date", 3),
            ("人工处理", "manual", 4),
        ],
    ),
]


def upgrade() -> None:
    now = datetime.utcnow()
    conn = op.get_bind()

    for code, name, description, items in DICT_TYPES:
        dict_type_id = str(uuid.uuid4())

        # 插入字典类型（不关联租户，作为全局默认）
        conn.execute(
            sa.text(
                "INSERT INTO dict_types (id, code, name, description, status, tenant_id, created_at, updated_at) "
                "VALUES (:id, :code, :name, :description, 1, NULL, :now, :now)"
            ),
            {
                "id": dict_type_id,
                "code": code,
                "name": name,
                "description": description,
                "now": now,
            },
        )

        # 插入字典项
        for label, value, sort_order in items:
            conn.execute(
                sa.text(
                    "INSERT INTO dict_items (id, dict_type_id, label, value, sort_order, status, extra, tenant_id, created_at, updated_at) "
                    "VALUES (:id, :type_id, :label, :value, :sort, 1, NULL, NULL, :now, :now)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "type_id": dict_type_id,
                    "label": label,
                    "value": value,
                    "sort": sort_order,
                    "now": now,
                },
            )


def downgrade() -> None:
    conn = op.get_bind()
    codes = [dt[0] for dt in DICT_TYPES]
    placeholders = ", ".join([f"'{c}'" for c in codes])

    # 先删字典项（外键约束）
    conn.execute(
        sa.text(
            f"DELETE FROM dict_items WHERE dict_type_id IN (SELECT id FROM dict_types WHERE code IN ({placeholders}))"
        )
    )
    conn.execute(sa.text(f"DELETE FROM dict_types WHERE code IN ({placeholders})"))
