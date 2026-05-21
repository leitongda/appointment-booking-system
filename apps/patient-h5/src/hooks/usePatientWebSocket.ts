/**
 * 患者端 WebSocket 连接管理 Hook
 * 用于患者端实时接收叫号、过号等通知
 */
import { useEffect, useRef, useCallback, useState } from 'react';
import { getToken } from '@hospital/shared';

// WebSocket 消息类型（患者相关）
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

// WebSocket 消息结构
export interface PatientWSMessage<T = any> {
  type: PatientWSMessageType | string;
  data: T;
  timestamp: string;
  message_id?: string;
}

// 连接状态
export enum PatientConnectionStatus {
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  DISCONNECTED = 'DISCONNECTED',
  RECONNECTING = 'RECONNECTING',
  ERROR = 'ERROR',
}

// Hook 配置
interface UsePatientWebSocketOptions {
  patientId: string;
  onMessage?: (message: PatientWSMessage) => void;
  onCalled?: (data: any) => void;
  onPassed?: (data: any) => void;
  onRecalled?: (data: any) => void;
  onNoShow?: (data: any) => void;
  onNewMessage?: (data: any) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

// 获取 WebSocket URL
const getPatientWebSocketUrl = (patientId: string, token: string): string => {
  // @ts-ignore
  const wsUrl = process.env.WS_URL || process.env.WEBSOCKET_URL;

  if (wsUrl) {
    return `${wsUrl}/api/v1/ws/patient/${patientId}?token=${encodeURIComponent(token)}`;
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/api/v1/ws/patient/${patientId}?token=${encodeURIComponent(token)}`;
};

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
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
  } = options;

  const [status, setStatus] = useState<PatientConnectionStatus>(PatientConnectionStatus.DISCONNECTED);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isManualCloseRef = useRef(false);

  // 发送心跳
  const sendHeartbeat = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'HEARTBEAT', timestamp: new Date().toISOString() }));
    }
  }, []);

  // 启动心跳定时器
  const startHeartbeat = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
    }
    heartbeatTimerRef.current = setInterval(sendHeartbeat, 25000);
  }, [sendHeartbeat]);

  // 停止心跳定时器
  const stopHeartbeat = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
  }, []);

  // 处理消息
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const msg: PatientWSMessage = JSON.parse(event.data);

      onMessage?.(msg);

      switch (msg.type) {
        case PatientWSMessageType.CONNECTED:
          console.log('[PatientWS] 连接成功');
          break;

        case PatientWSMessageType.HEARTBEAT:
          break;

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
          console.log('[PatientWS] 未知消息类型:', msg.type, msg.data);
      }
    } catch (e) {
      console.error('[PatientWS] 解析消息失败:', e);
    }
  }, [onMessage, onCalled, onPassed, onRecalled, onNoShow, onNewMessage]);

  // 连接 WebSocket
  const connect = useCallback(() => {
    if (!patientId) {
      console.warn('[PatientWS] patientId 为空，跳过连接');
      return;
    }

    const token = getToken();
    if (!token) {
      console.warn('[PatientWS] token 为空，跳过连接');
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN ||
        wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    setStatus(PatientConnectionStatus.CONNECTING);
    isManualCloseRef.current = false;

    const url = getPatientWebSocketUrl(patientId, token);
    console.log('[PatientWS] 连接中...', url.replace(/token=.*/, 'token=***'));

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('[PatientWS] 已连接');
        setStatus(PatientConnectionStatus.CONNECTED);
        reconnectAttemptsRef.current = 0;
        startHeartbeat();
      };

      ws.onmessage = handleMessage;

      ws.onclose = (event) => {
        console.log('[PatientWS] 已断开:', event.code, event.reason);
        setStatus(PatientConnectionStatus.DISCONNECTED);
        stopHeartbeat();

        if (!isManualCloseRef.current && autoReconnect) {
          if (reconnectAttemptsRef.current < maxReconnectAttempts) {
            reconnectAttemptsRef.current++;
            const attempt = reconnectAttemptsRef.current;
            const baseDelay = reconnectInterval * Math.pow(2, attempt - 1);
            const cappedDelay = Math.min(baseDelay, 30000);
            const jitter = cappedDelay * (0.5 + Math.random() * 0.5);
            setStatus(PatientConnectionStatus.RECONNECTING);
            console.log(`[PatientWS] 将在 ${Math.round(jitter)}ms 后尝试第 ${attempt} 次重连...`);

            reconnectTimerRef.current = setTimeout(() => {
              connect();
            }, jitter);
          } else {
            console.error('[PatientWS] 重连次数已达上限');
            setStatus(PatientConnectionStatus.ERROR);
          }
        }
      };

      ws.onerror = (error) => {
        console.error('[PatientWS] 错误:', error);
        setStatus(PatientConnectionStatus.ERROR);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[PatientWS] 创建失败:', error);
      setStatus(PatientConnectionStatus.ERROR);
    }
  }, [patientId, handleMessage, autoReconnect, reconnectInterval, maxReconnectAttempts, startHeartbeat, stopHeartbeat]);

  // 断开连接
  const disconnect = useCallback(() => {
    isManualCloseRef.current = true;

    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    stopHeartbeat();

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setStatus(PatientConnectionStatus.DISCONNECTED);
    reconnectAttemptsRef.current = 0;
  }, [stopHeartbeat]);

  // 重新连接
  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttemptsRef.current = 0;
    setTimeout(connect, 100);
  }, [disconnect, connect]);

  // 组件挂载时连接
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [patientId]);

  return {
    status,
    isConnected: status === PatientConnectionStatus.CONNECTED,
    connect,
    disconnect,
    reconnect,
  };
};

export default usePatientWebSocket;
