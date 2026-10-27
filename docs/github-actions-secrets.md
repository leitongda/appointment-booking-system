# GitHub Actions Secrets 配置说明

本文档说明 CI/CD 工作流所需的 GitHub Secrets 配置。

## 必须配置的 Secrets

在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 中配置以下变量：

| Secret 名称 | 是否必须 | 说明 | 示例值 |
|------------|---------|------|--------|
| `CVM_HOST` | ✅ 必须 | 腾讯云服务器的 IP 地址或域名 | `123.456.789.0` |
| `CVM_USERNAME` | ✅ 必须 | SSH 登录用户名 | `root` 或 `ubuntu` |
| `CVM_SSH_KEY` | ✅ 必须 | SSH 私钥（完整内容） | 见下方说明 |
| `CVM_PORT` | ❌ 可选 | SSH 端口号，默认为 `22` | `22` |

## 配置步骤

### 1. 获取 SSH 私钥

如果服务器已配置 SSH 密钥登录，复制本地私钥内容：

```bash
cat ~/.ssh/id_rsa
# 或
cat ~/.ssh/id_ed25519
```

私钥格式示例（需要完整复制，包括首尾行）：

```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
...（中间内容省略）...
QyMDIzMDEwMQAAAA==
-----END OPENSSH PRIVATE KEY-----
```

### 2. 在 GitHub 添加 Secrets

1. 进入仓库页面
2. 点击 **Settings** 选项卡
3. 左侧菜单选择 **Secrets and variables** → **Actions**
4. 点击 **New repository secret**
5. 依次添加上表中的 4 个变量

### 3. 确保服务器已添加公钥

服务器的 `~/.ssh/authorized_keys` 文件中需要包含对应的公钥：

```bash
# 在服务器上执行
cat ~/.ssh/authorized_keys
```

如果没有，需要将本地公钥添加到服务器：

```bash
# 在本地执行
ssh-copy-id -i ~/.ssh/id_rsa.pub username@your-server-ip
```

## 工作流使用的 Secrets

### build-frontend.yml（前端构建部署）

| Secret | 用途 |
|--------|------|
| `CVM_HOST` | SCP 上传和 SSH 连接的目标主机 |
| `CVM_USERNAME` | SSH/SCP 登录用户名 |
| `CVM_SSH_KEY` | SSH 认证私钥 |
| `CVM_PORT` | SSH/SCP 连接端口 |

### build-server.yml（后端部署）

| Secret | 用途 |
|--------|------|
| `CVM_HOST` | SSH 连接的目标主机 |
| `CVM_USERNAME` | SSH 登录用户名 |
| `CVM_SSH_KEY` | SSH 认证私钥 |
| `CVM_PORT` | SSH 连接端口 |

## 环境变量（硬编码在工作流中）

以下变量直接写在工作流文件中，如需修改请编辑对应的 `.yml` 文件：

| 变量名 | 当前值 | 说明 |
|-------|-------|------|
| `PROJECT_DIR` | `/www/hospital-booking` | 服务器上的项目根目录 |

## 故障排查

### SSH 连接失败

1. 检查 `CVM_HOST` 是否正确
2. 检查 `CVM_SSH_KEY` 是否完整复制（包括首尾行）
3. 检查服务器防火墙是否允许 SSH 端口
4. 检查服务器 `~/.ssh/authorized_keys` 是否包含对应公钥

### SCP 上传失败

1. 检查目标目录是否存在：`/www/hospital-booking/apps/*/dist`
2. 检查用户是否有写入权限
3. 检查服务器磁盘空间

### 构建失败

1. 检查 GitHub Actions 日志中的具体错误信息
2. 确保 `pnpm-lock.yaml` 已提交到仓库
3. 本地运行 `pnpm build:admin` 等命令验证是否能正常构建

## 高德地图配置说明

Admin 后台使用高德地图进行位置选择功能。通过 `.env` 文件配置（不通过 GitHub Secrets）。

### 配置方式

在 `apps/admin/` 目录下创建 `.env` 文件：

```bash
# apps/admin/.env
AMAP_KEY=your_amap_key
AMAP_SERVICE_HOST=https://your-domain.com/_AMapService
```

### 1. 获取 AMAP_KEY

从高德开放平台获取 Web JS API Key：

1. 访问 [高德开放平台](https://lbs.amap.com/)
2. 注册/登录账号
3. 进入控制台 → 应用管理 → 我的应用
4. 创建新应用，选择 **Web端(JS API)** 类型
5. 复制生成的 Key

### 2. 配置 AMAP_SERVICE_HOST

高德地图 Web 服务 API 需要配置代理服务，防止 Key 暴露：

在 Nginx 配置中添加代理规则：

```nginx
# 高德地图 API 代理
location /_AMapService/ {
    proxy_pass https://restapi.amap.com/;
    proxy_set_header Host restapi.amap.com;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

然后配置 `AMAP_SERVICE_HOST` 为您的代理地址：
- 格式：`https://your-domain.com/_AMapService`
- 示例：`https://admin.hospital.com/_AMapService`

## 桌面端发布（desktop-release.yml）

桌面客户端已启用 Tauri updater 自动更新，推 `desktop-v*` tag 时以下三项**缺一不可**（prepare 阶段 fail-fast）：

| Secret 名称 | 是否必须 | 说明 |
|------------|---------|------|
| `TAURI_SIGNING_PRIVATE_KEY` | ✅ 必须 | 更新包 minisign 私钥，`~/.tauri/hospital-desktop.key` 的**文件内容**。丢失 = 已安装客户端永远收不到更新，请另备份到密码管理器 |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | ✅ 必须 | 上述私钥口令，`~/.tauri/hospital-desktop.key.password` 的内容 |
| `DESKTOP_UPDATE_BASE_URL` | ✅ 必须 | 更新源根地址，必须 https（如 `https://yy.xxx.com`）；域名不入库，构建期用 `tauri build --config` 注入 |
| `APPLE_CERTIFICATE` 等六项 | ❌ 可选 | macOS 签名与公证，缺失时出未签名包 |

发版流程、nginx 布局与发布脚本见 [`desktop-release/README.md`](../desktop-release/README.md)。


