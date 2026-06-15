"""微信支付服务 — 支持 direct 和 service_provider 两种模式"""

from __future__ import annotations

import logging
from decimal import Decimal

from wechatpayv3 import WeChatPay, WeChatPayType

from app.common.secret_refs import resolve_secret_ref
from app.models.miniapp_platform import PaymentProfile

logger = logging.getLogger(__name__)


class WeChatPayService:
    """微信支付服务

    支持两种模式:
    - direct: 直连商户模式
    - service_provider: 服务商模式（sp_mchid + sub_mchid）
    """

    def __init__(self, payment_profile: PaymentProfile, cert_dir: str | None = None):
        """初始化微信支付服务

        Args:
            payment_profile: 支付配置模型
            cert_dir: 平台证书缓存目录（可选）
        """
        self.profile = payment_profile

        # 解析密钥引用
        api_v3_key = self._load_secret(payment_profile.api_v3_key_ref)
        private_key = self._load_secret(payment_profile.private_key_ref)

        if not api_v3_key:
            raise ValueError(f"PaymentProfile {payment_profile.id} 缺少 api_v3_key")
        if not private_key:
            raise ValueError(f"PaymentProfile {payment_profile.id} 缺少 private_key")
        if not payment_profile.cert_serial_no:
            raise ValueError(f"PaymentProfile {payment_profile.id} 缺少 cert_serial_no")

        # 判断支付模式
        partner_mode = payment_profile.mode == "service_provider"

        try:
            self.wxpay = WeChatPay(
                wechatpay_type=WeChatPayType.MINIPROG,  # 小程序支付
                mchid=payment_profile.mch_id or "",  # 服务商模式下是 sp_mchid
                private_key=private_key,
                cert_serial_no=payment_profile.cert_serial_no,
                apiv3_key=api_v3_key,
                appid=payment_profile.app_id or "",
                notify_url=payment_profile.notify_url or "",
                cert_dir=cert_dir,
                logger=logger,
                partner_mode=partner_mode,
            )
        except Exception as e:
            logger.error(f"初始化 WeChatPay 失败: {e}")
            raise

    def _load_secret(self, secret_ref: str | None) -> str | None:
        """加载密钥

        支持两种格式:
        - env:VAR_NAME: 从环境变量读取
        - 直接值: pem 格式的私钥内容
        """
        if not secret_ref:
            return None

        value = resolve_secret_ref(secret_ref)
        if value and value.startswith("-----BEGIN"):
            # 直接是 PEM 格式
            return value

        return value

    async def create_order(
        self,
        out_trade_no: str,
        description: str,
        amount: Decimal,  # 单位：元
        openid: str,
        app_id: str,
        notify_url: str | None = None,
    ) -> dict:
        """微信统一下单（JSAPI），返回 prepay_id

        Args:
            out_trade_no: 商户订单号
            description: 商品描述
            amount: 金额（单位：元）
            openid: 用户 openid
            app_id: 小程序 app_id
            notify_url: 回调地址（可选，覆盖默认）

        Returns:
            包含 prepay_id 的字典

        Raises:
            Exception: 下单失败
        """
        # 转换金额：元 -> 分
        total_amount = int(amount * Decimal("100"))

        # 构建下单参数
        pay_params = {
            "description": description,
            "out_trade_no": out_trade_no,
            "amount": {"total": total_amount},
            "payer": {"openid": openid},
        }

        # 服务商模式需要传 sub_mchid
        if self.profile.mode == "service_provider":
            if not self.profile.sub_mchid:
                raise ValueError("服务商模式缺少 sub_mchid")
            pay_params["sub_mchid"] = self.profile.sub_mchid

        # 覆盖 notify_url
        if notify_url:
            pay_params["notify_url"] = notify_url

        logger.info(f"微信下单: {out_trade_no}, 金额: {amount}元, 模式: {self.profile.mode}")

        try:
            code, message = self.wxpay.pay(**pay_params)
            if code != 200:
                logger.error(f"微信下单失败: code={code}, message={message}")
                raise Exception(f"微信下单失败: {message}")

            # message 是 JSON 字符串，需要解析
            import json
            result = json.loads(message) if isinstance(message, str) else message

            prepay_id = result.get("prepay_id")
            if not prepay_id:
                logger.error(f"微信下单响应缺少 prepay_id: {result}")
                raise Exception("微信下单响应异常")

            return {"prepay_id": prepay_id, "raw_response": result}

        except Exception as e:
            logger.error(f"微信下单异常: {e}")
            raise

    async def query_order(self, out_trade_no: str) -> dict:
        """查询支付订单

        Args:
            out_trade_no: 商户订单号

        Returns:
            订单信息字典

        Raises:
            Exception: 查询失败
        """
        try:
            code, message = self.wxpay.query(out_trade_no=out_trade_no)
            if code != 200:
                raise Exception(f"查询订单失败: {message}")

            import json
            result = json.loads(message) if isinstance(message, str) else message
            return result

        except Exception as e:
            logger.error(f"查询订单异常: {e}")
            raise

    async def create_refund(
        self,
        out_trade_no: str,
        out_refund_no: str,
        total: Decimal,  # 原订单金额（元）
        refund: Decimal,  # 退款金额（元）
        reason: str = "",
        notify_url: str | None = None,
        transaction_id: str | None = None,
    ) -> dict:
        """申请退款

        Args:
            out_trade_no: 商户订单号
            out_refund_no: 商户退款单号
            total: 原订单金额（元）
            refund: 退款金额（元）
            reason: 退款原因
            notify_url: 退款回调地址（可选）
            transaction_id: 微信支付交易号（可选，优先用于历史订单兼容）

        Returns:
            退款结果字典

        Raises:
            Exception: 退款失败
        """
        # 转换金额：元 -> 分
        total_amount = int(total * Decimal("100"))
        refund_amount = int(refund * Decimal("100"))

        refund_params = {
            "out_refund_no": out_refund_no,
            "amount": {
                "refund": refund_amount,
                "total": total_amount,
                "currency": "CNY",
            },
        }

        if reason:
            refund_params["reason"] = reason

        # 如果传了 notify_url 则覆盖默认
        if notify_url:
            refund_params["notify_url"] = notify_url

        if transaction_id:
            refund_params["transaction_id"] = transaction_id
        else:
            # 未传入 transaction_id 时，回查订单获取；若拿不到则退回 out_trade_no 模式。
            order_info = await self.query_order(out_trade_no)
            transaction_id = order_info.get("transaction_id")
            if not transaction_id:
                # 可能订单未支付，尝试用 out_trade_no
                refund_params["out_trade_no"] = out_trade_no
            else:
                refund_params["transaction_id"] = transaction_id

        logger.info(f"微信退款: {out_refund_no}, 订单: {out_trade_no}, 金额: {refund}元")

        try:
            code, message = self.wxpay.refund(**refund_params)
            if code != 200:
                logger.error(f"微信退款失败: code={code}, message={message}")
                raise Exception(f"微信退款失败: {message}")

            import json
            result = json.loads(message) if isinstance(message, str) else message
            return result

        except Exception as e:
            logger.error(f"微信退款异常: {e}")
            raise

    async def query_refund(self, out_refund_no: str) -> dict:
        """查询退款

        Args:
            out_refund_no: 商户退款单号

        Returns:
            退款信息字典

        Raises:
            Exception: 查询失败
        """
        try:
            code, message = self.wxpay.query_refund(out_refund_no=out_refund_no)
            if code != 200:
                raise Exception(f"查询退款失败: {message}")

            import json
            result = json.loads(message) if isinstance(message, str) else message
            return result

        except Exception as e:
            logger.error(f"查询退款异常: {e}")
            raise

    def verify_callback(self, headers: dict, body: bytes) -> dict:
        """验证回调签名并解析数据

        Args:
            headers: 请求头字典
            body: 请求体字节

        Returns:
            解密后的回调数据字典

        Raises:
            Exception: 验签失败或解密失败
        """
        try:
            result = self.wxpay.callback(headers=headers, body=body)
            if not result:
                raise Exception("回调验证失败")

            return result

        except Exception as e:
            logger.error(f"回调验证异常: {e}")
            raise
