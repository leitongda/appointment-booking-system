import { useState, useEffect, useCallback } from 'react';
import { Badge } from 'antd-mobile';
import { messageApi } from '@hospital/api';
import { usePatientWebSocket } from '@/hooks/usePatientWebSocket';

interface MessageBadgeProps {
  children: React.ReactNode;
  max?: number;
  userId?: string;
}

export const MessageBadge: React.FC<MessageBadgeProps> = ({
  children,
  max = 99,
  userId,
}) => {
  const [unreadCount, setUnreadCount] = useState(0);
  const effectiveUserId = userId || localStorage.getItem('userId') || '';

  const loadUnreadCount = useCallback(async () => {
    if (!effectiveUserId) return;
    try {
      const count = await messageApi.getUnreadCount(effectiveUserId, 'patient');
      setUnreadCount(count?.total || 0);
    } catch {
      // silent
    }
  }, [effectiveUserId]);

  useEffect(() => {
    loadUnreadCount();
  }, [loadUnreadCount]);

  // WebSocket 实时更新未读数
  usePatientWebSocket({
    patientId: effectiveUserId,
    onNewMessage: () => {
      setUnreadCount((prev) => prev + 1);
    },
  });

  const displayCount = unreadCount > max ? `${max}+` : unreadCount;

  return (
    <Badge content={unreadCount > 0 ? displayCount : null}>
      {children}
    </Badge>
  );
};

export default MessageBadge;
