import request from '../request';
import type { Appointment, PageResult } from '@hospital/shared';

export interface AppointmentListParams {
  status?: number;
  patientId?: string;
  doctorId?: string;
  storeId?: string;
  startDate?: string;
  endDate?: string;
  /** 关键字搜索（预约编号/患者姓名/手机号） */
  keyword?: string;
  /** 科室ID */
  departmentId?: string;
  /** 创建时间开始 */
  createdStart?: string;
  /** 创建时间结束 */
  createdEnd?: string;
  /** 页码，默认1 */
  page?: number;
  /**
   * 每页数量
   * - 默认 10
   * - 常规上限 100
   * - 扩展上限 500（需管理员权限 + 必须同时提供 startDate 和 endDate）
   */
  pageSize?: number;
}

export interface AppointmentCreateData {
  scheduleId: string;
  patientId: string;
  symptomDescription?: string;
}

export interface PaymentParams {
  timeStamp: string;
  nonceStr: string;
  package: string;
  signType: string;
  paySign: string;
}

export interface AppointmentCreatePaymentPayload {
  appointment: Appointment;
  payment_required: boolean;
  payment_amount?: number;
  payment_params?: PaymentParams | null;
  payment_param_error?: string | null;
}

export interface RefundRecord {
  id: string;
  refundNo: string;
  refundAmount: number;
  status: string;
  refundReason?: string;
  createdAt?: string;
  updatedAt?: string;
  failedReason?: string;
}

// 重复预约检查结果
export interface DuplicateAppointmentInfo {
  id: string;
  appointmentNo: string;
  doctorName: string | null;
  departmentName: string | null;
  scheduleDate: string | null;
  timeSlot: string | null;
  status: number;
}

export interface CheckDuplicateResult {
  hasDuplicate: boolean;
  appointments: DuplicateAppointmentInfo[];
}

export interface AppointmentStatistics {
  total: number;
  confirmed: number;
  signedIn: number;
  inProgress: number;
  completed: number;
  cancelled: number;
  noShow: number;
}

export interface QueueInfo {
  current: {
    id: string;
    queueNumber: number;
    patientName: string;
    callTime: string;
  } | null;
  waitingCount: number;
  waitingList: {
    id: string;
    queueNumber: number;
    patientName: string;
    signInTime: string;
  }[];
  passedCount: number;
  passedList: {
    id: string;
    queueNumber: number;
    patientName: string;
  }[];
}

// 待签到预约（用于扫码签到）
export interface PendingAppointment {
  id: string;
  appointmentNo: string;
  patientName: string | null;
  doctorName: string | null;
  departmentName: string | null;
  scheduleDate: string | null;
  timeSlot: string | null;
  startTime?: string | null;
  endTime?: string | null;
  status: number;
  signInStatus?: 'early' | 'available' | 'late' | 'error';
  signInMessage?: string;
  // 新增字段：签到时间窗信息
  checkinOpenAt?: string | null;
  checkinCloseAt?: string | null;
  minutesUntilOpen?: number | null;
  minutesUntilClose?: number | null;
}

// 签到队列项
export interface CheckinQueueItem {
  id: string;
  appointmentNo: string;
  queueNumber: number | null;
  patientId: string;
  patientName: string | null;
  doctorId: string;
  doctorName: string | null;
  departmentName: string | null;
  scheduleDate: string | null;
  timeSlot: number | null;
  status: number;
  signInTime: string | null;
  callTime: string | null;
  /** 签到方式: QR_CODE/MANUAL/PHONE */
  checkinMethod?: string | null;
}

// 患者历史就诊记录项
export interface PatientHistoryItem {
  id: string;
  appointmentNo: string;
  scheduleDate: string | null;
  timeSlot: string | null;
  status: number;
  completeTime: string | null;
  symptomDescription: string | null;
  hasMedicalRecord: boolean;
}

