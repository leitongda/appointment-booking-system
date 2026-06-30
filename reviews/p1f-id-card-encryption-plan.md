# P1-F: id_card 加密存储+展示脱敏方案

> 状态：待审批
> 日期：2026-06-30
> 优先级：P1（Critic🚨关键，阻塞 To-B 医院签约）

---

## 1. 问题陈述

**现状**：`Patient.id_card` 为明文 `String(18)` 存储（`models/user.py:56`），全仓库无加密列、无脱敏函数。

**风险**：
- **PIPL 合规**：身份证号属《个人信息保护法》敏感个人信息，明文存储违反"采取相应加密等安全技术措施"要求
- **To-B 签约阻塞**：正规医院采购评审（等保三级）会要求加密存储敏感字段，明文存储 = 一票否决
- **多租户泄露风险**：SaaS 场景下，租户 A 的 STORE_ADMIN 通过 list 接口可看到明文身份证
- **不可轮换**：身份证号泄露后无法像密码那样重置

**影响范围**（代码调研）：
- 模型：`Patient.id_card`（`models/user.py:56`）
- Schema：6 处暴露明文（`schemas/user.py:122,150,173,195,222,255`）
- API 返回：`patients/service_manage.py` 12 处、`patients/service_users.py` 2 处返回明文
- 前端：`admin/user/detail.tsx` 显示/编辑、`admin/settings.tsx` 黑名单搜索

---

## 2. 方案设计

### 2.1 加密策略

**应用层加密**（AES-256-GCM），不依赖数据库加密函数（pgcrypto），原因：
- 应用层加密可跨数据库迁移（SQLite 测试 / PostgreSQL 生产）
- 密钥管理独立于数据库，可配合 KMS
- 加密/解密在应用层完成，数据库只存密文

**密钥管理**：
- 配置项：`ENCRYPTION_KEY`（环境变量，32 字节 base64）
- 密钥轮换：支持 `ENCRYPTION_KEY_PREVIOUS`（旧密钥，用于解密历史数据）
- 本地开发：提供默认测试密钥（`dev-only-test-key-32bytes!!`）

### 2.2 存储设计

**方案：双列迁移**（非原地加密）

```sql
-- 新增加密列
ALTER TABLE patients ADD COLUMN id_card_encrypted BYTEA;
ALTER TABLE patients ADD COLUMN id_card_hash VARCHAR(64);  -- SHA-256 哈希，用于搜索/去重

-- 迁移：加密现有数据
-- UPDATE patients SET id_card_encrypted = encrypt(id_card), id_card_hash = sha256(id_card);

-- 最终：删除明文列
-- ALTER TABLE patients DROP COLUMN id_card;
```

**为什么双列**：
- `id_card_encrypted`：AES-256-GCM 加密后的密文，用于需要还原明文的场景（导出、详情页）
- `id_card_hash`：SHA-256 哈希，用于搜索/去重/黑名单匹配（不需要还原明文）
- 迁移期间双列并存，确保零停机

### 2.3 API 设计

**原则**：API 默认返回脱敏值，仅授权操作可获取明文

| 场景 | 返回值 | 授权要求 |
|---|---|---|
| 列表页 / 详情页 | `idCard: "110***********1234"`（脱敏） | 普通权限 |
| 搜索（黑名单/患者搜索） | 使用 `id_card_hash` 匹配 | 普通权限 |
| 导出 Excel | 明文 | `patients:export` 权限 |
| 编辑表单 | 明文（回填） | `patients:edit` 权限 |

**脱敏函数**：
```python
def mask_id_card(id_card: str | None) -> str | None:
    """身份证号脱敏：保留前3位和后4位，中间用*替换"""
    if not id_card or len(id_card) < 8:
        return id_card
    return id_card[:3] + "*" * (len(id_card) - 7) + id_card[-4:]
```

### 2.4 迁移策略

**三阶段迁移**（零停机）：

| 阶段 | 操作 | 风险 | 回滚 |
|---|---|---|---|
| 阶段 1 | 新增 `id_card_encrypted` + `id_card_hash` 列，代码双写 | 低（只加列） | 删列 |
| 阶段 2 | 迁移脚本：加密存量数据，填充新列 | 中（批量更新） | 清空新列 |
| 阶段 3 | 代码切换：读新列、删明文列 | 高（不可逆） | 需从备份恢复 |

**关键约束**：
- 阶段 3（删明文列）**不可逆**，必须在阶段 2 完成且验证后执行
- 迁移脚本需支持断点续传（147 个迁移 + 大量患者数据）
- 迁移前需备份数据库

---

## 3. 实现计划

### 阶段 1：基础设施（4h）
- [ ] 添加 `cryptography` 依赖（`requirements.txt`）
- [ ] 实现 `app/core/encryption.py`（AES-256-GCM 加密/解密/哈希/脱敏）
- [ ] 添加配置项 `ENCRYPTION_KEY` / `ENCRYPTION_KEY_PREVIOUS`
- [ ] 单元测试覆盖

