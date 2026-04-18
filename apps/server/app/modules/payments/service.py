"""支付服务"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.payments.config_resolver import PaymentConfigResolver
from app.infrastructure.payments.wechat_pay_service import WeChatPayService
from app.middleware.tenant_context import get_current_tenant_id
from app.models.appointment import Appointment
from app.models.miniapp_platform import PaymentProfile
from app.modules.appointments.common import APPOINTMENT_STATUS

logger = logging.getLogger(__name__)

PAYMENT_SUCCESS_REPLAY_STATUSES = {
    APPOINTMENT_STATUS["CONFIRMED"],
    APPOINTMENT_STATUS["SIGNED"],
    APPOINTMENT_STATUS["SEEING"],
    APPOINTMENT_STATUS["COMPLETED"],
}


class PaymentService:
    """支付服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_payment_order(
        self,
        appointment_id: str,
        openid: str,
        miniapp_instance_id: Optional[str] = None,
    ) -> dict:
        """创建支付订单

        Args:
            appointment_id: 预约ID
            openid: 微信用户 openid
            miniapp_instance_id: 小程序实例ID（可选）

        Returns:
            小程序调起支付所需的参数
        """
        # 1. 查询预约信息
        stmt = (
            select(Appointment)
            .options(
                selectinload(Appointment.payment_profile),
                selectinload(Appointment.payment_miniapp_instance),
            )
            .where(Appointment.id == appointment_id)
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(Appointment.tenant_id == tenant_id)

        result = await self.db.execute(stmt)
        appointment = result.scalar_one_or_none()

        if not appointment:
            raise ValueError(f"预约不存在: {appointment_id}")

        # 2. 验证预约状态
        if appointment.status != 0:  # 0=待支付
            raise ValueError(f"预约状态不正确，当前状态: {appointment.status}")

        if not appointment.payment_amount or appointment.payment_amount <= 0:
            raise ValueError(f"预约金额无效: {appointment.payment_amount}")

        # 3. 获取支付配置
        payment_config = await self._resolve_payment_config(
            appointment=appointment,
            miniapp_instance_id=miniapp_instance_id,
        )

        if not payment_config:
            raise ValueError("无法获取支付配置")

        # 4. 查询完整的 PaymentProfile
        profile_stmt = select(PaymentProfile).where(
            PaymentProfile.id == payment_config.payment_profile_id
        )
        if tenant_id:
            profile_stmt = profile_stmt.where(PaymentProfile.tenant_id == tenant_id)

        profile_result = await self.db.execute(profile_stmt)
        payment_profile = profile_result.scalar_one_or_none()

        if not payment_profile:
            raise ValueError(f"支付配置不存在: {payment_config.payment_profile_id}")

        # 5. 初始化微信支付服务
        wxpay_service = WeChatPayService(
            payment_profile=payment_profile,
            cert_dir=None,  # 可选：平台证书缓存目录
        )

        # 6. 生成商户订单号
        out_trade_no = self._generate_out_trade_no(appointment)

        # 7. 调用微信统一下单
        order_result = await wxpay_service.create_order(
            out_trade_no=out_trade_no,
            description=f"预约挂号-{appointment.doctor_name or ''}",
            amount=appointment.payment_amount,
            openid=openid,
            app_id=payment_config.app_id or "",
            notify_url=payment_config.notify_url or "",
        )

        prepay_id = order_result.get("prepay_id")
        if not prepay_id:
            raise Exception("微信下单失败：未返回 prepay_id")

        # 8. 更新预约的支付快照（如果还没设置）
        if not appointment.payment_profile_id:
            appointment.payment_profile_id = payment_profile.id
            appointment.payment_miniapp_instance_id = (
                appointment.payment_miniapp_instance_id or miniapp_instance_id
            )
            appointment.payment_mode = payment_config.mode
            appointment.payment_app_id = payment_config.app_id
            appointment.payment_mch_id = payment_config.mch_id
            appointment.payment_sub_mchid = payment_config.sub_mchid
            appointment.payment_notify_url = payment_config.notify_url
            await self.db.flush()

        # 9. 生成小程序支付签名参数
        pay_sign_params = self._generate_miniapp_pay_sign(
            app_id=payment_config.app_id or "",
            prepay_id=prepay_id,
            private_key=wxpay_service._load_secret(payment_profile.private_key_ref or ""),
        )

        # 10. 组装返回数据
        return {
            "appointment_id": appointment.id,
            "payment_amount": float(appointment.payment_amount),
            "time_stamp": pay_sign_params["timeStamp"],
            "nonce_str": pay_sign_params["nonceStr"],
            "package": pay_sign_params["package"],
            "sign_type": pay_sign_params["signType"],
            "pay_sign": pay_sign_params["paySign"],
        }

    async def handle_payment_callback(
        self,
        headers: dict,
        body: bytes,
    ) -> dict:
        """处理支付回调

        Args:
            headers: 请求头
            body: 请求体

        Returns:
            处理结果
        """
        # 注意：不要在验签前解析 body 内容做任何业务判断。
        # 仅从 header 取出证书序列号用于反查 PaymentProfile，反查严格按 tenant_id 隔离，
        # 不做任何跨租户 fallback，避免被伪造请求触达其他租户的密钥。
        cert_serial_no = headers.get("Wechatpay-Serial") or headers.get("wechatpay-serial")

        if not cert_serial_no:
            raise ValueError("缺少 Wechatpay-Serial header")

        tenant_id = get_current_tenant_id()
        if not tenant_id:
            # 回调路由必须能定位租户上下文（通过子域名 / 路径前缀 / Header），否则拒收。
            raise ValueError("回调缺少租户上下文")

        stmt = select(PaymentProfile).where(
            PaymentProfile.cert_serial_no == cert_serial_no,
            PaymentProfile.status == 1,
            PaymentProfile.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        payment_profile = result.scalar_one_or_none()

        if not payment_profile:
            raise ValueError(
                f"未找到支付配置: cert_serial_no={cert_serial_no}, tenant_id={tenant_id}"
            )

        # 2. 验签并解密
        wxpay_service = WeChatPayService(payment_profile=payment_profile)
        decrypted_data = wxpay_service.verify_callback(headers=headers, body=body)

        # 3. 解析回调数据
        event_type = decrypted_data.get("event_type")
        resource = decrypted_data.get("resource", {})

        if event_type != "TRANSACTION.SUCCESS":
            logger.warning(f"非成功事件: {event_type}")
            return {"code": "SUCCESS", "message": "忽略非成功事件"}

        out_trade_no = resource.get("out_trade_no")
        transaction_id = resource.get("transaction_id")
        callback_amount = resource.get("amount") or {}
        callback_total_fen = callback_amount.get("total")

        if not out_trade_no:
            raise ValueError("回调数据缺少 out_trade_no")

        # 4. 查找预约
        appointment = await self._get_appointment_by_out_trade_no(out_trade_no)

        if not appointment:
            raise ValueError(f"未找到预约: out_trade_no={out_trade_no}")

        # 4.1 金额一致性校验：回调中的 total（单位:分）必须等于预约的 payment_amount*100
        expected_total_fen = (
            int(Decimal(str(appointment.payment_amount)) * Decimal("100"))
            if appointment.payment_amount is not None
            else None
        )
        if callback_total_fen is None or callback_total_fen != expected_total_fen:
            logger.error(
                "支付回调金额与预约金额不一致: out_trade_no=%s, callback=%s, expected=%s",
                out_trade_no,
                callback_total_fen,
                expected_total_fen,
            )
            raise ValueError("回调金额与预约金额不一致")

        callback_at = datetime.now()

        # 5. 优先尝试以条件更新完成结算，避免并发回调重复落库。
        if appointment.status == 0:
            settle_stmt = (
                update(Appointment)
                .where(
                    Appointment.id == appointment.id,
                    Appointment.status == 0,
                )
                .values(
                    status=APPOINTMENT_STATUS["CONFIRMED"],
                    payment_transaction_id=transaction_id,
                    paid_at=callback_at,
                )
            )
            settle_result = await self.db.execute(settle_stmt)
            if settle_result.rowcount:
                await self.db.commit()

                logger.info(
                    f"支付成功: appointment_id={appointment.id}, "
                    f"out_trade_no={out_trade_no}, transaction_id={transaction_id}"
                )
                return {"code": "SUCCESS", "message": "成功"}

            appointment = await self._get_appointment_by_out_trade_no(out_trade_no)

        # 6. 已成功结算的重复回调视为幂等成功，可补齐缺失元数据。
        if appointment and appointment.status in PAYMENT_SUCCESS_REPLAY_STATUSES:
            should_commit = False
            if transaction_id and not appointment.payment_transaction_id:
                appointment.payment_transaction_id = transaction_id
                should_commit = True
            if not appointment.paid_at:
                appointment.paid_at = callback_at
                should_commit = True
            if should_commit:
                await self.db.commit()

            logger.info(
                "支付回调重复到达，已按幂等成功处理: "
                f"appointment_id={appointment.id}, out_trade_no={out_trade_no}, "
                f"transaction_id={transaction_id}"
            )
            return {"code": "SUCCESS", "message": "成功"}

        # 7. 超时后晚到的支付成功回调不再恢复预约状态，避免号源二次占用。
        #    钱已被微信扣走，必须自动退款，否则会出现"号源已释放但用户钱被扣"的资损。
        if appointment and appointment.status == APPOINTMENT_STATUS["EXPIRED"]:
            logger.warning(
                "支付成功回调到达时预约已过期，触发自动退款: "
                f"appointment_id={appointment.id}, out_trade_no={out_trade_no}, "
                f"transaction_id={transaction_id}"
            )
            await self._auto_refund_on_late_callback(
                appointment=appointment,
                transaction_id=transaction_id,
                callback_at=callback_at,
                reason="支付回调晚到，预约已过期",
            )
            return {"code": "SUCCESS", "message": "成功"}

        # 8. 取消状态：与 cancel 竞态导致回调晚到。钱已扣，必须自动退款。
        if appointment and appointment.status == APPOINTMENT_STATUS["CANCELLED"]:
            logger.warning(
                "支付成功回调到达时预约已取消，触发自动退款: "
                f"appointment_id={appointment.id}, out_trade_no={out_trade_no}, "
                f"transaction_id={transaction_id}"
            )
            await self._auto_refund_on_late_callback(
                appointment=appointment,
                transaction_id=transaction_id,
                callback_at=callback_at,
                reason="支付回调晚到，预约已被取消",
            )
            return {"code": "SUCCESS", "message": "成功"}

        # 9. 其他状态保守忽略，避免非待支付预约被回调覆盖。
        if appointment:
            logger.warning(
                "支付成功回调到达时预约状态非待支付，忽略状态变更: "
                f"appointment_id={appointment.id}, status={appointment.status}, "
                f"out_trade_no={out_trade_no}, transaction_id={transaction_id}"
            )
            await self.db.commit()

        return {"code": "SUCCESS", "message": "成功"}

    async def _auto_refund_on_late_callback(
        self,
        appointment: Appointment,
        transaction_id: Optional[str],
        callback_at: datetime,
        reason: str,
    ) -> None:
        """晚到的支付成功回调触发自动全额退款。

        - 先把 transaction_id / paid_at 写入预约（满足 RefundService 的支付凭证校验）
        - 再调 RefundService 创建 pending 退款 + WeChatPayService 调微信退款 → processing
        - in-flight 去重命中（已存在 pending/processing 退款）则跳过，幂等。
        - 任一步失败抛错，回调返回 FAILED，让微信稍后重试。
        """
        from app.infrastructure.payments.wechat_pay_service import WeChatPayService
        from app.modules.refunds.service import IN_FLIGHT_REFUND_STATUSES, RefundService
        from sqlalchemy import func as _func

        if transaction_id and not appointment.payment_transaction_id:
            appointment.payment_transaction_id = transaction_id
        if not appointment.paid_at:
            appointment.paid_at = callback_at
        await self.db.flush()

        # 幂等：若已有 in-flight 或 success 退款单，则不再重复创建
        from app.models.refund import RefundRecord

        existing_stmt = select(_func.count(RefundRecord.id)).where(
            RefundRecord.appointment_id == appointment.id,
            RefundRecord.status.in_(IN_FLIGHT_REFUND_STATUSES + ("success",)),
        )
        if appointment.tenant_id:
            existing_stmt = existing_stmt.where(RefundRecord.tenant_id == appointment.tenant_id)
        existing_count = (await self.db.execute(existing_stmt)).scalar() or 0
        if existing_count > 0:
            logger.info(
                "自动退款跳过：已存在退款记录: appointment_id=%s",
                appointment.id,
            )
            await self.db.commit()
            return

        refund_service = RefundService(self.db)
        refund_record = await refund_service.create_refund(
            appointment_id=appointment.id,
            refund_amount=appointment.payment_amount,
            refund_reason=reason,
            operator_id="system:late_callback",
        )

        if not refund_record.payment_profile_id:
            raise ValueError("自动退款失败：预约缺少支付配置快照")

        profile_stmt = select(PaymentProfile).where(
            PaymentProfile.id == refund_record.payment_profile_id
        )
        profile = (await self.db.execute(profile_stmt)).scalar_one_or_none()
        if not profile:
            raise ValueError("自动退款失败：支付配置不存在")

        wx_service = WeChatPayService(profile)
        out_trade_no, txn_id = await refund_service.ensure_refund_payment_reference(refund_record)
        wx_result = await wx_service.create_refund(
            out_trade_no=out_trade_no,
            out_refund_no=refund_record.refund_no,
            total=refund_record.original_amount,
            refund=refund_record.refund_amount,
            reason=refund_record.refund_reason or "",
            notify_url=profile.refund_notify_url or profile.notify_url or "",
            transaction_id=txn_id,
        )
        refund_record.status = "processing"
        if wx_result.get("refund_id"):
            refund_record.wx_refund_id = wx_result.get("refund_id")
        await refund_service.sync_appointment_refund_state(refund_record.appointment_id)
        await self.db.commit()

    async def _resolve_payment_config(
        self,
        appointment: Appointment,
        miniapp_instance_id: Optional[str] = None,
    ) -> Optional[object]:
        """解析支付配置"""
        resolver = PaymentConfigResolver(self.db)

        # 优先级：预约快照 > 小程序实例 > 门店 > 租户默认
        if appointment.payment_profile_id:
            # 预约时已保存的配置（跳过已禁用的配置）
            stmt = select(PaymentProfile).where(
                PaymentProfile.id == appointment.payment_profile_id,
                PaymentProfile.status == 1,
            )
            tenant_id = get_current_tenant_id()
            if tenant_id:
                stmt = stmt.where(PaymentProfile.tenant_id == tenant_id)
            result = await self.db.execute(stmt)
            profile = result.scalar_one_or_none()
            if profile:
                return profile

        # 传入的小程序实例
        if miniapp_instance_id:
            config = await resolver.resolve(miniapp_instance_id=miniapp_instance_id)
            if config:
                return config

        # 预约关联的小程序实例
        if appointment.payment_miniapp_instance_id:
            config = await resolver.resolve(
                miniapp_instance_id=appointment.payment_miniapp_instance_id
            )
            if config:
                return config

        # 通过预约的 schedule 查找 store
        if appointment.schedule and appointment.schedule.store_id:
            config = await resolver.resolve(store_id=appointment.schedule.store_id)
            if config:
                return config

        return None

    async def _get_appointment_by_out_trade_no(
        self, out_trade_no: str
    ) -> Optional[Appointment]:
        """根据商户订单号查找预约。

        当前规则使用 appointment_no（YY+yyyymmddHHMMSS+4位，22字符，满足微信 6-32 上限）。
        历史数据可能仍是 APPT{uuid} 形式，按租户隔离同时兼容这两种格式。
        """
        tenant_id = get_current_tenant_id()

        stmt = select(Appointment).where(Appointment.appointment_no == out_trade_no)
        if tenant_id:
            stmt = stmt.where(Appointment.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        appointment = result.scalar_one_or_none()
        if appointment:
            return appointment

        if out_trade_no.startswith("APPT"):
            legacy_id = out_trade_no[4:]
            legacy_stmt = select(Appointment).where(Appointment.id == legacy_id)
            if tenant_id:
                legacy_stmt = legacy_stmt.where(Appointment.tenant_id == tenant_id)
            legacy_result = await self.db.execute(legacy_stmt)
            return legacy_result.scalar_one_or_none()

        return None

    def _generate_out_trade_no(self, appointment: Appointment) -> str:
        """生成商户订单号。

        微信支付 V3 要求 out_trade_no 长度 6-32 字符。
        appointment_no 形如 YY+yyyymmddHHMMSS+4 字符随机串=22 字符，符合要求且租户内唯一。
        历史数据若曾使用 APPT+UUID(40字符)会被微信拒单，回调反查保留兼容。
        """
        if not appointment.appointment_no:
            raise ValueError(f"预约缺少 appointment_no，无法生成商户订单号: {appointment.id}")
        return appointment.appointment_no

    def _generate_miniapp_pay_sign(
        self,
        app_id: str,
        prepay_id: str,
        private_key: str,
    ) -> dict:
        """生成小程序支付签名

        按照微信官方文档的签名规则生成
        """
        # 生成随机字符串
        nonce_str = str(uuid.uuid4()).replace("-", "")

        # 时间戳
        time_stamp = str(int(time.time()))

        # 组合参数
        package = f"prepay_id={prepay_id}"

        # 签名字符串
        sign_str = f"{app_id}\n{time_stamp}\n{nonce_str}\n{package}\n"

        # 使用商户私钥签名
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend
        import base64

        try:
            # 解析私钥
            private_key_obj = serialization.load_pem_private_key(
                private_key.encode(),
                password=None,
                backend=default_backend(),
            )

            # 签名
            signature = private_key_obj.sign(
                sign_str.encode("utf-8"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )

            pay_sign = base64.b64encode(signature).decode("utf-8")

            return {
                "timeStamp": time_stamp,
                "nonceStr": nonce_str,
                "package": package,
                "signType": "RSA",
                "paySign": pay_sign,
            }

        except Exception as e:
            logger.error(f"生成支付签名失败: {e}")
            raise
