"""知识库 API：租户隔离 / 共享权限矩阵 / 目录规则 / 上传校验 / 重试 / 下载 / 检索守卫

SQLite 可跑；向量排序与引用字段见 tests/integration/test_knowledge_search.py（仅 PG）。
响应信封：成功 {code, message, data}；错误 {code, message, error: {code, message}}。
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.modules.knowledge.service_search as search_module
from app.core.config import settings
from app.enums.knowledge import KnowledgeDocStatus
from app.infrastructure.embedding import EmbeddingError, get_embedding_config
from app.models.knowledge import KnowledgeBase, KnowledgeDocument
from tests.fixtures.knowledge import KnowledgeEnv

BASES = "/api/v1/knowledge/bases"
DEFAULT_TXT = "第一条 测试内容\n\n第二条 更多内容".encode()


def data(response) -> dict | list:
    return response.json()["data"]


def error_code(response) -> str | None:
    return (response.json().get("error") or {}).get("code")


async def create_kb(client, env: KnowledgeEnv, admin=None, **overrides) -> dict:
    payload = {"name": "院感制度", "description": "测试库", **overrides}
    response = await client.post(BASES, json=payload, headers=env.h(admin or env.owner))
    assert response.status_code == 201, response.text
    return data(response)


async def share(client, env: KnowledgeEnv, kb_id: str, grantee_type: str, grantee_id: str, permission: str) -> dict:
    response = await client.post(
        f"{BASES}/{kb_id}/shares",
        json={"granteeType": grantee_type, "granteeId": grantee_id, "permission": permission},
        headers=env.h(env.owner),
    )
    assert response.status_code == 201, response.text
    return data(response)


async def upload_txt(client, env: KnowledgeEnv, kb_id: str, admin=None, name="制度.txt", content: bytes = DEFAULT_TXT):
    return await client.post(
        f"{BASES}/{kb_id}/documents",
        files={"file": (name, content, "text/plain")},
        headers=env.h(admin or env.owner),
    )


# ==================== 开关 / 创建 / 租户隔离 ====================

async def test_disabled_flag_hides_all_routes(async_client, kb_env: KnowledgeEnv, monkeypatch):
    monkeypatch.setattr(settings, "KB_ENABLED", False)
    response = await async_client.get(BASES, headers=kb_env.h(kb_env.owner))
    assert response.status_code == 404


async def test_create_base_defaults_to_private_owner(async_client, kb_env: KnowledgeEnv):
    kb = await create_kb(async_client, kb_env)
    assert kb["visibility"] == "private"
    assert kb["ownerAdminId"] == kb_env.owner.id
    assert kb["myPermission"] == "owner"
    assert kb["embeddingModel"] == get_embedding_config().model
    assert kb["embeddingDims"] == settings.KB_EMBEDDING_DIMS

    listed = await async_client.get(BASES, headers=kb_env.h(kb_env.owner))
    assert listed.status_code == 200
    assert [item["id"] for item in data(listed)] == [kb["id"]]
    assert listed.json()["total"] == 1


async def test_private_base_invisible_to_colleague_without_share(async_client, kb_env: KnowledgeEnv):
    kb = await create_kb(async_client, kb_env)
    response = await async_client.get(f"{BASES}/{kb['id']}", headers=kb_env.h(kb_env.colleague))
    assert response.status_code == 404
    listed = await async_client.get(BASES, headers=kb_env.h(kb_env.colleague))
    assert listed.json()["total"] == 0


async def test_cross_tenant_is_404_not_403(async_client, kb_env: KnowledgeEnv):
    kb = await create_kb(async_client, kb_env)
    outsider = kb_env.h(kb_env.outsider)
    assert (await async_client.get(f"{BASES}/{kb['id']}", headers=outsider)).status_code == 404
    assert (await async_client.get(f"{BASES}/{kb['id']}/documents", headers=outsider)).status_code == 404
    assert (await async_client.delete(f"{BASES}/{kb['id']}", headers=outsider)).status_code == 404
    listed = await async_client.get(BASES, headers=outsider)
    assert listed.json()["total"] == 0


async def test_tenant_visibility_grants_read_to_everyone_in_tenant(async_client, kb_env: KnowledgeEnv):
    kb = await create_kb(async_client, kb_env, visibility="tenant")
    detail = await async_client.get(f"{BASES}/{kb['id']}", headers=kb_env.h(kb_env.reader))
    assert detail.status_code == 200
    assert data(detail)["myPermission"] == "read"
    scoped = await async_client.get(BASES, params={"scope": "tenant"}, headers=kb_env.h(kb_env.colleague))
    assert [item["id"] for item in data(scoped)] == [kb["id"]]


# ==================== 共享权限矩阵 ====================

async def test_read_share_allows_browse_but_not_edit_share_delete(async_client, kb_env: KnowledgeEnv):
    kb = await create_kb(async_client, kb_env)
    await share(async_client, kb_env, kb["id"], "admin", kb_env.colleague.id, "read")
    colleague = kb_env.h(kb_env.colleague)

    shared_list = await async_client.get(BASES, params={"scope": "shared"}, headers=colleague)
    assert [item["id"] for item in data(shared_list)] == [kb["id"]]
    assert data(shared_list)[0]["myPermission"] == "read"
    assert (await async_client.get(f"{BASES}/{kb['id']}/documents", headers=colleague)).status_code == 200

    assert (await upload_txt(async_client, kb_env, kb["id"], admin=kb_env.colleague)).status_code == 403
    folder = await async_client.post(f"{BASES}/{kb['id']}/folders", json={"name": "新目录"}, headers=colleague)
    assert folder.status_code == 403
    reshare = await async_client.post(
        f"{BASES}/{kb['id']}/shares",
        json={"granteeType": "admin", "granteeId": kb_env.reader.id, "permission": "read"},
        headers=colleague,
    )
    assert reshare.status_code == 403
    assert (await async_client.delete(f"{BASES}/{kb['id']}", headers=colleague)).status_code == 403


async def test_edit_share_allows_upload_and_folders_but_not_share_or_delete_base(async_client, kb_env: KnowledgeEnv):
    kb = await create_kb(async_client, kb_env)
    await share(async_client, kb_env, kb["id"], "admin", kb_env.colleague.id, "edit")
    colleague = kb_env.h(kb_env.colleague)

    folder = await async_client.post(f"{BASES}/{kb['id']}/folders", json={"name": "SOP"}, headers=colleague)
    assert folder.status_code == 201
    uploaded = await upload_txt(async_client, kb_env, kb["id"], admin=kb_env.colleague)
    assert uploaded.status_code == 201
    assert data(uploaded)["status"] == "pending"

    reshare = await async_client.post(
        f"{BASES}/{kb['id']}/shares",
        json={"granteeType": "admin", "granteeId": kb_env.reader.id, "permission": "read"},
        headers=colleague,
    )
    assert reshare.status_code == 403
    assert (await async_client.delete(f"{BASES}/{kb['id']}", headers=colleague)).status_code == 403
    assert (await async_client.get(f"{BASES}/{kb['id']}/shares", headers=colleague)).status_code == 403


async def test_role_share_covers_every_admin_with_that_role(async_client, kb_env: KnowledgeEnv):
    kb = await create_kb(async_client, kb_env)
    created = await share(async_client, kb_env, kb["id"], "role", kb_env.reader_role.id, "read")
    assert created["granteeName"] == kb_env.reader_role.name

    detail = await async_client.get(f"{BASES}/{kb['id']}", headers=kb_env.h(kb_env.reader))
    assert detail.status_code == 200
    assert data(detail)["myPermission"] == "read"


async def test_revoking_share_takes_effect_immediately(async_client, kb_env: KnowledgeEnv):
    kb = await create_kb(async_client, kb_env)
    created = await share(async_client, kb_env, kb["id"], "admin", kb_env.colleague.id, "read")
    colleague = kb_env.h(kb_env.colleague)
    assert (await async_client.get(f"{BASES}/{kb['id']}", headers=colleague)).status_code == 200

    removed = await async_client.delete(f"/api/v1/knowledge/shares/{created['id']}", headers=kb_env.h(kb_env.owner))
    assert removed.status_code == 204
    assert (await async_client.get(f"{BASES}/{kb['id']}", headers=colleague)).status_code == 404
    search = await async_client.post(
        "/api/v1/knowledge/search", json={"query": "x", "kbIds": [kb["id"]]}, headers=colleague
    )
    assert search.status_code == 403


async def test_sharing_to_owner_or_duplicate_updates_instead_of_duplicating(async_client, kb_env: KnowledgeEnv):
    kb = await create_kb(async_client, kb_env)
    self_share = await async_client.post(
        f"{BASES}/{kb['id']}/shares",
        json={"granteeType": "admin", "granteeId": kb_env.owner.id, "permission": "read"},
        headers=kb_env.h(kb_env.owner),
    )
    assert self_share.status_code == 409

    first = await share(async_client, kb_env, kb["id"], "admin", kb_env.colleague.id, "read")
    second = await share(async_client, kb_env, kb["id"], "admin", kb_env.colleague.id, "edit")
    assert first["id"] == second["id"]
    assert second["permission"] == "edit"
    shares = await async_client.get(f"{BASES}/{kb['id']}/shares", headers=kb_env.h(kb_env.owner))
    assert len(data(shares)) == 1


async def test_manage_permission_sees_and_controls_private_bases(async_client, kb_env: KnowledgeEnv):
    kb = await create_kb(async_client, kb_env)
    manager = kb_env.h(kb_env.manager)
    listed = await async_client.get(BASES, headers=manager)
    assert [item["id"] for item in data(listed)] == [kb["id"]]
    detail = await async_client.get(f"{BASES}/{kb['id']}", headers=manager)
    assert data(detail)["myPermission"] == "owner"
    renamed = await async_client.patch(f"{BASES}/{kb['id']}", json={"name": "治理后"}, headers=manager)
    assert renamed.status_code == 200
    assert data(renamed)["name"] == "治理后"


# ==================== 目录规则 ====================

async def test_folder_tree_rules(async_client, kb_env: KnowledgeEnv):
    kb = await create_kb(async_client, kb_env)
    owner = kb_env.h(kb_env.owner)
    root = data(await async_client.post(f"{BASES}/{kb['id']}/folders", json={"name": "制度"}, headers=owner))
    child = data(
        await async_client.post(
            f"{BASES}/{kb['id']}/folders", json={"name": "现行", "parentId": root["id"]}, headers=owner
        )
    )

    duplicate = await async_client.post(f"{BASES}/{kb['id']}/folders", json={"name": "制度"}, headers=owner)
    assert duplicate.status_code == 409

    into_descendant = await async_client.patch(
        f"/api/v1/knowledge/folders/{root['id']}", json={"parentId": child["id"]}, headers=owner
    )
    assert into_descendant.status_code == 409
    into_self = await async_client.patch(
        f"/api/v1/knowledge/folders/{root['id']}", json={"parentId": root["id"]}, headers=owner
    )
    assert into_self.status_code == 409

    non_empty = await async_client.delete(f"/api/v1/knowledge/folders/{root['id']}", headers=owner)
    assert non_empty.status_code == 409

    moved = await async_client.patch(f"/api/v1/knowledge/folders/{child['id']}", json={"parentId": None}, headers=owner)
    assert moved.status_code == 200
    assert data(moved)["parentId"] is None

    tree = await async_client.get(f"{BASES}/{kb['id']}/folders", headers=owner)
    assert {item["id"] for item in data(tree)} == {root["id"], child["id"]}
    assert (await async_client.delete(f"/api/v1/knowledge/folders/{root['id']}", headers=owner)).status_code == 204


# ==================== 上传校验 / 重试 / 下载 ====================

async def test_upload_rejects_unsupported_type_and_oversize(async_client, kb_env: KnowledgeEnv, monkeypatch):
    kb = await create_kb(async_client, kb_env)
    pptx = await upload_txt(async_client, kb_env, kb["id"], name="课件.pptx", content=b"x" * 10)
    assert pptx.status_code == 400
    assert error_code(pptx) == "KB_INVALID_FILE"
    assert "不支持的文件类型" in pptx.json()["message"]

    monkeypatch.setattr(settings, "KB_MAX_FILE_MB", 1)
    too_big = await upload_txt(async_client, kb_env, kb["id"], name="大文件.txt", content=b"x" * (1024 * 1024 + 1))
    assert too_big.status_code == 400
    assert "1MB" in too_big.json()["message"]
    assert kb_env.enqueued == []


async def test_upload_success_persists_file_and_enqueues(async_client, kb_env: KnowledgeEnv, db_session: AsyncSession):
    kb = await create_kb(async_client, kb_env)
    response = await upload_txt(async_client, kb_env, kb["id"])
    assert response.status_code == 201, response.text
    body = data(response)
    assert body["status"] == "pending"
    assert body["title"] == "制度"
    assert body["mimeType"] == "text/plain"
    assert kb_env.enqueued == [body["id"]]

    doc = await db_session.get(KnowledgeDocument, body["id"])
    assert doc is not None
    assert doc.file_key.startswith(f"tenants/{kb_env.tenant.id}/knowledge/{kb['id']}/{doc.id}/")
    from app.modules.knowledge.service import resolve_local_file

    assert resolve_local_file(doc.file_key) is not None

    detail = await async_client.get(f"{BASES}/{kb['id']}", headers=kb_env.h(kb_env.owner))
    assert data(detail)["docCount"] == 1


async def test_retry_only_allowed_for_failed_documents(async_client, kb_env: KnowledgeEnv, db_session: AsyncSession):
    kb = await create_kb(async_client, kb_env)
    doc_id = data(await upload_txt(async_client, kb_env, kb["id"]))["id"]
    kb_env.enqueued.clear()
    owner = kb_env.h(kb_env.owner)

    pending_retry = await async_client.post(f"/api/v1/knowledge/documents/{doc_id}/retry", headers=owner)
    assert pending_retry.status_code == 409

    doc = await db_session.get(KnowledgeDocument, doc_id)
    doc.status = KnowledgeDocStatus.FAILED.value
    doc.failed_stage = "parsing"
    doc.error_message = "PDF 无文本层（疑似扫描件），暂不支持 OCR"
    await db_session.commit()

    retried = await async_client.post(f"/api/v1/knowledge/documents/{doc_id}/retry", headers=owner)
    assert retried.status_code == 200
    assert data(retried)["status"] == "pending"
    assert data(retried)["errorMessage"] is None
    assert kb_env.enqueued == [doc_id]


async def test_download_requires_visibility_and_streams_file(async_client, kb_env: KnowledgeEnv):
    kb = await create_kb(async_client, kb_env)
    content = b"only owner may read this"
    doc_id = data(await upload_txt(async_client, kb_env, kb["id"], content=content))["id"]

    denied = await async_client.get(f"/api/v1/knowledge/documents/{doc_id}/file", headers=kb_env.h(kb_env.colleague))
    assert denied.status_code == 404

    inline = await async_client.get(f"/api/v1/knowledge/documents/{doc_id}/file", headers=kb_env.h(kb_env.owner))
    assert inline.status_code == 200
    assert inline.content == content
    assert inline.headers["content-disposition"].startswith("inline;")

    attachment = await async_client.get(
        f"/api/v1/knowledge/documents/{doc_id}/file", params={"download": "true"}, headers=kb_env.h(kb_env.owner)
    )
    assert attachment.headers["content-disposition"].startswith("attachment;")


async def test_delete_document_and_base_cleanup(async_client, kb_env: KnowledgeEnv, db_session: AsyncSession):
    kb = await create_kb(async_client, kb_env)
    doc_id = data(await upload_txt(async_client, kb_env, kb["id"]))["id"]
    owner = kb_env.h(kb_env.owner)

    assert (await async_client.delete(f"/api/v1/knowledge/documents/{doc_id}", headers=owner)).status_code == 204
    assert await db_session.get(KnowledgeDocument, doc_id) is None
    assert data(await async_client.get(f"{BASES}/{kb['id']}", headers=owner))["docCount"] == 0

    assert (await async_client.delete(f"{BASES}/{kb['id']}", headers=owner)).status_code == 204
    remaining = await db_session.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb["id"]))
    assert remaining.scalar_one_or_none() is None


# ==================== 检索守卫（排序逻辑见集成测试） ====================

async def test_search_rejects_top_k_over_limit(async_client, kb_env: KnowledgeEnv):
    await create_kb(async_client, kb_env)
    response = await async_client.post(
        "/api/v1/knowledge/search", json={"query": "术前禁食", "topK": 50}, headers=kb_env.h(kb_env.owner)
    )
    assert response.status_code == 400
    assert error_code(response) == "KB_TOP_K_EXCEEDED"


async def test_search_with_invisible_kb_id_is_403_not_silently_trimmed(async_client, kb_env: KnowledgeEnv):
    private_kb = await create_kb(async_client, kb_env)
    own_kb = await create_kb(async_client, kb_env, admin=kb_env.colleague, name="同事自己的库")
    response = await async_client.post(
        "/api/v1/knowledge/search",
        json={"query": "术前禁食", "kbIds": [own_kb["id"], private_kb["id"]]},
        headers=kb_env.h(kb_env.colleague),
    )
    assert response.status_code == 403
    assert error_code(response) == "KB_FORBIDDEN"


async def test_search_blocks_embedding_model_mismatch(async_client, kb_env: KnowledgeEnv, db_session: AsyncSession):
    kb = await create_kb(async_client, kb_env)
    row = await db_session.get(KnowledgeBase, kb["id"])
    row.embedding_model = "legacy-model"
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/knowledge/search", json={"query": "术前禁食", "kbIds": [kb["id"]]}, headers=kb_env.h(kb_env.owner)
    )
    assert response.status_code == 409
    assert error_code(response) == "KB_EMBEDDING_MISMATCH"


async def test_search_maps_provider_failure_to_503_without_leaking(async_client, kb_env: KnowledgeEnv, monkeypatch):
    await create_kb(async_client, kb_env)

    def broken_provider():
        raise EmbeddingError("upstream said: secret internal detail")

    monkeypatch.setattr(search_module, "get_embedding_provider", broken_provider)
    response = await async_client.post(
        "/api/v1/knowledge/search", json={"query": "术前禁食"}, headers=kb_env.h(kb_env.owner)
    )
    assert response.status_code == 503
    assert error_code(response) == "KB_EMBEDDING_UNAVAILABLE"
    assert "secret internal detail" not in response.text


async def test_search_without_any_visible_base_returns_empty(async_client, kb_env: KnowledgeEnv):
    response = await async_client.post(
        "/api/v1/knowledge/search", json={"query": "术前禁食"}, headers=kb_env.h(kb_env.reader)
    )
    assert response.status_code == 200
    assert data(response) == {"hits": [], "total": 0, "tookMs": 0}
