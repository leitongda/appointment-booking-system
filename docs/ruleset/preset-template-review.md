# 预设模板参数业务审查报告

## 1 审查范围

本报告对 `apps/admin/src/constants/rule-set.ts` 中定义的 4 个预设模板逐一进行参数合理性审查：

| 编号 | 模板 | preset id | priority |
|------|------|-----------|----------|
| 1 | 标准门诊 | `standard-clinic` | 100 |
| 2 | 专家门诊 | `expert-clinic` | 50 |
| 3 | 体检预约 | `health-check` | 80 |
| 4 | 急诊 | `emergency` | 10 |

审查对照文件：`docs/ruleset/后台配置清单.md`、`docs/ruleset/readme.md`。

---

## 2 逐模板审查

### 2.1 标准门诊（PRESET_STANDARD_CLINIC）

#### 基本配置

| 参数 | 值 | 评估 |
|------|-----|------|
| priority | 100 | 合理。标准门诊作为默认规则组，低优先级（高数值），确保被更具体的规则覆盖 |
| comparePrecision | MINUTE | 合理。门诊场景按分钟即可 |
| clockSkewToleranceSec | 5 | 合理 |

#### 预约策略

| 参数 | 值 | 评估 |
|------|-----|------|
| requireAuth | true | 合理 |
| requirePatientProfileComplete | false | 合理。普通门诊降低门槛，允许现场补全 |
| perUserPerShift | 1 | 合理 |
| perUserPerDay | 3 | 合理。普通门诊一天看 3 个科室是常见场景 |
| perUserPerWeek | 10 | 合理 |
| conflictSameShift | REJECT | 合理 |
| conflictOverlapTime | REJECT | 合理 |
| conflictSameTypeSameDay | ALLOW | 合理。同类型同日可再约（如上午门诊+下午门诊） |

#### 签到策略

| 参数 | 值 | 评估 |
|------|-----|------|
| requireBooking | true | 合理 |
| allowOnsiteBooking | false | 合理。标准门诊应走预约流程 |
| gracePeriodSec | 900 (15分钟) | 合理 |
| afterGraceStatus | LATE | 合理 |
| noCheckinAfterClose | KEEP_BOOKED | **[问题 S-1]** 见下方 |

#### 容量策略

| 参数 | 值 | 评估 |
|------|-----|------|
| totalCapacity | 30 | 合理 |
| waitlistEnabled | false | 合理。普通门诊号源较充裕 |
| overbookingEnabled | false | 合理 |

#### 时间窗

| 窗口 | openOffset | closeOffset | 评估 |
|------|------------|-------------|------|
| 预约 BOOK | -7天 | 0 (SHIFT_START) | 合理 |
| 签到 CHECKIN | -30分 (SHIFT_START前) | +1小时 (SHIFT_START后) | 合理 |
| 取消 CANCEL | -7天 | -2小时 | 合理。开始前2小时截止取消 |

#### 问题清单

**[S-1] noCheckinAfterClose=KEEP_BOOKED 可能导致资源浪费**

- **现状**：签到截止后未签到，预约状态保持不变（KEEP_BOOKED），号源被占用但患者未到场
- **风险**：爽约号源无法释放，影响其他患者预约
- **建议值**：`ABSENT`（标记为爽约）或 `AUTO_CANCEL`（自动取消并释放号源）
- **业务理由**：标准门诊号源有限，应及时释放爽约号源。如果担心误判，可结合较宽的签到窗口（当前已设置到班次开始后1小时）来降低误判概率

---

### 2.2 专家门诊（PRESET_EXPERT_CLINIC）

#### 基本配置

| 参数 | 值 | 评估 |
|------|-----|------|
| priority | 50 | 合理。比标准门诊优先级高，确保专家号走专门规则 |
| comparePrecision | MINUTE | 合理 |
| clockSkewToleranceSec | 5 | 合理 |

#### 预约策略

| 参数 | 值 | 评估 |
|------|-----|------|
| requireAuth | true | 合理 |
| requirePatientProfileComplete | true | 合理。专家号资源宝贵，应要求档案完整 |
| perUserPerShift | 1 | 合理 |
| perUserPerDay | 1 | 合理。专家号限制每日1次 |
| perUserPerWeek | 3 | 合理 |
| conflictSameShift | REJECT | 合理 |
| conflictOverlapTime | REJECT | 合理 |
| conflictSameTypeSameDay | REJECT | 合理。同类型同日不可重复 |

#### 签到策略

