/**
 * 共享 WebSocket 连接管理基础 Hook
 *
 * 封装连接生命周期、心跳、指数退避重连。各端通过传入 URL 构建函数和
 * 消息处理回调来定制行为，避免重复实现连接管理逻辑。
 *
 * 使用方式：
 * - doctor 端: 构建 /ws/doctor/{doctorId} URL + antd notification 集成
 * - patient 端: 构建 /ws/patient/{patientId} URL + 简单回调
 */
import { useEffect, useRef, useCallback, useState } from 'react';
import { getToken } from './storage';

// ─── 共享类型 ──────────────────────────────────────────────────────

/** 连接状态枚举 */
export enum ConnectionStatus {
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  DISCONNECTED = 'DISCONNECTED',
  RECONNECTING = 'RECONNECTING',
  ERROR = 'ERROR',
}

/** WebSocket 消息结构 */
export interface WSMessage<T = any> {
  type: string;
  data: T;
  timestamp: string;
  message_id?: string;
}

// ─── Hook 配置 ─────────────────────────────────────────────────────

export interface UseWebSocketConnectionOptions {
  /** 构建 WebSocket URL 的函数（接收 token，返回完整 ws:// 或 wss:// URL） */
  buildUrl: (token: string) => string;
  /** 消息处理回调 */
  onMessage?: (message: WSMessage) => void;
  /** 是否自动重连（默认 true） */
  autoReconnect?: boolean;
  /** 重连基础间隔毫秒数（默认 3000） */
  reconnectInterval?: number;
  /** 最大重连次数（默认 10） */
  maxReconnectAttempts?: number;
  /** 日志前缀（默认 '[WS]'） */
  logPrefix?: string;
}

export interface UseWebSocketConnectionReturn {
  /** 当前连接状态 */
  status: ConnectionStatus;
  /** 是否已连接 */
  isConnected: boolean;
  /** 手动连接 */
  connect: () => void;
  /** 手动断开 */
  disconnect: () => void;
  /** 重新连接 */
  reconnect: () => void;
  /** 发送消息 */
  send: (data: any) => void;
}

// ─── 默认 URL 构建 ─────────────────────────────────────────────────

/**
 * 从环境变量或当前页面推断 WebSocket 基础 URL
 */
export const getWebSocketBaseUrl = (): string => {
  // @ts-ignore
  const wsUrl = process.env.WS_URL || process.env.WEBSOCKET_URL;
  if (wsUrl) return wsUrl;

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}`;
};

/**
 * 创建 WebSocket URL 构建器
 *
 * @param path - WebSocket 路径，如 `/api/v1/ws/doctor/123`
 * @returns buildUrl 函数
 */
export const createWebSocketUrlBuilder = (path: string) => {
  return (token: string): string => {
    const base = getWebSocketBaseUrl();
    return `${base}${path}?token=${encodeURIComponent(token)}`;
  };
};

// ─── 基础 Hook ─────────────────────────────────────────────────────

/**
 * WebSocket 连接管理基础 Hook
 *
 * 管理连接生命周期、心跳（25s 间隔）、指数退避重连（3s base, 30s cap, jitter）。
 * 各端通过 buildUrl 和 onMessage 定制行为。
 */
export const useWebSocketConnection = (
  options: UseWebSocketConnectionOptions
): UseWebSocketConnectionReturn => {
  const {
    buildUrl,
    onMessage,
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
    logPrefix = '[WS]',
  } = options;

  const [status, setStatus] = useState<ConnectionStatus>(ConnectionStatus.DISCONNECTED);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isManualCloseRef = useRef(false);

  // 使用 ref 保存最新的 onMessage 回调，避免 connect 依赖变化
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  // ── 心跳管理 ──

  const sendHeartbeat = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'HEARTBEAT', timestamp: new Date().toISOString() }));
    }
  }, []);

  const startHeartbeat = useCallback(() => {
    if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);
    heartbeatTimerRef.current = setInterval(sendHeartbeat, 25000);
  }, [sendHeartbeat]);

  const stopHeartbeat = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
  }, []);

  // ── 连接管理 ──

  const connect = useCallback(() => {
    const token = getToken();
    if (!token) {
      console.warn(`${logPrefix} token 为空，跳过连接`);
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN ||
        wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    setStatus(ConnectionStatus.CONNECTING);
    isManualCloseRef.current = false;

    const url = buildUrl(token);
    console.log(`${logPrefix} 连接中...`, url.replace(/token=.*/, 'token=***'));

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log(`${logPrefix} 已连接`);
        setStatus(ConnectionStatus.CONNECTED);
        reconnectAttemptsRef.current = 0;
        startHeartbeat();
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const msg: WSMessage = JSON.parse(event.data);
          // 心跳响应不传递给 onMessage
          if (msg.type !== 'HEARTBEAT') {
            onMessageRef.current?.(msg);
          }
        } catch (e) {
          console.error(`${logPrefix} 解析消息失败:`, e);
        }
      };

      ws.onclose = (event) => {
        console.log(`${logPrefix} 已断开:`, event.code, event.reason);
        setStatus(ConnectionStatus.DISCONNECTED);
        stopHeartbeat();

        if (!isManualCloseRef.current && autoReconnect) {
          if (reconnectAttemptsRef.current < maxReconnectAttempts) {
            reconnectAttemptsRef.current++;
            const attempt = reconnectAttemptsRef.current;
            const baseDelay = reconnectInterval * Math.pow(2, attempt - 1);
            const cappedDelay = Math.min(baseDelay, 30000);
            const jitter = cappedDelay * (0.5 + Math.random() * 0.5);
            setStatus(ConnectionStatus.RECONNECTING);
            console.log(`${logPrefix} 将在 ${Math.round(jitter)}ms 后尝试第 ${attempt} 次重连...`);

            reconnectTimerRef.current = setTimeout(() => {
              connect();
            }, jitter);
          } else {
            console.error(`${logPrefix} 重连次数已达上限`);
            setStatus(ConnectionStatus.ERROR);
          }
        }
      };

      ws.onerror = (error) => {
        console.error(`${logPrefix} 错误:`, error);
        setStatus(ConnectionStatus.ERROR);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error(`${logPrefix} 创建失败:`, error);
      setStatus(ConnectionStatus.ERROR);
    }
  }, [buildUrl, autoReconnect, reconnectInterval, maxReconnectAttempts, startHeartbeat, stopHeartbeat, logPrefix]);

  // ── 断开/重连 ──

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

  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttemptsRef.current = 0;
    setTimeout(connect, 100);
  }, [disconnect, connect]);

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data));
    } else {
      console.warn(`${logPrefix} 未连接，无法发送消息`);
    }
  }, [logPrefix]);

  // ── 生命周期 ──

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    status,
    isConnected: status === ConnectionStatus.CONNECTED,
    connect,
    disconnect,
    reconnect,
    send,
  };
};
