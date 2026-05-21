import { useState, useEffect, useCallback } from 'react';
import { Toast } from 'antd-mobile';
import { usePatientWebSocket } from '@/hooks/usePatientWebSocket';
import { Card } from '@/components/ui';

interface QueueStatus {
  appointmentId: string;
  queueNumber: number;
  doctorName: string;
  status: 'waiting' | 'called' | 'passed' | 'recalled' | 'completed' | 'no_show';
  currentCallingNumber?: number;
}

interface Props {
  appointmentId: string;
  patientId: string;
  initialQueueNumber?: number;
  doctorName?: string;
  onStatusChange?: (status: QueueStatus['status']) => void;
}

const STATUS_CONFIG = {
  waiting: {
    label: '等待中',
    color: 'text-blue-500',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    icon: '⏳',
  },
  called: {
    label: '已叫号',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    icon: '📢',
  },
  passed: {
    label: '已过号',
    color: 'text-orange-500',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    icon: '⚠️',
  },
  recalled: {
    label: '重新叫号',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    icon: '🔄',
  },
  completed: {
    label: '已完成',
    color: 'text-gray-500',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
    icon: '✅',
  },
  no_show: {
    label: '已爽约',
    color: 'text-red-500',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    icon: '❌',
  },
};

export const QueueStatusCard: React.FC<Props> = ({
  appointmentId,
  patientId,
  initialQueueNumber,
  doctorName,
  onStatusChange,
}) => {
  const [queueStatus, setQueueStatus] = useState<QueueStatus>({
    appointmentId,
    queueNumber: initialQueueNumber || 0,
    doctorName: doctorName || '',
    status: 'waiting',
  });

  const handleCalled = useCallback((data: any) => {
    if (data.appointment_id === appointmentId) {
      setQueueStatus((prev) => ({
        ...prev,
        status: 'called',
        queueNumber: data.queue_number || prev.queueNumber,
        doctorName: data.doctor_name || prev.doctorName,
      }));
      Toast.show({
        content: `请前往诊室就诊 - ${data.doctor_name || '医生'}`,
        icon: 'success',
        duration: 5000,
      });
      onStatusChange?.('called');
    }
  }, [appointmentId, onStatusChange]);

  const handlePassed = useCallback((data: any) => {
    if (data.appointment_id === appointmentId) {
      setQueueStatus((prev) => ({
        ...prev,
        status: 'passed',
      }));
      Toast.show({
        content: '您已过号，请等待重新叫号',
        icon: 'fail',
        duration: 5000,
      });
      onStatusChange?.('passed');
    }
  }, [appointmentId, onStatusChange]);

  const handleRecalled = useCallback((data: any) => {
    if (data.appointment_id === appointmentId) {
      setQueueStatus((prev) => ({
        ...prev,
        status: 'recalled',
      }));
      Toast.show({
        content: '请重新前往诊室就诊',
        icon: 'success',
        duration: 5000,
      });
      onStatusChange?.('recalled');
    }
  }, [appointmentId, onStatusChange]);

  const handleNoShow = useCallback((data: any) => {
    if (data.appointment_id === appointmentId) {
      setQueueStatus((prev) => ({
        ...prev,
        status: 'no_show',
      }));
      Toast.show({
        content: '您已被标记为爽约',
        icon: 'fail',
        duration: 5000,
      });
      onStatusChange?.('no_show');
    }
  }, [appointmentId, onStatusChange]);

  const { isConnected } = usePatientWebSocket({
    patientId,
    onCalled: handleCalled,
    onPassed: handlePassed,
    onRecalled: handleRecalled,
    onNoShow: handleNoShow,
  });

  const config = STATUS_CONFIG[queueStatus.status];

  return (
    <Card variant="elevated" padding="lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-foreground">排队状态</h3>
        <div className="flex items-center gap-1">
          <div
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-gray-400'
            }`}
          />
          <span className="text-xs text-muted-foreground">
            {isConnected ? '实时' : '离线'}
          </span>
        </div>
      </div>

      <div className="space-y-4">
        {/* 状态显示 */}
        <div
          className={`flex items-center gap-3 p-4 rounded-xl ${config.bgColor} ${config.borderColor} border`}
        >
          <span className="text-2xl">{config.icon}</span>
          <div>
            <p className={`font-semibold ${config.color}`}>{config.label}</p>
            {queueStatus.status === 'called' && (
              <p className="text-sm text-muted-foreground mt-1">
                请尽快前往诊室
              </p>
            )}
            {queueStatus.status === 'passed' && (
              <p className="text-sm text-muted-foreground mt-1">
                请耐心等待重新叫号
              </p>
            )}
          </div>
        </div>

        {/* 队列信息 */}
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-3 bg-muted rounded-xl">
            <p className="text-2xl font-bold text-accent">
              {queueStatus.queueNumber}
            </p>
            <p className="text-xs text-muted-foreground mt-1">您的号码</p>
          </div>
          <div className="text-center p-3 bg-muted rounded-xl">
            <p className="text-sm font-medium text-foreground">
              {queueStatus.doctorName || '-'}
            </p>
            <p className="text-xs text-muted-foreground mt-1">就诊医生</p>
          </div>
        </div>

        {/* 提示信息 */}
        {queueStatus.status === 'waiting' && (
          <p className="text-xs text-muted-foreground text-center">
            请保持页面打开，叫号时会自动提醒
          </p>
        )}
      </div>
    </Card>
  );
};

export default QueueStatusCard;
