---
name: Cache Clear
description: 清空 Redis 缓存
category: system
tags: [cache, redis]
parameters:
  - name: pattern
    type: string
    required: false
    default: "*"
    description: 键名模式
---

**用途**
清空 Redis 缓存，支持按模式匹配删除。

**前置条件**
- Redis 正在运行

**参数说明**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --pattern | string | 否 | * | 键名模式（支持通配符） |

**执行步骤**

1. 检查 Redis 连接

2. 如果 pattern=*：
   - 显示警告（将清空所有缓存）
   - 用户确认
   - 执行 `FLUSHDB`

3. 如果 pattern 是其他模式：
   - 查找匹配的键
   - 显示匹配的键数量
   - 用户确认
   - 批量删除匹配的键

4. 显示删除的键数量

5. 显示当前 Redis 内存使用情况

**注意事项**
- 清空缓存可能导致性能暂时下降
- 生产环境谨慎使用
- 建议在维护时段执行

**示例**
```bash
# 清空所有缓存
/cache-clear

# 清空特定模式的缓存
/cache-clear --pattern "user:*"

# 清空会话缓存
/cache-clear --pattern "session:*"
```
