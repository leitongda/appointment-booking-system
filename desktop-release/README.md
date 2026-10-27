# 桌面端发版与自动更新（运维手册）

桌面端 = Tauri 2 壳 + 内嵌的 admin/doctor 前端产物（`frontendDist: ../dist`）。**前端 HTML 变化与壳子变化走同一条发版流水线**，
没有"只热更网页"的通道；用版本号语义区分轻重即可。客户端通过 `tauri-plugin-updater` 自动升级，更新源托管在生产 nginx。

## 一次发版（两端锁步，一个 tag 同时发 admin + doctor）

1. **写公告**：在 `CHANGELOG.md` 新增 `## X.Y.Z (YYYY-MM-DD)` 段落（规则见该文件头部）。
2. **bump 版本**：`apps/admin/package.json` 与 `apps/doctor/package.json` 的 `version` 改为 `X.Y.Z`
   （两端 `tauri.conf.json` 的 `version` 指向各自 package.json，不用另改）。
3. 合并到 `main` 后打 tag：`git tag desktop-vX.Y.Z && git push origin desktop-vX.Y.Z`。
4. CI `desktop-release.yml`：secrets 存在性 → tag 与两端版本号一致 → 公告段落非空 → 打包 → 草稿 Release。
   任何一道门禁失败都在 prepare 阶段红掉，不浪费打包时间。
5. 人工审核草稿（下载安装试跑），然后在 GitHub 上 **Publish**。
6. **同步更新源**：
   ```bash
   desktop-release/publish-updates.sh desktop-vX.Y.Z --dry-run   # 先看生成的目录与 latest.json
   desktop-release/publish-updates.sh desktop-vX.Y.Z             # 上传；latest.json 最后原子替换
   ```
7. 已安装客户端下次启动约 5 秒后弹出更新提示（含公告）；用户确认后下载安装，可选立即/稍后重启。

## 版本号语义

- **patch**（1.1.x）：纯前端改动、文案、小修。
- **minor**（1.x.0）：壳能力变化（新增 IPC 命令、插件、capabilities）或机构需要知道的新功能。
- **major**：破坏性变化——`desktop-config.json` 格式、最低后端版本要求等。
- 只影响一端也两端一起 bump：另一端多出一个无差别的几 MB 包，换来版本对齐和一条流水线。
- updater **只升不降**（semver 比较）：回滚 = 发一个更高 patch 版本、内容是旧代码。服务器上历史版本目录保留。

## 更新公告

唯一来源是 `CHANGELOG.md` 的版本段落，`extract-notes.sh` 把它同时送到两处：GitHub Release 正文（内部审阅）与
`latest.json` 的 `notes`（用户在应用内弹窗看到的文字）。写给机构管理员和医生看，需要用户配合的事放最前面。

## GitHub Secrets（Settings → Secrets and variables → Actions）

| 名称 | 值 | 必需 |
| --- | --- | --- |
| `TAURI_SIGNING_PRIVATE_KEY` | `~/.tauri/hospital-desktop.key` 的**文件内容** | 是 |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | `~/.tauri/hospital-desktop.key.password` 的内容 | 是 |
| `DESKTOP_UPDATE_BASE_URL` | 生产站点根地址，必须 https，如 `https://yy.xxx.com`（域名不入库） | 是 |
| `APPLE_*` 六项 | macOS 签名与公证 | 否（缺失出未签名包） |

密钥对由 `tauri signer generate` 生成，公钥已写进两端 `tauri.conf.json`。**私钥丢失 = 已安装客户端永远收不到更新**
（换钥等于全员手动重装），请另备份到密码管理器。私钥文件与口令文件都不入库。

## 生产 nginx

更新源布局（`DESKTOP_UPDATE_REMOTE_DIR = <站点根>/desktop/updates`）：

```
<站点根>/desktop/updates/admin/latest.json
<站点根>/desktop/updates/admin/<version>/HospitalAdmin*.app.tar.gz   # macOS universal 更新包
<站点根>/desktop/updates/admin/<version>/HospitalAdmin*-setup.exe    # Windows NSIS，既是更新包也是安装包
<站点根>/desktop/updates/admin/<version>/HospitalAdmin*.dmg          # macOS 首次安装用
<站点根>/desktop/updates/doctor/...                                  # 同上
```

```nginx
# latest.json 禁缓存：客户端每次启动都要看到最新清单；其余大文件走默认缓存
location = /desktop/updates/admin/latest.json  { root /www/wwwroot/<站点>; add_header Cache-Control "no-cache"; }
location = /desktop/updates/doctor/latest.json { root /www/wwwroot/<站点>; add_header Cache-Control "no-cache"; }
location /desktop/updates/ { root /www/wwwroot/<站点>; autoindex off; }
```

证书必须是浏览器信任的有效证书（Tauri updater 生产态强制 TLS，自签名会失败；宝塔可签 Let's Encrypt）。

## 客户端行为与边界

- 检查在 `getInitialState` 的桌面 baseURL 把关之后、延迟 5 秒、不阻塞首屏；任何失败（更新源不可达、签名不符、
  纯内网机构）只写 console/日志，不打扰用户。日志目录：macOS `~/Library/Logs/online.aicm.hospital.<admin|doctor>/`。
- 不自动重启：安装完成后弹"立即重启 / 稍后重启"。Windows 下 NSIS passive 安装由壳自行退出进程，属预期。
- `desktop-config.json`（机构后端地址）在应用数据目录，升级不会触碰。
- **纯内网机构**收不到自动更新：仍走安装包手动升级（`<version>/` 目录下的 dmg/exe 可直接下载）。
  以后若需内网镜像，再给 `desktop-config.json` 加 `desktop.updateUrl`（未实现）。
- **首次切换**：1.0.0 预览版不含更新组件，需手动安装 1.1.0 一次；Windows 上用 .msi 装过的先卸载再装 .exe。

## 本地验证

- `cargo check`：`cd apps/<app>/src-tauri && cargo check`。
- 本地 `pnpm tauri build` 出的包更新源是 `.invalid` 占位，启动后检查静默失败，正常。要端到端验证 updater，
  用 `--config '{"plugins":{"updater":{"endpoints":["https://<临时 https 主机>/desktop/updates/admin/latest.json"]}}}'`
  配合一个临时 https 静态目录（把 `publish-updates.sh --dry-run` 生成的 stage 目录放上去）。