| 参数 | 值 | 评估 |
|------|-----|------|
| requireBooking | true | 合理 |
| allowOnsiteBooking | false | 合理 |
| gracePeriodSec | 600 (10分钟) | 合理。专家号宽限期较短 |
| afterGraceStatus | LATE | 合理 |
| noCheckinAfterClose | ABSENT | 合理。专家号爽约应标记，防止资源浪费 |

#### 容量策略

| 参数 | 值 | 评估 |
|------|-----|------|
| totalCapacity | 15 | 合理。专家号源较少 |
| waitlistEnabled | true | 合理 |
| waitlistMaxSize | 5 | 合理 |
| waitlistPromotePolicy | AUTO | 合理 |
| overbookingEnabled | false | 合理 |
| overbookingMax | 0 | 合理 |

#### 时间窗

| 窗口 | openOffset | closeOffset | 评估 |
|------|------------|-------------|------|
| 预约 BOOK | -3天 | -1小时 | 合理 |
| 签到 CHECKIN | -30分 | +30分 | **[问题 E-1]** 见下方 |
| 取消 CANCEL | -3天 | -4小时 | 合理 |

#### 问题清单

**[E-1] 签到窗口偏窄，仅60分钟**

- **现状**：签到窗口为班次开始前30分钟到开始后30分钟，总计60分钟
- **风险**：专家门诊患者可能来自远途、需要提前到院做检查准备，30分钟签到截止可能不够
- **建议值**：`closeOffsetSec` 调整为 `5400`（班次开始后90分钟）或保持 `3600`（60分钟）但配合更宽的宽限期
- **补充说明**：由于 `gracePeriodSec=600`（10分钟宽限），实际最晚签到时间为开始后40分钟，窗口更窄

**[E-2] 预约开放窗口只有3天，偏短**

- **现状**：`openOffsetSec = -259200`（3天），对于专家号，患者通常需要提前更久规划
- **风险**：患者可能错过预约窗口，降低专家资源利用率
- **建议值**：调整为 `-604800`（7天）或 `-1209600`（14天）
- **反向考量**：如果专家排班每周四下午才公布下周排班，则3天是合理的。建议根据实际排班发布周期调整

---

### 2.3 体检预约（PRESET_HEALTH_CHECK）

#### 基本配置

| 参数 | 值 | 评估 |
|------|-----|------|
| priority | 80 | 合理 |
| comparePrecision | MINUTE | 合理 |

#### 预约策略

| 参数 | 值 | 评估 |
|------|-----|------|
| requireAuth | true | 合理 |
| requirePatientProfileComplete | true | 合理。体检需要完整个人信息 |
| perUserPerShift | 1 | 合理 |
| perUserPerDay | 1 | 合理 |
| perUserPerWeek | 1 | 合理。体检一周做一次足够 |
| conflictSameShift | REJECT | 合理 |
| conflictOverlapTime | REJECT | 合理 |
| conflictSameTypeSameDay | REJECT | 合理 |

#### 签到策略

| 参数 | 值 | 评估 |
|------|-----|------|
| requireBooking | true | 合理 |
| allowOnsiteBooking | false | 合理 |
| gracePeriodSec | 1800 (30分钟) | 合理。体检项目多，宽限期应较长 |
| afterGraceStatus | LATE | 合理 |
| noCheckinAfterClose | KEEP_BOOKED | **[问题 H-1]** 见下方 |

#### 容量策略

| 参数 | 值 | 评估 |
|------|-----|------|
| totalCapacity | 50 | 合理 |
| waitlistEnabled | true | 合理 |
| waitlistMaxSize | 20 | 合理 |
| waitlistPromotePolicy | AUTO | 合理 |
| overbookingEnabled | true | **[问题 H-2]** 见下方 |
| overbookingMax | 5 | 见下方 |

#### 时间窗

| 窗口 | openOffset | closeOffset | 评估 |
|------|------------|-------------|------|
| 预约 BOOK | -30天 | -1天 | 合理 |
| 签到 CHECKIN | -1小时 | +2小时 | 合理 |
| 取消 CANCEL | -30天 | -2天 | **[问题 H-3]** 见下方 |

#### 问题清单

**[H-1] noCheckinAfterClose=KEEP_BOOKED 与体检业务不符**

- **现状**：签到截止后仍保持预约状态
- **风险**：体检预约占用物料/设备资源，爽约应释放
- **建议值**：`AUTO_CANCEL`（自动取消并释放）
- **业务理由**：体检涉及空腹、试剂等准备，爽约资源浪费比普通门诊更严重

**[H-2] overbookingEnabled=true 需结合候补策略审慎使用**

