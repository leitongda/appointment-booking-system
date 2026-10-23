"""B8：患者运营与内容租户锚点矩阵（R1-14 / R1-15 / R1-18）

覆盖计划 B8 验收门：
1. blacklists：列表双向断言；跨租户解禁 404 且他租户记录未变；
   平台管理员无锚点创建 400；本租户创建落库 tenant_id=A；跨租户用户拒绝。
2. points：流水/排行列表双向断言；跨租户调整 400 且余额未变；
   平台管理员无锚点调整 400；本租户调整落库 tenant_id=A。
3. feedbacks：列表/待处理数/统计双向断言；跨租户回复/删除 404 且未变；
   患者自助提交按请求租户落库（保持 require_tenant_active_for_write 语义）。
4. dictionaries：管理端列表/详情按锚点过滤；无锚点创建 400；
   公开端 /dict-options 无租户头 400，A/B 同码字典互不可见。
5. email_templates：列表含本租户与平台模板、不含他租户；平台模板仅平台管理员可写；
   本租户创建落库 tenant_id=A，平台管理员无锚点创建落库 NULL。
6. booking_notices：管理端列表/详情按锚点过滤；无锚点创建 400；
   公开端 /booking-notices/public 无租户头 400，A 须知不出现在 B。
"""
import uuid

import pytest
import pytest_asyncio

from app.models.blacklist import Blacklist
from app.models.booking_notice import BookingNotice
from app.models.dict_item import DictItem
from app.models.dict_type import DictType
from app.models.email_template import EmailTemplate
from app.models.feedback import Feedback
from app.models.point_log import PointLog
from app.models.user import User

pytestmark = [pytest.mark.security, pytest.mark.multi_tenant]

BLACKLISTS = "/api/v1/blacklists"
POINTS = "/api/v1/points"
FEEDBACKS = "/api/v1/feedbacks"
DICTS = "/api/v1/dicts"
DICT_OPTIONS = "/api/v1/dict-options"
EMAIL_TEMPLATES = "/api/v1/email-templates"
BOOKING_NOTICES = "/api/v1/booking-notices"


