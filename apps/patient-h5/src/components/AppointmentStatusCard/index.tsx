import { Tag } from 'antd-mobile';
import { Card, Button } from '@/components/ui';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { AppointmentRecord, AppointmentStatusConfig } from '@/types/appointment';
import { APPOINTMENT_STATUS_CONFIG, AppointmentStatus } from '@/types/appointment';

export interface AppointmentStatusCardProps {
  /** 预约记录 */
  appointment: AppointmentRecord;
  /** 状态配置（可选，覆盖默认配置） */
  statusConfig?: AppointmentStatusConfig;
  /** 点击卡片 */
  onClick?: (appointment: AppointmentRecord) => void;
  /** 取消预约 */
  onCancel?: (id: string) => void;
  /** 签到 */
  onSignIn?: (id: string) => void;
}

/**
 * 预约状态卡片组件
 *
 * 展示预约的核心信息：科室、医生、时间、状态
 * 支持待就诊/已完成/已取消三种状态样式
 */
export const AppointmentStatusCard: React.FC<AppointmentStatusCardProps> = ({
  appointment,
  statusConfig,
  onClick,
  onCancel,
  onSignIn,
}) => {
  const config = statusConfig || APPOINTMENT_STATUS_CONFIG[appointment.status];
  const isPending = appointment.status === AppointmentStatus.CONFIRMED;
  const isPendingPayment = appointment.status === AppointmentStatus.PENDING_PAYMENT;

  return (
    <Card
      variant="default"
      padding="md"
      hoverable
      animated={false}
      className="cursor-pointer"
      onClick={() => onClick?.(appointment)}
      aria-label={`${appointment.doctorName} ${appointment.departmentName} ${config.label} ${appointment.scheduleDate}`}
    >
      {/* Header: 预约单号 + 状态标签 */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-muted-foreground">
          预约单号：{appointment.appointmentNo}
        </span>
        <span
          className={`text-xs px-2 py-1 rounded-full ${config.cssClass}`}
          aria-label={`状态：${config.label}`}
        >
          {config.label}
        </span>
      </div>

      {/* Body: 医生信息 + 时间 */}
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-semibold text-foreground text-lg">
            {appointment.doctorName}
          </h3>
          <p className="text-muted-foreground text-sm mt-1">
            {appointment.departmentName}
          </p>
        </div>
        <div className="text-right">
          <p className="font-medium text-foreground">{appointment.scheduleDate}</p>
          <p className="text-sm text-muted-foreground mt-1">
            {TIME_SLOT_MAP[appointment.timeSlot || 'morning']}
            {appointment.queueNumber && (
              <span className="ml-2 text-accent">第{appointment.queueNumber}号</span>
            )}
          </p>
        </div>
      </div>

      {/* 待支付金额 */}
      {isPendingPayment && appointment.paymentAmount !== undefined && appointment.paymentAmount > 0 && (
        <div className="mt-3 flex justify-between items-center rounded-xl bg-yellow-50 px-3 py-2 text-sm">
          <span className="text-yellow-700">待支付金额</span>
          <span className="font-semibold text-yellow-700">¥{appointment.paymentAmount.toFixed(2)}</span>
        </div>
      )}

      {/* Actions: 待就诊状态显示操作按钮 */}
      {(isPendingPayment || isPending) && (
        <div className="flex gap-2 mt-4 pt-4 border-t border-border">
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onCancel?.(appointment.id);
            }}
            aria-label={`取消${appointment.doctorName}的预约`}
          >
            {isPendingPayment ? '取消订单' : '取消预约'}
          </Button>
          {isPending && onSignIn && (
            <Button
              variant="primary"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onSignIn(appointment.id);
              }}
              aria-label={`签到${appointment.doctorName}的预约`}
            >
              签到
            </Button>
          )}
        </div>
      )}
    </Card>
  );
};

export default AppointmentStatusCard;
