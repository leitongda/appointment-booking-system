import { describe, expect, test } from 'vitest';
import {
  buildBookingResultUrl,
  getPaymentPreparationFailure,
  getPaymentRequestFailure,
} from '../payment';

describe('payment utils', () => {
  test('buildBookingResultUrl encodes appointment number, status, and message', () => {
    const url = buildBookingResultUrl('A&B 001', 'cancelled', '您已取消支付，请稍后重试');

    expect(url).toBe(
      '/packageBooking/pages/booking/result?appointmentNo=A%26B%20001&status=cancelled&message=%E6%82%A8%E5%B7%B2%E5%8F%96%E6%B6%88%E6%94%AF%E4%BB%98%EF%BC%8C%E8%AF%B7%E7%A8%8D%E5%90%8E%E9%87%8D%E8%AF%95'
    );
  });

  test('getPaymentPreparationFailure prefers backend readable message', () => {
    expect(getPaymentPreparationFailure({ message: 'openid 未绑定' })).toEqual({
      status: 'unavailable',
      message: 'openid 未绑定',
    });

    expect(getPaymentPreparationFailure({ errMsg: 'request:fail timeout' })).toEqual({
      status: 'unavailable',
      message: 'request:fail timeout',
    });
  });

  test('getPaymentPreparationFailure recognises payment_config_error', () => {
    expect(
      getPaymentPreparationFailure({ message: 'payment_config_error: 支付配置缺失' }),
    ).toEqual({
      status: 'unavailable',
      message: '该机构支付配置异常，请联系客服处理。订单已保留，配置恢复后可重新支付。',
    });
  });

  test('getPaymentPreparationFailure recognises payment_temporary_error', () => {
    expect(getPaymentPreparationFailure({ message: 'payment_temporary_error' })).toEqual({
      status: 'unavailable',
      message: '支付服务暂时繁忙，请稍后在预约详情页重新支付。',
    });
  });

  test('getPaymentPreparationFailure falls back when error has no message', () => {
    expect(getPaymentPreparationFailure(null)).toEqual({
      status: 'unavailable',
      message: '暂时无法发起支付，请稍后再试',
    });
  });

  test('getPaymentRequestFailure classifies common cancellation variants as cancelled', () => {
    expect(getPaymentRequestFailure({ errMsg: 'requestPayment:fail cancel' })).toEqual({
      status: 'cancelled',
      message: '您已取消支付，订单已保留，可稍后重新支付。',
    });

    expect(getPaymentRequestFailure({ errMsg: 'requestPayment:fail cancel by user' })).toEqual({
      status: 'cancelled',
      message: '您已取消支付，订单已保留，可稍后重新支付。',
    });

    expect(getPaymentRequestFailure({ message: '用户取消支付' })).toEqual({
      status: 'cancelled',
      message: '您已取消支付，订单已保留，可稍后重新支付。',
    });
  });

  test('getPaymentRequestFailure keeps non-cancel errors as failed', () => {
    expect(getPaymentRequestFailure({ errMsg: 'requestPayment:fail system error' })).toEqual({
      status: 'failed',
      message: '支付未完成，订单已保留，可稍后重新支付。',
    });
  });
});
