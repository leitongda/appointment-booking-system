"""系统设置 API"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.services.settings_service import SettingsService

router = APIRouter()


# ========== Schemas ==========
class BookingSettingsUpdate(BaseModel):
    advanceDays: Optional[int] = Field(None, ge=1, le=30)
    sameDayBooking: Optional[bool] = None
    cancelHours: Optional[int] = Field(None, ge=0, le=24)
    perDayLimit: Optional[int] = Field(None, ge=1, le=10)
    perDoctorLimit: Optional[int] = Field(None, ge=1, le=5)
    noShowLimit: Optional[int] = Field(None, ge=1, le=10)
    blacklistDays: Optional[int] = Field(None, ge=1, le=365)


class HospitalInfoUpdate(BaseModel):
    hospitalName: Optional[str] = Field(None, max_length=100)
    hospitalLevel: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=50)
    workTime: Optional[str] = Field(None, max_length=100)
    introduction: Optional[str] = None
    logo: Optional[str] = None


class WechatConfigUpdate(BaseModel):
    appId: Optional[str] = Field(None, max_length=100)
    appSecret: Optional[str] = Field(None, max_length=100)
    mchId: Optional[str] = Field(None, max_length=100)
    apiKey: Optional[str] = Field(None, max_length=100)
    notifyUrl: Optional[str] = Field(None, max_length=200)


class SmsConfigUpdate(BaseModel):
    smsProvider: Optional[str] = Field(None, max_length=50)
    accessKeyId: Optional[str] = Field(None, max_length=100)
    accessKeySecret: Optional[str] = Field(None, max_length=100)
    signName: Optional[str] = Field(None, max_length=50)
    templateCode: Optional[str] = Field(None, max_length=50)


class EmailConfigUpdate(BaseModel):
    smtpHost: Optional[str] = Field(None, max_length=100, description="SMTP服务器地址")
    smtpPort: Optional[int] = Field(None, ge=1, le=65535, description="SMTP端口")
    smtpUser: Optional[str] = Field(None, max_length=100, description="SMTP用户名")
    smtpPassword: Optional[str] = Field(None, max_length=200, description="SMTP密码")
    smtpSsl: Optional[bool] = Field(None, description="是否使用SSL")
    senderName: Optional[str] = Field(None, max_length=100, description="发件人名称")
    senderEmail: Optional[str] = Field(None, max_length=100, description="发件人邮箱")


# ========== 预约设置 ==========
@router.get("/booking")
async def get_booking_settings(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取预约设置"""
    service = SettingsService(db)
    return await service.get_booking_settings()


