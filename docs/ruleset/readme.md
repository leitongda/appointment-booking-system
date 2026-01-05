“医院预约系统（预约+签到）”可高度组合的**后台配置项抽象**。

目标是：不靠写死逻辑，靠**时间窗 + 边界 + 状态策略 + 冲突策略**拼出几乎所有规则。

---

## 0）抽象原则

把所有限制拆成 4 类配置：

1. **时间参考点**：以班次的 `startAt / endAt` 或“预约成功时间”等为基准
2. **时间窗**：开放/截止，支持“提前/延后”
3. **边界与校验口径**：是否包含边界、用服务端时间/用户时间、时区
4. **策略**：不满足规则时如何处理（拒绝/候补/置为迟到/自动取消等）

---

## 1）后台配置结构（推荐“规则组 + 规则项”）

### 1.1 规则组（RuleSet）

用于按科室/医生/号源类型应用不同规则。

* `ruleSetId`
* `name`
* `scope`：适用范围（全局/院区/科室/医生/号源类型/渠道）
* `priority`：多规则冲突时优先级（大优先或小优先，二选一）
* `enabled`

> 实现上：一次生效只挑一个 RuleSet（按优先级匹配），或多套叠加（复杂但更灵活）。

---

## 2）时间相关配置：统一用“时间窗 Window”

### 2.1 通用 Window 配置项（核心）

一个 Window 用于“允许执行某动作的时间区间”。

**Window 定义：**

* `action`：动作类型

  * `BOOK`（预约）
  * `CANCEL`（取消预约）
  * `CHECKIN`（签到）
  * （可扩展：改期 RESCHEDULE、候补 WAITLIST_JOIN 等）
* `reference`：参考点（枚举）

  * `SHIFT_START`（班次开始）
  * `SHIFT_END`（班次结束）
  * `BOOKING_CREATED_AT`（预约成功时间）
  * `CHECKIN_OPEN_AT`（签到开放时间，便于链式）
* `openOffset`：开放偏移（duration，可正可负）

  * 例：`-7d` 表示提前 7 天开放
  * 例：`-10m` 表示提前 10 分钟开放
* `closeOffset`：截止偏移（duration，可正可负）

  * 例：`-30m` 表示开始前 30 分钟截止
  * 例：`+15m` 表示开始后 15 分钟截止
* `openInclusive`：是否包含开放边界（true/false）
* `closeInclusive`：是否包含截止边界（true/false）
* `timeSource`：时间来源（强烈建议默认 SERVER）

  * `SERVER` / `CLIENT`
* `timezoneSource`：时区来源

  * `HOSPITAL`（院区时区）/ `SHIFT`（班次所属）/ `USER`
* `failPolicy`：不在窗口内怎么处理（枚举）

  * `REJECT`（拒绝）
  * `ALLOW_WITH_TAG`（允许但打标签，如“超时预约/迟到签到”）
  * `AUTO_TO_WAITLIST`（自动转候补，仅对预约类动作有意义）

> 你把“提前多久”“延后多久”“是否包含边界”等都塞进 Window 里，就能组合出极多规则。

---

## 3）预约（BOOK）建议的最小配置集

### 3.1 预约窗口（BOOK_WINDOW）

一个 Window：

* `action=BOOK`
* `reference=SHIFT_START`（大多数以开始为准）
* `openOffset`：如 `-7d`
* `closeOffset`：如 `-30m`
* `openInclusive/closeInclusive`
* `failPolicy=REJECT`

### 3.2 容量与资源策略（非时间窗，但必须可配）

* `capacity.total`：总名额
* `capacity.perUser`：每用户最多占用几个名额（通常 1）
* `waitlist.enabled`：是否启用候补
* `waitlist.maxSize`：候补队列长度
* `waitlist.promotePolicy`：递补策略

  * `AUTO_PROMOTE_IMMEDIATE`（有人取消立即递补）
  * `AUTO_PROMOTE_AT_TIME`（在某时间点统一递补，比如开始前 2 小时）
  * `MANUAL`（人工确认）
* `overbooking.enabled`：是否允许超额（医院有些场景会开“加号”）

### 3.3 重复/冲突预约策略（医院很常见）

* `conflict.sameShift`：同一班次重复预约

  * `REJECT` / `REPLACE`（覆盖旧单）/ `ALLOW`（不建议）
* `conflict.overlapTime`：时间重叠的班次是否允许同用户预约

  * `REJECT` / `ALLOW`
* `conflict.sameDeptSameDay`：同科室同日限制
* `quota.perDay / perWeek / perMonth`：周期配额（可选）

---

## 4）签到（CHECKIN）建议的最小配置集

### 4.1 签到窗口（CHECKIN_WINDOW）

一个 Window：

