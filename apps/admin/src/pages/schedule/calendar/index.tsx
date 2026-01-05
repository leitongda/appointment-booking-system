import { PageContainer } from '@ant-design/pro-components';
import { Card, Spin, message } from 'antd';
import { useState, useEffect, useCallback } from 'react';
import dayjs, { Dayjs } from 'dayjs';
import { scheduleApi, appointmentApi } from '@hospital/api';
import type { Schedule, Appointment, Doctor } from '@hospital/shared';
import { PAGINATION_CONFIG } from '@/constants/pagination';
import { requestDeduplicator } from '@/utils/requestDeduplication';
import DoctorSelector from './components/DoctorSelector';
import CalendarHeader from './components/CalendarHeader';
import WeekView from './components/WeekView';
import MonthView from './components/MonthView';
import DayDetailDrawer from './components/DayDetailDrawer';
import AppointmentDetailModal from './components/AppointmentDetailModal';
import CreateAppointmentModal from './components/CreateAppointmentModal';
import './styles/calendar.less';

export type ViewMode = 'week' | 'month';

export interface ScheduleSlot {
  schedule: Schedule;
  appointments: Appointment[];
  availableCount: number;
  bookedCount: number;
  status: 'available' | 'booked' | 'full' | 'suspended';
}

const STORAGE_KEY_VIEW_MODE = 'schedule_calendar_view_mode';

const getInitialViewMode = (): ViewMode => {
  const cached = localStorage.getItem(STORAGE_KEY_VIEW_MODE);
  if (cached === 'week' || cached === 'month') {
    return cached;
  }
  return 'month'; // 默认月视图
};

