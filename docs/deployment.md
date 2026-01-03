# 医院挂号系统部署指南

本文档介绍如何在 CentOS/Rocky Linux 服务器上手动部署医院挂号系统。

## 目录

- [架构概览](#架构概览)
- [访问路径规划](#访问路径规划)
- [服务器环境准备](#1-服务器环境准备)
- [部署后端服务](#2-部署后端服务)
- [构建前端应用](#3-构建前端应用)
- [配置 Nginx](#4-配置-nginx)
- [验证部署](#5-验证部署)
- [常用运维命令](#6-常用运维命令)

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              yy.xxx.com 服务器                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     Nginx 反向代理 (443/80)                          │    │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐   │    │
│  │  │    /     │  │  /patient/   │  │   /doctor/   │  │  /api/v1/  │   │    │
│  │  │  Admin   │  │  Patient H5  │  │    Doctor    │  │  FastAPI   │   │    │
│  │  └──────────┘  └──────────────┘  └──────────────┘  └────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         后端服务                                      │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │    │
│  │  │   FastAPI    │  │ Celery Worker│  │ Celery Beat  │               │    │
│  │  │  (端口 8000) │  │  (异步任务)   │  │  (定时任务)   │               │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         依赖服务                                      │    │
│  │  ┌──────────────────────┐     ┌──────────────────────┐              │    │
│  │  │     PostgreSQL 16     │     │       Redis 7        │              │    │
│  │  │      (端口 5432)      │     │     (端口 6379)       │              │    │
│  │  └──────────────────────┘     └──────────────────────┘              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 访问路径规划

| 应用 | 访问地址 | 说明 |
|------|----------|------|
| Admin 管理后台 | `https://yy.xxx.com/` | 机构端后台管理 |
| Patient 患者端 | `https://yy.xxx.com/patient/` | 患者 H5 页面 |
| Doctor 医生端 | `https://yy.xxx.com/doctor/` | 医生工作台 |
| API 接口 | `https://yy.xxx.com/api/v1/` | 后端 REST API |
| API 文档 | `https://yy.xxx.com/docs` | Swagger 文档 |

---

## 1. 服务器环境准备

### 1.1 系统要求

- **操作系统**: CentOS 8+ / Rocky Linux 8+ / RHEL 8+
- **内存**: 最低 4GB，建议 8GB+
- **磁盘**: 最低 40GB
- **CPU**: 2 核+

### 1.2 安装基础依赖

```bash
# 更新系统
sudo dnf update -y

# 安装基础工具
sudo dnf install -y git curl wget vim gcc make openssl-devel bzip2-devel libffi-devel
```

### 1.3 安装 Python 3.12

```bash
# CentOS 8+ 使用 dnf 安装
sudo dnf install -y python3.12 python3.12-pip python3.12-devel

# 如果仓库没有 Python 3.12，可以从源码编译：
# cd /usr/src
# sudo wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz
# sudo tar xzf Python-3.12.0.tgz
# cd Python-3.12.0
# sudo ./configure --enable-optimizations
# sudo make altinstall
```

### 1.4 安装 Node.js 20

```bash
# 通过 NodeSource 安装
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo dnf install -y nodejs

# 验证安装
node --version  # 应显示 v20.x.x
npm --version

# 安装 pnpm
npm install -g pnpm
```

### 1.5 安装 PostgreSQL 16

```bash
# 添加 PostgreSQL 官方仓库
sudo dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm

# 禁用内置 PostgreSQL 模块
sudo dnf -qy module disable postgresql

# 安装 PostgreSQL 16
sudo dnf install -y postgresql16-server postgresql16

# 初始化数据库
sudo /usr/pgsql-16/bin/postgresql-16-setup initdb

# 启动并设置开机自启
sudo systemctl enable postgresql-16
sudo systemctl start postgresql-16

# 创建数据库和用户
sudo -u postgres psql << EOF
CREATE USER hospital WITH PASSWORD 'your_secure_password';
CREATE DATABASE hospital_booking OWNER hospital;
GRANT ALL PRIVILEGES ON DATABASE hospital_booking TO hospital;
EOF
```

配置 PostgreSQL 允许密码认证，编辑 `/var/lib/pgsql/16/data/pg_hba.conf`:

```
# 将 ident 改为 md5
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
```

重启 PostgreSQL：

```bash
sudo systemctl restart postgresql-16
```

### 1.6 安装 Redis 7

```bash
# 安装 Redis
sudo dnf install -y redis

# 启动并设置开机自启
sudo systemctl enable redis
sudo systemctl start redis

# 验证
redis-cli ping  # 应返回 PONG
```

### 1.7 安装 Nginx

```bash
sudo dnf install -y nginx
sudo systemctl enable nginx
```

---

## 2. 部署后端服务

### 2.1 克隆代码

```bash
# 创建应用目录
sudo mkdir -p /opt/hospital
sudo chown $USER:$USER /opt/hospital
cd /opt/hospital

# 克隆代码（替换为您的仓库地址）
git clone https://github.com/your-org/appointment-booking-system.git .
```

### 2.2 配置 Python 虚拟环境

```bash
cd /opt/hospital/apps/server

# 创建虚拟环境
python3.12 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.3 配置环境变量

创建 `/opt/hospital/apps/server/.env` 文件：

```bash
cat > /opt/hospital/apps/server/.env << 'EOF'
# 数据库配置
DATABASE_URL=postgresql+asyncpg://hospital:your_secure_password@localhost:5432/hospital_booking

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# 安全配置（生产环境必须修改）
SECRET_KEY=your-very-secure-secret-key-change-this-in-production

# 运行环境
DEBUG=false
ENVIRONMENT=production

# 存储配置
STORAGE_TYPE=local
LOCAL_UPLOAD_DIR=/opt/hospital/apps/server/uploads

# CORS 配置
CORS_ORIGINS=https://yy.xxx.com

# 日志配置
LOG_LEVEL=INFO
EOF
```

> ⚠️ **重要提示**: 
> - `SECRET_KEY` 必须使用强随机字符串，可用 `openssl rand -hex 32` 生成
> - 数据库密码请使用安全的强密码

### 2.4 数据库迁移

```bash
cd /opt/hospital/apps/server
source venv/bin/activate

# 执行数据库迁移
alembic upgrade head

# 初始化管理员账号（如果有初始化脚本）
python scripts/init_admin.py
```

### 2.5 创建 Systemd 服务

#### FastAPI 服务

创建 `/etc/systemd/system/hospital-api.service`:

```ini
[Unit]
Description=Hospital API Service
After=network.target postgresql-16.service redis.service
Wants=postgresql-16.service redis.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/hospital/apps/server
Environment="PATH=/opt/hospital/apps/server/venv/bin"
EnvironmentFile=/opt/hospital/apps/server/.env
ExecStart=/opt/hospital/apps/server/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### Celery Worker 服务

创建 `/etc/systemd/system/hospital-celery.service`:

```ini
[Unit]
Description=Hospital Celery Worker
After=network.target redis.service
Wants=redis.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/hospital/apps/server
Environment="PATH=/opt/hospital/apps/server/venv/bin"
EnvironmentFile=/opt/hospital/apps/server/.env
ExecStart=/opt/hospital/apps/server/venv/bin/celery -A app.celery_app worker -l info -c 4 -Q default,scheduled,notification
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### Celery Beat 服务

创建 `/etc/systemd/system/hospital-celery-beat.service`:

```ini
[Unit]
Description=Hospital Celery Beat Scheduler
After=network.target redis.service hospital-celery.service
Wants=redis.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/hospital/apps/server
Environment="PATH=/opt/hospital/apps/server/venv/bin"
EnvironmentFile=/opt/hospital/apps/server/.env
ExecStart=/opt/hospital/apps/server/venv/bin/celery -A app.celery_app beat -l info --pidfile=/tmp/celerybeat.pid
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### 启动服务

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启用服务开机自启
sudo systemctl enable hospital-api hospital-celery hospital-celery-beat

# 启动服务
sudo systemctl start hospital-api
sudo systemctl start hospital-celery
sudo systemctl start hospital-celery-beat

# 检查服务状态
sudo systemctl status hospital-api
sudo systemctl status hospital-celery
sudo systemctl status hospital-celery-beat
```

---

## 3. 构建前端应用

### 3.1 修改前端配置

由于三个前端应用部署在不同路径，需要修改配置：

#### Admin（根路径 `/`）

Admin 部署在根路径，无需修改 base 配置。

#### Patient-H5（路径 `/patient/`）

编辑 `apps/patient-h5/.umirc.ts` 或对应配置文件，添加：

```typescript
export default {
  // ... 其他配置
  base: '/patient/',
  publicPath: '/patient/',
};
```

#### Doctor（路径 `/doctor/`）

编辑 `apps/doctor/.umirc.ts` 或对应配置文件，添加：

```typescript
export default {
  // ... 其他配置
  base: '/doctor/',
  publicPath: '/doctor/',
};
```

### 3.2 构建前端

```bash
cd /opt/hospital

# 安装依赖
pnpm install

# 构建共享包
pnpm --filter @hospital/shared build
pnpm --filter @hospital/api build

# 构建各前端应用
pnpm --filter @hospital/admin build
pnpm --filter @hospital/patient-h5 build
pnpm --filter @hospital/doctor build
```

### 3.3 部署静态文件

```bash
# 创建静态文件目录
sudo mkdir -p /var/www/hospital/{admin,patient,doctor}

# 复制构建产物
sudo cp -r /opt/hospital/apps/admin/dist/* /var/www/hospital/admin/
sudo cp -r /opt/hospital/apps/patient-h5/dist/* /var/www/hospital/patient/
sudo cp -r /opt/hospital/apps/doctor/dist/* /var/www/hospital/doctor/

# 设置权限
sudo chown -R nginx:nginx /var/www/hospital
```

---

## 4. 配置 Nginx

### 4.1 上传 SSL 证书

```bash
# 创建证书目录
sudo mkdir -p /etc/nginx/ssl

# 上传您的 SSL 证书文件到服务器
# - 证书文件: /etc/nginx/ssl/yy.xxx.com.crt
# - 私钥文件: /etc/nginx/ssl/yy.xxx.com.key

# 设置证书文件权限
sudo chmod 600 /etc/nginx/ssl/yy.xxx.com.key
sudo chmod 644 /etc/nginx/ssl/yy.xxx.com.crt
```

### 4.2 创建 Nginx 配置

创建 `/etc/nginx/conf.d/hospital.conf`:

```nginx
# HTTP 重定向到 HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yy.xxx.com;
    
    # Let's Encrypt 验证路径（如需要）
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # 其他请求重定向到 HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS 主配置
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yy.xxx.com;

    # SSL 证书配置
    ssl_certificate /etc/nginx/ssl/yy.xxx.com.crt;
    ssl_certificate_key /etc/nginx/ssl/yy.xxx.com.key;
    
    # SSL 安全配置
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    # 上传文件大小限制
    client_max_body_size 50M;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/x-javascript application/xml application/json;

    # ============================================
    # Admin 管理后台 - 根路径
    # ============================================
    location / {
        root /var/www/hospital/admin;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # ============================================
    # Patient 患者端 - /patient/ 路径
    # ============================================
    location /patient/ {
        alias /var/www/hospital/patient/;
        index index.html;
        try_files $uri $uri/ /patient/index.html;
    }

    # ============================================
    # Doctor 医生端 - /doctor/ 路径
    # ============================================
    location /doctor/ {
        alias /var/www/hospital/doctor/;
        index index.html;
        try_files $uri $uri/ /doctor/index.html;
    }

    # ============================================
    # API 代理 - 转发到 FastAPI 后端
    # ============================================
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # ============================================
    # Swagger 文档
    # ============================================
    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    location /redoc {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # ============================================
    # 上传文件访问
    # ============================================
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # 静态文件缓存
        expires 7d;
        add_header Cache-Control "public";
    }

    # ============================================
    # 静态资源缓存配置
    # ============================================
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # ============================================
    # 安全头配置
    # ============================================
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

### 4.3 测试并启动 Nginx

```bash
# 测试配置语法
sudo nginx -t

# 如果测试通过，启动 Nginx
sudo systemctl start nginx

# 查看状态
sudo systemctl status nginx
```

### 4.4 配置防火墙

```bash
# 开放 HTTP 和 HTTPS 端口
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## 5. 验证部署

### 5.1 服务状态检查

```bash
# 检查所有服务状态
echo "=== PostgreSQL ===" && sudo systemctl status postgresql-16 --no-pager
echo "=== Redis ===" && sudo systemctl status redis --no-pager
echo "=== Hospital API ===" && sudo systemctl status hospital-api --no-pager
echo "=== Hospital Celery ===" && sudo systemctl status hospital-celery --no-pager
echo "=== Hospital Celery Beat ===" && sudo systemctl status hospital-celery-beat --no-pager
echo "=== Nginx ===" && sudo systemctl status nginx --no-pager
```

### 5.2 端口检查

```bash
# 检查端口监听
ss -tlnp | grep -E '(5432|6379|8000|80|443)'
```

### 5.3 API 健康检查

```bash
# 本地测试 API
curl http://127.0.0.1:8000/api/v1/health

# 通过域名测试
curl https://yy.xxx.com/api/v1/health
```

### 5.4 页面访问测试

| 测试项 | 地址 |
|--------|------|
| Admin 管理后台 | `https://yy.xxx.com/` |
| Patient 患者端 | `https://yy.xxx.com/patient/` |
| Doctor 医生端 | `https://yy.xxx.com/doctor/` |
| API 文档 | `https://yy.xxx.com/docs` |

---

## 6. 常用运维命令

### 6.1 日志查看

```bash
# 查看 API 服务日志
sudo journalctl -u hospital-api -f

# 查看 Celery Worker 日志
sudo journalctl -u hospital-celery -f

# 查看 Celery Beat 日志
sudo journalctl -u hospital-celery-beat -f

# 查看 Nginx 访问日志
sudo tail -f /var/log/nginx/access.log

# 查看 Nginx 错误日志
sudo tail -f /var/log/nginx/error.log

# 查看应用日志
tail -f /opt/hospital/apps/server/logs/hospital.log
```

### 6.2 服务管理

```bash
# 重启服务
sudo systemctl restart hospital-api
sudo systemctl restart hospital-celery
sudo systemctl restart hospital-celery-beat
sudo systemctl restart nginx

# 停止服务
sudo systemctl stop hospital-api

# 启动服务
sudo systemctl start hospital-api

# 查看服务状态
sudo systemctl status hospital-api
```

### 6.3 代码更新部署

```bash
#!/bin/bash
# 更新脚本 /opt/hospital/deploy.sh

cd /opt/hospital

# 拉取最新代码
git pull origin main

# 更新后端依赖
cd apps/server
source venv/bin/activate
pip install -r requirements.txt

# 执行数据库迁移
alembic upgrade head

# 重启后端服务
sudo systemctl restart hospital-api hospital-celery hospital-celery-beat

# 返回项目根目录
cd /opt/hospital

# 更新前端依赖并构建
pnpm install
pnpm --filter @hospital/admin build
pnpm --filter @hospital/patient-h5 build
pnpm --filter @hospital/doctor build

# 部署前端静态文件
sudo cp -r apps/admin/dist/* /var/www/hospital/admin/
sudo cp -r apps/patient-h5/dist/* /var/www/hospital/patient/
sudo cp -r apps/doctor/dist/* /var/www/hospital/doctor/

# 重新加载 Nginx
sudo nginx -s reload

echo "部署完成!"
```

### 6.4 数据库备份

```bash
# 备份数据库
pg_dump -U hospital -h localhost hospital_booking > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复数据库
psql -U hospital -h localhost hospital_booking < backup_file.sql
```

### 6.5 Redis 管理

```bash
# 连接 Redis
redis-cli

# 查看所有键
redis-cli KEYS "*"

# 清空缓存（谨慎使用）
redis-cli FLUSHALL
```

---

## 7. 故障排查

### 7.1 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 502 Bad Gateway | 后端服务未启动 | `sudo systemctl start hospital-api` |
| 数据库连接失败 | PostgreSQL 未启动或密码错误 | 检查服务状态和 `.env` 配置 |
| 静态资源 404 | 前端未构建或路径错误 | 重新构建并检查 Nginx 配置 |
| API 跨域错误 | CORS 配置错误 | 检查 `.env` 中的 `CORS_ORIGINS` |
| 上传失败 | 文件大小限制 | 检查 Nginx `client_max_body_size` |

### 7.2 调试命令

```bash
# 检查 Nginx 配置语法
sudo nginx -t

# 查看端口占用
sudo lsof -i :8000
sudo lsof -i :80
sudo lsof -i :443

# 测试数据库连接
psql -U hospital -h localhost -d hospital_booking -c "SELECT 1;"

# 测试 Redis 连接
redis-cli ping
```

---

## 8. 安全建议

1. **修改默认密码**: 确保数据库密码、SECRET_KEY 使用强随机字符串
2. **防火墙配置**: 只开放必要端口（80、443），数据库和 Redis 端口不对外开放
3. **定期备份**: 配置定时任务定期备份数据库
4. **日志监控**: 配置日志轮转，避免日志文件过大
5. **SSL 证书更新**: 设置证书到期提醒，及时更新证书
6. **系统更新**: 定期更新系统和依赖包的安全补丁

---

## 附录：Docker Compose 部署（可选）

如果您更倾向于使用 Docker 部署，项目已包含 `docker-compose.yml` 配置，请参考：

```bash
# 启动所有服务
docker-compose --profile production up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

详细 Docker 部署说明请参考项目根目录的 [docker-compose.yml](../docker-compose.yml)。

