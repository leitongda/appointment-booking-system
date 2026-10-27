/**
 * 医生端 WebSocket Hook
 * 基于 @hospital/shared 的共享连接管理，添加医生端特有的消息处理和通知
 */
import { useMemo, useCallback } from 'react';
import {
  useWebSocketConnection,
  createWebSocketUrlBuilder,
  ConnectionStatus,
} from '@hospital/shared';
import type { WSMessage, UseWebSocketConnectionReturn } from '@hospital/shared';
import { notification } from 'antd';
import { isWindowInactive, sendDesktopNotification } from '../utils/desktopNotify';

// 医生端消息类型
export enum WSMessageType {
  CONNECTED = 'CONNECTED',
  HEARTBEAT = 'HEARTBEAT',
  ERROR = 'ERROR',
  PATIENT_SIGNED_IN = 'PATIENT_SIGNED_IN',
  PATIENT_CALLED = 'PATIENT_CALLED',
  PATIENT_PASSED = 'PATIENT_PASSED',
  PATIENT_RECALLED = 'PATIENT_RECALLED',
  PATIENT_COMPLETED = 'PATIENT_COMPLETED',
  PATIENT_NO_SHOW = 'PATIENT_NO_SHOW',
  QUEUE_UPDATED = 'QUEUE_UPDATED',
  NEW_APPOINTMENT = 'NEW_APPOINTMENT',
  SCHEDULE_SUSPENDED = 'SCHEDULE_SUSPENDED',
  LEAVE_REQUEST_REVIEWED = 'LEAVE_REQUEST_REVIEWED',
  SYSTEM_MESSAGE = 'SYSTEM_MESSAGE',
}

// 重新导出共享类型
export { ConnectionStatus };
export type { WSMessage };

// Hook 配置
interface UseWebSocketOptions {
  doctorId: string;
  onMessage?: (message: WSMessage) => void;
  onPatientSignedIn?: (data: any) => void;
  onQueueUpdated?: (data: any) => void;
  onNewAppointment?: (data: any) => void;
  onLeaveRequestReviewed?: (data: any) => void;
  onSystemMessage?: (data: any) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  showNotifications?: boolean;
}

/**
 * 医生端 WebSocket 连接管理 Hook
 */
export const useWebSocket = (options: UseWebSocketOptions) => {
  const {
    doctorId,
    onMessage,
    onPatientSignedIn,
    onQueueUpdated,
    onNewAppointment,
    onLeaveRequestReviewed,
    onSystemMessage,
    showNotifications = true,
    ...connectionOptions
  } = options;

  // 构建 URL（仅在 doctorId 变化时重建）
  const buildUrl = useMemo(
    () => createWebSocketUrlBuilder(`/api/v1/ws/doctor/${doctorId}`),
    [doctorId]
  );

  // 消息处理：分发到各业务回调 + 通知
  const handleMessage = useCallback(
    (msg: WSMessage) => {
      onMessage?.(msg);

      switch (msg.type) {
        // 系统通知兜底（桌面打包态）：窗口隐藏到托盘 / 失焦时，应用内 antd 通知看不到，
        // 对适合推送的类型补发系统通知（同一 showNotifications 总开关；正文与应用内一致）。
        // 高频「刷新数据」类（PATIENT_CALLED/QUEUE_UPDATED 等）不推送，避免噪音。
        case WSMessageType.PATIENT_SIGNED_IN:
          onPatientSignedIn?.(msg.data);
          if (showNotifications) {
            notification.info({
              message: '患者签到',
              description: `${msg.data.patient_name}（第${msg.data.queue_number}号）已签到`,
              placement: 'topRight',
              duration: 5,
            });
            if (isWindowInactive()) {
              void sendDesktopNotification({
                title: '患者签到',
                body: `${msg.data.patient_name}（第${msg.data.queue_number}号）已签到`,
              });
            }
          }
          break;

        case WSMessageType.PATIENT_CALLED:
        case WSMessageType.PATIENT_PASSED:
        case WSMessageType.PATIENT_RECALLED:
        case WSMessageType.PATIENT_COMPLETED:
        case WSMessageType.PATIENT_NO_SHOW:
        case WSMessageType.QUEUE_UPDATED:
          onQueueUpdated?.(msg.data);
          break;

        case WSMessageType.NEW_APPOINTMENT:
          onNewAppointment?.(msg.data);
          if (showNotifications) {
            notification.info({
              message: '新预约',
              description: `收到新的预约：${msg.data.patient_name}`,
              placement: 'topRight',
              duration: 5,
            });
            if (isWindowInactive()) {
              void sendDesktopNotification({
                title: '新预约',
                body: `收到新的预约：${msg.data.patient_name}`,
              });
            }
          }
          break;

        case WSMessageType.LEAVE_REQUEST_REVIEWED:
          onLeaveRequestReviewed?.(msg.data);
          if (showNotifications) {
            const statusText = msg.data.status === 'approved' ? '已通过' : '已拒绝';
            notification.info({
              message: '请假审核结果',
              description: `您的请假申请${statusText}`,
              placement: 'topRight',
              duration: 5,
            });
            if (isWindowInactive()) {
              void sendDesktopNotification({
                title: '请假审核结果',
                body: `您的请假申请${statusText}`,
              });
            }
          }
          break;

        case WSMessageType.SYSTEM_MESSAGE:
          onSystemMessage?.(msg.data);
          if (showNotifications) {
            notification.info({
              message: msg.data.title || '系统通知',
              description: msg.data.message,
              placement: 'topRight',
              duration: 10,
            });
            if (isWindowInactive()) {
              void sendDesktopNotification({
                title: msg.data.title || '系统通知',
                body: msg.data.message,
              });
            }
          }
          break;

        case WSMessageType.SCHEDULE_SUSPENDED:
          // 停诊/排班暂停（通知渠道映射 schedule/stop_clinic → SCHEDULE_SUSPENDED，
          // data={title,content,...}）：此前无任何处理，对托盘常驻场景是关键遗漏，
          // 这里仅补系统通知兜底，不新增应用内通知（保持页面行为不变）。
          if (showNotifications && isWindowInactive()) {
            void sendDesktopNotification({
              title: msg.data?.title || '停诊通知',
              body: msg.data?.content || '',
            });
          }
          break;

        default:
          console.log('收到未知消息类型:', msg.type, msg.data);
      }
    },
    [onMessage, onPatientSignedIn, onQueueUpdated, onNewAppointment, onLeaveRequestReviewed, onSystemMessage, showNotifications]
  );

  const connection = useWebSocketConnection({
    buildUrl,
    onMessage: handleMessage,
    logPrefix: '[DoctorWS]',
    ...connectionOptions,
  });

  return connection;
};

export default useWebSocket;
