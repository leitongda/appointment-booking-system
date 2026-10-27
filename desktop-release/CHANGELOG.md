# 桌面客户端更新公告

本文件是桌面端（HospitalAdmin 管理端 / HospitalDoctor 医生端）**面向用户的更新公告**，读者是机构管理员和医生，
用他们能看懂的话写，不写提交粒度的开发细节（开发细节看 git log 与 Release 页）。

规则：

- 每次发版前新增 `## X.Y.Z (YYYY-MM-DD)` 段落，版本号必须与 `apps/admin/package.json`、`apps/doctor/package.json`
  的 `version` 和 tag `desktop-vX.Y.Z` 完全一致——CI 门禁三者缺一不可。
- 段落必须非空；CI 提取它作为 GitHub Release 正文，`publish-updates.sh` 再把同一段落写进 `latest.json` 的 `notes`，
  也就是用户在应用内更新弹窗里看到的文字。
- 两端锁步同版本、共用同一段公告；只影响一端的条目前加【管理端】或【医生端】。
- 需要用户配合的事（必须重启、需先升级后端、配置格式变化）写在最前面。

## 1.1.0 (2026-10-26)

本版本需要手动安装一次：之前的 1.0.0 预览版不含更新组件。安装后不影响已配置的后端地址（desktop-config.json）。

- 新增自动更新：启动后自动检查新版本，弹窗展示更新说明，确认后下载安装，安装完成后可选择立即重启或稍后重启。
- Windows 安装包统一为 .exe（NSIS）。此前通过 .msi 安装的电脑请先卸载旧版、再用 .exe 安装一次，之后即可自动更新。
- macOS 安装包合并为同时支持 Apple 芯片与 Intel 芯片的通用版本。
