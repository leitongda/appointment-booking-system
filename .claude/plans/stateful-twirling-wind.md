# Server 端文件管理/命名/组织规范审查报告

## Context

基于自适应团队审查的后续跟进，对 `apps/server/app/` 下的文件管理、命名规范、组织方式进行系统性审查，识别不符合规范的问题。

---

## 审查范围

| 目录 | 文件数 | 说明 |
|------|--------|------|
| modules/ | 57 模块, ~200 .py | 业务模块主战场 |
| models/ | 51 .py | SQLAlchemy 模型 |
| schemas/ | 37 .py | Pydantic DTO |
| middleware/ | 7 .py | 中间件 |
| common/ | 16 .py | 跨模块共享工具 |
| core/ | 7 .py | 基础设施配置 |
| infrastructure/ | 8 子目录, ~30 .py | 外部集成层 |
| services/ | 2 .py | 全局服务（剩余） |
| utils/ | 6 .py | 工具函数 |
| migrations/ | 118 .py | Alembic 迁移 |
| tests/ | ~90 .py | 测试 |

---

## 发现的问题（按严重程度排序）

### P0 — 必须修复

无。

### P1 — 应该修复

#### 1. `support_tickets/` 缺少 `__init__.py`
```
modules/support_tickets/
├── router.py
├── service.py
└── (缺少 __init__.py)
```
影响：Python 包识别、模块导入可能失败。

#### 2. `infrastructure/payments/` 缺少 `__init__.py`
```
infrastructure/payments/
├── config_resolver.py
├── schemas.py
├── wechat_pay_service.py
└── (缺少 __init__.py)
```
影响同上。

#### 3. `common/` 与 `core/` 职责重叠
- `common/error_codes.py` 与 `core/error_codes.py` 并存，功能重叠
- `common/` 有 16 个文件，部分与 `core/` 定位不清（如 `common/decorators.py`、`common/feature_flags.py` 更接近 core 层）
- 缺乏清晰的分层规则文档

#### 4. `services/` 全局目录仅剩 2 个文件
- `services/email_template_service.py`
- `services/rule_performance_service.py`
这 2 个文件应该评估是否可以迁入对应模块（按 CLAUDE.md 中的 Service 归属规则）。

### P2 — 建议改进

#### 5. 迁移文件命名不一致
- 117 个文件使用 `NNN_描述.py` 格式（如 `116_create_follow_up_tables.py`）
- 最后 1 个使用 Alembic 自动生成的 hex hash 格式：`2fc10ef02888_remove_weekday_column_from_schedule_.py`
- 应重命名为 `118_remove_weekday_from_schedule_templates.py` 保持一致

#### 6. 迁移编号有重复
- `004_add_consultation_fee.py` 和 `004_add_department_fields.py` 编号重复
- `007_schedule_management.py` 和 `007_schedule_template.py` 编号重复
- `058_add_notification_logs.py` 和 `058_add_rule_set_audit_logs.py` 编号重复
- 这是 Alembic 多分支开发的正常产物（已通过 `011_merge_heads.py` 等合并），但应知道这是一个已知的混乱点。

#### 7. 模块目录命名风格不统一
| 类型 | 示例 |
|------|------|
| 复数名词 | `users/`, `doctors/`, `departments/`, `appointments/`, `patients/` |
| 单数名词 | `auth/`, `content/`, `export/`, `revenue/`, `upload/`, `waitlist/` |
| 下划线复合 | `doctor_booking_settings/`, `leave_requests/`, `schedule_templates/` |

命名本身在 REST 语境下是合理的（复数 = 资源集合，单数 = 功能域），不需要强行统一，但应在 CLAUDE.md 中**文档化这个规则**。

#### 8. `feedbacks/` 语法问题
`feedback` 本身是不可数名词，`feedbacks/` 不符合英语语法。但由于 API 路由也用了 `/feedbacks`，改动成本较高，列为 P2 仅作记录。

#### 9. 缺少 `pyproject.toml`
项目使用 `requirements.txt` + `pytest.ini` + `alembic.ini` 的传统配置方式。现代 Python 项目推荐使用 `pyproject.toml` 统一管理。这是渐进式改进，不紧急。

#### 10. 测试目录缺少部分模块的测试
已有 75+ 测试文件，但仍有约 20 个模块没有对应的测试。这是已知的 P2 事项，不在此处重复。

---

## 整体评价 — 符合规范的方面

| 方面 | 评价 |
|------|------|
| 文件命名 snake_case | 全部符合，无 camelCase/PascalCase 文件名 |
| API 路由前缀 kebab-case | 全部一致：`/medical-records`, `/leave-requests` |
| 测试文件 `test_*.py` | 全部符合 |
| 模块标准结构 `router.py + service.py` | 大部分遵循 |
| 大模块拆分模式 `service_query.py + service_mutation.py` | 6 个模块使用，一致 |
| `__init__.py` 存在性 | 仅 `support_tickets/` 和 `infrastructure/payments/` 缺失 |
| 全局 services/ 迁移进度 | 48 个 → 2 个，几乎完成 |

---

## 行动计划

| # | 优先级 | 行动 | 成本 |
|---|--------|------|------|
| 1 | P1 | 补充 `support_tickets/__init__.py` | 0.1h |
| 2 | P1 | 补充 `infrastructure/payments/__init__.py` | 0.1h |
| 3 | P1 | 分析 `common/` vs `core/` 职责边界，写入 CLAUDE.md | 2h |
| 4 | P1 | 评估剩余 2 个全局 service 是否可迁入模块 | 1h |
| 5 | P2 | 重命名 hex hash 迁移文件为数字编号 | 0.5h |
| 6 | P2 | 在 CLAUDE.md 文档化模块命名规则（复数资源/单数功能域） | 0.5h |

## 验证

```bash
cd apps/server
python -m pytest tests/unit/test_architecture_migrated_wrappers.py -v
python -c "from app.modules.support_tickets import router"  # 验证 __init__.py
python -c "from app.infrastructure.payments import wechat_pay_service"  # 同上
```
