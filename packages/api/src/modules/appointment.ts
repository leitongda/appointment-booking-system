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
  page?: number;
  pageSize?: number;
}

export interface AppointmentCreateData {
  scheduleId: string;
  patientId: string;
  symptomDescription?: string;
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
  pending: number;
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
  signInStatus?: 'early' | 'available' | 'late';
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
    return request.get('/appointments/check-duplicate', {
      params: { schedule_id: scheduleId.trim(), patient_id: patientId.trim() }
    });
  },

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
    return request.get('/appointments', { params: queryParams });
  },

  getToday: (): Promise<Appointment[]> => {
    return request.get('/appointments/today');
  },

  getStatistics: (params?: { doctorId?: string; startDate?: string; endDate?: string }): Promise<AppointmentStatistics> => {
    return request.get('/appointments/statistics', { params });
  },

  getDetail: (id: string): Promise<Appointment> => {
    return request.get(`/appointments/${id}`);
  },

  /**
   * 按预约号获取预约详情
   */
  getDetailByNo: (appointmentNo: string): Promise<Appointment> => {
    return request.get(`/appointments/by-no/${appointmentNo}`);
  },

  create: (data: AppointmentCreateData): Promise<Appointment> => {
    return request.post('/appointments', data);
  },

  cancel: (id: string, reason?: string): Promise<void> => {
    return request.put(`/appointments/${id}/cancel`, { reason });
  },

  signIn: (id: string): Promise<{ message: string; queueNumber: number }> => {
    return request.put(`/appointments/${id}/sign-in`);
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
    return request.get('/appointments/queue/info');
  },

  /**
   * 获取用户在指定门店的今日待签到预约
   * 用于患者扫码签到时选择要签到的预约
   */
  getTodayPending: (storeId: string): Promise<PendingAppointment[]> => {
    return request.get('/appointments/today-pending', { params: { store_id: storeId } });
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
    return request.get('/appointments/queue', { params: queryParams });
  },
};
