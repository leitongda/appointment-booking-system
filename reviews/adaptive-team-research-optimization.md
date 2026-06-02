# adaptive-team-research Skill 优化分析报告

> 日期：2026-06-01
> 方法：deep-research 工作流（5 角度并行搜索 → 26 源获取 → 114 声明提取 → 25 条对抗性验证 → 16 条确认）
> 置信度标注：[高] = 3-0 或 2-1 确认 | [中] = 1-1 确认 | [低] = 仅有分析推导

---

## 一、总体评估

当前 skill 的设计是**成熟且务实的**：三轮固定流程 + 三种协作模式 + 结构化画布，在 Claude Code 的 Explore subagent 限制下做到了合理的工程权衡。但深度研究发现，以下五个维度存在明确的优化空间。

**核心矛盾：** 该 skill 的核心场景（交叉辩论、共识收敛）恰好是 Anthropic 官方文档标注为"需要 Agent Teams 而非 Subagents"的用例，但当前实现使用的是 Explore subagent 模式（单父节点回报），错失了原生 peer-to-peer 通信能力。

---

## 二、五大优化方向

### 优化 1：编排模式 — 从固定三轮到自适应路由 [高置信]

**当前问题：**
- 固定 Round 1/2/3 三轮流水线，无论任务复杂度如何都走完整流程
- 三种模式（集中调度/领域主导/对等协作）是 Phase 0 预选的静态拓扑，无法随任务演进调整
- 中途切换机制虽有提及但缺乏结构化触发条件

**研究发现：**

| 策略 | 来源 | 核心思路 | 适用性 |
|------|------|---------|--------|
| HERA 经验库 | [arxiv 2604.00901] | Profile-Insight-Utility 结构，通过 ADD/MERGE/PRUNE/KEEP 四种操作在线学习编排策略 | 高 — 可实现跨会话策略积累 |
| MoMA 分层路由 | [arxiv 2509.07571] | 语义嵌入粗分类 + 上下文感知有限状态机细路由 | 中 — 实现复杂度高 |
| Minstrel 工作组 | [arxiv 2409.13449] | 分析组/设计组/测试组按需激活，而非执行完整流水线 | 高 — 可直接映射到现有三角色 |

**具体建议：**

1. **引入任务复杂度分级**：Phase 0 时评估任务规模（文件数/模块数/变更行数），动态决定是否需要完整三轮：
   - 小型评审（< 10 文件）：集中调度 Round 1 + Team Lead 直接裁决，跳过 Round 2
   - 中型评审（10-50 文件）：标准三轮流进
   - 大型评审（> 50 文件）：对等协作 + 可选 Round 4 深入

2. **条件性轮次跳过**：当 Round 1 事实收集显示无跨领域争议时，Round 2 可降级为 Critic-only（无需交叉评论），直接进入 Round 3。

3. **中途切换触发条件结构化**：在画布中增加"切换触发器"字段：
   - Round 2 出现 > 3 个 Critic 关键质询 → 自动升级为对等协作
   - Round 1 某领域发现 > 70% 事实 → 自动切换为该领域主导模式

---

### 优化 2：通信机制 — 从文件画布到原生 Agent Teams 通信 [高置信]

**当前问题：**
- Explore subagent 通过共享画布文件间接通信（写文件 → 读文件）
- 所有 agent 输出汇聚到 Team Lead，agent 之间无法直接交互
- 画布文件成为串行化瓶颈（Round 2 必须等 Round 1 画布写入完成）

**研究发现：**

Anthropic 官方文档明确区分了两种多 agent 架构：
- **Subagents**（当前 skill 使用的）：单父节点回报，适合并行实验、定义明确的独立任务
- **Agent Teams**：peer-to-peer 直接通信，适合"需要讨论和协作的复杂工作"

Claude Code Agent Teams 提供三种通信原语：
| 原语 | 说明 | 对应场景 |
|------|------|---------|
| SendMessage | 按名称的点对点消息 | 交叉辩论中 PM → Designer 直接反驳 |
| 共享任务列表 | 带文件锁的并发领取 | Round 1 事实收集去重 |
| 自动空闲通知 | 无需轮询 | Round 2 依赖触发 |

**具体建议：**

1. **短期（保持 Explore 模式）**：
   - 将画布从单一文件拆分为按 Round 的结构化 JSON 文件，支持增量写入
   - Round 1 agent 完成后立即写入各自分区，无需等全部完成
   - Team Lead 在 Round 2 前做一次合并去重，而非当前的全量等待

2. **中期（迁移到 Agent Teams）**：
   - 使用 TeamCreate 创建正式团队
   - Round 1：三个 agent 并行写入共享任务列表
   - Round 2：使用 SendMessage 实现真正的 peer-to-peer 交叉辩论
   - 利用 TeammateIdle 钩子触发 Round 2 启动（无需轮询）

3. **增加钩子式质量门禁**：
   - TaskCompleted 钩子（退出码 2）可阻止质量不合格的 agent 完成并反馈
   - Round 1 完成时自动检查：事实是否包含来源引用？是否有评价性词汇？
   - Round 2 完成时自动检查：反驳是否附带理由？

