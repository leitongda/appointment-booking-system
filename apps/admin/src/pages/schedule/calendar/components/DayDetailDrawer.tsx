import { Drawer, Button, Tag, Space, Empty, Divider, Checkbox, Popconfirm, Input, Modal } from 'antd';
import { PlusOutlined, CalendarOutlined, UserAddOutlined, CheckCircleOutlined, StopOutlined } from '@ant-design/icons';
import { useState } from 'react';
import type { Dayjs } from 'dayjs';
import { useAccess } from '@umijs/max';
import type { Schedule, Appointment } from '@hospital/shared';
import { TIME_SLOT_LABEL } from '@hospital/shared';
import { TEXT_SECONDARY } from '@/themes/scheduleColors';

interface DayDetailDrawerProps {
  open: boolean;
  onClose: () => void;
  date: Dayjs | null;
  schedules: Schedule[];
  appointments: Appointment[];
  onAppointmentClick: (appointment: Appointment) => void;
  onCreateClick: (scheduleId: string) => void;
  onExtraQuotaClick?: (scheduleId: string) => void;
  onSwitchToWeek: (date: Dayjs) => void;
  onBatchPublish?: (scheduleIds: string[]) => Promise<void>;
  onBatchWithdraw?: (scheduleIds: string[], reason?: string) => Promise<void>;
}

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六'];

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '待支付', color: 'warning' },
  1: { text: '已预约', color: 'processing' },
  2: { text: '已签到', color: 'cyan' },
  3: { text: '历史候诊', color: 'default' },
  4: { text: '就诊中', color: 'processing' },
  5: { text: '已完成', color: 'success' },
  6: { text: '已取消', color: 'default' },
  7: { text: '已过期', color: 'default' },
};

const PUBLISH_STATUS_MAP: Record<string, { text: string; color: string }> = {
  draft: { text: '草稿', color: 'default' },
  published: { text: '已发布', color: 'success' },
  withdrawn: { text: '已撤回', color: 'error' },
};