const ScheduleCalendarPage: React.FC = () => {
  // 状态管理
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>(getInitialViewMode);
  const [currentDate, setCurrentDate] = useState<Dayjs>(dayjs());
  const [selectedDoctor, setSelectedDoctor] = useState<Doctor | null>(null);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  
  // 抽屉和弹窗状态
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerDate, setDrawerDate] = useState<Dayjs | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedAppointment, setSelectedAppointment] = useState<Appointment | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createScheduleId, setCreateScheduleId] = useState<string | null>(null);

  // 计算日期范围
  const getDateRange = useCallback(() => {
    if (viewMode === 'week') {
      return {
        startDate: currentDate.startOf('week').format('YYYY-MM-DD'),
        endDate: currentDate.endOf('week').format('YYYY-MM-DD'),
      };
    } else {
      return {
        startDate: currentDate.startOf('month').format('YYYY-MM-DD'),
        endDate: currentDate.endOf('month').format('YYYY-MM-DD'),
      };
    }
  }, [currentDate, viewMode]);

  // 加载排班数据（优化后：使用请求去重和更大的pageSize）
  const loadSchedules = useCallback(async () => {
    if (!selectedDoctor) return;

    setLoading(true);
    try {
      const { startDate, endDate } = getDateRange();

      // 使用请求去重，避免并发相同请求
      const result = await requestDeduplicator.dedupe(
        `schedules-${selectedDoctor.id}-${startDate}-${endDate}`,
        () => scheduleApi.getList({
          doctorId: selectedDoctor.id,
          startDate,
          endDate,
          page: 1,
          pageSize: PAGINATION_CONFIG.CALENDAR_MAX_SIZE, // 使用更大的pageSize
        })
      );

      setSchedules(result.data || []);
    } catch (error) {
      message.error('加载排班失败，请稍后重试');
      console.error('加载排班失败', error);
    } finally {
      setLoading(false);
    }
  }, [selectedDoctor, getDateRange]);

  // 加载预约数据（优化后：使用请求去重和更大的pageSize）
  const loadAppointments = useCallback(async () => {
    if (!selectedDoctor) return;

    try {
      const { startDate, endDate } = getDateRange();

      // 使用请求去重，避免并发相同请求
      const result = await requestDeduplicator.dedupe(
        `appointments-${selectedDoctor.id}-${startDate}-${endDate}`,
        () => appointmentApi.getList({
          doctorId: selectedDoctor.id,
          startDate,
          endDate,
          page: 1,
          pageSize: PAGINATION_CONFIG.CALENDAR_MAX_SIZE, // 使用更大的pageSize
        })
      );

      setAppointments(result.data || []);
    } catch (error) {
      message.error('加载预约失败，请稍后重试');
      console.error('加载预约失败', error);
    }
  }, [selectedDoctor, getDateRange]);

  // 刷新数据
  const refreshData = useCallback(() => {
    loadSchedules();
    loadAppointments();
  }, [loadSchedules, loadAppointments]);

  useEffect(() => {
    if (selectedDoctor) {
      refreshData();
    }
  }, [selectedDoctor, currentDate, viewMode, refreshData]);

  // 处理日期点击（月视图）
  const handleDateClick = (date: Dayjs) => {
    setDrawerDate(date);
    setDrawerOpen(true);
  };

  // 处理预约点击
  const handleAppointmentClick = (appointment: Appointment) => {
    setSelectedAppointment(appointment);
    setDetailModalOpen(true);
  };

  // 处理创建预约
  const handleCreateClick = (scheduleId: string) => {
    setCreateScheduleId(scheduleId);
    setCreateModalOpen(true);
  };

  // 处理视图模式切换
  const handleViewModeChange = (mode: ViewMode) => {
    setViewMode(mode);
    localStorage.setItem(STORAGE_KEY_VIEW_MODE, mode);
  };

  // 处理切换到周视图
  const handleSwitchToWeek = (date: Dayjs) => {
    setCurrentDate(date);
    handleViewModeChange('week');
    setDrawerOpen(false);
  };

  // 按日期分组排班
  const getSchedulesByDate = (date: Dayjs): Schedule[] => {
    const dateStr = date.format('YYYY-MM-DD');
    return schedules.filter(s => s.scheduleDate === dateStr);
  };

  // 按日期分组预约
  const getAppointmentsByDate = (date: Dayjs): Appointment[] => {
    const dateStr = date.format('YYYY-MM-DD');
    return appointments.filter(a => a.scheduleDate === dateStr);
  };

  return (
    <PageContainer
      title="排班日历"
      subTitle={selectedDoctor ? `${selectedDoctor.name} - ${selectedDoctor.departmentName || ''}` : '请选择医生'}
    >
      <Card className="schedule-calendar-card">
        {/* 医生选择器 */}
        <DoctorSelector
          selectedDoctor={selectedDoctor}
          onSelect={setSelectedDoctor}
        />

        {selectedDoctor && (
          <>
            {/* 日历头部 */}
            <CalendarHeader
              viewMode={viewMode}
              currentDate={currentDate}
              onViewModeChange={handleViewModeChange}
              onDateChange={setCurrentDate}
              onRefresh={refreshData}
            />

            {/* 视图区域 */}
            <Spin spinning={loading}>
              <div className="calendar-view-container">
                {viewMode === 'week' ? (
                  <WeekView
                    currentDate={currentDate}
                    schedules={schedules}
                    appointments={appointments}
                    onAppointmentClick={handleAppointmentClick}
                    onCreateClick={handleCreateClick}
                  />
                ) : (
                  <MonthView
                    currentDate={currentDate}
                    schedules={schedules}
                    appointments={appointments}
                    onDateClick={handleDateClick}
                  />
                )}
              </div>
            </Spin>
          </>
        )}
      </Card>

      {/* 日期详情抽屉 */}
      <DayDetailDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        date={drawerDate}
        schedules={drawerDate ? getSchedulesByDate(drawerDate) : []}
        appointments={drawerDate ? getAppointmentsByDate(drawerDate) : []}
        onAppointmentClick={handleAppointmentClick}
        onCreateClick={handleCreateClick}
        onSwitchToWeek={handleSwitchToWeek}
      />

      {/* 预约详情弹窗 */}
      <AppointmentDetailModal
        open={detailModalOpen}
        onClose={() => setDetailModalOpen(false)}
        appointment={selectedAppointment}
      />

      {/* 创建预约弹窗 */}
      <CreateAppointmentModal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        scheduleId={createScheduleId}
        onSuccess={refreshData}
      />
    </PageContainer>
  );
};

export default ScheduleCalendarPage;