- **现状**：同时启用了候补（waitlistEnabled=true）和超额（overbookingEnabled=true, overbookingMax=5）
- **风险**：当 `totalCapacity=50` 且超额 5 时，实际容量为 55。候补队列在总容量 50 已满时即开始累积。但超额机制会允许额外 5 人直接预约，这意味着候补队列可能永远无法递补（被超额预约抢占）
- **建议值**：二选一
  - 方案 A：关闭超额（`overbookingEnabled=false`），仅用候补机制
  - 方案 B：关闭候补（`waitlistEnabled=false`），仅用超额机制（体检场景超额 5 人合理）
- **推荐**：方案 B 更适合体检场景。体检通常按批次进行，超额几人可安排，但候补递补在体检场景不太适用

**[H-3] 取消截止时间-2天可能过严**

- **现状**：`closeOffsetSec = -172800`（班次开始前2天截止取消）
- **风险**：体检前1-2天患者可能有突发情况（如感冒、生理期），无法取消会严重影响患者体验
- **建议值**：调整为 `-86400`（前1天截止）或 `-43200`（前12小时截止）
- **业务理由**：体检取消释放的资源可以快速被候补/超额机制消化，过长的不可取消窗口没有实际收益

---

### 2.4 急诊（PRESET_EMERGENCY）

#### 基本配置

| 参数 | 值 | 评估 |
|------|-----|------|
| priority | 10 | 合理。最高优先级，确保急诊走专门规则 |
| comparePrecision | MINUTE | 合理 |
| defaultCloseInclusive | true | **[问题 EM-1]** 见下方 |
| clockSkewToleranceSec | 10 | 合理。急诊场景可略宽松 |

#### 预约策略

| 参数 | 值 | 评估 |
|------|-----|------|
| requireAuth | true | 合理 |
| requirePatientProfileComplete | false | 合理。急诊不应因档案不全而拒绝 |
| perUserPerShift | 3 | 合理。急诊可能有多次就诊需求 |
| perUserPerDay | 0 (不限制) | **[问题 EM-2]** 见下方 |
| perUserPerWeek | 0 (不限制) | 合理 |
| conflictSameShift | ALLOW | 合理。急诊允许重复 |
| conflictOverlapTime | ALLOW | 合理 |
| conflictSameTypeSameDay | ALLOW | 合理 |

#### 签到策略

| 参数 | 值 | 评估 |
|------|-----|------|
| requireBooking | false | 合理。急诊允许直接就诊 |
| allowOnsiteBooking | true | 合理 |
| maxTimes | 3 | 合理 |
| gracePeriodSec | 3600 (1小时) | 合理。急诊等待时间长 |
| afterGraceStatus | ON_TIME | **[问题 EM-3]** 见下方 |
| noCheckinAfterClose | KEEP_BOOKED | 合理 |

#### 容量策略

| 参数 | 值 | 评估 |
|------|-----|------|
| totalCapacity | 0 (不限制) | **[问题 EM-4]** 见下方 |
| perUserCapacity | 3 | 合理 |
| waitlistEnabled | false | 合理。急诊不需要候补 |
| overbookingEnabled | true | **[问题 EM-4]** 与 totalCapacity=0 矛盾，见下方 |
| overbookingMax | 999 | **[问题 EM-4]** 见下方 |

#### 时间窗

| 窗口 | openOffset | closeOffset | 评估 |
|------|------------|-------------|------|
| 预约 BOOK | -1天 | +2小时 | 合理。急诊允许迟到预约 |
| 签到 CHECKIN | -1天 | 0 (SHIFT_END) | 合理 |
| (无取消窗口) | - | - | **[问题 EM-5]** 见下方 |

#### 问题清单

**[EM-1] defaultCloseInclusive=true 与全局默认不一致**

- **现状**：`defaultCloseInclusive = true`，而其他模板和全局默认值为 `false`
- **风险**：边界行为不一致。当 Window 的 `closeInclusive=null` 时，急诊模板的截止时刻包含在内，而其他模板不包含。虽然当前急诊模板的所有窗口都显式设置了 `closeInclusive`，此参数暂时无影响，但未来新增窗口时容易忽略
- **建议**：保持 `false` 与其他模板一致，在具体窗口中显式设置 `closeInclusive=true` 来控制边界行为

**[EM-2] perUserPerDay=0 语义模糊**

- **现状**：`perUserPerDay = 0`，注释说"不限制"
- **风险**：代码中 `validation.py` 的判断条件为 `if policy.per_user_per_day and policy.per_user_per_day > 0`，当值为 0 时该条件为 False，确实跳过了检查。但这种"0 表示不限制"的语义与直觉（0 应该是"完全不允许"）相反
- **建议值**：使用 `null` 表示不限制更清晰（代码中 `per_user_per_day` 字段允许 null）。但考虑到此为前端常量定义，发送到后端后行为正确，标记为低优先级
- **建议**：添加注释明确说明 `0` 在此系统中表示"不限制"