---

### 优化 3：Prompt 工程 — 从静态三版本到自适应演化 [高置信]

**当前问题：**
- 标准/加深/精简三版本 prompt 是手工设计的静态模板
- 无法根据执行反馈自动调整
- 缺少对"中间 agent 满足本地指令但误导下游 peer"的防护

**研究发现：**

| 技术 | 来源 | 核心发现 | 适用性 |
|------|------|---------|--------|
| RoPE 双维度演化 | [arxiv 2604.00901] | 操作规则（短期纠正）+ 行为原则（长期策略），移除 prompt 演化导致准确率下降 30% | 高 |
| MASPO 硬负例挖掘 | [arxiv 2605.06623] | Local-Global Misalignment 是多 agent prompt 的关键失败模式，K_mis=3 为最优注入量 | 高 |
| Minstrel 五位评论者 | [arxiv 2409.13449] | 2 批评 + 2 支持 + 1 中立，比单一 Critic 更平衡 | 高 |

**具体建议：**

1. **引入 Prompt 版本标注与 A/B 测试机制**：
   - 在画布中记录使用的 prompt 版本 ID
   - 跨执行实例对比不同 prompt 版本产生的行动项采纳率
   - 建立简单的 prompt 效果跟踪：哪些 prompt 模板产生了被标记为"关键"的发现？

2. **增强 Critic 角色为多立场评审组**：
   - 当前单一 Critic → 演化为"评审组"（2 质疑 + 1 中立审计）
   - 质疑者从反对角度挑战，审计者检查逻辑一致性
   - 这在 Agent Teams 模式下可自然并行化

3. **添加 Local-Global Misalignment 防护**：
   - Round 2 交叉评论者除了评论他人发现，还需检查自己的输出是否可能误导下游
   - 在 prompt 中增加检查点："你的输出是否可能被其他角色误解？如有，请添加澄清说明"

4. **实现增量 prompt 更新（Minstrel 模式）**：
   - 在 prompt 模板中增加 `{{LEARNED_RULES}}` 占位符
   - 每次执行后，将评审中发现的系统性问题（如"PM agent 总是忽略安全维度"）提炼为规则
   - 下次执行时注入对应角色的 prompt

---

### 优化 4：软件工程工作流集成 [中置信]

**当前问题：**
- 作为纯分析工具，产出画布文件和行动计划，但与 CI/CD、代码审查无原生集成
- Explore agent 的只读限制阻止了自动修复、PR 评论等写操作
- 缺少与 ADR（架构决策记录）、SonarQube 等现有工具的协同

**研究发现：**

Anthropic 识别的三种多 agent 模式与软件工程场景的自然映射：
| 模式 | 适用场景 | 当前 skill 对应 |
|------|---------|---------------|
| Parallel Claude | 独立 bug 修复 | 无 |
| Subagents | PR 审查 | Round 1 事实收集 |
| Agent Teams | 跨服务重构 | Round 2 交叉辩论 |

**具体建议：**

1. **输出格式适配**：
   - 行动计划增加 GitHub Issue 格式模板（标题、标签、指派人、描述）
   - 共识项可自动生成 ADR 草稿（背景、决策、后果）
   - Critic 关键质询可映射为 PR review comment

2. **增加 general-purpose agent 模式**：
   - 当前仅用 Explore（只读），可增加可选的 Round 4 执行阶段
   - 使用 general-purpose agent 类型（可写文件）自动执行 P0 行动项
   - 例如：自动补充缺失的 API 输入验证、自动添加 loading 骨架屏

3. **与 Claude Code Hooks 集成**：
   - 注册 `TaskCompleted` 钩子，在评审完成后自动触发 lint/test
   - 注册 `TeammateIdle` 钩子，在 agent 空闲时自动分配下一个可用任务

---

### 5：质量门禁与反馈循环 [中置信]

**当前问题：**
- 无结构化的输出质量验证（仅有禁用词列表）
- 无跨执行实例的经验积累
- 固定三轮结构，缺少对"是否值得继续迭代"的动态判断

**研究发现：**

| 机制 | 来源 | 说明 | 适用性 |
|------|------|------|--------|
| 执行时门禁 | Claude Code Hooks | TaskCompleted 退出码 2 阻止完成 + 反馈 | 高 — 可立即实施 |
| 跨会话经验库 | HERA | Profile-Insight-Utility 结构，ADD/MERGE/PRUNE 在线更新 | 中 — 需要持久化机制 |
| 辩论轮次动态判断 | MLC [acl 2025] | 3 轮辩论可能不如 2 轮，存在收益递减天花板 | 高 — 可简化流程 |

**具体建议：**