const DayDetailDrawer: React.FC<DayDetailDrawerProps> = ({
  open,
  onClose,
  date,
  schedules,
  appointments,
  onAppointmentClick,
  onCreateClick,
  onExtraQuotaClick,
  onSwitchToWeek,
  onBatchPublish,
  onBatchWithdraw,
}) => {
  const access = useAccess();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [withdrawModalOpen, setWithdrawModalOpen] = useState(false);
  const [withdrawReason, setWithdrawReason] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  if (!date) return null;

  // 切换选中状态
  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  // 批量发布
  const handlePublish = async () => {
    if (!onBatchPublish || selectedIds.length === 0) return;
    setActionLoading(true);
    try {
      await onBatchPublish(selectedIds);
      setSelectedIds([]);
    } finally {
      setActionLoading(false);
    }
  };

  // 批量撤回
  const handleWithdraw = async () => {
    if (!onBatchWithdraw || selectedIds.length === 0) return;
    setActionLoading(true);
    try {
      await onBatchWithdraw(selectedIds, withdrawReason || undefined);
      setSelectedIds([]);
      setWithdrawModalOpen(false);
      setWithdrawReason('');
    } finally {
      setActionLoading(false);
    }
  };

  // 按时段排序
  const sortOrder = { morning: 0, afternoon: 1, evening: 2 };
  const sortedSchedules = [...schedules].sort(
    (a, b) => (sortOrder[a.timeSlot as keyof typeof sortOrder] ?? 3) - 
              (sortOrder[b.timeSlot as keyof typeof sortOrder] ?? 3)
  );

  // 获取某个排班的预约列表
  const getAppointmentsForSchedule = (schedule: Schedule): Appointment[] => {
    return appointments.filter(a => a.scheduleId === schedule.id);
  };

  // 脱敏姓名
  const maskName = (name: string): string => {
    if (!name) return '-';
    if (name.length <= 1) return name;
    if (name.length === 2) return name[0] + '*';
    return name[0] + '*'.repeat(name.length - 2) + name[name.length - 1];
  };

  // 脱敏手机号
  const maskPhone = (phone: string): string => {
    if (!phone) return '-';
    if (phone.length <= 7) return phone;
    return phone.substring(0, 3) + '****' + phone.substring(phone.length - 4);
  };

  return (
    <Drawer
      title={null}
      placement="right"
      width={400}
      open={open}
      onClose={onClose}
      className="day-detail-drawer"
    >
      <div className="drawer-header">
        <span className="drawer-date">{date.format('YYYY年MM月DD日')}</span>
        <span className="drawer-weekday">周{WEEKDAYS[date.day()]}</span>
      </div>

      {sortedSchedules.length === 0 ? (
        <Empty description="当日暂无排班" />
      ) : (
        sortedSchedules.map(schedule => {
          const scheduleAppointments = getAppointmentsForSchedule(schedule);
          const available = schedule.totalSlots - schedule.bookedSlots;
          const isSuspended = schedule.status === 0;
          const pubStatus = schedule.publishStatus || 'draft';
          const pubInfo = PUBLISH_STATUS_MAP[pubStatus] || PUBLISH_STATUS_MAP.draft;

          return (
            <div key={schedule.id} className="schedule-section">
              <div className="section-title">
                <Space>
                  <Checkbox
                    checked={selectedIds.includes(schedule.id)}
                    onChange={() => toggleSelect(schedule.id)}
                  />
                  <span>{TIME_SLOT_LABEL[schedule.timeSlot ?? ''] || schedule.timeSlot}</span>
                  <span style={{ fontSize: 12, color: '#666' }}>
                    {schedule.startTime} - {schedule.endTime}
                  </span>
                  <Tag color={pubInfo.color}>{pubInfo.text}</Tag>
                  {isSuspended ? (
                    <Tag color="default">停诊</Tag>
                  ) : available <= 0 ? (
                    <Tag color="error">已满</Tag>
                  ) : (
                    <Tag color="success">剩余 {available}</Tag>
                  )}
                </Space>
                <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>
                  {schedule.bookedSlots}/{schedule.totalSlots}
                </span>
              </div>

              {scheduleAppointments.length > 0 ? (
                <div className="appointment-list">
                  {scheduleAppointments.map(appointment => {
                    const statusInfo = STATUS_MAP[appointment.status] || { text: '-', color: 'default' };
                    return (
                      <div
                        key={appointment.id}
                        className="appointment-item"
                        onClick={() => onAppointmentClick(appointment)}
                      >
                        <div className="patient-name">
                          <span data-rrweb-mask-text>{maskName(appointment.patientName || '')}</span>
                          <Tag color={statusInfo.color} style={{ marginLeft: 8 }}>
                            {statusInfo.text}
                          </Tag>
                        </div>
                        <div className="appointment-meta">
                          <Space separator="·">
                            <span data-rrweb-mask-text>{maskPhone(appointment.patientPhone || '')}</span>
                            <span>{appointment.timeSlot === 'morning' ? '上午' :
                                   appointment.timeSlot === 'afternoon' ? '下午' :
                                   appointment.timeSlot === 'evening' ? '晚上' : '普通'}</span>
                          </Space>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="empty-text">暂无预约</div>
              )}

              {!isSuspended && available > 0 && access.hasPermission?.('appointment:create') && (
                <Button
                  type="dashed"
                  icon={<PlusOutlined />}
                  block
                  style={{ marginTop: 8 }}
                  onClick={() => onCreateClick(schedule.id)}
                >
                  创建预约
                </Button>
              )}

              {!isSuspended && onExtraQuotaClick && (
                <Button
                  type="dashed"
                  icon={<UserAddOutlined />}
                  block
                  style={{ marginTop: 4 }}
                  onClick={() => onExtraQuotaClick(schedule.id)}
                >
                  申请加号
                </Button>
              )}
            </div>
          );
        })
      )}

      <Divider />

      {/* 发布/撤回操作栏 */}
      {selectedIds.length > 0 && (
        <div style={{ marginBottom: 12, padding: '8px 12px', background: '#f5f5f5', borderRadius: 6 }}>
          <Space>
            <span style={{ fontSize: 13 }}>已选 {selectedIds.length} 项</span>
            {onBatchPublish && (
              <Popconfirm
                title={`确定发布选中的 ${selectedIds.length} 条排班吗？`}
                onConfirm={handlePublish}
                okButtonProps={{ loading: actionLoading }}
              >
                <Button type="primary" size="small" icon={<CheckCircleOutlined />}>
                  批量发布
                </Button>
              </Popconfirm>
            )}
            {onBatchWithdraw && (
              <Button
                size="small"
                danger
                icon={<StopOutlined />}
                onClick={() => setWithdrawModalOpen(true)}
              >
                批量撤回
              </Button>
            )}
          </Space>
        </div>
      )}

      <div className="drawer-actions">
        <Button
          icon={<CalendarOutlined />}
          onClick={() => onSwitchToWeek(date)}
        >
          查看周视图
        </Button>
      </div>

      {/* 撤回原因弹窗 */}
      <Modal
        title="撤回排班"
        open={withdrawModalOpen}
        onCancel={() => { setWithdrawModalOpen(false); setWithdrawReason(''); }}
        onOk={handleWithdraw}
        confirmLoading={actionLoading}
        okText="确认撤回"
        okButtonProps={{ danger: true }}
      >
        <p>确定撤回选中的 {selectedIds.length} 条排班吗？撤回后患者将无法预约。</p>
        <Input.TextArea
          placeholder="撤回原因（可选）"
          value={withdrawReason}
          onChange={(e) => setWithdrawReason(e.target.value)}
          rows={3}
        />
      </Modal>
    </Drawer>
  );
};

export default DayDetailDrawer;
