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

    async def get_email_config(self) -> Dict[str, Any]:
        """获取邮件配置"""
        data = await self.get_by_category('email')
        return {
            'smtp_host': data.get('smtp_host', ''),
            'smtp_port': data.get('smtp_port', 465),
            'smtp_user': data.get('smtp_user', ''),
            'smtp_password': data.get('smtp_password', ''),
            'smtp_ssl': data.get('smtp_ssl', True),
            'sender_name': data.get('sender_name', ''),
            'sender_email': data.get('sender_email', ''),
        }

    async def update_email_config(
        self,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_password: str = None,
        smtp_ssl: bool = None,
        sender_name: str = None,
        sender_email: str = None,
    ) -> Dict[str, Any]:
        """更新邮件配置"""
        if smtp_host is not None:
            await self.set_value('email', 'smtp_host', smtp_host, 'SMTP服务器地址')
        if smtp_port is not None:
            await self.set_value('email', 'smtp_port', smtp_port, 'SMTP端口')
        if smtp_user is not None:
            await self.set_value('email', 'smtp_user', smtp_user, 'SMTP用户名')
        if smtp_password is not None:
            await self.set_value('email', 'smtp_password', smtp_password, 'SMTP密码')
        if smtp_ssl is not None:
            await self.set_value('email', 'smtp_ssl', smtp_ssl, '是否使用SSL')
        if sender_name is not None:
            await self.set_value('email', 'sender_name', sender_name, '发件人名称')
        if sender_email is not None:
            await self.set_value('email', 'sender_email', sender_email, '发件人邮箱')
        
        return await self.get_email_config()

    async def get_booking_fields(self) -> list:
        """获取预约选项配置"""
        data = await self.get_by_category('booking_fields')
        
        # 字段顺序和中文名称
        field_names = {
            'name': '姓名',
            'phone': '联系电话',
            'gender': '性别',
            'province_city_district': '省/市/区',
            'street': '街道/社区',
            'card_no': '就诊卡编号',
            'id_card_type': '证件类型',
            'id_card': '证件号',
            'ethnicity': '民族',
            'birthday': '出生日期',
            'age': '年龄',
            'relationship': '关系',
            'address': '详细地址',
        }
        
        result = []
        for field, name in field_names.items():
            config = data.get(field, {'enabled': False, 'required': False})
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except:
                    config = {'enabled': False, 'required': False}
            
            result.append({
                'field': field,
                'name': name,
                'enabled': config.get('enabled', False),
                'required': config.get('required', False),
            })
        
        return result

    async def update_booking_field(self, field: str, enabled: bool, required: bool) -> Dict[str, Any]:
        """更新单个预约选项配置"""
        value = {'enabled': enabled, 'required': required}
        await self.set_value('booking_fields', field, value)
        return value

    async def update_booking_fields(self, fields: list) -> list:
        """批量更新预约选项配置"""
        for item in fields:
            field = item.get('field')
            enabled = item.get('enabled', False)
            required = item.get('required', False)
            if field:
                await self.update_booking_field(field, enabled, required)
        
        return await self.get_booking_fields()

    async def get_patient_card_config(self) -> Dict[str, Any]:
        """获取就诊卡配置"""
        data = await self.get_by_category('patient_card')
        return {
            'cardName': data.get('card_name', '就诊卡'),
            'cardDescription': data.get('card_description', ''),
            'maxCardsPerUser': data.get('max_cards_per_user', 5),
            'showOnHomepage': data.get('show_on_homepage', False),
        }

    async def update_patient_card_config(
        self,
        card_name: str = None,
        card_description: str = None,
        max_cards_per_user: int = None,
        show_on_homepage: bool = None,
    ) -> Dict[str, Any]:
        """更新就诊卡配置"""
        if card_name is not None:
            await self.set_value('patient_card', 'card_name', card_name)
        if card_description is not None:
            await self.set_value('patient_card', 'card_description', card_description)
        if max_cards_per_user is not None:
            await self.set_value('patient_card', 'max_cards_per_user', max_cards_per_user)
        if show_on_homepage is not None:
            await self.set_value('patient_card', 'show_on_homepage', show_on_homepage)
        
        return await self.get_patient_card_config()

    async def get_image_config(self) -> Dict[str, Any]:
        """获取图片处理配置"""
        data = await self.get_by_category('image')
        
        # 解析缩略图尺寸
        thumbnail_sizes = data.get('thumbnail_sizes', [])
        if isinstance(thumbnail_sizes, str):
            try:
                thumbnail_sizes = json.loads(thumbnail_sizes)
            except json.JSONDecodeError:
                thumbnail_sizes = []
        
        return {
            'thumbnailSizes': thumbnail_sizes,
            'compressQuality': data.get('compress_quality', 85),
        }

    async def update_image_config(
        self,
        thumbnail_sizes: list = None,
        compress_quality: int = None,
    ) -> Dict[str, Any]:
        """更新图片处理配置"""
        if thumbnail_sizes is not None:
            await self.set_value('image', 'thumbnail_sizes', thumbnail_sizes, '缩略图尺寸配置')
        if compress_quality is not None:
            # 确保质量在有效范围内
            compress_quality = max(1, min(100, compress_quality))
            await self.set_value('image', 'compress_quality', compress_quality, '压缩质量')
        
        return await self.get_image_config()

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


