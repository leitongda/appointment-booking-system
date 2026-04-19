#!/usr/bin/env python3
"""
小程序模板 Seed 数据脚本

为 5 套不同类型的小程序模板创建初始数据。
包含完整的导航配置、设计令牌、功能开关等。
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.miniapp_platform import AppTemplate, TemplateVersion
from app.core.config import settings
import json


# 模板配置数据
TEMPLATES = [
    {
        "name": "现代综合医疗",
        "code": "modern-general",
        "description": "通用型医院模板，面向大众用户，突出专业、清晰、可信赖",
        "category": "general",
        "default_config": {
            "navSchema": {
                "tabs": [
                    {"pagePath": "/pages/index/index", "text": "首页", "iconKey": "home", "activeIconKey": "home-active"},
                    {"pagePath": "/pages/appointment/index", "text": "预约", "iconKey": "appointment", "activeIconKey": "appointment-active"},
                    {"pagePath": "/pages/profile/index", "text": "我的", "iconKey": "profile", "activeIconKey": "profile-active"}
                ],
                "height": 100
            },
            "homeSchema": [
                {"id": "banner", "type": "banner", "visible": True, "order": 1, "config": {}},
                {"id": "quick_menu", "type": "quick_menu", "visible": True, "order": 2, "config": {"columns": 4}},
                {"id": "patient_card", "type": "patient_card", "visible": True, "order": 3, "config": {}},
                {"id": "recommend_doctor", "type": "recommend_doctor", "visible": True, "order": 4, "config": {}}
            ],
            "pageShells": {
                "home": "standard",
                "department": "sidebar",
                "doctorList": "cards",
                "doctorDetail": "standard",
                "appointment": "tabs",
                "profile": "standard"
            },
            "designTokens": {
                "primary": "#3D6CA8",
                "primarySoft": "#EAF1F8",
                "accent": "#2D4E82",
                "bodyFontSize": 30,
                "displayFontSize": 60,
                "radiusMd": 16,
                "radiusLg": 24,
                "spacingMultiplier": 1,
                "touchTargetMin": 88,
                "customColors": {}
            },
            "assets": {
                "iconStyle": "outlined",
                "tabBarIconStyle": "filled",
                "decorationStyle": "none"
            },
            "tone": {
                "bookingLabel": "预约挂号",
                "patientLabel": "就诊人",
                "addressMode": "您",
                "emptyBookingText": "暂无预约记录",
                "confirmSuccessText": "预约成功！请于就诊当天携带有效身份证件到院",
                "custom": {}
            },
            "constraints": {
                "lockedPages": [
                    "packageBooking/pages/booking/index",
                    "packageBooking/pages/booking/result",
                    "packageBooking/pages/checkin/scan",
                    "packageBooking/pages/checkin/select"
                ],
                "forceElderMode": False,
                "confirmBeforeAction": False
            },
            "features": {
                "onlineBooking": True,
                "onlinePayment": True,
                "healthRecord": True,
                "onlineConsult": True,
                "notification": True,
                "pointSystem": True
            }
        },
        "versions": [
            {
                "version": "1.0.0",
                "source_ref": "git://templates/modern-general.git#v1.0.0",
                "schema_version": "1.0.0",
                "changelog": "初始版本"
            }
        ]
    },
    {
        "name": "长辈友好/中医康养",
        "code": "elderly-tcm",
        "description": "面向55岁以上长辈用户，大按钮、低信息密度、口语化文案，温暖棕主色",
        "category": "tcm",
        "default_config": {
            "navSchema": {
                "tabs": [
                    {"pagePath": "/pages/index/index", "text": "首页", "iconKey": "home", "activeIconKey": "home-active"},
                    {"pagePath": "/pages/appointment/index", "text": "预约", "iconKey": "appointment", "activeIconKey": "appointment-active"},
                    {"pagePath": "/pages/profile/index", "text": "我的", "iconKey": "profile", "activeIconKey": "profile-active"}
                ],
                "height": 120
            },
            "homeSchema": [
                {"id": "quick_action", "type": "quick_action", "visible": True, "order": 1, "config": {"columns": 2}},
                {"id": "simple_notice", "type": "simple_notice", "visible": True, "order": 2, "config": {}},
                {"id": "recent_doctor", "type": "recent_doctor", "visible": True, "order": 3, "config": {"maxItems": 3}}
            ],
            "pageShells": {
                "home": "home-elderly",
                "department": "dept-large-grid",
                "doctorList": "doctor-large-cards",
                "doctorDetail": "doctor-detail-elderly",
                "appointment": "appoint-simple",
                "profile": "profile-elderly"
            },
            "designTokens": {
                "primary": "#8B6F47",
                "primarySoft": "#F5EDE0",
                "accent": "#6B5235",
                "bodyFontSize": 36,
                "displayFontSize": 72,
                "radiusMd": 24,
                "radiusLg": 32,
                "spacingMultiplier": 1.5,
                "touchTargetMin": 88,
                "customColors": {
                    "success": "#52C41A",
                    "warning": "#E8A838",
                    "danger": "#D32F2F",
                    "gradientPrimary": "linear-gradient(135deg, #8B6F47, #A68B5B)"
                }
            },
            "assets": {
                "iconStyle": "bold",
                "tabBarIconStyle": "filled",
                "decorationStyle": "traditional"
            },
            "tone": {
                "bookingLabel": "挂号",
                "patientLabel": "就诊人",
                "addressMode": "您",
                "emptyBookingText": "您还没有挂过号，点这里挂号",
                "confirmSuccessText": "挂号成功！请在看病当天带着身份证来医院",
                "custom": {
                    "confirmBooking": "确认挂号",
                    "guideText": "点击这里挂号",
                    "nextStep": "下一步"
                }
            },
            "constraints": {
                "lockedPages": [
                    "packageBooking/pages/booking/index",
                    "packageBooking/pages/booking/result",
                    "packageBooking/pages/checkin/scan",
                    "packageBooking/pages/checkin/select"
                ],
                "forceElderMode": True,
                "confirmBeforeAction": True
            },
            "features": {
                "onlineBooking": True,
                "onlinePayment": True,
                "healthRecord": True,
                "onlineConsult": False,
                "notification": True,
                "pointSystem": True,
                "tcmServices": True
            }
        },
        "versions": [
            {
                "version": "1.0.0",
                "source_ref": "git://templates/elderly-tcm.git#v1.0.0",
                "schema_version": "1.0.0",
                "changelog": "初始版本"
            }
        ]
    },
    {
        "name": "高端专科门诊",
        "code": "premium-specialty",
        "description": "面向口腔、医美、私立专科、会员制门诊，突出品牌感、精致、专家驱动",
        "category": "specialty",
        "default_config": {
            "navSchema": {
                "tabs": [
                    {"pagePath": "/pages/index/index", "text": "首页", "iconKey": "home", "activeIconKey": "home-active"},
                    {"pagePath": "/pages/doctor/index", "text": "专家", "iconKey": "doctor", "activeIconKey": "doctor-active"},
                    {"pagePath": "/pages/appointment/index", "text": "预约", "iconKey": "appointment", "activeIconKey": "appointment-active"},
                    {"pagePath": "/pages/profile/index", "text": "我的", "iconKey": "profile", "activeIconKey": "profile-active"}
                ],
                "height": 100
            },
            "homeSchema": [
                {"id": "banner", "type": "banner", "visible": True, "order": 1, "config": {}},
                {"id": "featured_doctor", "type": "featured_doctor", "visible": True, "order": 2, "config": {}},
                {"id": "featured_service", "type": "featured_service", "visible": True, "order": 3, "config": {}},
                {"id": "quick_menu", "type": "quick_menu", "visible": True, "order": 4, "config": {"columns": 4}},
                {"id": "brand_story", "type": "brand_story", "visible": True, "order": 5, "config": {}}
            ],
            "pageShells": {
                "home": "home-premium",
                "department": "dept-minimal",
                "doctorList": "doctor-showcase",
                "doctorDetail": "doctor-detail-premium",
                "appointment": "tabs",
                "profile": "profile-premium"
            },
            "designTokens": {
                "primary": "#7B6345",
                "primarySoft": "#F6F0E3",
                "accent": "#5B4730",
                "bodyFontSize": 28,
                "displayFontSize": 56,
                "radiusMd": 12,
                "radiusLg": 16,
                "spacingMultiplier": 1.1,
                "touchTargetMin": 88,
                "customColors": {
                    "success": "#52C41A",
                    "warning": "#FAAD14",
                    "danger": "#C0392B",
                    "gradientPrimary": "linear-gradient(135deg, #8B7355, #6B5740)"
                }
            },
            "assets": {
                "iconStyle": "thin",
                "tabBarIconStyle": "outlined",
                "decorationStyle": "minimal"
            },
            "tone": {
                "bookingLabel": "预约咨询",
                "patientLabel": "就诊人",
                "addressMode": "您",
                "emptyBookingText": "暂无预约记录，立即预约专家",
                "confirmSuccessText": "您的专属专家已确认预约，请准时到院",
                "custom": {
                    "confirmBooking": "确认预约",
                    "expertLabel": "专家",
                    "serviceLabel": "服务项目"
                }
            },
            "constraints": {
                "lockedPages": [
                    "packageBooking/pages/booking/index",
                    "packageBooking/pages/booking/result",
                    "packageBooking/pages/checkin/scan",
                    "packageBooking/pages/checkin/select"
                ],
                "forceElderMode": False,
                "confirmBeforeAction": False
            },
            "features": {
                "onlineBooking": True,
                "onlinePayment": True,
                "healthRecord": True,
                "onlineConsult": True,
                "notification": True,
                "pointSystem": True,
                "caseGallery": True,
                "virtualConsult": True
            }
        },
        "versions": [
            {
                "version": "1.0.0",
                "source_ref": "git://templates/premium-specialty.git#v1.0.0",
                "schema_version": "1.0.0",
                "changelog": "初始版本"
            }
        ]
    },
    {
        "name": "亲子儿科",
        "code": "family-pediatrics",
        "description": "面向儿童医院、儿科门诊、家庭健康场景，突出亲和、活泼、家庭成员管理",
        "category": "pediatrics",
        "default_config": {
            "navSchema": {
                "tabs": [
                    {"pagePath": "/pages/index/index", "text": "首页", "iconKey": "home", "activeIconKey": "home-active"},
                    {"pagePath": "/pages/appointment/index", "text": "预约", "iconKey": "appointment", "activeIconKey": "appointment-active"},
                    {"pagePath": "/pages/profile/index", "text": "成长", "iconKey": "profile", "activeIconKey": "profile-active"}
                ],
                "height": 100
            },
            "homeSchema": [
                {"id": "family_switcher", "type": "family_switcher", "visible": True, "order": 1, "config": {}},
                {"id": "banner", "type": "banner", "visible": True, "order": 2, "config": {}},
                {"id": "quick_menu", "type": "quick_menu", "visible": True, "order": 3, "config": {"columns": 3, "rows": 2}},
                {"id": "common_service", "type": "common_service", "visible": True, "order": 4, "config": {}},
                {"id": "recommend_doctor", "type": "recommend_doctor", "visible": True, "order": 5, "config": {}}
            ],
            "pageShells": {
                "home": "home-family",
                "department": "dept-colorful",
                "doctorList": "cards",
                "doctorDetail": "doctor-detail-family",
                "appointment": "tabs",
                "profile": "profile-family"
            },
            "designTokens": {
                "primary": "#3A7AB3",
                "primarySoft": "#EDF4FB",
                "accent": "#C58603",
                "bodyFontSize": 30,
                "displayFontSize": 64,
                "radiusMd": 20,
                "radiusLg": 28,
                "spacingMultiplier": 1.05,
                "touchTargetMin": 88,
                "customColors": {
                    "success": "#52C41A",
                    "warning": "#FAAD14",
                    "danger": "#FF6B6B",
                    "gradientPrimary": "linear-gradient(135deg, #5B9BD5, #7EC8E3)",
                    "fun1": "#FFB6C1",
                    "fun2": "#98D8C8",
                    "fun3": "#FFE66D"
                }
            },
            "assets": {
                "iconStyle": "filled",
                "tabBarIconStyle": "filled",
                "decorationStyle": "playful"
            },
            "tone": {
                "bookingLabel": "预约挂号",
                "patientLabel": "宝宝",
                "addressMode": "您",
                "emptyBookingText": "还没有预约记录，给宝宝挂个号吧",
                "confirmSuccessText": "预约成功！请带好宝宝的预防接种证和医保卡",
                "custom": {
                    "babyLabel": "宝宝",
                    "parentLabel": "家长",
                    "growthLabel": "成长"
                }
            },
            "constraints": {
                "lockedPages": [
                    "packageBooking/pages/booking/index",
                    "packageBooking/pages/booking/result",
                    "packageBooking/pages/checkin/scan",
                    "packageBooking/pages/checkin/select"
                ],
                "forceElderMode": False,
                "confirmBeforeAction": False
            },
            "features": {
                "onlineBooking": True,
                "onlinePayment": True,
                "healthRecord": True,
                "onlineConsult": True,
                "notification": True,
                "pointSystem": True,
                "growthRecord": True,
                "vaccination": True
            }
        },
        "versions": [
            {
                "version": "1.0.0",
                "source_ref": "git://templates/family-pediatrics.git#v1.0.0",
                "schema_version": "1.0.0",
                "changelog": "初始版本"
            }
        ]
    },
    {
        "name": "女性健康",
        "code": "womens-health",
        "description": "面向妇科、产康、女性体检、专科中心，突出安心、柔和、细致、陪伴感",
        "category": "womens",
        "default_config": {
            "navSchema": {
                "tabs": [
                    {"pagePath": "/pages/index/index", "text": "首页", "iconKey": "home", "activeIconKey": "home-active"},
                    {"pagePath": "/pages/appointment/index", "text": "预约", "iconKey": "appointment", "activeIconKey": "appointment-active"},
                    {"pagePath": "/pages/profile/index", "text": "我的", "iconKey": "profile", "activeIconKey": "profile-active"}
                ],
                "height": 100
            },
            "homeSchema": [
                {"id": "banner", "type": "banner", "visible": True, "order": 1, "config": {}},
                {"id": "health_service", "type": "health_service", "visible": True, "order": 2, "config": {}},
                {"id": "quick_menu", "type": "quick_menu", "visible": True, "order": 3, "config": {"columns": 4}},
                {"id": "health_reminder", "type": "health_reminder", "visible": True, "order": 4, "config": {}},
                {"id": "recommend_doctor", "type": "recommend_doctor", "visible": True, "order": 5, "config": {}}
            ],
            "pageShells": {
                "home": "home-womens",
                "department": "dept-soft",
                "doctorList": "doctor-cards-soft",
                "doctorDetail": "doctor-detail-womens",
                "appointment": "tabs",
                "profile": "profile-womens"
            },
            "designTokens": {
                "primary": "#945050",
                "primarySoft": "#FBF0F0",
                "accent": "#703030",
                "bodyFontSize": 30,
                "displayFontSize": 60,
                "radiusMd": 20,
                "radiusLg": 28,
                "spacingMultiplier": 1,
                "touchTargetMin": 88,
                "customColors": {
                    "success": "#7AC74F",
                    "warning": "#F5C542",
                    "danger": "#E07B7B",
                    "gradientPrimary": "linear-gradient(135deg, #C4908D, #E8B4B8)",
                    "warmBg": "#FFF9F5"
                }
            },
            "assets": {
                "iconStyle": "thin",
                "tabBarIconStyle": "outlined",
                "decorationStyle": "floral"
            },
            "tone": {
                "bookingLabel": "预约挂号",
                "patientLabel": "就诊人",
                "addressMode": "您",
                "emptyBookingText": "暂无预约，关爱自己从一次检查开始",
                "confirmSuccessText": "预约成功！记得按时到院，如有不适可随时咨询",
                "custom": {
                    "warmGreeting": "亲爱的",
                    "reminderPrefix": "关爱提示"
                }
            },
            "constraints": {
                "lockedPages": [
                    "packageBooking/pages/booking/index",
                    "packageBooking/pages/booking/result",
                    "packageBooking/pages/checkin/scan",
                    "packageBooking/pages/checkin/select"
                ],
                "forceElderMode": False,
                "confirmBeforeAction": False
            },
            "features": {
                "onlineBooking": True,
                "onlinePayment": True,
                "healthRecord": True,
                "onlineConsult": True,
                "notification": True,
                "pointSystem": True
            }
        },
        "versions": [
            {
                "version": "1.0.0",
                "source_ref": "git://templates/womens-health.git#v1.0.0",
                "schema_version": "1.0.0",
                "changelog": "初始版本"
            }
        ]
    }
]


async def seed_templates():
    """创建模板种子数据"""
    # 创建数据库引擎
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("开始创建模板数据...")

        for template_data in TEMPLATES:
            # 检查模板是否已存在
            from sqlalchemy import select
            existing = await session.execute(
                select(AppTemplate).where(AppTemplate.code == template_data["code"])
            )
            if existing.scalar_one_or_none():
                print(f"模板 {template_data['code']} 已存在，跳过")
                continue

            # 提取版本数据
            versions_data = template_data.pop("versions", [])

            # 创建模板
            # 注意：AppTemplate 模型没有 category 字段，将其包含在 default_config 中
            template = AppTemplate(
                name=template_data["name"],
                code=template_data["code"],
                description=template_data["description"],
                default_config=json.dumps(template_data["default_config"]),
                status=1
            )
            session.add(template)
            await session.flush()  # 获取 template.id

            print(f"创建模板: {template.name} ({template.code})")

            # 创建版本
            for version_data in versions_data:
                version = TemplateVersion(
                    template_id=template.id,
                    version=version_data["version"],
                    source_ref=version_data.get("source_ref"),
                    schema_version=version_data.get("schema_version"),
                    changelog=version_data.get("changelog"),
                    status=1
                )
                session.add(version)
                print(f"  创建版本: {version.version}")

        await session.commit()
        print("模板数据创建完成!")


if __name__ == "__main__":
    asyncio.run(seed_templates())