**[EM-3] afterGraceStatus=ON_TIME 逻辑上自相矛盾**

- **现状**：宽限期内标记为 `ON_TIME`（准时）
- **风险**：`afterGraceStatus` 的语义是"宽限期后"的状态。宽限期本身已经是迟到的缓冲，宽限期后仍标记为"准时"等于宽限期形同虚设
- **建议值**：`LATE` 或 `null`（不标记）
- **业务理由**：如果急诊不关心迟到概念，应该设 `afterGraceStatus = null`（不标记），而不是标记为 `ON_TIME`。标记为 `ON_TIME` 在统计报表中会产生误导

**[EM-4] totalCapacity=0 + overbookingEnabled=true + overbookingMax=999 参数组合矛盾**

- **现状**：
  ```
  totalCapacity = 0         (注释说"不限制")
  overbookingEnabled = true  (允许超额)
  overbookingMax = 999       (超额上限999)
  ```
- **风险**：
  1. 代码中 `check_capacity_limits()` 的逻辑为 `if policy.total_capacity:`，当 `total_capacity=0` 时，该条件为 False（Python 中 0 为 falsy），直接跳过容量检查
  2. 这意味着 `overbookingEnabled=true` 和 `overbookingMax=999` 完全不生效 -- 因为容量检查被整体跳过了
  3. 如果未来有人将 `totalCapacity` 改为非零值（如 100），则 `overbookingMax=999` 会导致实际容量变为 1099，显然不合理
- **建议值**：
  - 方案 A（推荐）：`totalCapacity=0, overbookingEnabled=false, overbookingMax=0` -- 简洁明了地表达"不限制"
  - 方案 B：如果确实需要急诊有容量上限但允许大量超额，设 `totalCapacity=100, overbookingEnabled=true, overbookingMax=20` 等合理值

**[EM-5] 缺少取消时间窗**

- **现状**：急诊模板只配置了预约和签到窗口，没有取消窗口
- **风险**：
  - 没有取消窗口时，系统会走到 `_get_default_window_result()`，返回 `allowed=True` 且有效期 365 天
  - 这意味着急诊预约可以随时取消，**但这可能不是期望的行为**
  - 如果急诊确实应该随时可取消，应显式配置一个宽松的取消窗口，使行为可预测
- **建议**：添加取消窗口
  ```typescript
  {
    name: '取消时间窗',
    action: 'CANCEL',
    referencePoint: 'SHIFT_START',
    openOffsetSec: -86400,   // 提前1天
    closeOffsetSec: 3600,    // 班次开始后1小时仍可取消
    openInclusive: true,
    closeInclusive: true,
    failPolicy: 'ALLOW_WITH_TAG',  // 超时取消打标签但不拒绝
    enabled: true,
  }
  ```

---

## 3 跨模板对比与一致性问题

### 3.1 参数语义不一致

| 参数 | 标准门诊 | 专家门诊 | 体检 | 急诊 | 问题 |
|------|----------|----------|------|------|------|
| noCheckinAfterClose | KEEP_BOOKED | ABSENT | KEEP_BOOKED | KEEP_BOOKED | 只有专家号标记爽约，其他都保留 |
| afterGraceStatus | LATE | LATE | LATE | ON_TIME | 急诊与其他不一致 |
| defaultCloseInclusive | false | false | false | true | 急诊与其他不一致 |

**建议**：统一 `noCheckinAfterClose` 的默认值。对于有号源限制的场景（标准门诊 30 人、体检 50 人），建议都设为 `ABSENT` 或 `AUTO_CANCEL`，以释放爽约资源。

### 3.2 取消时间窗对比

| 模板 | 取消开放 | 取消截止 | 实际可取消时长 |
|------|----------|----------|----------------|
| 标准门诊 | -7天 | -2小时 | 约6天22小时 |
| 专家门诊 | -3天 | -4小时 | 约2天20小时 |
| 体检 | -30天 | -2天 | 约28天 |
| 急诊 | 无窗口 | 无窗口 | 365天（默认） |

**建议**：体检的取消截止时间（-2天）过严，急诊应显式配置取消窗口。

### 3.3 优先级排序合理性

当前优先级（越小越优先）：

```
急诊(10) > 专家门诊(50) > 体检(80) > 标准门诊(100)
```

