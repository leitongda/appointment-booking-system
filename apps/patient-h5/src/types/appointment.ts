import type { Appointment } from '@hospital/shared';

/**
 * 预约状态枚举
 *
 * 注意：状态码必须与后端 app/constants/appointment.py 与 @hospital/shared 的 APPOINTMENT_STATUS 严格对齐。
 * 历史问题：本地曾把 IN_PROGRESS 错标为 3、NO_SHOW 错标为 7、缺失 EXPIRED，
 * 导致后端返回 status=4(就诊中)/8(已爽约)/7(已过期) 时患者端查不到 config 显示空白。
 * 此处已对齐为权威值（详见 packages/shared/src/constants/appointment.ts）。
 */
export enum AppointmentStatus {
  /** 待支付 */
  PENDING_PAYMENT = 0,
  /** 已预约（待就诊） */
  CONFIRMED = 1,
  /** 已签到 */
  SIGNED_IN = 2,
  /** 历史候诊（后端遗留值，前端一般不展示） */
  WAITING = 3,
  /** 就诊中 */
  IN_PROGRESS = 4,
  /** 已完成 */
  COMPLETED = 5,
  /** 已取消 */
  CANCELLED = 6,
  /** 已过期 */
  EXPIRED = 7,
  /** 已爽约 */
  NO_SHOW = 8,
}

/** 预约状态配置 */
export interface AppointmentStatusConfig {
  label: string;
  color: 'primary' | 'success' | 'warning' | 'danger' | 'default';
  cssClass: string;
}

/** 预约状态映射表 */
export const APPOINTMENT_STATUS_CONFIG: Record<number, AppointmentStatusConfig> = {
  [AppointmentStatus.PENDING_PAYMENT]: {
    label: '待支付',
    color: 'warning',
    cssClass: 'bg-yellow-100 text-yellow-600',
  },
  [AppointmentStatus.CONFIRMED]: {
    label: '待就诊',
    color: 'primary',
    cssClass: 'bg-accent/10 text-accent',
  },
  [AppointmentStatus.SIGNED_IN]: {
    label: '已签到',
    color: 'primary',
    cssClass: 'bg-blue-100 text-blue-600',
  },
  [AppointmentStatus.WAITING]: {
    label: '候诊中',
    color: 'default',
    cssClass: 'bg-muted text-muted-foreground',
  },
  [AppointmentStatus.IN_PROGRESS]: {
    label: '就诊中',
    color: 'primary',
    cssClass: 'bg-blue-100 text-blue-600',
  },
  [AppointmentStatus.COMPLETED]: {
    label: '已完成',
    color: 'success',
    cssClass: 'bg-green-100 text-green-600',
  },
  [AppointmentStatus.CANCELLED]: {
    label: '已取消',
    color: 'default',
    cssClass: 'bg-muted text-muted-foreground',
  },
  [AppointmentStatus.EXPIRED]: {
    label: '已过期',
    color: 'default',
    cssClass: 'bg-muted text-muted-foreground',
  },
  [AppointmentStatus.NO_SHOW]: {
    label: '已爽约',
    color: 'danger',
    cssClass: 'bg-red-100 text-red-600',
  },
};

/** 预约记录类型（复用 @hospital/shared 的 Appointment） */
export type AppointmentRecord = Appointment;
