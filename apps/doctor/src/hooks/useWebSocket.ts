/**
 * WebSocket 连接管理 Hook
 * 用于医生端实时接收患者签到、叫号等通知
 */
import { useEffect, useRef, useCallback, useState } from 'react';
import { getToken } from '@hospital/shared';
import { message, notification } from 'antd';

// WebSocket 消息类型
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

// WebSocket 消息结构
export interface WSMessage<T = any> {
  type: WSMessageType | string;
  data: T;
  timestamp: string;
}

// 连接状态
export enum ConnectionStatus {
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  DISCONNECTED = 'DISCONNECTED',
  RECONNECTING = 'RECONNECTING',
  ERROR = 'ERROR',
}

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

// 获取 WebSocket URL
const getWebSocketUrl = (doctorId: string, token: string): string => {
  // 优先使用环境变量配置的 WebSocket URL
  // @ts-ignore
  const wsUrl = process.env.WS_URL || process.env.WEBSOCKET_URL;
  
  if (wsUrl) {
    return `${wsUrl}/api/v1/ws/doctor/${doctorId}?token=${encodeURIComponent(token)}`;
  }
  
  // 自动从当前页面 URL 推断 WebSocket URL
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/api/v1/ws/doctor/${doctorId}?token=${encodeURIComponent(token)}`;
};

/**
 * WebSocket 连接管理 Hook
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
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
    showNotifications = true,
  } = options;

  const [status, setStatus] = useState<ConnectionStatus>(ConnectionStatus.DISCONNECTED);
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
    heartbeatTimerRef.current = setInterval(sendHeartbeat, 25000); // 每 25 秒发送心跳
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
      const msg: WSMessage = JSON.parse(event.data);
      
      // 调用通用消息回调
      onMessage?.(msg);

      // 根据消息类型处理
      switch (msg.type) {
        case WSMessageType.CONNECTED:
          console.log('WebSocket 连接成功');
          break;

        case WSMessageType.HEARTBEAT:
          // 心跳响应，无需处理
          break;

        case WSMessageType.PATIENT_SIGNED_IN:
          onPatientSignedIn?.(msg.data);
          if (showNotifications) {
            notification.info({
              message: '患者签到',
              description: `${msg.data.patient_name}（第${msg.data.queue_number}号）已签到`,
              placement: 'topRight',
              duration: 5,
            });
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
          }
          break;

        default:
          console.log('收到未知消息类型:', msg.type, msg.data);
      }
    } catch (e) {
      console.error('解析 WebSocket 消息失败:', e);
    }
  }, [onMessage, onPatientSignedIn, onQueueUpdated, onNewAppointment, onLeaveRequestReviewed, onSystemMessage, showNotifications]);

  // 连接 WebSocket
  const connect = useCallback(() => {
    if (!doctorId) {
      console.warn('WebSocket: doctorId 为空，跳过连接');
      return;
    }

    const token = getToken();
    if (!token) {
      console.warn('WebSocket: token 为空，跳过连接');
      return;
    }

    // 如果已经连接或正在连接，跳过
    if (wsRef.current?.readyState === WebSocket.OPEN || 
        wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    setStatus(ConnectionStatus.CONNECTING);
    isManualCloseRef.current = false;

    const url = getWebSocketUrl(doctorId, token);
    console.log('WebSocket 连接中...', url.replace(/token=.*/, 'token=***'));

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('WebSocket 已连接');
        setStatus(ConnectionStatus.CONNECTED);
        reconnectAttemptsRef.current = 0;
        startHeartbeat();
      };

      ws.onmessage = handleMessage;

      ws.onclose = (event) => {
        console.log('WebSocket 已断开:', event.code, event.reason);
        setStatus(ConnectionStatus.DISCONNECTED);
        stopHeartbeat();

        // 如果不是手动关闭且需要自动重连
        if (!isManualCloseRef.current && autoReconnect) {
          if (reconnectAttemptsRef.current < maxReconnectAttempts) {
            reconnectAttemptsRef.current++;
            setStatus(ConnectionStatus.RECONNECTING);
            console.log(`WebSocket 将在 ${reconnectInterval}ms 后尝试第 ${reconnectAttemptsRef.current} 次重连...`);
            
            reconnectTimerRef.current = setTimeout(() => {
              connect();
            }, reconnectInterval);
          } else {
            console.error('WebSocket 重连次数已达上限');
            setStatus(ConnectionStatus.ERROR);
          }
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket 错误:', error);
        setStatus(ConnectionStatus.ERROR);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('WebSocket 创建失败:', error);
      setStatus(ConnectionStatus.ERROR);
    }
  }, [doctorId, handleMessage, autoReconnect, reconnectInterval, maxReconnectAttempts, startHeartbeat, stopHeartbeat]);

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
    
    setStatus(ConnectionStatus.DISCONNECTED);
    reconnectAttemptsRef.current = 0;
  }, [stopHeartbeat]);

  // 重新连接
  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttemptsRef.current = 0;
    setTimeout(connect, 100);
  }, [disconnect, connect]);

  // 发送消息
  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket 未连接，无法发送消息');
    }
  }, []);

  // 组件挂载时连接
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [doctorId]); // 当 doctorId 变化时重新连接

  return {
    status,
    isConnected: status === ConnectionStatus.CONNECTED,
    connect,
    disconnect,
    reconnect,
    send,
  };
};

export default useWebSocket;