* `action=CHECKIN`
* `reference=SHIFT_START`（常用）
* `openOffset`：如 `-10m`
* `closeOffset`：如 `+15m`
* `openInclusive/closeInclusive`
* `failPolicy`：医院常见是：

  * 超过截止：`REJECT`（不能签到）+ 自动标记未到
  * 或 `ALLOW_WITH_TAG`（允许但记“迟到”）

### 4.2 签到前置条件（可配置）

* `checkin.requireBooking`：是否必须预约才可签到（true/false）
* `checkin.allowOnsiteBooking`：是否允许现场补预约再签到（true/false）
* `checkin.maxTimes`：允许签到次数（通常 1）
* `checkin.identityMode`：核验方式（医院可能要）

  * `QR` / `ID_CARD` / `PHONE` / `MANUAL`

### 4.3 迟到与缺席的状态策略（强烈建议可配）

* `attendance.gracePeriod`：宽限期（例如 +5m 仍算准时）
* `attendance.afterGraceStatus`：超过宽限但在签到窗口内

  * `LATE` / `ON_TIME`（极少）
* `attendance.noCheckinAfterClose`：到截止仍未签到的处理

  * `ABSENT` / `AUTO_CANCEL` / `KEEP_BOOKED`

---

## 5）取消（CANCEL）也建议做成窗口（医院很需要）

同样用 Window：

* `action=CANCEL`
* `reference=SHIFT_START`
* `openOffset`：通常 `-9999d`（表示预约后随时可取消）或不配 open
* `closeOffset`：如 `-2h`（开始前2小时后不可取消）
* `failPolicy`：`REJECT` 或 `ALLOW_WITH_TAG`（允许取消但记违约）

再配：

* `cancel.penaltyPolicy`：违约策略（计入黑名单/扣次数/冻结X天等）

---

## 6）边界/口径类“全局系统设置”（你提到的重点）

这些不应该散落在各动作里，建议有全局默认值，Window 可覆盖。

* `default.timeSource = SERVER`
* `default.timezoneSource = HOSPITAL`
* `default.openInclusive = true`
* `default.closeInclusive = true`
* `default.rounding`：时间取整策略（医院常用“按分钟”）

  * `NONE` / `FLOOR_TO_MINUTE` / `CEIL_TO_MINUTE`
* `default.comparePrecision`：比较精度（秒/毫秒/分钟）
* `clockSkewTolerance`：允许客户端与服务端误差（即使 timeSource=SERVER，也可能用于展示）

  * 例：`<=5s` 直接忽略

---

## 7）给你一个可直接落库的配置示例（JSON 思路）

班次 10:00–11:00：

* 7 天前开放预约，开始前 30 分钟截止预约
* 开始前 10 分钟开放签到，开始后 15 分钟截止签到
* 边界都包含
* 必须先预约才能签到
* 超过 10:15 未签到标记缺席

```json
{
  "ruleSetId": "hospital_default",
  "scope": { "level": "HOSPITAL", "id": "all" },
  "defaults": {
    "timeSource": "SERVER",
    "timezoneSource": "HOSPITAL",
    "openInclusive": true,
    "closeInclusive": true,
    "comparePrecision": "SECOND"
  },
  "windows": [
    {
      "action": "BOOK",
      "reference": "SHIFT_START",
      "openOffset": "-7d",
      "closeOffset": "-30m",
      "failPolicy": "REJECT"
    },
    {
      "action": "CHECKIN",
      "reference": "SHIFT_START",
      "openOffset": "-10m",
      "closeOffset": "+15m",
      "failPolicy": "REJECT"
    },
    {
      "action": "CANCEL",
      "reference": "SHIFT_START",
      "openOffset": "-3650d",
      "closeOffset": "-2h",
      "failPolicy": "REJECT"
    }
  ],
  "policies": {
    "checkin": { "requireBooking": true, "maxTimes": 1 },
    "attendance": {
      "gracePeriod": "+5m",
      "afterGraceStatus": "LATE",
      "noCheckinAfterClose": "ABSENT"
    },
    "capacity": { "total": 20, "perUser": 1 },
    "waitlist": { "enabled": true, "maxSize": 30, "promotePolicy": "AUTO_PROMOTE_IMMEDIATE" }
  }
}
```

---

## 8）落地建议：实现时的“判定函数”统一化

无论预约/签到/取消，都走同一套判断：

1. 取动作对应 Window（先 RuleSet 匹配，再 action 过滤）
2. 算出 `openAt = referenceTime + openOffset`
3. 算出 `closeAt = referenceTime + closeOffset`
4. 用 `Inclusive` 和 `comparePrecision` 比较 `now`
5. 不满足 → 按 `failPolicy` 决策
6. 满足 → 再校验容量/冲突/前置条件等 policy