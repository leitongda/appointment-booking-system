# 清理 adaptive-review skill 中的版本升级描述

## Context

adaptive-review skill 经过 v1 → v2 → v2.1 三轮迭代，文件中残留了大量版本过渡描述（"v2.1 变更"、"v2 在 v1 基础上"、"Enhancement N" 标注）。这些信息对使用者无价值，应只保留最终版的功能描述。

## 清理范围

6 个文件，32 处修改，分三类模式处理：

### 模式 A：删除版本变更说明行（4 处）

直接删除以 `> v2.1 变更：` 开头的引用块，以及 "v2.1 在 v2 基础上的核心改进" 列表。

| 文件 | 位置 | 操作 |
|------|------|------|
| SKILL.md | L7-12 的改进列表 | 删除整个列表，概述段落中不提版本号 |
| mode-selection.md | L3 引用块 | 删除 |
| round-protocols.md | L3 引用块 | 删除 |
| role-prompts-r1.md | L3 引用块 | 删除 |
| role-prompts-r2.md | L3 引用块 | 删除 |

### 模式 B：移除 Enhancement N 标注（14 处）

将 `(Enhancement N)` 括号标注从标题和内联文本中删除，保留标题本身。

示例：`## 证据分级框架（Enhancement 5）` → `## 证据分级框架`

涉及文件：SKILL.md、round-protocols.md、role-prompts-r1.md、canvas-template.md

### 模式 C：清理"增加/新增"升级措辞（14 处）

将加深版 prompt 中的 "增加：xxx" 改为直接列出调研内容，去除对比意味。

示例：`1. **产品定位** - 增加：定位声明与实际功能的匹配度分析` → `1. **产品定位** - 定位声明与实际功能的匹配度分析、矛盾描述检测`

涉及文件：role-prompts-r1.md 的加深版 prompt 部分

## 执行顺序

1. SKILL.md — 最大量修改（版本列表 + Enhancement 标注）
2. references/mode-selection.md — 删除引用块
3. references/round-protocols.md — 删除引用块 + Enhancement 标注
4. references/role-prompts-r1.md — 删除引用块 + Enhancement 标注 + 加深版措辞
5. references/role-prompts-r2.md — 删除引用块
6. assets/canvas-template.md — Enhancement 标注

## 验证

```bash
# 确认无残留版本描述
grep -rn "v2\.\|Enhancement\|v2 变更\|在 v2\|v1 →" ~/.claude/skills/adaptive-review/
# 应返回空
```

然后将更新后的文件同步到 GitHub 仓库 `/tmp/leitongda-skill/` 并提交推送。