### 阶段 2：模型+Schema（8h）
- [ ] 模型新增 `id_card_encrypted` + `id_card_hash` 列
- [ ] Alembic 迁移脚本（新增列）
- [ ] Schema 层：添加 `mask_id_card` 脱敏函数
- [ ] 响应 Schema 默认返回脱敏值
- [ ] 双写逻辑：保存时同时写入明文列 + 加密列 + 哈希列

### 阶段 3：API 层改造（8h）
- [ ] 列表/详情 API 返回脱敏值
- [ ] 搜索 API 改用 `id_card_hash` 匹配
- [ ] 导出 API 保持明文（需 `patients:export` 权限）
- [ ] 编辑 API 回填明文（需 `patients:edit` 权限）
- [ ] 黑名单搜索改用哈希匹配

### 阶段 4：前端适配（4h）
- [ ] admin/user/detail.tsx：编辑时回填明文，列表显示脱敏
- [ ] admin/settings.tsx：黑名单搜索改用哈希
- [ ] 患者端：不显示身份证号（或脱敏显示）

### 阶段 5：存量数据迁移（8h）
- [ ] 迁移脚本：加密存量 `id_card` → `id_card_encrypted`
- [ ] 迁移脚本：计算存量 `id_card` → `id_card_hash`
- [ ] 断点续传支持
- [ ] 数据校验：加密后解密对比

### 阶段 6：切换+清理（8h）
- [ ] 代码切换：读 `id_card_encrypted` 而非 `id_card`
- [ ] 灰度验证
- [ ] 删除明文列 `id_card`（**不可逆，需最终确认**）
- [ ] 清理双写逻辑

**总成本：约 40h**（与原估一致）

---

## 4. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 密钥泄露 | 所有加密数据可解密 | KMS 管理 + 密钥轮换 + 访问审计 |
| 迁移中断 | 部分数据未加密 | 断点续传 + 数据校验 |
| 性能影响 | 加密/解密增加延迟 | 异步加密 + 缓存脱敏值 |
| 前端兼容 | 旧版前端期望明文 | 灰度发布 + 版本检测 |

---

## 5. 审批清单

- [ ] 确认加密方案（应用层 AES-256-GCM vs 数据库层 pgcrypto）
- [ ] 确认密钥管理方式（环境变量 vs KMS）
- [ ] 确认迁移窗口（低峰期执行）
- [ ] 确认阶段 3 的"删除明文列"时机
- [ ] 确认导出权限策略（哪些角色可导出明文）

---

## 6. 已确认决策（2026-06-30）

1. **密钥管理**：✅ KMS（云厂商密钥管理服务）
2. **导出权限**：✅ 不允许导出明文（所有角色只能看脱敏值）
3. **迁移窗口**：待确认（需评估患者数据量）
4. **加密范围**：✅ phone + id_card 一起加密（一次性解决敏感数据问题）

## 7. 实施计划（更新）

### 阶段 1：基础设施（6h）
- [ ] 添加 `cryptography` 依赖
- [ ] 实现 `app/core/encryption.py`（AES-256-GCM 加密/解密/哈希/脱敏）
- [ ] KMS 集成模块（支持阿里云 KMS / 腾讯云 KMS）
- [ ] 添加配置项 `KMS_KEY_ID` / `ENCRYPTION_KEY`（本地开发 fallback）
- [ ] 单元测试覆盖

### 阶段 2：模型+Schema（12h）
- [ ] 模型新增 `id_card_encrypted` + `id_card_hash` + `phone_encrypted` + `phone_hash` 列
- [ ] Alembic 迁移脚本（新增列）
- [ ] Schema 层：添加 `mask_id_card` / `mask_phone` 脱敏函数
- [ ] 响应 Schema 默认返回脱敏值
- [ ] 双写逻辑：保存时同时写入明文列 + 加密列 + 哈希列

### 阶段 3：API 层改造（8h）
- [ ] 列表/详情 API 返回脱敏值（id_card 前3后4，phone 前3后4）
- [ ] 搜索 API 改用哈希匹配
- [ ] 导出 API 返回脱敏值（不允许明文导出）
- [ ] 编辑 API 回填脱敏值（不回填明文）
- [ ] 黑名单搜索改用哈希匹配

### 阶段 4：前端适配（4h）
- [ ] admin/user/detail.tsx：编辑时显示脱敏值，提示用户重新输入
- [ ] admin/settings.tsx：黑名单搜索改用哈希
- [ ] 患者端：不显示身份证号/手机号（或脱敏显示）

### 阶段 5：存量数据迁移（12h）
- [ ] 迁移脚本：加密存量 `id_card` → `id_card_encrypted` + `id_card_hash`
- [ ] 迁移脚本：加密存量 `phone` → `phone_encrypted` + `phone_hash`
- [ ] 断点续传支持
- [ ] 数据校验：加密后解密对比

### 阶段 6：切换+清理（8h）
- [ ] 代码切换：读加密列而非明文列
- [ ] 灰度验证
- [ ] 删除明文列（**不可逆，需最终确认**）
- [ ] 清理双写逻辑

**总成本：约 50h**（比原估 40h 多 10h，因增加 phone 加密 + KMS 集成）
