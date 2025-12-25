import { Drawer, Button, Tag, Space, Empty, Divider } from 'antd';
import { PlusOutlined, CalendarOutlined } from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import { useAccess } from '@umijs/max';
import type { Schedule, Appointment } from '@hospital/shared';

interface DayDetailDrawerProps {
  open: boolean;
  onClose: () => void;
  date: Dayjs | null;
  schedules: Schedule[];
  appointments: Appointment[];
  onAppointmentClick: (appointment: Appointment) => void;
  onCreateClick: (scheduleId: string) => void;
  onSwitchToWeek: (date: Dayjs) => void;
}

const TIME_SLOT_LABELS: Record<string, string> = {
  morning: '上午',
  afternoon: '下午',
  evening: '晚上',
};

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六'];

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '待就诊', color: 'processing' },
  1: { text: '已签到', color: 'warning' },
  2: { text: '就诊中', color: 'processing' },
  3: { text: '已完成', color: 'success' },
  4: { text: '已取消', color: 'default' },
  5: { text: '爽约', color: 'error' },
};

const DayDetailDrawer: React.FC<DayDetailDrawerProps> = ({
  open,
  onClose,
  date,
  schedules,
  appointments,
  onAppointmentClick,
  onCreateClick,
  onSwitchToWeek,
}) => {
  const access = useAccess();

  if (!date) return null;

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

          return (
            <div key={schedule.id} className="schedule-section">
              <div className="section-title">
                <Space>
                  <span>{TIME_SLOT_LABELS[schedule.timeSlot] || schedule.timeSlot}</span>
                  <span style={{ fontSize: 12, color: '#666' }}>
                    {schedule.startTime} - {schedule.endTime}
                  </span>
                  {isSuspended ? (
                    <Tag color="default">停诊</Tag>
                  ) : available <= 0 ? (
                    <Tag color="error">已满</Tag>
                  ) : (
                    <Tag color="success">剩余 {available}</Tag>
                  )}
                </Space>
                <span style={{ fontSize: 12, color: '#999' }}>
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
                          {maskName(appointment.patientName || '')}
                          <Tag color={statusInfo.color} style={{ marginLeft: 8 }}>
                            {statusInfo.text}
                          </Tag>
                        </div>
                        <div className="appointment-meta">
                          <Space split="·">
                            <span>{maskPhone(appointment.patientPhone || '')}</span>
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
            </div>
          );
        })
      )}

      <Divider />

      <div className="drawer-actions">
        <Button
          icon={<CalendarOutlined />}
          onClick={() => onSwitchToWeek(date)}
        >
          查看周视图
        </Button>
      </div>
    </Drawer>
  );
};

export default DayDetailDrawer;

