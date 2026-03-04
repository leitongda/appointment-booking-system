# 规则组权限控制验证清单

## 后端 API 权限验证

### 文件位置
`/Users/leijiadashao/leitond/appointment-booking-system/apps/server/app/api/v1/rule_sets.py`

### 验证方法
运行以下 Python 代码片段验证 API 权限配置：

```python
from app.api.v1.rule_sets import router
from app.api.deps import get_current_admin, get_current_super_admin

# 打印所有路由及其权限依赖
for route in router.routes:
    if hasattr(route, 'methods') and hasattr(route, 'dependencies'):
        deps = []
        for dep in route.dependencies:
            if dep.dependency == get_current_admin:
                deps.append("get_current_admin (普通管理员)")
            elif dep.dependency == get_current_super_admin:
                deps.append("get_current_super_admin (超级管理员)")

        if deps:
            print(f"{route.methods} {route.path}: {', '.join(deps)}")
```

### 预期结果

#### 查询操作（普通管理员可访问）
- `GET /api/v1/rule-sets`: get_current_admin
- `GET /api/v1/rule-sets/{rule_set_id}`: get_current_admin
- `POST /api/v1/rule-sets/preview`: get_current_admin

#### 修改操作（仅超级管理员可访问）
- `POST /api/v1/rule-sets`: get_current_super_admin
- `PUT /api/v1/rule-sets/{rule_set_id}`: get_current_super_admin
- `DELETE /api/v1/rule-sets/{rule_set_id}`: get_current_super_admin
- `POST /api/v1/rule-sets/{rule_set_id}/enable`: get_current_super_admin
- `POST /api/v1/rule-sets/{rule_set_id}/disable`: get_current_super_admin
- `POST /api/v1/rule-sets/{rule_set_id}/windows`: get_current_super_admin
- `PUT /api/v1/rule-sets/windows/{window_id}`: get_current_super_admin
- `DELETE /api/v1/rule-sets/windows/{window_id}`: get_current_super_admin
- `PUT /api/v1/rule-sets/{rule_set_id}/booking-policy`: get_current_super_admin
- `PUT /api/v1/rule-sets/{rule_set_id}/checkin-policy`: get_current_super_admin
- `PUT /api/v1/rule-sets/{rule_set_id}/capacity-policy`: get_current_super_admin

## 前端权限控制验证

### 文件位置
`/Users/leijiadashao/leitond/appointment-booking-system/apps/admin/src/pages/system/components/RuleSetTableColumns.tsx`

### 验证方法
1. 登录普通管理员账号
2. 访问规则组列表页面 `/system/rule-sets`
3. 检查操作列中的按钮状态

### 预期结果（普通管理员）
- "查看" 链接：正常显示且可点击
- "编辑" 链接：灰色显示，不可点击
- "启用/禁用" 链接：灰色显示，不可点击
- "删除" 链接：不显示

### 预期结果（超级管理员）
- "查看" 链接：正常显示且可点击
- "编辑" 链接：正常显示且可点击
- "启用/禁用" 链接：正常显示且可点击
- "删除" 链接：正常显示且可点击

## API 手动测试

### 测试工具
使用 Postman 或 curl 进行 API 测试

### 测试步骤
1. 使用超级管理员账号登录，获取 token
2. 使用普通管理员账号登录，获取 token
3. 分别使用两个 token 测试各 API 端点

### 测试用例

#### 1. 创建规则组
```bash
# 超级管理员 - 应该成功
curl -X POST http://localhost:8000/api/v1/rule-sets \
  -H "Authorization: Bearer <SUPER_ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "测试规则组", "enabled": true, "priority": 100}'

# 普通管理员 - 应该返回 403 Forbidden
curl -X POST http://localhost:8000/api/v1/rule-sets \
  -H "Authorization: Bearer <STORE_ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "测试规则组", "enabled": true, "priority": 100}'
```

#### 2. 查询规则组列表
```bash
# 普通管理员 - 应该成功
curl -X GET http://localhost:8000/api/v1/rule-sets \
  -H "Authorization: Bearer <STORE_ADMIN_TOKEN>"

# 超级管理员 - 应该成功
curl -X GET http://localhost:8000/api/v1/rule-sets \
  -H "Authorization: Bearer <SUPER_ADMIN_TOKEN>"
```

#### 3. 更新规则组
```bash
# 超级管理员 - 应该成功
curl -X PUT http://localhost:8000/api/v1/rule-sets/{rule_set_id} \
  -H "Authorization: Bearer <SUPER_ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "更新后的规则组"}'

# 普通管理员 - 应该返回 403 Forbidden
curl -X PUT http://localhost:8000/api/v1/rule-sets/{rule_set_id} \
  -H "Authorization: Bearer <STORE_ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "更新后的规则组"}'
```

#### 4. 删除规则组
```bash
# 超级管理员 - 应该成功
curl -X DELETE http://localhost:8000/api/v1/rule-sets/{rule_set_id} \
  -H "Authorization: Bearer <SUPER_ADMIN_TOKEN>"

# 普通管理员 - 应该返回 403 Forbidden
curl -X DELETE http://localhost:8000/api/v1/rule-sets/{rule_set_id} \
  -H "Authorization: Bearer <STORE_ADMIN_TOKEN>"
```

#### 5. 启用/禁用规则组
```bash
# 超级管理员 - 应该成功
curl -X POST http://localhost:8000/api/v1/rule-sets/{rule_set_id}/enable \
  -H "Authorization: Bearer <SUPER_ADMIN_TOKEN>"

# 普通管理员 - 应该返回 403 Forbidden
curl -X POST http://localhost:8000/api/v1/rule-sets/{rule_set_id}/enable \
  -H "Authorization: Bearer <STORE_ADMIN_TOKEN>"
```

## 安全性验证

### 检查点
1. 后端 API 不依赖前端权限控制
2. 即使前端绕过限制，后端仍会拒绝请求
3. 错误消息不泄露敏感信息
4. 普通管理员无法通过修改请求头来获得超级管理员权限

### 验证方法
使用普通管理员 token，尝试通过修改请求头或请求体来绕过权限检查

```bash
# 尝试模拟超级管理员（应该失败）
curl -X POST http://localhost:8000/api/v1/rule-sets \
  -H "Authorization: Bearer <STORE_ADMIN_TOKEN>" \
  -H "X-Role: SUPER_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"name": "测试规则组", "enabled": true}'
```

## 完成标准
- [x] 后端所有修改操作都使用 `get_current_super_admin`
- [x] 后端所有查询操作都使用 `get_current_admin`
- [x] 前端编辑/启用/禁用按钮根据 `canSuperAdmin` 控制显示
- [x] 前端删除按钮仅对超级管理员显示
- [x] 前端普通管理员看到的操作按钮灰显且不可点击
- [x] 前端新增按钮仅对超级管理员显示
