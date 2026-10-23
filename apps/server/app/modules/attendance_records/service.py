"""考勤打卡记录服务

负责签到/签退、记录查询、统计等业务逻辑。
"""
import math
import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.attendance import (
    AttendanceGroup,
    AttendanceRecord,
    AttendanceShift,
)


class AttendanceRecordService:
    """考勤打卡记录服务

    Args:
        db: 数据库会话
        tenant_id: 管理员账号租户锚点（R1-11）。管理端查询以锚点强过滤；
            未传入（平台管理员）表示全平台视图。打卡自助端按账号自身归属读写。
    """

    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------ #
    #  签到
    # ------------------------------------------------------------------ #

    async def check_in(
        self,
        *,
        account_id: str,
        tenant_id: str | None,
        account_name: str | None,
        lat: float,
        lng: float,
        device_info: str | None = None,
        group_id: str | None = None,
        wifi_ssid: str | None = None,
        device_id: str | None = None,
        remark: str | None = None,
    ) -> AttendanceRecord:
        """签到

        1. 验证当天是否已签到
        2. 验证位置是否在签到组范围内（如有 group_id）
        3. 验证 WiFi SSID / 设备白名单
        4. 创建记录，设置 check_in_time
        5. 判定迟到（对比班次 start_time + grace_minutes）
        """
        tenant_id = tenant_id or self.tenant_id or get_current_tenant_id()
        today = date.today()
        now = datetime.now()

        # 1. 检查是否已签到
        existing = await self._get_record_by_account_date(account_id, today)
        if existing and existing.check_in_time:
            raise ValueError("今日已签到，无需重复打卡")

        # 2. 确定班次
        shift = await self._resolve_shift(account_id, tenant_id)

        # 3. 验证签到组
        group = None
        if group_id:
            group = await self._get_group(group_id, tenant_id)
            if not group:
                raise ValueError("签到组不存在")
            if group.location_lat and group.location_lng:
                distance = self._calc_distance(
                    lat, lng, group.location_lat, group.location_lng
                )
                if distance > group.location_radius:
                    raise ValueError(
                        f"不在签到范围内（距离{int(distance)}米，要求{group.location_radius}米内）"
                    )

            # 3a. WiFi SSID 校验
            if "wifi" in (group.check_method or ""):
                allowed_ssids = self._parse_allowed_ssids(group)
                if allowed_ssids and wifi_ssid:
                    if wifi_ssid not in allowed_ssids:
                        raise ValueError(
                            f"WiFi SSID 不在允许列表中（当前: {wifi_ssid}）"
                        )
                elif allowed_ssids and not wifi_ssid:
                    raise ValueError("签到组要求 WiFi 校验，但未提供 WiFi SSID")

            # 3b. 设备白名单校验
            if "device" in (group.check_method or ""):
                if group.require_device_bind:
                    whitelist = self._parse_device_whitelist(group)
                    if whitelist and device_id:
                        if device_id not in whitelist:
                            raise ValueError(
                                f"设备不在白名单中（当前设备: {device_id}）"
                            )
                    elif whitelist and not device_id:
                        raise ValueError("签到组要求设备绑定，但未提供设备 ID")

        # 4. 判定迟到
        late_minutes = 0
        status = "normal"
        if shift:
            shift_start = datetime.combine(today, time.fromisoformat(shift.start_time))
            grace_deadline = shift_start + timedelta(minutes=shift.grace_minutes)
            if now > grace_deadline:
                late_minutes = int((now - shift_start).total_seconds() / 60)
                status = "late"

        # 5. 创建或更新记录
        if existing:
            record = existing
            record.check_in_time = now
            record.check_in_lat = lat
            record.check_in_lng = lng
            record.check_in_device = device_info
            record.status = status
            record.late_minutes = late_minutes
            if group_id:
                record.group_id = group_id
            if shift:
                record.shift_id = shift.id
            if remark:
                record.remark = remark
        else:
            record = AttendanceRecord(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                account_id=account_id,
                shift_id=shift.id if shift else None,
                group_id=group_id,
                check_date=today,
                check_in_time=now,
                check_in_lat=lat,
                check_in_lng=lng,
                check_in_device=device_info,
                status=status,
                late_minutes=late_minutes,
                remark=remark,
            )
            self.db.add(record)

        await self.db.commit()
        await self.db.refresh(record)
        return record

    # ------------------------------------------------------------------ #
    #  签退
    # ------------------------------------------------------------------ #

    async def check_out(
        self,
        *,
        account_id: str,
        lat: float,
        lng: float,
        device_info: str | None = None,
        remark: str | None = None,
    ) -> AttendanceRecord:
        """签退

        1. 验证已有签到记录
        2. 更新 check_out_time
        3. 判定早退（对比班次 end_time）
        4. 计算工作时长
        """
        today = date.today()
        now = datetime.now()

        record = await self._get_record_by_account_date(account_id, today)
        if not record or not record.check_in_time:
            raise ValueError("尚未签到，请先签到")

        if record.check_out_time:
            raise ValueError("今日已签退，无需重复打卡")

        # 确定班次
        shift = None
        if record.shift_id:
            result = await self.db.execute(
                select(AttendanceShift).where(AttendanceShift.id == record.shift_id)
            )
            shift = result.scalar_one_or_none()

        # 判定早退
        early_minutes = 0
        if shift:
            shift_end = datetime.combine(today, time.fromisoformat(shift.end_time))
            if now < shift_end:
                early_minutes = int((shift_end - now).total_seconds() / 60)
                if record.status == "normal":
                    record.status = "early"
                elif record.status == "late":
                    record.status = "late"  # 迟到 + 早退保持 late

        # 计算工作时长
        work_hours = round((now - record.check_in_time).total_seconds() / 3600, 2)

        record.check_out_time = now
        record.check_out_lat = lat
        record.check_out_lng = lng
        record.check_out_device = device_info
        record.early_minutes = early_minutes
        record.work_hours = work_hours
        if remark:
            record.remark = remark

        await self.db.commit()
        await self.db.refresh(record)
        return record

    # ------------------------------------------------------------------ #
    #  我的考勤记录
    # ------------------------------------------------------------------ #

    async def get_my_records(
        self,
        account_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[AttendanceRecord], int]:
        """获取我的考勤记录"""
        conditions = [AttendanceRecord.account_id == account_id]

        if start_date:
            conditions.append(AttendanceRecord.check_date >= start_date)
        if end_date:
            conditions.append(AttendanceRecord.check_date <= end_date)

        where = and_(*conditions)

        # 总数
        count_result = await self.db.execute(
            select(func.count(AttendanceRecord.id)).where(where)
        )
        total = count_result.scalar_one() or 0

        # 分页数据
        query = (
            select(AttendanceRecord)
            .where(where)
            .order_by(AttendanceRecord.check_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        records = list(result.scalars().all())

        return records, total

    # ------------------------------------------------------------------ #
    #  每日统计（管理员）
    # ------------------------------------------------------------------ #

    async def get_daily_stats(
        self, tenant_id: str | None, target_date: date
    ) -> dict:
        """获取某日考勤统计"""
        tenant_id = tenant_id or self.tenant_id
        conditions = [AttendanceRecord.check_date == target_date]
        if tenant_id:
            conditions.append(AttendanceRecord.tenant_id == tenant_id)

        where = and_(*conditions)

        # 按状态分别统计
        stats = {"total": 0, "normal": 0, "late": 0, "early": 0, "absent": 0, "leave": 0, "expected": 0}

        status_result = await self.db.execute(
            select(
                AttendanceRecord.status,
                func.count(AttendanceRecord.id).label("cnt"),
            )
            .where(where)
            .group_by(AttendanceRecord.status)
        )

        for row in status_result:
            cnt = row.cnt
            stats["total"] += cnt
            if row.status in stats:
                stats[row.status] = cnt

        return {
            "date": target_date.isoformat(),
            **stats,
        }

    # ------------------------------------------------------------------ #
    #  全部记录（管理员）
    # ------------------------------------------------------------------ #

    async def get_all_records(
        self,
        tenant_id: str | None,
        start_date: date | None = None,
        end_date: date | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[AttendanceRecord], int]:
        """获取全部考勤记录（管理员视图）"""
        tenant_id = tenant_id or self.tenant_id
        conditions = []
        if tenant_id:
            conditions.append(AttendanceRecord.tenant_id == tenant_id)
        if start_date:
            conditions.append(AttendanceRecord.check_date >= start_date)
        if end_date:
            conditions.append(AttendanceRecord.check_date <= end_date)

        where = and_(*conditions) if conditions else True

        # 总数
        count_result = await self.db.execute(
            select(func.count(AttendanceRecord.id)).where(where)
        )
        total = count_result.scalar_one() or 0

        # 分页数据
        query = (
            select(AttendanceRecord)
            .where(where)
            .order_by(AttendanceRecord.check_date.desc(), AttendanceRecord.check_in_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        records = list(result.scalars().all())

        return records, total

    # ------------------------------------------------------------------ #
    #  内部辅助
    # ------------------------------------------------------------------ #

    async def _get_record_by_account_date(
        self, account_id: str, target_date: date
    ) -> AttendanceRecord | None:
        """按账号+日期获取记录"""
        result = await self.db.execute(
            select(AttendanceRecord).where(
                and_(
                    AttendanceRecord.account_id == account_id,
                    AttendanceRecord.check_date == target_date,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _resolve_shift(
        self, account_id: str, tenant_id: str | None
    ) -> AttendanceShift | None:
        """解析账号对应的班次

        当前简化实现：返回租户下第一个启用的班次。
        后续可扩展为按签到组或排班表关联班次。
        """
        conditions = [AttendanceShift.enabled.is_(True)]
        if tenant_id:
            conditions.append(AttendanceShift.tenant_id == tenant_id)

        result = await self.db.execute(
            select(AttendanceShift)
            .where(and_(*conditions))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_group(
        self, group_id: str, tenant_id: str | None
    ) -> AttendanceGroup | None:
        """获取签到组"""
        conditions = [AttendanceGroup.id == group_id]
        if tenant_id:
            conditions.append(AttendanceGroup.tenant_id == tenant_id)

        result = await self.db.execute(
            select(AttendanceGroup).where(and_(*conditions))
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _parse_allowed_ssids(group: AttendanceGroup) -> list[str]:
        """解析签到组允许的 WiFi SSID 列表

        优先使用 wifi_ssids（多 SSID，逗号分隔），回退到 wifi_ssid（单个，向后兼容）。
        """
        raw = group.wifi_ssids or group.wifi_ssid
        if not raw:
            return []
        return [s.strip() for s in raw.split(",") if s.strip()]

    @staticmethod
    def _parse_device_whitelist(group: AttendanceGroup) -> list[str]:
        """解析签到组允许的设备 ID 列表（逗号分隔）"""
        raw = group.device_whitelist
        if not raw:
            return []
        return [s.strip() for s in raw.split(",") if s.strip()]

    @staticmethod
    def _calc_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """计算两点间距离（米），使用 Haversine 公式"""
        R = 6371000  # 地球半径（米）
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lng2 - lng1)

        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        )
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # ------------------------------------------------------------------ #
    #  排班联动：生成预期考勤记录
    # ------------------------------------------------------------------ #

    @staticmethod
    async def create_expected_records(db: AsyncSession, schedule) -> None:
        """为已发布的排班创建预期考勤记录。

        当排班发布时调用，为医生在排班日期创建一条 status="expected" 的记录。
        如果当天已有实际打卡记录（非 expected），则不覆盖。

        Args:
            db: 异步数据库会话
            schedule: Schedule ORM 对象（需包含 doctor_id, tenant_id, schedule_date, shift_type_id）
        """
        from sqlalchemy.exc import IntegrityError

        from app.models.schedule import Schedule

        account_id = schedule.doctor_id  # account_sync 中 doctor.id == account.id

        # 1. 如果已有实际打卡记录（非 expected），不覆盖
        existing_actual = await db.execute(
            select(AttendanceRecord).where(
                and_(
                    AttendanceRecord.account_id == account_id,
                    AttendanceRecord.check_date == schedule.schedule_date,
                    AttendanceRecord.status != "expected",
                )
            )
        )
        if existing_actual.scalar_one_or_none():
            return

        # 2. 如果已有预期记录，不重复创建
        existing_expected = await db.execute(
            select(AttendanceRecord).where(
                and_(
                    AttendanceRecord.account_id == account_id,
                    AttendanceRecord.check_date == schedule.schedule_date,
                    AttendanceRecord.status == "expected",
                )
            )
        )
        if existing_expected.scalar_one_or_none():
            return

        # 3. 尝试匹配考勤班次（通过 shift_type_id 或租户默认班次）
        shift_id = None
        if schedule.shift_type_id:
            # 排班的 shift_type_id 可能直接对应考勤班次
            shift_result = await db.execute(
                select(AttendanceShift).where(
                    and_(
                        AttendanceShift.id == schedule.shift_type_id,
                        AttendanceShift.enabled.is_(True),
                    )
                )
            )
            shift = shift_result.scalar_one_or_none()
            if shift:
                shift_id = shift.id

        if not shift_id:
            # 使用租户下第一个启用的默认班次
            default_shift_conditions = [AttendanceShift.enabled.is_(True)]
            if schedule.tenant_id:
                default_shift_conditions.append(AttendanceShift.tenant_id == schedule.tenant_id)
            default_shift_result = await db.execute(
                select(AttendanceShift)
                .where(and_(*default_shift_conditions))
                .limit(1)
            )
            default_shift = default_shift_result.scalar_one_or_none()
            if default_shift:
                shift_id = default_shift.id

        # 4. 创建预期记录
        record = AttendanceRecord(
            tenant_id=schedule.tenant_id,
            account_id=account_id,
            shift_id=shift_id,
            check_date=schedule.schedule_date,
            status="expected",
        )
        db.add(record)
        try:
            await db.flush()
        except IntegrityError:
            # 唯一约束冲突（并发场景），静默忽略
            await db.rollback()
