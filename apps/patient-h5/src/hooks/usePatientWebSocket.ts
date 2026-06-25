/**
 * 患者端 WebSocket Hook
 * 基于 @hospital/shared 的共享连接管理，添加患者端特有的消息处理
 */
import { useMemo, useCallback } from 'react';
import {
  useWebSocketConnection,
  createWebSocketUrlBuilder,
  ConnectionStatus,
} from '@hospital/shared';
import type { WSMessage, UseWebSocketConnectionReturn } from '@hospital/shared';

// 患者端消息类型
export enum PatientWSMessageType {
  CONNECTED = 'CONNECTED',
  HEARTBEAT = 'HEARTBEAT',
  ERROR = 'ERROR',
  PATIENT_CALLED = 'PATIENT_CALLED',
  PATIENT_PASSED = 'PATIENT_PASSED',
  PATIENT_RECALLED = 'PATIENT_RECALLED',
  PATIENT_NO_SHOW = 'PATIENT_NO_SHOW',
  NEW_MESSAGE = 'NEW_MESSAGE',
  SYSTEM_MESSAGE = 'SYSTEM_MESSAGE',
}

// 重新导出共享类型（保持向后兼容）
export { ConnectionStatus as PatientConnectionStatus };
export type { WSMessage as PatientWSMessage };

// Hook 配置
interface UsePatientWebSocketOptions {
  patientId: string;
  onMessage?: (message: WSMessage) => void;
  onCalled?: (data: any) => void;
  onPassed?: (data: any) => void;
  onRecalled?: (data: any) => void;
  onNoShow?: (data: any) => void;
  onNewMessage?: (data: any) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

/**
 * 患者端 WebSocket 连接管理 Hook
 */
export const usePatientWebSocket = (options: UsePatientWebSocketOptions) => {
  const {
    patientId,
    onMessage,
    onCalled,
    onPassed,
    onRecalled,
    onNoShow,
    onNewMessage,
    ...connectionOptions
  } = options;

  // 构建 URL（仅在 patientId 变化时重建）
  const buildUrl = useMemo(
    () => createWebSocketUrlBuilder(`/api/v1/ws/patient/${patientId}`),
    [patientId]
  );

  // 消息处理：分发到各业务回调
  const handleMessage = useCallback(
    (msg: WSMessage) => {
      onMessage?.(msg);

      switch (msg.type) {
        case PatientWSMessageType.PATIENT_CALLED:
          onCalled?.(msg.data);
          break;
        case PatientWSMessageType.PATIENT_PASSED:
          onPassed?.(msg.data);
          break;
        case PatientWSMessageType.PATIENT_RECALLED:
          onRecalled?.(msg.data);
          break;
        case PatientWSMessageType.PATIENT_NO_SHOW:
          onNoShow?.(msg.data);
          break;
        case PatientWSMessageType.NEW_MESSAGE:
          onNewMessage?.(msg.data);
          break;
        default:
          break;
      }
    },
    [onMessage, onCalled, onPassed, onRecalled, onNoShow, onNewMessage]
  );

  const connection = useWebSocketConnection({
    buildUrl,
    onMessage: handleMessage,
    logPrefix: '[PatientWS]',
    ...connectionOptions,
  });

  return connection;
};

export default usePatientWebSocket;
