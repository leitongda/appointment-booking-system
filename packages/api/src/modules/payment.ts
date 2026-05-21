import request from '../request';

export interface PaymentOrderStatus {
  appointment_id: string;
  status: number;
  payment_amount: number;
  payment_transaction_id: string | null;
  paid_at: string | null;
  refund_status: string | null;
  refund_amount: number;
}

export const paymentApi = {
  /**
   * 查询支付订单状态
   */
  getOrderStatus: (appointmentId: string): Promise<PaymentOrderStatus> => {
    return request.get(`/payments/orders/${appointmentId}`);
  },
};
