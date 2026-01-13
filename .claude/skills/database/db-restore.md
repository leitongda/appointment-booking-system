---
name: Database Restore
description: 从备份恢复数据库
category: database
tags: [backup, database, restore]
parameters:
  - name: input
    type: string
    required: true
    default: ""
    description: 备份文件路径
---

**用途**
从备份文件恢复数据库。

**前置条件**
- 备份文件存在
- 数据库正在运行

**参数说明**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --input | string | 是 | - | 备份文件路径（.sql 或 .sql.gz） |

**执行步骤**

1. 验证备份文件存在

2. 如果是压缩文件（.sql.gz），先解压

3. 显示警告（将覆盖当前数据库）
   - 用户确认

4. 执行恢复：
   ```bash
   psql -h localhost -U hospital -d hospital -f "$input_file"
   ```

5. 显示恢复结果

6. 可选：运行数据验证

**注意事项**
- 恢复操作不可逆，请谨慎
- 建议先备份当前数据库
- 恢复耗时取决于备份文件大小
- 生产环境需要停机维护

**示例**
```bash
# 从备份恢复
/db-restore --input ./backups/hospital_backup_20240101.sql

# 从压缩备份恢复
/db-restore --input ./backups/hospital_backup_20240101.sql.gz
```