1. **每轮输出质量检查清单**：

   Round 1 质量门禁：
   - [ ] 每条事实是否包含来源（文件路径:行号）？
   - [ ] 是否零评价性词汇？（自动扫描禁用词列表）
   - [ ] 是否覆盖了 prompt 要求的所有调研维度？

   Round 2 质量门禁：
   - [ ] 每个反驳是否附带理由？
   - [ ] Critic 是否标记了关键质询（1-3 条）？
   - [ ] 交叉评论是否覆盖了其他两方的主要发现？

   Round 3 质量门禁：
   - [ ] 每个行动项是否包含成本估算？
   - [ ] 每个行动项是否标注负责角色？
   - [ ] Critic 关键质询是否逐条回应？

2. **引入"继续迭代价值"判断**：
   - Round 2 完成后，评估争议密度（分歧项 / 总议题数）
   - 争议密度 < 20% → Round 3 直接裁决（跳过投票矩阵）
   - 争议密度 > 50% → 考虑增加 Round 2.5（补充调研）
   - 避免无意义的第 3 轮辩论（MLC 研究表明收益递减）

3. **跨会话经验积累（长期）**：
   - 在 `.claude/` 目录下维护 `review-experience.json`
   - 记录：任务类型 → 使用的模式 → 产出质量 → 行动项采纳率
   - Phase 0 模式选择时参考历史数据，而非仅凭决策树

---

## 三、优先级排序与实施路径

| 优先级 | 优化项 | 预期收益 | 实施成本 | 依赖 |
|--------|--------|---------|---------|------|
| **P0** | 质量门禁检查清单 | 防止低质量输出，立即可实施 | 低（修改 SKILL.md 增加检查步骤） | 无 |
| **P0** | 任务复杂度分级 + 条件性轮次跳过 | 减少不必要 agent 调用，节省 token | 低（修改 mode-selection.md） | 无 |
| **P1** | 画布文件拆分为结构化 JSON | 解除串行瓶颈 | 中（修改 canvas-template + round-protocols） | 无 |
| **P1** | Critic 角色增强为多立场评审组 | 更平衡的评估 | 中（新增 prompt 模板） | 无 |
| **P1** | 输出格式适配（GitHub Issue / ADR） | 与软件工程工作流对接 | 中（修改 canvas-template） | 无 |
| **P2** | Local-Global Misalignment 防护 | 防止 agent 间误导 | 中（修改 role-prompts-r2.md） | 无 |
| **P2** | 迁移到 Agent Teams 原生通信 | 根本性改善通信效率 | 高（重写 round-protocols + 通信层） | Agent Teams 功能稳定 |
| **P2** | 跨会话经验积累 | 跨执行策略学习 | 高（需要持久化机制） | 需设计存储格式 |
| **待定** | Prompt 自适应演化（RoPE 风格） | 自动优化 prompt 质量 | 很高（需要评估框架） | 需先建立度量体系 |

---

## 四、被否决的优化方向（附理由）

以下方向经对抗性验证被否决（2/3 或 3/3 refuted），不建议采用：

1. **AgentNet 去中心化 DAG 协调** — 声称消除静态角色分配，但验证者认为去中心化协调在当前 agent 能力下不可靠，增加的复杂性远超收益
2. **MoMA 的 Pareto+TOPSIS 多目标优化** — 在 agent 编排场景下过度工程化，简单的启发式路由即可达到类似效果
3. **MASPO 坐标上升式调度** — 理论上优雅但在实践中收敛速度不可控，与固定三轮的确定性需求冲突

---

## 五、关键局限声明

1. HERA、MASPO、MoMA 的研究来自 2024-2026 年 arXiv 预印本，未经独立复现，迁移到软件评审场景的有效性未经验证
2. Claude Code Agent Teams 为实验性功能，不支持跨会话通信，当前实际可用性受限
3. MLC 的多 agent 辩论有效性存在学术争议 — AISTATS 2024 和 ACL 2024 均有论文质疑多 agent 辩论是否优于精心提示的单 agent
4. 建议的优化方向需在实际项目中验证，建议先实施 P0 项，观察效果后再决定 P1/P2 的投入

---

## 六、参考来源

- [HERA: Human-Encoding-Regularized Agentic Prompt Evolution](https://arxiv.org/abs/2604.00901) — 经验库 + RoPE prompt 演化
- [MoMA: Modular Multi-Agent System for Adaptive Routing](https://arxiv.org/abs/2509.07571) — 分层意图路由
- [MASPO: Multi-Agent System Prompt Optimization](https://arxiv.org/abs/2605.06623) — Local-Global Misalignment + 硬负例挖掘
- [Minstrel: Modular Multi-Agent System](https://arxiv.org/abs/2409.13449) — 工作组架构 + 五位评论者 + 反射循环
- [MLC: Multi-LLM Cooperation](https://aclanthology.org/2025.acl-long.1105.pdf) — 辩论收益递减研究
- [Claude Code Agent Teams 官方文档](https://code.claude.com/docs/en/agent-teams) — 通信原语 + 钩子系统
- [Anthropic Advanced Patterns](https://resources.anthropic.com/hubfs/Claude%20Code%20Advanced%20Patterns_%20Subagents%2C%20MCP%2C%20and%20Scaling%20to%20Real%20Codebases.pdf) — 三种多 agent 模式分类
