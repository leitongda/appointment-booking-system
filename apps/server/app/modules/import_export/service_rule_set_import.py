"""规则组导入服务"""
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from openpyxl import load_workbook
from io import BytesIO

from app.models.rule_set import (
    RuleSet, RuleWindow, RuleBookingPolicy, RuleCheckinPolicy,
    RuleCapacityPolicy, ShiftType, RuleSetShiftType
)


class RuleSetImportService:
    """规则组导入服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def import_rule_sets(self, file_content: bytes, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        导入规则组数据

        Args:
            file_content: Excel 文件内容
            tenant_id: 租户ID，用于租户隔离

        Returns:
            导入结果统计
        """
        if not tenant_id:
            from app.middleware.tenant_context import get_current_tenant_id
            tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("导入规则组需要租户上下文")
        # 解析多工作表 Excel
        wb = load_workbook(filename=BytesIO(file_content), read_only=True)

        # 解析各工作表
        rule_sets_data = self._parse_sheet(wb, "规则组", self._get_rule_set_headers())
        windows_data = self._parse_sheet(wb, "时间窗", self._get_window_headers())
        booking_data = self._parse_sheet(wb, "预约策略", self._get_booking_headers())
        checkin_data = self._parse_sheet(wb, "签到策略", self._get_checkin_headers())
        capacity_data = self._parse_sheet(wb, "容量策略", self._get_capacity_headers())

        wb.close()

        # 验证数据
        errors = []
        errors.extend(self._validate_rule_sets(rule_sets_data))
        errors.extend(self._validate_references(
            rule_sets_data, windows_data, booking_data, checkin_data, capacity_data
        ))

        if errors:
            return {
                "success_count": 0,
                "fail_count": len(errors),
                "total": len(errors),
                "errors": errors
            }

        # 导入数据
        success_count = 0
        fail_count = 0

        for rs_data in rule_sets_data:
            try:
                await self._import_rule_set(
                    rs_data,
                    windows_data,
                    booking_data,
                    checkin_data,
                    capacity_data,
                    tenant_id=tenant_id,
                )
                success_count += 1
            except Exception as e:
                fail_count += 1
                errors.append({
                    "row": rs_data.get("_row", 0),
                    "data": rs_data,
                    "errors": [str(e)]
                })

        await self.db.commit()

        if success_count > 0 and tenant_id:
            from app.core.redis import RedisCache
            from app.modules.rule_engine.cache import RuleCache
            try:
                await RuleCache(RedisCache()).invalidate_tenant(tenant_id)
            except Exception:
                pass

        return {
            "success_count": success_count,
            "fail_count": fail_count,
            "total": success_count + fail_count,
            "errors": errors[:50]
        }

    def _parse_sheet(self, wb, sheet_name: str, expected_headers: List[str]) -> List[Dict[str, Any]]:
        """解析单个工作表"""
        if sheet_name not in wb.sheetnames:
            return []

        ws = wb[sheet_name]
        rows = []

        # 读取表头
        headers = []
        for cell in ws[1]:
            headers.append(str(cell.value).strip() if cell.value else "")

        # 建立表头映射
        header_map = {}
        for idx, expected in enumerate(expected_headers):
            for actual_idx, actual in enumerate(headers):
                if actual == expected:
                    header_map[expected] = actual_idx
                    break

        if len(header_map) < len(expected_headers):
            # 表头不匹配，尝试模糊匹配
            for idx, expected in enumerate(expected_headers):
                if expected not in header_map:
                    for actual_idx, actual in enumerate(headers):
                        if expected.replace("(", "\uff08").replace(")", "\uff09") == actual or \
                           actual.replace("(", "\uff08").replace(")", "\uff09") == expected:
                            header_map[expected] = actual_idx
                            break

        # 读取数据行
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            if not any(row):  # 跳过空行
                continue

            row_data = {"_row": row_idx}
            for header in expected_headers:
                col_idx = header_map.get(header)
                if col_idx is not None and col_idx < len(row):
                    value = row[col_idx]
                    if isinstance(value, str):
                        value = value.strip()
                    row_data[header] = value
                else:
                    row_data[header] = None

            rows.append(row_data)

        return rows

    def _get_rule_set_headers(self) -> List[str]:
        return ["规则组名称", "优先级", "是否启用", "时间来源", "时区来源", "比较精度",
                "开放边界包含", "截止边界包含", "取整模式", "时钟偏差容忍度(秒)", "描述"]

    def _get_window_headers(self) -> List[str]:
        return ["规则组名称", "动作类型", "参考点", "开放偏移(秒)", "截止偏移(秒)",
                "开放边界包含", "截止边界包含", "失败策略", "失败标签", "是否启用", "描述"]

    def _get_booking_headers(self) -> List[str]:
        return ["规则组名称", "要求登录", "要求档案完整", "每用户每班次", "每用户每天", "每用户每周",
                "同班次冲突策略", "时间重叠策略", "同类型同日策略"]

    def _get_checkin_headers(self) -> List[str]:
        return ["规则组名称", "必须预约", "允许现场补约", "允许签到次数", "记录审计日志",
                "宽限期(秒)", "宽限后状态", "截止后未签到处理"]

    def _get_capacity_headers(self) -> List[str]:
        return ["规则组名称", "总容量", "每用户容量", "启用候补", "候补队列最大长度",
                "候补递补策略", "允许超额", "超额最大数量"]

    def _validate_rule_sets(self, rule_sets_data: List[Dict]) -> List[Dict]:
        """验证规则组基础数据"""
        errors = []
        seen_names = set()

        for rs in rule_sets_data:
            row = rs.get("_row", 0)

            # 检查必填字段
            if not rs.get("规则组名称"):
                errors.append({
                    "row": row,
                    "data": rs,
                    "errors": ["规则组名称为必填项"]
                })
                continue

            # 检查名称重复
            name = rs["规则组名称"]
            if name in seen_names:
                errors.append({
                    "row": row,
                    "data": rs,
                    "errors": [f"规则组名称 '{name}' 重复"]
                })
            seen_names.add(name)

        return errors

    def _validate_references(self, rule_sets_data, windows_data, booking_data,
                            checkin_data, capacity_data) -> List[Dict]:
        """验证数据关联关系"""
        errors = []
        rule_set_names = {rs["规则组名称"] for rs in rule_sets_data if rs.get("规则组名称")}

        # 验证时间窗的规则组引用
        for window in windows_data:
            rs_name = window.get("规则组名称")
            if rs_name and rs_name not in rule_set_names:
                errors.append({
                    "row": window.get("_row", 0),
                    "data": window,
                    "errors": [f"规则组 '{rs_name}' 不存在"]
                })

        # 验证预约策略的规则组引用
        for policy in booking_data:
            rs_name = policy.get("规则组名称")
            if rs_name and rs_name not in rule_set_names:
                errors.append({
                    "row": policy.get("_row", 0),
                    "data": policy,
                    "errors": [f"规则组 '{rs_name}' 不存在"]
                })

        # 验证签到策略的规则组引用
        for policy in checkin_data:
            rs_name = policy.get("规则组名称")
            if rs_name and rs_name not in rule_set_names:
                errors.append({
                    "row": policy.get("_row", 0),
                    "data": policy,
                    "errors": [f"规则组 '{rs_name}' 不存在"]
                })

        # 验证容量策略的规则组引用
        for policy in capacity_data:
            rs_name = policy.get("规则组名称")
            if rs_name and rs_name not in rule_set_names:
                errors.append({
                    "row": policy.get("_row", 0),
                    "data": policy,
                    "errors": [f"规则组 '{rs_name}' 不存在"]
                })

        return errors

    async def _import_rule_set(self, rs_data: Dict, windows_data: List,
                               booking_data: List, checkin_data: List,
                               capacity_data: List, tenant_id: str):
        """导入单个规则组及其关联数据"""

        # 检查是否已存在（同一租户内名称不能重复）
        existing = await self.db.execute(
            select(RuleSet).where(
                RuleSet.name == rs_data["规则组名称"],
                RuleSet.tenant_id == tenant_id,
            )
        )
        if existing.scalar():
            raise ValueError(f"规则组 '{rs_data['规则组名称']}' 已存在")

        # 解析布尔值
        def parse_bool(val):
            if val in ["是", "1", 1, True, "true", "True"]:
                return True
            if val in ["否", "0", 0, False, "false", "False"]:
                return False
            return None

        # 创建规则组
        rule_set = RuleSet(
            name=rs_data["规则组名称"],
            priority=int(rs_data.get("优先级", 100) or 100),
            enabled=parse_bool(rs_data.get("是否启用")) or True,
            time_source=rs_data.get("时间来源") or "SERVER",
            timezone_source=rs_data.get("时区来源") or "HOSPITAL",
            compare_precision=rs_data.get("比较精度") or "SECOND",
            default_open_inclusive=parse_bool(rs_data.get("开放边界包含")) if rs_data.get("开放边界包含") else True,
            default_close_inclusive=parse_bool(rs_data.get("截止边界包含")) if rs_data.get("截止边界包含") else True,
            rounding_mode=rs_data.get("取整模式") or "NONE",
            clock_skew_tolerance_sec=int(rs_data.get("时钟偏差容忍度(秒)", 5) or 5),
            description=rs_data.get("描述"),
            tenant_id=tenant_id,
        )
        self.db.add(rule_set)
        await self.db.flush()

        # 导入时间窗
        for window_data in windows_data:
            if window_data.get("规则组名称") == rs_data["规则组名称"]:
                window = RuleWindow(
                    rule_set_id=rule_set.id,
                    action=window_data.get("动作类型") or "BOOK",
                    reference_point=window_data.get("参考点") or "SHIFT_START",
                    open_offset_sec=int(window_data.get("开放偏移(秒)", 0) or 0),
                    close_offset_sec=int(window_data.get("截止偏移(秒)", 0) or 0),
                    open_inclusive=parse_bool(window_data.get("开放边界包含")),
                    close_inclusive=parse_bool(window_data.get("截止边界包含")),
                    fail_policy=window_data.get("失败策略") or "REJECT",
                    fail_tag=window_data.get("失败标签"),
                    enabled=parse_bool(window_data.get("是否启用")) if window_data.get("是否启用") else True,
                    description=window_data.get("描述"),
                )
                self.db.add(window)

        # 导入预约策略
        for policy_data in booking_data:
            if policy_data.get("规则组名称") == rs_data["规则组名称"]:
                booking_policy = RuleBookingPolicy(
                    rule_set_id=rule_set.id,
                    require_auth=parse_bool(policy_data.get("要求登录")) if policy_data.get("要求登录") else True,
                    require_patient_profile_complete=parse_bool(policy_data.get("要求档案完整")) or False,
                    per_user_per_shift=int(policy_data.get("每用户每班次", 1) or 1),
                    per_user_per_day=int(policy_data.get("每用户每天")) if policy_data.get("每用户每天") else None,
                    per_user_per_week=int(policy_data.get("每用户每周")) if policy_data.get("每用户每周") else None,
                    conflict_same_shift=policy_data.get("同班次冲突策略") or "REJECT",
                    conflict_overlap_time=policy_data.get("时间重叠策略") or "REJECT",
                    conflict_same_type_same_day=policy_data.get("同类型同日策略") or "ALLOW",
                )
                self.db.add(booking_policy)

        # 导入签到策略
        for policy_data in checkin_data:
            if policy_data.get("规则组名称") == rs_data["规则组名称"]:
                checkin_policy = RuleCheckinPolicy(
                    rule_set_id=rule_set.id,
                    require_booking=parse_bool(policy_data.get("必须预约")) if policy_data.get("必须预约") else True,
                    allow_onsite_booking=parse_bool(policy_data.get("允许现场补约")) or False,
                    max_times=int(policy_data.get("允许签到次数", 1) or 1),
                    audit_log=parse_bool(policy_data.get("记录审计日志")) if policy_data.get("记录审计日志") else True,
                    grace_period_sec=int(policy_data.get("宽限期(秒)", 0) or 0),
                    after_grace_status=policy_data.get("宽限后状态"),
                    no_checkin_after_close=policy_data.get("截止后未签到处理") or "KEEP_BOOKED",
                )
                self.db.add(checkin_policy)

        # 导入容量策略
        for policy_data in capacity_data:
            if policy_data.get("规则组名称") == rs_data["规则组名称"]:
                capacity_policy = RuleCapacityPolicy(
                    rule_set_id=rule_set.id,
                    total_capacity=int(policy_data.get("总容量", 0) or 0),
                    per_user_capacity=int(policy_data.get("每用户容量", 1) or 1),
                    waitlist_enabled=parse_bool(policy_data.get("启用候补")) or False,
                    waitlist_max_size=int(policy_data.get("候补队列最大长度", 0) or 0),
                    waitlist_promote_policy=policy_data.get("候补递补策略") or "MANUAL",
                    overbooking_enabled=parse_bool(policy_data.get("允许超额")) or False,
                    overbooking_max=int(policy_data.get("超额最大数量", 0) or 0),
                )
                self.db.add(capacity_policy)

        await self.db.flush()
