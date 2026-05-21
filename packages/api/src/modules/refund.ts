import request from '../request';

export interface RefundRecordItem {
  id: string;
  appointment_id: string;
  refund_no: string;
  out_trade_no?: string | null;
  refund_amount: number;
  original_amount: number;
  refund_reason?: string | null;
  status: string;
  wx_refund_id?: string | null;
  failed_reason?: string | null;
  mch_id?: string | null;
  sub_mchid?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface RefundListParams {
  appointmentId?: string;
  status?: string;
  page?: number;
  pageSize?: number;
}

export interface RefundListResult {
  total: number;
  items: RefundRecordItem[];
}

export interface RefundableAmount {
  payment_amount: number | null;
  refunded_amount: number;
  refundable_amount: number;
  refund_status: string | null;
}

export interface RefundCreateData {
  appointmentId: string;
  refundAmount: number;
  refundReason: string;
}

export const refundApi = {
  /**
   * 获取退款记录列表
   */
  getList: (params?: RefundListParams): Promise<RefundListResult> => {
    const queryParams = params
      ? {
          appointment_id: params.appointmentId,
          status: params.status,
          page: params.page,
          page_size: params.pageSize,
        }
      : undefined;
    return request.get('/refunds', { params: queryParams });
  },

  /**
   * 获取退款详情
   */
  getDetail: (refundId: string): Promise<RefundRecordItem> => {
    return request.get(`/refunds/${refundId}`);
  },

  /**
   * 查询预约的可退款金额
   */
  getRefundableAmount: (appointmentId: string): Promise<RefundableAmount> => {
    return request.get(`/refunds/refundable-amount/${appointmentId}`);
  },

  /**
   * 创建退款
   */
  create: (data: RefundCreateData): Promise<RefundRecordItem> => {
    return request.post('/refunds', {
      appointment_id: data.appointmentId,
      refund_amount: data.refundAmount,
      refund_reason: data.refundReason,
    });
  },
};
