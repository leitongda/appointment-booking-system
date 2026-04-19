export type BookingResultStatus =
  | 'success'
  | 'confirmed'
  | 'cancelled'
  | 'failed'
  | 'unavailable';

const REQUEST_PAYMENT_CANCEL_ERRMSG = 'requestPayment:fail cancel';
const PAYMENT_CANCEL_PATTERNS = [
  REQUEST_PAYMENT_CANCEL_ERRMSG,
  'requestpayment:fail cancel by user',
  'cancel by user',
  'user cancel',
  '用户取消',
  '已取消支付',
];

const getReadableErrorMessage = (error: any) => {
  const candidates = [error?.message, error?.errMsg];

  for (const candidate of candidates) {
    if (typeof candidate === 'string' && candidate.trim()) {
      return candidate.trim();
    }
  }

  return '';
};

const isPaymentCancelled = (error: any) => {
  const message = getReadableErrorMessage(error).toLowerCase();

  if (!message) return false;

  return PAYMENT_CANCEL_PATTERNS.some((pattern) => message.includes(pattern.toLowerCase()));
};

export const buildBookingResultUrl = (
  appointmentNo: string,
  status: BookingResultStatus,
  message?: string
) => {
  const params = [
    `appointmentNo=${encodeURIComponent(appointmentNo)}`,
    `status=${encodeURIComponent(status)}`,
  ];

  if (message) {
    params.push(`message=${encodeURIComponent(message)}`);
  }

  return `/packageBooking/pages/booking/result?${params.join('&')}`;
};

export const getPaymentPreparationFailure = (
  error: any,
  fallbackMessage = '暂时无法发起支付，请稍后再试'
) => {
  const rawMessage = getReadableErrorMessage(error);
  const message = rawMessage || fallbackMessage;

  // 根据后端错误码细化提示
  if (rawMessage.includes('payment_config_error')) {
    return {
      status: 'unavailable' as const,
      message: '该机构支付配置异常，请联系客服处理。订单已保留，配置恢复后可重新支付。',
    };
  }

  if (rawMessage.includes('payment_temporary_error')) {
    return {
      status: 'unavailable' as const,
      message: '支付服务暂时繁忙，请稍后在预约详情页重新支付。',
    };
  }

  return {
    status: 'unavailable' as const,
    message,
  };
};

export const getPaymentRequestFailure = (error: any) => {
  if (isPaymentCancelled(error)) {
    return {
      status: 'cancelled' as const,
      message: '您已取消支付，订单已保留，可稍后重新支付。',
    };
  }

  return {
    status: 'failed' as const,
    message: '支付未完成，订单已保留，可稍后重新支付。',
  };
};

/**
 * 支付结果二次确认：Taro.requestPayment reject 后向服务端查询实际支付状态。
 *
 * 返回 true 表示后端已确认支付成功，调用方应跳转成功结果页。
 * 返回 false 表示后端仍为待支付，调用方按原 reject 逻辑处理。
 */
export const verifyPaymentResult = async (
  getPaymentStatus: (id: string) => Promise<{ status: number }>,
  appointmentId: string,
): Promise<boolean> => {
  try {
    const result = await getPaymentStatus(appointmentId);
    return result.status !== 0;
  } catch {
    return false;
  }
};
