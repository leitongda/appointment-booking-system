import {
  APPOINTMENT_STATUS,
  APPOINTMENT_STATUS_TAG,
  type Appointment,
} from '@hospital/shared';

/** 预约状态配置 */
export interface AppointmentStatusConfig {
  label: string;
  color: 'primary' | 'success' | 'warning' | 'danger' | 'default';
  cssClass: string;
}

const STATUS_CLASS_MAP: Record<number, Pick<AppointmentStatusConfig, 'color' | 'cssClass'>> = {
  [APPOINTMENT_STATUS.PENDING_PAYMENT]: {
    color: 'warning',
    cssClass: 'bg-yellow-100 text-yellow-600',
  },
  [APPOINTMENT_STATUS.CONFIRMED]: {
    color: 'primary',
    cssClass: 'bg-accent/10 text-accent',
  },
  [APPOINTMENT_STATUS.SIGNED]: {
    color: 'primary',
    cssClass: 'bg-blue-100 text-blue-600',
  },
  [APPOINTMENT_STATUS.WAITING]: {
    color: 'default',
    cssClass: 'bg-muted text-muted-foreground',
  },
  [APPOINTMENT_STATUS.SEEING]: {
    color: 'primary',
    cssClass: 'bg-blue-100 text-blue-600',
  },
  [APPOINTMENT_STATUS.COMPLETED]: {
    color: 'success',
    cssClass: 'bg-green-100 text-green-600',
  },
  [APPOINTMENT_STATUS.CANCELLED]: {
    color: 'default',
    cssClass: 'bg-muted text-muted-foreground',
  },
  [APPOINTMENT_STATUS.EXPIRED]: {
    color: 'default',
    cssClass: 'bg-muted text-muted-foreground',
  },
  [APPOINTMENT_STATUS.NO_SHOW]: {
    color: 'danger',
    cssClass: 'bg-red-100 text-red-600',
  },
};

/** 预约记录类型（复用 @hospital/shared 的 Appointment） */
export type AppointmentRecord = Appointment;

/** 患者 H5 预约状态展示配置，文案与状态码来自 shared，样式只在本端适配。 */
export const getAppointmentStatusConfig = (status: number): AppointmentStatusConfig => {
  const tag = APPOINTMENT_STATUS_TAG[status] || { text: '未知', color: 'default' };
  const localStyle = STATUS_CLASS_MAP[status] || {
    color: 'default',
    cssClass: 'bg-muted text-muted-foreground',
  };

  return {
    label: tag.text,
    color: localStyle.color,
    cssClass: localStyle.cssClass,
  };
};
