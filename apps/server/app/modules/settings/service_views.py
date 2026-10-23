"""Higher-level config views for system settings."""

from typing import Any


class SettingsViewMixin:
    async def get_booking_settings(self, store_id=None, tenant_id=None) -> dict:
        data = await self.get_by_category("booking", store_id=store_id, tenant_id=tenant_id)
        return {
            "advanceDays": data.get("advance_days", 10),
            "sameDayBooking": data.get("same_day_booking", True),
            "cancelHours": data.get("cancel_hours", 2),
            "perDayLimit": data.get("per_day_limit", 3),
            "perDoctorLimit": data.get("per_doctor_limit", 1),
            "noShowLimit": data.get("no_show_limit", 3),
            "blacklistDays": data.get("blacklist_days", 30),
            "advanceBookingMinutes": data.get("advance_booking_minutes", 0),
            "advanceBookingDirection": data.get("advance_booking_direction", "before"),
            "advanceBookingReference": data.get("advance_booking_reference", "end"),
            "signInAdvanceMinutes": data.get("sign_in_advance_minutes", 30),
            "signInLateMinutes": data.get("sign_in_late_minutes", 30),
            # 通知策略
            "appointmentReminderHours": data.get("appointment_reminder_hours", 24),
        }

    async def get_hospital_info(self, tenant_id=None) -> dict:
        data = await self.get_by_category("hospital", tenant_id=tenant_id)
        return {
            "hospitalName": data.get("name", ""),
            "hospitalLevel": data.get("level", ""),
            "address": data.get("address", ""),
            "phone": data.get("phone", ""),
            "workTime": data.get("work_time", ""),
            "introduction": data.get("introduction", ""),
            "logo": data.get("logo", ""),
        }

    async def get_wechat_config(self, tenant_id=None) -> dict:
        data = await self.get_by_category("wechat", tenant_id=tenant_id)
        return {
            "appId": data.get("app_id", ""),
            "appSecret": data.get("app_secret", ""),
            "token": data.get("token", ""),
            "aesKey": data.get("aes_key", ""),
        }

    async def get_sms_config(self, tenant_id=None) -> dict:
        data = await self.get_by_category("sms", tenant_id=tenant_id)
        return {
            "provider": data.get("provider", "aliyun"),
            "accessKeyId": data.get("access_key_id", ""),
            "accessKeySecret": data.get("access_key_secret", ""),
            "signName": data.get("sign_name", ""),
            "templateCode": data.get("template_code", ""),
            # 通知策略参数
            "codeExpireSeconds": data.get("code_expire_seconds", 300),
            "sendIntervalSeconds": data.get("send_interval_seconds", 60),
        }

    async def get_email_config(self, tenant_id=None) -> dict:
        from app.utils.email_sync import decrypt_password
        data = await self.get_by_category("email", tenant_id=tenant_id)
        password = data.get("password", "")
        if password:
            try:
                password = decrypt_password(password)
            except (RuntimeError, ValueError) as e:
                # 密钥未配置或不匹配时，返回空密码并记录错误
                import logging
                logging.getLogger(__name__).warning("SMTP 密码解密失败: %s", e)
                password = ""
        return {
            "enabled": data.get("enabled", False),
            "host": data.get("host", ""),
            "port": data.get("port", 587),
            "username": data.get("username", ""),
            "password": password,
            "fromEmail": data.get("from_email", ""),
            "fromName": data.get("from_name", ""),
            "useTls": data.get("use_tls", True),
        }

    async def update_email_config(self, data: dict, operator_id=None, tenant_id=None) -> dict:
        from app.utils.email_sync import encrypt_password
        category = "email"
        mapping = {
            "enabled": "enabled",
            "host": "host",
            "port": "port",
            "username": "username",
            "password": "password",
            "fromEmail": "from_email",
            "fromName": "from_name",
            "useTls": "use_tls",
        }
        for api_key, db_key in mapping.items():
            if api_key in data:
                value = data[api_key]
                # 密码字段加密存储
                if db_key == "password" and value:
                    value = encrypt_password(str(value))
                await self.set_value(
                    category, db_key, value, operator_id=operator_id, tenant_id=tenant_id
                )
        return await self.get_email_config(tenant_id=tenant_id)

    async def get_booking_fields(self, tenant_id=None) -> list:
        fields = []
        fields_config = await self.get_by_category("booking_fields", tenant_id=tenant_id)
        default_fields = {
            "name": {"label": "姓名", "enabled": True, "required": True},
            "gender": {"label": "性别", "enabled": True, "required": False},
            "age": {"label": "年龄", "enabled": True, "required": False},
            "phone": {"label": "手机号", "enabled": True, "required": True},
            "idCard": {"label": "身份证号", "enabled": True, "required": False},
            "address": {"label": "地址", "enabled": False, "required": False},
            "symptom": {"label": "症状描述", "enabled": True, "required": False},
        }

        for field, defaults in default_fields.items():
            config = fields_config.get(field, {}) if isinstance(fields_config.get(field), dict) else {}
            fields.append(
                {
                    "field": field,
                    "label": defaults["label"],
                    "enabled": config.get("enabled", defaults["enabled"]),
                    "required": config.get("required", defaults["required"]),
                }
            )
        return fields

    async def update_booking_field(
        self, field: str, enabled: bool, required: bool, tenant_id=None
    ) -> dict[str, Any]:
        value = {"enabled": enabled, "required": required}
        await self.set_value("booking_fields", field, value, tenant_id=tenant_id)
        return value

    async def update_booking_fields(self, fields: list, tenant_id=None) -> list:
        for field_config in fields:
            await self.update_booking_field(
                field_config["field"],
                field_config["enabled"],
                field_config["required"],
                tenant_id=tenant_id,
            )
        return await self.get_booking_fields(tenant_id=tenant_id)

    async def get_patient_card_config(self, tenant_id=None) -> dict:
        data = await self.get_by_category("patient_card", tenant_id=tenant_id)
        return {
            "enabled": data.get("enabled", False),
            "cardTitle": data.get("card_title", "我的健康卡"),
            "showQrCode": data.get("show_qr_code", True),
        }

    async def update_patient_card_config(self, data: dict, operator_id=None, tenant_id=None) -> dict:
        category = "patient_card"
        mapping = {"enabled": "enabled", "cardTitle": "card_title", "showQrCode": "show_qr_code"}
        for api_key, db_key in mapping.items():
            if api_key in data:
                await self.set_value(
                    category, db_key, data[api_key], operator_id=operator_id, tenant_id=tenant_id
                )
        return await self.get_patient_card_config(tenant_id=tenant_id)

    async def get_security_config(self, tenant_id=None) -> dict:
        data = await self.get_by_category("security", tenant_id=tenant_id)
        return {
            "accessTokenExpireMinutes": data.get("access_token_expire_minutes", 30),
            "refreshTokenExpireDays": data.get("refresh_token_expire_days", 7),
            "defaultPassword": data.get("default_password", "admin123"),
            "rateLimitPerMinute": data.get("rate_limit_per_minute", 300),
            "rateLimitPerSecond": data.get("rate_limit_per_second", 50),
            "loginFailureLockCount": data.get("login_failure_lock_count", 5),
            "sessionTimeoutMinutes": data.get("session_timeout_minutes", 120),
        }

    async def get_source_release_config(self, tenant_id=None) -> dict:
        data = await self.get_by_category("source_release", tenant_id=tenant_id)
        return {
            "lockTimeoutMinutes": data.get("lock_timeout_minutes", 15),
            "batchReleaseEnabled": data.get("batch_release_enabled", "false") == "true",
            "batchReleaseDays": data.get("batch_release_days", 7),
            "batchReleaseTime": data.get("batch_release_time", "08:00"),
            "autoCancelUnpaidMinutes": data.get("auto_cancel_unpaid_minutes", 30),
            "noShowAutoMarkHours": data.get("no_show_auto_mark_hours", 24),
            "allowOverbooking": data.get("allow_overbooking", "false") == "true",
            "overbookingLimit": data.get("overbooking_limit", 0),
        }

    async def get_image_config(self, tenant_id=None) -> dict:
        data = await self.get_by_category("image", tenant_id=tenant_id)
        return {
            "maxSize": data.get("max_size", 5),
            "allowedTypes": data.get("allowed_types", ["jpg", "jpeg", "png"]),
            "compressEnabled": data.get("compress_enabled", True),
            "compressQuality": data.get("compress_quality", 80),
        }

    async def update_image_config(self, data: dict, operator_id=None, tenant_id=None) -> dict:
        category = "image"
        mapping = {
            "maxSize": "max_size",
            "allowedTypes": "allowed_types",
            "compressEnabled": "compress_enabled",
            "compressQuality": "compress_quality",
        }
        for api_key, db_key in mapping.items():
            if api_key in data:
                await self.set_value(
                    category, db_key, data[api_key], operator_id=operator_id, tenant_id=tenant_id
                )
        return await self.get_image_config(tenant_id=tenant_id)
