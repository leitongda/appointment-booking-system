/**
 * 医生端叫号队列专用接口
 *
 * 这些端点挂在 /doctor-portal/queue 前缀下，使用 get_current_doctor_by_token 鉴权
 * （要求 doctor token）。医生端必须走这些端点而非共享的 appointmentApi.call 等
 * （后者指向 /appointments/{id}/call，挂 get_current_admin，doctor token 会被 403）。
 */
import { request } from '../request';

export const doctorQueueApi = {
  /** 叫号 */
  call: (appointmentId: string): Promise<void> => {
    return request.put(`/doctor-portal/queue/${appointmentId}/call`);
  },

  /** 完成就诊 */
  complete: (appointmentId: string): Promise<void> => {
    return request.put(`/doctor-portal/queue/${appointmentId}/complete`);
  },

  /** 过号 */
  pass: (appointmentId: string): Promise<void> => {
    return request.put(`/doctor-portal/queue/${appointmentId}/pass`);
  },

  /** 重新叫号 */
  recall: (appointmentId: string): Promise<void> => {
    return request.put(`/doctor-portal/queue/${appointmentId}/recall`);
  },

  /** 标记爽约 */
  markNoShow: (appointmentId: string): Promise<void> => {
    return request.put(`/doctor-portal/queue/${appointmentId}/no-show`);
  },
};