这个排序是合理的：急诊优先匹配，标准门诊作为兜底规则。但需注意，只有在同一班次类型命中多个规则组时优先级才生效。如果各模板绑定不同的班次类型（通常如此），则优先级实际不参与判断。

---

## 4 问题汇总

### 4.1 按严重程度排序

| 级别 | 编号 | 模板 | 问题 | 建议 |
|------|------|------|------|------|
| **高** | EM-4 | 急诊 | totalCapacity=0 使超额配置完全失效 | 改为 `overbookingEnabled=false, overbookingMax=0` |
| **高** | H-2 | 体检 | 候补+超额同时启用逻辑矛盾 | 二选一，推荐关闭候补 |
| **中** | EM-5 | 急诊 | 缺少取消窗口，依赖隐式默认行为 | 显式配置取消窗口 |
| **中** | EM-3 | 急诊 | afterGraceStatus=ON_TIME 语义矛盾 | 改为 `null`（不标记）或 `LATE` |
| **中** | S-1 | 标准门诊 | noCheckinAfterClose=KEEP_BOOKED 导致爽约不释放 | 改为 `ABSENT` |
| **中** | H-1 | 体检 | noCheckinAfterClose=KEEP_BOOKED | 改为 `AUTO_CANCEL` |
| **低** | E-1 | 专家门诊 | 签到窗口偏窄（60分钟） | closeOffsetSec 调为 5400 或 7200 |
| **低** | H-3 | 体检 | 取消截止-2天过严 | 调为 -86400（1天）或 -43200（12小时） |
| **低** | EM-1 | 急诊 | defaultCloseInclusive=true 与其他不一致 | 改为 false |
| **低** | EM-2 | 急诊 | perUserPerDay=0 语义模糊 | 添加注释说明 |
| **低** | E-2 | 专家门诊 | 预约窗口3天可能偏短 | 视排班发布周期调整为7或14天 |

### 4.2 建议的参数修正

以下为建议修正后的急诊模板关键参数（变化部分标 `*`）：

```typescript
// 急诊 - 建议修正版
{
  defaultCloseInclusive: false,              // * 与其他模板一致
  bookingPolicy: {
    perUserPerDay: 0,  // 0 表示不限制（后端判断逻辑已兼容）
    // ... 其余不变
  },
  checkinPolicy: {
    afterGraceStatus: null,                  // * 不标记（而非ON_TIME）
    // ... 其余不变
  },
  capacityPolicy: {
    totalCapacity: 0,
    waitlistEnabled: false,
    overbookingEnabled: false,               // * 总容量为0时超额无意义
    overbookingMax: 0,                       // *
  },
  windows: [
    // 预约时间窗（不变）
    // 签到时间窗（不变）
    {                                        // * 新增
      name: '取消时间窗',
      action: 'CANCEL',
      referencePoint: 'SHIFT_START',
      openOffsetSec: -86400,
      closeOffsetSec: 3600,
      openInclusive: true,
      closeInclusive: true,
      failPolicy: 'ALLOW_WITH_TAG',
      failTag: '超时取消',
      enabled: true,
    },
  ],
}
```

以下为建议修正后的标准门诊和体检的 `noCheckinAfterClose` 参数：

```typescript
// 标准门诊
checkinPolicy: {
  noCheckinAfterClose: 'ABSENT',             // * 从 KEEP_BOOKED 改为 ABSENT
}

// 体检预约
checkinPolicy: {
  noCheckinAfterClose: 'AUTO_CANCEL',        // * 从 KEEP_BOOKED 改为 AUTO_CANCEL
}
capacityPolicy: {
  waitlistEnabled: false,                    // * 从 true 改为 false（与超额二选一）
  // overbookingEnabled 和 overbookingMax 保持不变
}
windows: [
  // ...
  {
    name: '取消时间窗',
    // ...
    closeOffsetSec: -86400,                  // * 从 -172800(2天) 改为 -86400(1天)
  },
]
```

---

## 5 审查结论

四个预设模板整体设计合理，覆盖了不同业务场景的核心需求。主要问题集中在：

1. **急诊模板的容量策略配置**：`totalCapacity=0` 导致超额配置完全无效，是最需优先修复的问题
2. **体检模板的候补+超额并用**：两种机制在当前实现下会互相冲突，需要二选一
3. **爽约处理过于宽松**：标准门诊和体检的 `noCheckinAfterClose=KEEP_BOOKED` 会导致资源浪费
4. **急诊模板的语义矛盾**：`afterGraceStatus=ON_TIME` 和缺失取消窗口应修正

上述问题均为配置层面的问题，不涉及代码逻辑缺陷。修改建议可在后台管理页面直接调整预设模板的默认值即可生效。