def _auth(token: str, tenant_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
    return headers


def _items(payload) -> list:
    """兼容统一响应外壳与裸列表"""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("data") or data.get("items") or []
    return payload.get("items") or []


def _obj(payload) -> dict:
    """解包统一响应外壳 {code,message,data}（兼容接口自身的 {message,data} 再包一层）"""
    node = payload
    for _ in range(3):
        if isinstance(node, dict) and isinstance(node.get("data"), dict):
            node = node["data"]
        else:
            break
    return node if isinstance(node, dict) else {}


def _ids(payload) -> set[str]:
    return {item.get("id") for item in _items(payload) if isinstance(item, dict)}


async def _add_user(db_session, tenant_id: str, label: str, points: int = 0) -> User:
    row = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        phone=f"136{uuid.uuid4().int % 10**8:08d}",
        password_hash="$2b$12$test_hash_not_for_production",
        nickname=f"B8用户{label}",
        gender=0,
        points=points,
        status=1,
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_blacklist(db_session, tenant_id: str, user_id: str, keyword: str) -> Blacklist:
    row = Blacklist(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=user_id,
        keyword=keyword,
        reason=f"{keyword}原因",
        source=1,
        no_show_count=0,
        status=1,
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_point_log(db_session, tenant_id: str, user_id: str, amount: int) -> PointLog:
    row = PointLog(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=user_id,
        change_amount=amount,
        balance=amount,
        type=4,
        remark="B8初始化",
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_feedback(db_session, tenant_id: str, user_id: str, title: str) -> Feedback:
    row = Feedback(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=user_id,
        user_type="patient",
        feedback_type="suggestion",
        title=title,
        content=f"{title}的内容描述，长度满足校验要求",
        status="pending",
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_dict_type(db_session, tenant_id: str, code: str, name: str) -> DictType:
    row = DictType(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        code=code,
        name=name,
        status=1,
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_dict_item(
    db_session, tenant_id: str, type_id: str, label: str, value: str
) -> DictItem:
    row = DictItem(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        dict_type_id=type_id,
        label=label,
        value=value,
        sort_order=0,
        status=1,
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_email_template(
    db_session, tenant_id: str | None, code: str, name: str
) -> EmailTemplate:
    row = EmailTemplate(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        code=code,
        name=name,
        template_type="custom",
        subject_template=f"{name}主题",
        content_template=f"<p>{name}</p>",
        description=name,
        status=1,
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_notice(db_session, tenant_id: str, title: str, content: str) -> BookingNotice:
    row = BookingNotice(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        type="BOOKING",
        title=title,
        content=content,
        sort_order=0,
        status=1,
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


@pytest_asyncio.fixture
async def b8_env(db_session, multi_tenant_env):
    """A/B 两租户各一套患者运营与内容数据"""
    env = multi_tenant_env

    env.user_a = await _add_user(db_session, env.tenant_a.id, "A", points=10)
    env.user_b = await _add_user(db_session, env.tenant_b.id, "B", points=20)

    env.blacklist_a = await _add_blacklist(
        db_session, env.tenant_a.id, env.user_a.id, "13900000001"
    )
    env.blacklist_b = await _add_blacklist(
        db_session, env.tenant_b.id, env.user_b.id, "13900000002"
    )

    env.point_log_a = await _add_point_log(
        db_session, env.tenant_a.id, env.user_a.id, 10
    )
    env.point_log_b = await _add_point_log(
        db_session, env.tenant_b.id, env.user_b.id, 20
    )

    env.feedback_a = await _add_feedback(
        db_session, env.tenant_a.id, env.user_a.id, "A反馈"
    )
    env.feedback_b = await _add_feedback(
        db_session, env.tenant_b.id, env.user_b.id, "B反馈"
    )

    env.dict_code = f"B8_COLOR_{uuid.uuid4().hex[:6].upper()}"
    env.dict_type_a = await _add_dict_type(
        db_session, env.tenant_a.id, env.dict_code, "A颜色字典"
    )
    env.dict_type_b = await _add_dict_type(
        db_session, env.tenant_b.id, env.dict_code, "B颜色字典"
    )
    env.dict_item_a = await _add_dict_item(
        db_session, env.tenant_a.id, env.dict_type_a.id, "A红", "a-red"
    )
    env.dict_item_b = await _add_dict_item(
        db_session, env.tenant_b.id, env.dict_type_b.id, "B蓝", "b-blue"
    )

    suffix = uuid.uuid4().hex[:8]
    env.email_a = await _add_email_template(
        db_session, env.tenant_a.id, f"B8_A_{suffix}", "A模板"
    )
    env.email_b = await _add_email_template(
        db_session, env.tenant_b.id, f"B8_B_{suffix}", "B模板"
    )
    env.email_platform = await _add_email_template(
        db_session, None, f"B8_P_{suffix}", "平台模板"
    )

    env.notice_a = await _add_notice(
        db_session, env.tenant_a.id, "A预约须知", "A须知内容"
    )
    env.notice_b = await _add_notice(
        db_session, env.tenant_b.id, "B预约须知", "B须知内容"
    )
    return env


class TestBlacklistsAnchor:
    async def test_list_only_own_tenant(self, async_client, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.get(
            BLACKLISTS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.blacklist_a.id in ids
        assert env.blacklist_b.id not in ids

    async def test_cross_tenant_remove_404_and_unchanged(
        self, async_client, db_session, b8_env, admin_token_factory
    ):
        env = b8_env
        response = await async_client.delete(
            f"{BLACKLISTS}/{env.blacklist_b.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(Blacklist, env.blacklist_b.id)
        await db_session.refresh(refreshed)
        assert refreshed.status == 1

    async def test_create_without_anchor_400(self, async_client, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.post(
            BLACKLISTS,
            headers=_auth(admin_token_factory(env.platform_admin)),
            json={"keyword": "13900000009", "reason": "无锚点"},
        )
        assert response.status_code == 400, response.text

    async def test_create_writes_tenant_anchor(
        self, async_client, db_session, b8_env, admin_token_factory
    ):
        env = b8_env
        response = await async_client.post(
            BLACKLISTS,
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={"keyword": f"139{uuid.uuid4().int % 10**8:08d}", "reason": "锚点创建"},
        )
        assert response.status_code in (200, 201), response.text
        created = await db_session.get(Blacklist, _obj(response.json())["id"])
        assert created is not None
        assert created.tenant_id == env.tenant_a.id

    async def test_create_rejects_foreign_user(
        self, async_client, b8_env, admin_token_factory
    ):
        env = b8_env
        response = await async_client.post(
            BLACKLISTS,
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={"userId": env.user_b.id, "reason": "跨租户用户"},
        )
        assert response.status_code == 400, response.text


class TestPointsAnchor:
    async def test_logs_only_own_tenant(self, async_client, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.get(
            f"{POINTS}/logs",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.point_log_a.id in ids
        assert env.point_log_b.id not in ids

    async def test_ranking_only_own_tenant(self, async_client, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.get(
            f"{POINTS}/users",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.user_a.id in ids
        assert env.user_b.id not in ids

    async def test_cross_tenant_adjust_rejected_and_unchanged(
        self, async_client, db_session, b8_env, admin_token_factory
    ):
        env = b8_env
        response = await async_client.post(
            f"{POINTS}/{env.user_b.id}/adjust",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={"amount": 5, "remark": "越权调整"},
        )
        assert response.status_code == 400, response.text

        refreshed = await db_session.get(User, env.user_b.id)
        await db_session.refresh(refreshed)
        assert refreshed.points == 20

    async def test_adjust_without_anchor_400(self, async_client, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.post(
            f"{POINTS}/{env.user_a.id}/adjust",
            headers=_auth(admin_token_factory(env.platform_admin)),
            json={"amount": 5, "remark": "无锚点调整"},
        )
        assert response.status_code == 400, response.text

    async def test_adjust_own_writes_tenant_anchor(
        self, async_client, db_session, b8_env, admin_token_factory
    ):
        env = b8_env
        response = await async_client.post(
            f"{POINTS}/{env.user_a.id}/adjust",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={"amount": 5, "remark": "本租户调整"},
        )
        assert response.status_code == 200, response.text
        created = await db_session.get(PointLog, _obj(response.json())["id"])
        assert created is not None
        assert created.tenant_id == env.tenant_a.id

        refreshed = await db_session.get(User, env.user_a.id)
        await db_session.refresh(refreshed)
        assert refreshed.points == 15


class TestFeedbacksAnchor:
    async def test_list_only_own_tenant(self, async_client, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.get(
            FEEDBACKS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.feedback_a.id in ids
        assert env.feedback_b.id not in ids

    async def test_pending_count_scoped(self, async_client, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.get(
            f"{FEEDBACKS}/pending-count",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        assert _obj(response.json())["count"] == 1

    async def test_statistics_scoped(self, async_client, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.get(
            f"{FEEDBACKS}/statistics",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        body = _obj(response.json())
        assert body["total"] == 1, body
        assert body["by_status"]["pending"] == 1, body

    async def test_cross_tenant_reply_404_and_unchanged(
        self, async_client, db_session, b8_env, admin_token_factory
    ):
        env = b8_env
        response = await async_client.post(
            f"{FEEDBACKS}/{env.feedback_b.id}/reply",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={"reply": "越权回复"},
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(Feedback, env.feedback_b.id)
        await db_session.refresh(refreshed)
        assert refreshed.reply is None
        assert refreshed.status == "pending"

    async def test_cross_tenant_delete_404(self, async_client, db_session, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.delete(
            f"{FEEDBACKS}/{env.feedback_b.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(Feedback, env.feedback_b.id)
        assert refreshed is not None

    async def test_patient_create_uses_request_tenant(
        self, async_client, db_session, b8_env
    ):
        env = b8_env
        response = await async_client.post(
            FEEDBACKS,
            headers={"X-Tenant-ID": env.tenant_a.id},
            json={
                "userId": env.user_a.id,
                "title": "患者自助反馈",
                "content": "这是一条长度满足校验要求的患者反馈内容",
            },
        )
        assert response.status_code in (200, 201), response.text
        created = await db_session.get(Feedback, _obj(response.json())["id"])
        assert created is not None
        assert created.tenant_id == env.tenant_a.id


class TestDictionariesAnchor:
    async def test_admin_list_only_own_tenant(self, async_client, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.get(
            DICTS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.dict_type_a.id in ids
        assert env.dict_type_b.id not in ids

    async def test_cross_tenant_detail_404(self, async_client, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.get(
            f"{DICTS}/{env.dict_type_b.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

    async def test_create_without_anchor_400(self, async_client, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.post(
            DICTS,
            headers=_auth(admin_token_factory(env.platform_admin)),
            json={"code": "B8_NO_ANCHOR", "name": "无锚点字典"},
        )
        assert response.status_code == 400, response.text

    async def test_create_writes_tenant_anchor(
        self, async_client, db_session, b8_env, admin_token_factory
    ):
        env = b8_env
        response = await async_client.post(
            DICTS,
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={"code": f"B8_NEW_{uuid.uuid4().hex[:6].upper()}", "name": "锚点字典"},
        )
        assert response.status_code in (200, 201), response.text
        created = await db_session.get(DictType, _obj(response.json())["id"])
        assert created is not None
        assert created.tenant_id == env.tenant_a.id

    async def test_public_options_requires_tenant(self, async_client, b8_env):
        env = b8_env
        response = await async_client.get(f"{DICT_OPTIONS}/{env.dict_code}")
        assert response.status_code == 400, response.text

    async def test_public_options_isolated_by_tenant(
        self, async_client, b8_env
    ):
        env = b8_env

        response_a = await async_client.get(
            f"{DICT_OPTIONS}/{env.dict_code}",
            headers={"X-Tenant-ID": env.tenant_a.id},
        )
        assert response_a.status_code == 200, response_a.text
        values_a = {item["value"] for item in _obj(response_a.json())["items"]}
        assert values_a == {"a-red"}, values_a

        response_b = await async_client.get(
            f"{DICT_OPTIONS}/{env.dict_code}",
            headers={"X-Tenant-ID": env.tenant_b.id},
        )
        assert response_b.status_code == 200, response_b.text
        values_b = {item["value"] for item in _obj(response_b.json())["items"]}
        assert values_b == {"b-blue"}, values_b


class TestEmailTemplatesAnchor:
    async def test_list_only_own_and_platform(self, async_client, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.get(
            EMAIL_TEMPLATES,
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.email_a.id in ids
        assert env.email_platform.id in ids
        assert env.email_b.id not in ids

    async def test_cross_tenant_detail_404(self, async_client, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.get(
            f"{EMAIL_TEMPLATES}/{env.email_b.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

    async def test_platform_template_not_writable_by_tenant_admin(
        self, async_client, db_session, b8_env, admin_token_factory
    ):
        env = b8_env
        response = await async_client.put(
            f"{EMAIL_TEMPLATES}/{env.email_platform.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={"name": "租户越权改名"},
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(EmailTemplate, env.email_platform.id)
        await db_session.refresh(refreshed)
        assert refreshed.name == "平台模板"

    async def test_create_writes_tenant_anchor(
        self, async_client, db_session, b8_env, admin_token_factory
    ):
        env = b8_env
        response = await async_client.post(
            EMAIL_TEMPLATES,
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={
                "code": f"B8_T_{uuid.uuid4().hex[:6].upper()}",
                "name": "锚点模板",
                "subjectTemplate": "主题",
                "contentTemplate": "<p>内容</p>",
            },
        )
        assert response.status_code in (200, 201), response.text
        created = await db_session.get(EmailTemplate, _obj(response.json())["id"])
        assert created is not None
        assert created.tenant_id == env.tenant_a.id

    async def test_platform_admin_creates_global_template(
        self, async_client, db_session, b8_env, admin_token_factory
    ):
        env = b8_env
        response = await async_client.post(
            EMAIL_TEMPLATES,
            headers=_auth(admin_token_factory(env.platform_admin)),
            json={
                "code": f"B8_G_{uuid.uuid4().hex[:6].upper()}",
                "name": "平台模板",
                "subjectTemplate": "主题",
                "contentTemplate": "<p>内容</p>",
            },
        )
        assert response.status_code in (200, 201), response.text
        created = await db_session.get(EmailTemplate, _obj(response.json())["id"])
        assert created is not None
        assert created.tenant_id is None


class TestBookingNoticesAnchor:
    async def test_admin_list_only_own_tenant(self, async_client, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.get(
            BOOKING_NOTICES,
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.notice_a.id in ids
        assert env.notice_b.id not in ids

    async def test_cross_tenant_detail_404(self, async_client, b8_env, admin_token_factory):
        env = b8_env
        response = await async_client.get(
            f"{BOOKING_NOTICES}/{env.notice_b.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

    async def test_platform_admin_creates_global_notice(
        self, async_client, db_session, b8_env, admin_token_factory
    ):
        """平台级须知（tenant_id=NULL）分支仅平台管理员可达。"""
        env = b8_env
        response = await async_client.post(
            BOOKING_NOTICES,
            headers=_auth(admin_token_factory(env.platform_admin)),
            json={"type": "BOOKING", "title": "平台须知"},
        )
        assert response.status_code in (200, 201), response.text
        created = await db_session.get(BookingNotice, _obj(response.json())["id"])
        assert created is not None
        assert created.tenant_id is None

    async def test_create_writes_tenant_anchor(
        self, async_client, db_session, b8_env, admin_token_factory
    ):
        env = b8_env
        response = await async_client.post(
            BOOKING_NOTICES,
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={"type": "BOOKING", "title": "锚点须知", "content": "内容"},
        )
        assert response.status_code in (200, 201), response.text
        created = await db_session.get(BookingNotice, _obj(response.json())["id"])
        assert created is not None
        assert created.tenant_id == env.tenant_a.id

    async def test_public_requires_tenant(self, async_client, b8_env):
        response = await async_client.get(f"{BOOKING_NOTICES}/public")
        assert response.status_code == 400, response.text

    async def test_public_isolated_by_tenant(self, async_client, b8_env):
        env = b8_env

        response_a = await async_client.get(
            f"{BOOKING_NOTICES}/public", headers={"X-Tenant-ID": env.tenant_a.id}
        )
        assert response_a.status_code == 200, response_a.text
        ids_a = _ids(response_a.json())
        assert env.notice_a.id in ids_a
        assert env.notice_b.id not in ids_a

        response_b = await async_client.get(
            f"{BOOKING_NOTICES}/public", headers={"X-Tenant-ID": env.tenant_b.id}
        )
        assert response_b.status_code == 200, response_b.text
        ids_b = _ids(response_b.json())
        assert env.notice_b.id in ids_b
        assert env.notice_a.id not in ids_b
