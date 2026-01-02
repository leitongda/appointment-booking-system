# 宝塔面板 + Docker 混合部署指南

本文档介绍如何在安装了宝塔面板的服务器上，使用混合方式部署医院挂号系统。

## 目录

- [架构说明](#架构说明)
- [前置条件](#前置条件)
- [第一部分：服务器环境准备](#第一部分服务器环境准备)
- [第二部分：拉取代码](#第二部分拉取代码)
- [第三部分：配置数据库和 Redis](#第三部分配置数据库和-redis)
- [第四部分：配置 Docker](#第四部分配置-docker)
- [第五部分：启动后端服务](#第五部分启动后端服务)
- [第六部分：部署前端](#第六部分部署前端)
- [第七部分：配置 Nginx](#第七部分配置-nginx)
- [常用运维命令](#常用运维命令)
- [常见问题](#常见问题)

---

## 架构说明

采用混合部署方式：

| 组件 | 部署方式 | 说明 |
|------|----------|------|
| PostgreSQL | 宝塔安装 | 数据更稳定，管理方便 |
| Redis | 宝塔安装 | 一键安装，有图形界面 |
| 后端 API | Docker | 环境隔离，更新方便 |
| Celery Worker | Docker | 异步任务处理 |
| Celery Beat | Docker | 定时任务调度 |
| 前端静态文件 | 宝塔 Nginx | 静态托管，性能最好 |

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              服务器                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     Nginx (宝塔管理)                              │    │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │    │
│  │  │    /     │  │  /patient/   │  │   /doctor/   │  │  /api/   │ │    │
│  │  │  Admin   │  │  Patient H5  │  │    Doctor    │  │ → :8000  │ │    │
│  │  └──────────┘  └──────────────┘  └──────────────┘  └──────────┘ │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                      │                                   │
│                                      ▼                                   │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      Docker 容器                                  │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │    │
│  │  │   FastAPI    │  │ Celery Worker│  │ Celery Beat  │           │    │
│  │  │  (端口 8000) │  │  (异步任务)   │  │  (定时任务)   │           │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                      │                                   │
│                                      ▼                                   │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      宝塔安装的服务                                │    │
│  │  ┌──────────────────────┐     ┌──────────────────────┐          │    │
│  │  │     PostgreSQL 16     │     │       Redis 7        │          │    │
│  │  │      (端口 5432)      │     │     (端口 6379)       │          │    │
│  │  └──────────────────────┘     └──────────────────────┘          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 前置条件

- 服务器已安装宝塔面板
- 代码托管在 GitHub（私有仓库）
- 本地电脑可以构建前端项目

---

## 第一部分：服务器环境准备

### 1.1 登录服务器

通过宝塔面板的「终端」或 SSH 工具连接：

```bash
ssh root@你的服务器IP
```

### 1.2 在宝塔面板安装必要软件

登录宝塔面板（通常是 `http://服务器IP:8888`），在 **软件商店** 中安装：

1. **Docker管理器** - 用于运行后端容器
2. **PostgreSQL 16** - 主数据库
3. **Redis** - 缓存和消息队列
4. **Nginx** - Web 服务器（通常已预装）

### 1.3 安装 Git

```bash
# CentOS
yum install -y git

# Ubuntu
apt install -y git

# 验证安装
git --version
```

### 1.4 安装 Docker Compose

```bash
# 检查是否已安装
docker-compose --version

# 如果没有安装，执行：
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 验证安装
docker-compose --version
```

---

## 第二部分：拉取代码

### 2.1 生成 GitHub Personal Access Token（私有仓库需要）

1. 打开 GitHub → 右上角头像 → **Settings**
2. 左侧滚动到最下面 → **Developer settings**
3. **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**
4. 填写信息：
   - Note: `server-deploy`
   - Expiration: 选择有效期
   - 勾选权限: ✅ `repo`
5. 点击 **Generate token**
6. ⚠️ **立即复制 Token**（只显示一次！）

### 2.2 克隆代码到服务器

```bash
# 进入网站目录
cd /www/wwwroot

# 克隆私有仓库（替换为你的信息）
git clone https://你的GitHub用户名:你的Token@github.com/你的GitHub用户名/appointment-booking-system.git

# 进入项目目录
cd appointment-booking-system

# 保存认证信息（避免每次输入）
git config credential.helper store
```

### 2.3 后续更新代码

```bash
cd /www/wwwroot/appointment-booking-system
git pull origin main
```

---

## 第三部分：配置数据库和 Redis

### 3.1 创建 PostgreSQL 数据库

#### 方法一：通过宝塔面板（推荐）

1. 宝塔面板 → **数据库**
2. 点击 **添加数据库**
3. 填写：
   - 数据库名：`hospital_booking`
   - 用户名：`hospital`
   - 密码：设置一个强密码（**记住它！**）

#### 方法二：通过命令行

```bash
# 找到 psql 命令路径
PSQL_PATH=$(find /www -name "psql" -type f 2>/dev/null | head -1)

# 创建用户和数据库
sudo -u postgres $PSQL_PATH -c "CREATE USER hospital WITH PASSWORD '你的密码';"
sudo -u postgres $PSQL_PATH -c "CREATE DATABASE hospital_booking OWNER hospital;"
sudo -u postgres $PSQL_PATH -c "GRANT ALL PRIVILEGES ON DATABASE hospital_booking TO hospital;"
```

### 3.2 配置 PostgreSQL 允许 Docker 连接

找到并编辑 `pg_hba.conf`：

```bash
# 查找配置文件
find /www -name "pg_hba.conf" 2>/dev/null

# 编辑文件（路径根据实际情况）
vim /www/server/pgsql/data/pg_hba.conf
```

在文件末尾添加一行：

```
host    all    all    172.0.0.0/8    md5
```

保存并退出：按 `Esc`，输入 `:wq`，按回车。

重启 PostgreSQL（在宝塔面板 → 软件商店 → PostgreSQL → 重启）。

### 3.3 配置 Redis 允许 Docker 连接

编辑 Redis 配置：

```bash
vim /www/server/redis/redis.conf
```

找到 `bind 127.0.0.1`，修改为：

```
bind 0.0.0.0
```

保存并退出：按 `Esc`，输入 `:wq`，按回车。

重启 Redis：

```bash
systemctl restart redis
```

---

## 第四部分：配置 Docker

### 4.1 创建 docker-compose.yml

```bash
cd /www/wwwroot/appointment-booking-system

# 备份原文件
cp docker-compose.yml docker-compose.yml.bak

# 创建新的配置文件
cat > docker-compose.yml << 'EOF'
services:
  # FastAPI 后端
  backend:
    build:
      context: ./apps/server
      dockerfile: Dockerfile
    container_name: hospital_backend
    restart: always
    environment:
      - DATABASE_URL=postgresql+asyncpg://hospital:你的数据库密码@host.docker.internal:5432/hospital_booking
      - REDIS_URL=redis://host.docker.internal:6379/0
      - SECRET_KEY=你的密钥
      - DEBUG=false
      - ENVIRONMENT=production
    ports:
      - "8000:8000"
    extra_hosts:
      - "host.docker.internal:host-gateway"

  # Celery Worker - 处理异步任务
  celery_worker:
    build:
      context: ./apps/server
      dockerfile: Dockerfile
    container_name: hospital_celery_worker
    restart: always
    environment:
      - DATABASE_URL=postgresql+asyncpg://hospital:你的数据库密码@host.docker.internal:5432/hospital_booking
      - REDIS_URL=redis://host.docker.internal:6379/0
      - SECRET_KEY=你的密钥
    command: celery -A app.celery_app worker -l info -c 4 -Q default,scheduled,notification
    extra_hosts:
      - "host.docker.internal:host-gateway"

  # Celery Beat - 定时任务调度
  celery_beat:
    build:
      context: ./apps/server
      dockerfile: Dockerfile
    container_name: hospital_celery_beat
    restart: always
    environment:
      - DATABASE_URL=postgresql+asyncpg://hospital:你的数据库密码@host.docker.internal:5432/hospital_booking
      - REDIS_URL=redis://host.docker.internal:6379/0
      - SECRET_KEY=你的密钥
    command: celery -A app.celery_app beat -l info --pidfile=/tmp/celerybeat.pid
    extra_hosts:
      - "host.docker.internal:host-gateway"
EOF
```

### 4.2 修改配置中的敏感信息

编辑 docker-compose.yml，替换以下内容：

- `你的数据库密码` → 改成实际的数据库密码
- `你的密钥` → 生成一个随机密钥：

```bash
# 生成随机密钥
openssl rand -hex 32
```

---

## 第五部分：启动后端服务

### 5.1 启动 Docker 容器

```bash
cd /www/wwwroot/appointment-booking-system

# 启动服务（首次会构建镜像，需要几分钟）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
```

### 5.2 初始化数据库

```bash
# 执行数据库迁移
docker-compose exec backend alembic upgrade head

# 初始化管理员账号（如果有此脚本）
docker-compose exec backend python scripts/init_admin.py
```

### 5.3 验证后端

```bash
# 测试 API
curl http://127.0.0.1:8000/api/v1/health

# 访问 Swagger 文档
# 浏览器打开：http://服务器IP:8000/docs
```

---

## 第六部分：部署前端

前端需要在本地电脑构建后上传到服务器。

### 6.1 在本地电脑构建前端

```bash
# 进入项目目录
cd /path/to/appointment-booking-system

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

### 6.2 打包并上传到服务器

```bash
# 打包构建产物
tar -czvf frontend-dist.tar.gz \
  apps/admin/dist \
  apps/patient-h5/dist \
  apps/doctor/dist

# 上传到服务器
scp frontend-dist.tar.gz root@服务器IP:/www/wwwroot/appointment-booking-system/
```

### 6.3 在服务器解压并部署

```bash
cd /www/wwwroot/appointment-booking-system

# 解压
tar -xzvf frontend-dist.tar.gz

# 创建前端目录
mkdir -p /www/wwwroot/hospital-web/{admin,patient,doctor}

# 复制文件
cp -r apps/admin/dist/* /www/wwwroot/hospital-web/admin/
cp -r apps/patient-h5/dist/* /www/wwwroot/hospital-web/patient/
cp -r apps/doctor/dist/* /www/wwwroot/hospital-web/doctor/

# 设置权限
chown -R www:www /www/wwwroot/hospital-web
```

---

## 第七部分：配置 Nginx

### 7.1 在宝塔创建站点

1. 宝塔面板 → **网站** → **添加站点**
2. 填写你的域名（如 `yy.xxx.com`）
3. 网站目录设为 `/www/wwwroot/hospital-web/admin`

### 7.2 修改 Nginx 配置

点击站点的 **设置** → **配置文件**，替换为以下内容：

```nginx
server {
    listen 80;
    listen 443 ssl http2;
    server_name yy.xxx.com;  # 替换为你的域名

    # SSL 证书配置（通过宝塔申请 Let's Encrypt）
    # ssl_certificate    /www/server/panel/vhost/cert/yy.xxx.com/fullchain.pem;
    # ssl_certificate_key    /www/server/panel/vhost/cert/yy.xxx.com/privkey.pem;

    # 上传文件大小限制
    client_max_body_size 50M;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;

    # ============================================
    # Admin 管理后台 - 根路径
    # ============================================
    location / {
        root /www/wwwroot/hospital-web/admin;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # ============================================
    # Patient 患者端 - /patient/ 路径
    # ============================================
    location /patient/ {
        alias /www/wwwroot/hospital-web/patient/;
        index index.html;
        try_files $uri $uri/ /patient/index.html;
    }

    # ============================================
    # Doctor 医生端 - /doctor/ 路径
    # ============================================
    location /doctor/ {
        alias /www/wwwroot/hospital-web/doctor/;
        index index.html;
        try_files $uri $uri/ /doctor/index.html;
    }

    # ============================================
    # API 代理 - 转发到 Docker 后端
    # ============================================
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
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
        expires 7d;
        add_header Cache-Control "public";
    }

    # ============================================
    # 静态资源缓存
    # ============================================
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
}
```

### 7.3 申请 SSL 证书

1. 宝塔面板 → 站点设置 → **SSL**
2. 选择 **Let's Encrypt**
3. 点击 **申请**
4. 开启 **强制 HTTPS**

### 7.4 配置防火墙

在宝塔 **安全** 中确保放行以下端口：

- 80（HTTP）
- 443（HTTPS）
- 8000（可选，仅调试时需要）

---

## 常用运维命令

### Docker 相关

```bash
cd /www/wwwroot/appointment-booking-system

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend          # 后端日志
docker-compose logs -f celery_worker    # Celery 日志

# 重启服务
docker-compose restart backend
docker-compose restart celery_worker
docker-compose restart celery_beat

# 停止所有服务
docker-compose down

# 启动所有服务
docker-compose up -d

# 重新构建并启动
docker-compose up -d --build

# 进入容器执行命令
docker-compose exec backend bash
```

### 代码更新部署

```bash
cd /www/wwwroot/appointment-booking-system

# 1. 拉取最新代码
git pull origin main

# 2. 重新构建并启动 Docker
docker-compose down
docker-compose up -d --build

# 3. 执行数据库迁移
docker-compose exec backend alembic upgrade head
```

### 数据库备份

```bash
# 备份数据库
PSQL_PATH=$(find /www -name "pg_dump" -type f 2>/dev/null | head -1)
$PSQL_PATH -U hospital -h localhost hospital_booking > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复数据库
$PSQL_PATH -U hospital -h localhost hospital_booking < backup_file.sql
```

---

## 常见问题

### 1. 端口被占用

```bash
# 查看端口占用
netstat -tlnp | grep 8000

# 解决：停止占用端口的进程，或修改 docker-compose.yml 中的端口
```

### 2. Docker 容器无法连接数据库

检查：
1. PostgreSQL 是否允许外部连接（pg_hba.conf）
2. Redis 是否绑定 0.0.0.0
3. docker-compose.yml 中的密码是否正确

### 3. 502 Bad Gateway

```bash
# 检查后端是否正常运行
docker-compose ps
docker-compose logs backend

# 检查端口
curl http://127.0.0.1:8000/api/v1/health
```

### 4. Vim 基本操作

| 操作 | 命令 |
|------|------|
| 进入编辑模式 | 按 `i` |
| 退出编辑模式 | 按 `Esc` |
| 保存并退出 | 输入 `:wq` 按回车 |
| 强制退出不保存 | 输入 `:q!` 按回车 |
| 搜索文本 | 输入 `/关键词` 按回车 |

---

## 安全建议

1. **修改默认密码**：数据库密码、SECRET_KEY 使用强随机字符串
2. **防火墙配置**：只开放必要端口（80、443）
3. **定期备份**：配置定时任务备份数据库
4. **更新系统**：定期更新系统和依赖包
5. **SSL 证书**：使用 HTTPS，定期更新证书

---

## 访问地址

| 应用 | 地址 |
|------|------|
| Admin 管理后台 | `https://你的域名/` |
| Patient 患者端 | `https://你的域名/patient/` |
| Doctor 医生端 | `https://你的域名/doctor/` |
| API 文档 | `https://你的域名/docs` |

