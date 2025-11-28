"""系统设置服务"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, Dict, Any
import uuid
import json

from app.models.settings import SystemSetting, DEFAULT_SETTINGS


class SettingsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_category(self, category: str) -> Dict[str, Any]:
        """获取某个分类的所有设置"""
        result = await self.db.execute(
            select(SystemSetting).where(SystemSetting.category == category)
        )
        settings = result.scalars().all()
        
        # 构建结果字典
        data = {}
        for setting in settings:
            data[setting.key] = self._parse_value(setting.value)
        
        # 补充默认值
        defaults = DEFAULT_SETTINGS.get(category, {})
        for key, config in defaults.items():
            if key not in data:
                data[key] = self._parse_value(config['value'])
        
        return data

    async def get_value(self, category: str, key: str, default: Any = None) -> Any:
        """获取单个设置值"""
        result = await self.db.execute(
            select(SystemSetting).where(
                and_(
                    SystemSetting.category == category,
                    SystemSetting.key == key
                )
            )
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            return self._parse_value(setting.value)
        
        # 返回默认值
        defaults = DEFAULT_SETTINGS.get(category, {})
        if key in defaults:
            return self._parse_value(defaults[key]['value'])
        
        return default

    async def set_value(self, category: str, key: str, value: Any, description: str = None) -> SystemSetting:
        """设置单个值"""
        result = await self.db.execute(
            select(SystemSetting).where(
                and_(
                    SystemSetting.category == category,
                    SystemSetting.key == key
                )
            )
        )
        setting = result.scalar_one_or_none()
        
        str_value = self._stringify_value(value)
        
        if setting:
            setting.value = str_value
            if description:
                setting.description = description
        else:
            setting = SystemSetting(
                id=str(uuid.uuid4()),
                category=category,
                key=key,
                value=str_value,
                description=description or DEFAULT_SETTINGS.get(category, {}).get(key, {}).get('description'),
            )
            self.db.add(setting)
        
        await self.db.commit()
        await self.db.refresh(setting)
        return setting

    async def update_category(self, category: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新某个分类的所有设置"""
        for key, value in data.items():
            await self.set_value(category, key, value)
        
        return await self.get_by_category(category)

    async def get_booking_settings(self) -> Dict[str, Any]:
        """获取预约设置"""
        data = await self.get_by_category('booking')
        return {
            'advanceDays': data.get('advance_days', 14),
            'sameDayBooking': data.get('same_day_booking', True),
            'cancelHours': data.get('cancel_hours', 2),
            'perDayLimit': data.get('per_day_limit', 3),
            'perDoctorLimit': data.get('per_doctor_limit', 1),
            'noShowLimit': data.get('no_show_limit', 3),
            'blacklistDays': data.get('blacklist_days', 30),
        }

    async def get_hospital_info(self) -> Dict[str, Any]:
        """获取医院信息"""
        data = await self.get_by_category('hospital')
        return {
            'hospitalName': data.get('name', ''),
            'hospitalLevel': data.get('level', ''),
            'address': data.get('address', ''),
            'phone': data.get('phone', ''),
            'workTime': data.get('work_time', ''),
            'introduction': data.get('introduction', ''),
            'logo': data.get('logo', ''),
        }

    async def get_wechat_config(self) -> Dict[str, Any]:
        """获取微信配置"""
        data = await self.get_by_category('wechat')
        return {
            'appId': data.get('app_id', ''),
            'appSecret': data.get('app_secret', ''),
            'mchId': data.get('mch_id', ''),
            'apiKey': data.get('api_key', ''),
            'notifyUrl': data.get('notify_url', ''),
        }

    async def get_sms_config(self) -> Dict[str, Any]:
        """获取短信配置"""
        data = await self.get_by_category('sms')
        return {
            'smsProvider': data.get('provider', 'aliyun'),
            'accessKeyId': data.get('access_key_id', ''),
            'accessKeySecret': data.get('access_key_secret', ''),
            'signName': data.get('sign_name', ''),
            'templateCode': data.get('template_code', ''),
        }

    def _parse_value(self, value: str) -> Any:
        """解析值"""
        if value is None:
            return None
        
        # 尝试解析为布尔值
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        
        # 尝试解析为数字
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # 尝试解析为JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            pass
        
        return value

    def _stringify_value(self, value: Any) -> str:
        """将值转为字符串"""
        if isinstance(value, bool):
            return 'true' if value else 'false'
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)


