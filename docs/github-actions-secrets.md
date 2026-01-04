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