@router.put("/booking")
async def update_booking_settings(
    data: BookingSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """更新预约设置"""
    service = SettingsService(db)
    
    update_data = {}
    if data.advanceDays is not None:
        update_data['advance_days'] = data.advanceDays
    if data.sameDayBooking is not None:
        update_data['same_day_booking'] = data.sameDayBooking
    if data.cancelHours is not None:
        update_data['cancel_hours'] = data.cancelHours
    if data.perDayLimit is not None:
        update_data['per_day_limit'] = data.perDayLimit
    if data.perDoctorLimit is not None:
        update_data['per_doctor_limit'] = data.perDoctorLimit
    if data.noShowLimit is not None:
        update_data['no_show_limit'] = data.noShowLimit
    if data.blacklistDays is not None:
        update_data['blacklist_days'] = data.blacklistDays
    
    await service.update_category('booking', update_data)
    return {"message": "保存成功"}


# ========== 医院信息 ==========
@router.get("/hospital")
async def get_hospital_info(
    db: AsyncSession = Depends(get_db),
):
    """获取医院信息（公开接口）"""
    service = SettingsService(db)
    return await service.get_hospital_info()


@router.put("/hospital")
async def update_hospital_info(
    data: HospitalInfoUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """更新医院信息"""
    service = SettingsService(db)
    
    update_data = {}
    if data.hospitalName is not None:
        update_data['name'] = data.hospitalName
    if data.hospitalLevel is not None:
        update_data['level'] = data.hospitalLevel
    if data.address is not None:
        update_data['address'] = data.address
    if data.phone is not None:
        update_data['phone'] = data.phone
    if data.workTime is not None:
        update_data['work_time'] = data.workTime
    if data.introduction is not None:
        update_data['introduction'] = data.introduction
    if data.logo is not None:
        update_data['logo'] = data.logo
    
    await service.update_category('hospital', update_data)
    return {"message": "保存成功"}


# ========== 微信配置 ==========
@router.get("/wechat")
async def get_wechat_config(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取微信配置"""
    service = SettingsService(db)
    config = await service.get_wechat_config()
    # 隐藏敏感信息
    if config.get('appSecret'):
        config['appSecret'] = '******'
    if config.get('apiKey'):
        config['apiKey'] = '******'
    return config


@router.put("/wechat")
async def update_wechat_config(
    data: WechatConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """更新微信配置"""
    service = SettingsService(db)
    
    update_data = {}
    if data.appId is not None:
        update_data['app_id'] = data.appId
    if data.appSecret is not None and data.appSecret != '******':
        update_data['app_secret'] = data.appSecret
    if data.mchId is not None:
        update_data['mch_id'] = data.mchId
    if data.apiKey is not None and data.apiKey != '******':
        update_data['api_key'] = data.apiKey
    if data.notifyUrl is not None:
        update_data['notify_url'] = data.notifyUrl
    
    await service.update_category('wechat', update_data)
    return {"message": "保存成功"}


# ========== 短信配置 ==========
@router.get("/sms")
async def get_sms_config(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取短信配置"""
    service = SettingsService(db)
    config = await service.get_sms_config()
    # 隐藏敏感信息
    if config.get('accessKeySecret'):
        config['accessKeySecret'] = '******'
    return config


@router.put("/sms")
async def update_sms_config(
    data: SmsConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """更新短信配置"""
    service = SettingsService(db)
    
    update_data = {}
    if data.smsProvider is not None:
        update_data['provider'] = data.smsProvider
    if data.accessKeyId is not None:
        update_data['access_key_id'] = data.accessKeyId
    if data.accessKeySecret is not None and data.accessKeySecret != '******':
        update_data['access_key_secret'] = data.accessKeySecret
    if data.signName is not None:
        update_data['sign_name'] = data.signName
    if data.templateCode is not None:
        update_data['template_code'] = data.templateCode
    
    await service.update_category('sms', update_data)
    return {"message": "保存成功"}


# ========== 邮件配置 ==========
@router.get("/email")
async def get_email_config(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取邮件配置"""
    service = SettingsService(db)
    config = await service.get_email_config()
    # 隐藏敏感信息
    if config.get('smtp_password'):
        config['smtp_password'] = '******'
    # 转换为驼峰命名
    return {
        'smtpHost': config.get('smtp_host', ''),
        'smtpPort': config.get('smtp_port', 465),
        'smtpUser': config.get('smtp_user', ''),
        'smtpPassword': config.get('smtp_password', ''),
        'smtpSsl': config.get('smtp_ssl', True),
        'senderName': config.get('sender_name', ''),
        'senderEmail': config.get('sender_email', ''),
    }


@router.put("/email")
async def update_email_config(
    data: EmailConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """更新邮件配置"""
    service = SettingsService(db)
    
    await service.update_email_config(
        smtp_host=data.smtpHost,
        smtp_port=data.smtpPort,
        smtp_user=data.smtpUser,
        smtp_password=data.smtpPassword if data.smtpPassword != '******' else None,
        smtp_ssl=data.smtpSsl,
        sender_name=data.senderName,
        sender_email=data.senderEmail,
    )
    return {"message": "保存成功"}


# ========== 公开接口：获取预约规则 ==========
@router.get("/booking/rules")
async def get_booking_rules(
    db: AsyncSession = Depends(get_db),
):
    """获取预约规则（公开接口，用于患者端）"""
    service = SettingsService(db)
    settings = await service.get_booking_settings()
    
    # 只返回患者需要知道的规则
    return {
        'advanceDays': settings.get('advanceDays', 14),
        'sameDayBooking': settings.get('sameDayBooking', True),
        'cancelHours': settings.get('cancelHours', 2),
        'perDayLimit': settings.get('perDayLimit', 3),
    }


# ========== 预约选项配置 ==========
class BookingFieldUpdate(BaseModel):
    field: str
    enabled: bool
    required: bool


class BookingFieldsUpdate(BaseModel):
    fields: list[BookingFieldUpdate]


@router.get("/booking-fields")
async def get_booking_fields(
    db: AsyncSession = Depends(get_db),
):
    """获取预约选项配置（公开接口，用于动态渲染表单）"""
    service = SettingsService(db)
    return await service.get_booking_fields()


@router.put("/booking-fields")
async def update_booking_fields(
    data: BookingFieldsUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """更新预约选项配置"""
    service = SettingsService(db)
    fields_data = [f.model_dump() for f in data.fields]
    result = await service.update_booking_fields(fields_data)
    return {"message": "保存成功", "data": result}


# ========== 就诊卡配置 ==========
class PatientCardConfigUpdate(BaseModel):
    cardName: Optional[str] = Field(None, max_length=50, description="就诊卡名称")
    cardDescription: Optional[str] = Field(None, max_length=16, description="描述文字（限16字）")
    maxCardsPerUser: Optional[int] = Field(None, ge=1, le=20, description="可建卡数量")
    showOnHomepage: Optional[bool] = Field(None, description="首页是否展示")


@router.get("/patient-card")
async def get_patient_card_config(
    db: AsyncSession = Depends(get_db),
):
    """获取就诊卡配置（公开接口）"""
    service = SettingsService(db)
    return await service.get_patient_card_config()


@router.put("/patient-card")
async def update_patient_card_config(
    data: PatientCardConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """更新就诊卡配置"""
    service = SettingsService(db)
    result = await service.update_patient_card_config(
        card_name=data.cardName,
        card_description=data.cardDescription,
        max_cards_per_user=data.maxCardsPerUser,
        show_on_homepage=data.showOnHomepage,
    )
    return {"message": "保存成功", "data": result}


# ========== 图片处理配置 ==========
class ThumbnailSizeItem(BaseModel):
    name: str = Field(..., max_length=50, description="尺寸名称，如 small, medium")
    width: int = Field(..., ge=1, le=4096, description="宽度像素")
    height: int = Field(..., ge=1, le=4096, description="高度像素")


class ImageConfigUpdate(BaseModel):
    thumbnailSizes: Optional[list[ThumbnailSizeItem]] = Field(None, description="缩略图尺寸配置")
    compressQuality: Optional[int] = Field(None, ge=1, le=100, description="压缩质量 1-100")


@router.get("/image")
async def get_image_config(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取图片处理配置"""
    service = SettingsService(db)
    return await service.get_image_config()


@router.put("/image")
async def update_image_config(
    data: ImageConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """更新图片处理配置"""
    service = SettingsService(db)
    
    thumbnail_sizes = None
    if data.thumbnailSizes is not None:
        thumbnail_sizes = [s.model_dump() for s in data.thumbnailSizes]
    
    result = await service.update_image_config(
        thumbnail_sizes=thumbnail_sizes,
        compress_quality=data.compressQuality,
    )
    return {"message": "保存成功", "data": result}


