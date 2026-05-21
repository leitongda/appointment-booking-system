/**
 * 共享 WebSocket 类型定义
 * 用于 doctor、patient-h5、patient-miniapp 端
 */

// WebSocket 消息类型
export enum WSMessageType {
  // 系统消息
  CONNECTED = 'CONNECTED',
  HEARTBEAT = 'HEARTBEAT',
  ERROR = 'ERROR',

  // 预约相关
  PATIENT_SIGNED_IN = 'PATIENT_SIGNED_IN',
  PATIENT_CALLED = 'PATIENT_CALLED',
  PATIENT_PASSED = 'PATIENT_PASSED',
  PATIENT_RECALLED = 'PATIENT_RECALLED',
  PATIENT_COMPLETED = 'PATIENT_COMPLETED',
  PATIENT_NO_SHOW = 'PATIENT_NO_SHOW',
  QUEUE_UPDATED = 'QUEUE_UPDATED',
  NEW_APPOINTMENT = 'NEW_APPOINTMENT',

  // 排班相关
  SCHEDULE_SUSPENDED = 'SCHEDULE_SUSPENDED',
  LEAVE_REQUEST_REVIEWED = 'LEAVE_REQUEST_REVIEWED',

  // 消息中心
  NEW_MESSAGE = 'NEW_MESSAGE',

  // 系统通知
  SYSTEM_MESSAGE = 'SYSTEM_MESSAGE',
}

// WebSocket 消息结构
export interface WSMessage<T = any> {
  type: WSMessageType | string;
  data: T;
  timestamp: string;
  message_id?: string;
}

// 连接状态
export enum ConnectionStatus {
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  DISCONNECTED = 'DISCONNECTED',
  RECONNECTING = 'RECONNECTING',
  ERROR = 'ERROR',
}

// 患者端常用消息类型
export const PATIENT_MESSAGE_TYPES = [
  WSMessageType.PATIENT_CALLED,
  WSMessageType.PATIENT_PASSED,
  WSMessageType.PATIENT_RECALLED,
  WSMessageType.PATIENT_NO_SHOW,
  WSMessageType.NEW_MESSAGE,
] as const;

// 医生端常用消息类型
export const DOCTOR_MESSAGE_TYPES = [
  WSMessageType.PATIENT_SIGNED_IN,
  WSMessageType.PATIENT_CALLED,
  WSMessageType.PATIENT_PASSED,
  WSMessageType.PATIENT_RECALLED,
  WSMessageType.PATIENT_COMPLETED,
  WSMessageType.PATIENT_NO_SHOW,
  WSMessageType.QUEUE_UPDATED,
  WSMessageType.NEW_APPOINTMENT,
  WSMessageType.LEAVE_REQUEST_REVIEWED,
  WSMessageType.NEW_MESSAGE,
] as const;
