---
name: Database Backup
description: 备份数据库
category: database
tags: [backup, database]
parameters:
  - name: output
    type: string
    required: false
    default: "./backups"
    description: 备份输出目录
---

**用途**
创建数据库备份文件。

**前置条件**
- 数据库正在运行
- 有足够的磁盘空间
- 备份目录可写

**参数说明**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --output | string | 否 | ./backups | 备份输出目录 |

**执行步骤**

1. 创建备份目录（如果不存在）

2. 生成备份文件名（包含时间戳）：
   ```
   hospital_backup_YYYYMMDD_HHMMSS.sql
   ```

3. 执行备份：
   ```bash
   pg_dump -h localhost -U hospital -d hospital -F p -f "$output_file"
   ```

4. 压缩备份文件：
   ```bash
   gzip "$output_file"
   ```

5. 显示备份文件路径和大小

6. 验证备份文件完整性

**注意事项**
- 备份文件较大时可能需要几分钟
- 生产环境建议定期自动备份
- 备份文件请妥善保管
- 默认保留最近 7 天的备份

**示例**
```bash
# 默认备份
/db-backup

# 指定输出目录
/db-backup --output /tmp/backups

# 备份到远程服务器
/db-backup --output /mnt/backup/hospital
```