export const appointmentApi = {
  /**
   * 检查同一天同一时段是否有重复预约
   * 用于在预约前提醒用户
   */
  checkDuplicate: (scheduleId: string, patientId: string): Promise<CheckDuplicateResult> => {
    // 验证参数非空
    if (!scheduleId?.trim() || !patientId?.trim()) {
      return Promise.reject(new Error('缺少必要参数：排班ID或就诊人ID'));
    }
    return request.get('/appointments/query/check-duplicate', {
      params: { schedule_id: scheduleId.trim(), patient_id: patientId.trim() }
    });
  },

  /**
   * 获取预约列表。
   * 当 pageSize > 100 时，后端要求调用方具备管理员权限，且必须同时传 startDate 和 endDate。
   */
  getList: (params?: AppointmentListParams): Promise<PageResult<Appointment>> => {
    // 转换 camelCase 到 snake_case
    const queryParams = params ? {
      status: params.status,
      patient_id: params.patientId,
      doctor_id: params.doctorId,
      store_id: params.storeId,
      start_date: params.startDate,
      end_date: params.endDate,
      keyword: params.keyword,
      department_id: params.departmentId,
      created_start: params.createdStart,
      created_end: params.createdEnd,
      page: params.page,
      page_size: params.pageSize,
    } : undefined;
    return request.get('/appointments/query', { params: queryParams });
  },

  getToday: (): Promise<Appointment[]> => {
    return request.get('/appointments/query/today');
  },

  getStatistics: (params?: { doctorId?: string; startDate?: string; endDate?: string }): Promise<AppointmentStatistics> => {
    return request.get('/appointments/query/statistics', { params });
  },

  getDetail: (id: string): Promise<Appointment> => {
    return request.get(`/appointments/query/${id}`);
  },

  /**
   * 按预约号获取预约详情
   */
  getDetailByNo: (appointmentNo: string): Promise<Appointment> => {
    return request.get(`/appointments/query/by-no/${appointmentNo}`);
  },

  create: (data: AppointmentCreateData): Promise<Appointment | AppointmentCreatePaymentPayload> => {
    return request.post('/appointments', data);
  },

  cancel: (id: string, reason?: string): Promise<void> => {
    return request.put(`/appointments/${id}/cancel`, { reason });
  },

  signIn: (id: string, data?: { checkin_method?: string }): Promise<{ message: string; queueNumber: number }> => {
    return request.put(`/appointments/${id}/sign-in`, data);
  },

  /**
   * 取消签到（仅超级管理员）
   * 将状态从"已签到"恢复为"已预约"
   */
  cancelSignIn: (id: string): Promise<{ message: string }> => {
    return request.put(`/appointments/${id}/cancel-sign-in`);
  },

  call: (id: string): Promise<void> => {
    return request.put(`/appointments/${id}/call`);
  },

  complete: (id: string): Promise<void> => {
    return request.put(`/appointments/${id}/complete`);
  },

  /**
   * 过号
   */
  pass: (id: string): Promise<void> => {
    return request.put(`/appointments/${id}/pass`);
  },

  /**
   * 重新叫号
   */
  recall: (id: string): Promise<void> => {
    return request.put(`/appointments/${id}/recall`);
  },

  /**
   * 标记爽约
   */
  markNoShow: (id: string): Promise<void> => {
    return request.put(`/appointments/${id}/no-show`);
  },

  /**
   * 获取叫号队列信息
   */
  getQueueInfo: (): Promise<QueueInfo> => {
    return request.get('/appointments/query/queue/info');
  },

  /**
   * 获取用户在指定门店的今日待签到预约
   * 用于患者扫码签到时选择要签到的预约
   */
  getTodayPending: (storeId: string): Promise<PendingAppointment[]> => {
    return request.get('/appointments/query/today-pending', { params: { store_id: storeId } });
  },

  /**
   * 获取签到队列
   * 用于管理后台和医生端查看当日已签到的患者队列
   */
  getCheckinQueue: (params?: {
    storeId?: string;
    doctorId?: string;
    targetDate?: string;
  }): Promise<CheckinQueueItem[]> => {
    const queryParams = params ? {
      store_id: params.storeId,
      doctor_id: params.doctorId,
      target_date: params.targetDate,
    } : undefined;
    return request.get('/appointments/query/queue', { params: queryParams });
  },

  /**
   * 获取医生端预约列表（doctor-portal 端点）
   * 自动限制为当前医生的预约
   */
  getMyAppointments: (params?: {
    status?: number;
    startDate?: string;
    endDate?: string;
    page?: number;
    pageSize?: number;
  }): Promise<Appointment[]> => {
    const queryParams = params ? {
      status: params.status,
      start_date: params.startDate,
      end_date: params.endDate,
      page: params.page,
      page_size: params.pageSize,
    } : undefined;
    return request.get('/doctor-portal/appointments', { params: queryParams });
  },

  /**
   * 获取患者历史就诊记录（医生端）
   * 返回该患者在当前医生处的历史预约
   */
  getPatientHistory: (patientId: string, params?: {
    status?: number;
    page?: number;
    pageSize?: number;
  }): Promise<{
    items: PatientHistoryItem[];
    total: number;
    page: number;
    pageSize: number;
  }> => {
    const queryParams = params ? {
      status: params.status,
      page: params.page,
      page_size: params.pageSize,
    } : undefined;
    return request.get(`/doctor-portal/patients/${patientId}/appointments`, { params: queryParams });
  },

  /**
   * 创建复诊预约（医生端）
   * 基于已完成的预约为患者创建复诊预约
   */
  createFollowUp: (appointmentId: string, scheduleId: string): Promise<{
    message: string;
    appointmentId: string;
    appointmentNo: string;
  }> => {
    return request.post(`/doctor-portal/appointments/${appointmentId}/follow-up`, { schedule_id: scheduleId });
  },

  /**
   * 创建退款
   */
  createRefund: (data: { appointmentId: string; refundAmount: number; refundReason: string }) => {
    return request.post('/refunds', {
      appointment_id: data.appointmentId,
      refund_amount: data.refundAmount,
      refund_reason: data.refundReason,
    });
  },

  /**
   * 获取退款记录
   */
  getRefundRecords: (appointmentId: string): Promise<RefundRecord[]> => {
    return request
      .get<{ total: number; items: RefundRecord[] }>('/refunds', { params: { appointment_id: appointmentId } })
      .then((result) => result.items ?? []);
  },

  /**
   * 获取诊费
   */
  getConsultationFee: (params: { doctorId: string; storeId: string; departmentId: string }) => {
    return request.get('/consultation-fees/amount', { params });
  },

  /**
   * 获取支付参数（用于待支付订单重新发起支付）
   */
  getPaymentParams: (appointmentId: string, openid?: string): Promise<PaymentParams> => {
    return request.get(`/appointments/${appointmentId}/payment-params`, {
      params: openid ? { openid } : undefined,
    });
  },

  /**
   * 查询支付订单状态（用于前端支付结果二次确认）
   */
  getPaymentStatus: (appointmentId: string): Promise<{
    appointment_id: string;
    status: number;
    payment_amount: number;
    payment_transaction_id: string | null;
    paid_at: string | null;
    refund_status: string | null;
    refund_amount: number;
  }> => {
    return request.get(`/payments/orders/${appointmentId}`);
  },

  /**
   * 提交预约满意度评价
   */
  createSatisfaction: (appointmentId: string, data: {
    overallScore: number;
    serviceScore?: number;
    environmentScore?: number;
    comment?: string;
    tags?: string[];
  }): Promise<any> => {
    return request.post(`/appointments/${appointmentId}/satisfaction`, {
      overall_score: data.overallScore,
      service_score: data.serviceScore,
      environment_score: data.environmentScore,
      comment: data.comment,
      tags: data.tags,
    });
  },

  /**
   * 查询预约满意度
   */
  getSatisfaction: (appointmentId: string): Promise<any> => {
    return request.get(`/appointments/${appointmentId}/satisfaction`);
  },
};
