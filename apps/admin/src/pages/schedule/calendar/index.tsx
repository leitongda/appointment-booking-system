import { PageContainer } from '@ant-design/pro-components';
import { Button, Skeleton, message } from 'antd';
import { CopyOutlined, ImportOutlined, ExportOutlined } from '@ant-design/icons';
import { useState, useEffect, useCallback, useMemo } from 'react';
import dayjs, { Dayjs } from 'dayjs';
import { scheduleApi, appointmentApi } from '@hospital/api';
import type { Schedule, Appointment, Doctor } from '@hospital/shared';
import { useAccess } from '@umijs/max';
import { PAGINATION_CONFIG } from '@/constants/pagination';
import { requestDeduplicator } from '@/utils/requestDeduplication';
import DoctorSelector from './components/DoctorSelector';
import DayDetailDrawer from './components/DayDetailDrawer';
import AppointmentDetailModal from './components/AppointmentDetailModal';
import CreateAppointmentModal from './components/CreateAppointmentModal';
import ExtraQuotaModal from './components/ExtraQuotaModal';
import BatchCopyModal from './components/BatchCopyModal';
import ImportModal from './components/ImportModal';
import DragConfirmModal from './components/DragConfirmModal';
import type { DragConflictItem } from './components/DragConfirmModal';
import { CalendarHeader, type CalendarView } from './components/kargul/CalendarHeader';
import { TimeGrid } from './components/kargul/TimeGrid';
import type { AllDayChip, CreatePayload, MovePayload } from './components/kargul/TimeGrid';
import { MonthView } from './components/kargul/MonthView';
import { SchedulePopover } from './components/kargul/SchedulePopover';
import type { PopoverTarget } from './components/kargul/SchedulePopover';
import CreateScheduleModal from './components/kargul/CreateScheduleModal';
import type { CreateScheduleInitial } from './components/kargul/CreateScheduleModal';
import { scheduleToEvent, inferTimeSlot } from './components/kargul/colors';
import { minutesToHHMM } from './components/kargul/layout';
import { ScheduleMessages } from '../utils/message';
import './styles/kargul.less';

export type ViewMode = CalendarView;

export interface ScheduleSlot {
  schedule: Schedule;
  appointments: Appointment[];
  availableCount: number;
  bookedCount: number;
  status: 'available' | 'booked' | 'full' | 'suspended';
}

const CalendarSkeleton = () => (
  <div style={{ padding: '24px' }}>
    <Skeleton.Input active style={{ width: 200, marginBottom: 16 }} />
    <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
      {Array.from({ length: 7 }).map((_, i) => (
        <Skeleton.Input key={i} active style={{ width: 120, height: 24 }} />
      ))}
    </div>
    {Array.from({ length: 6 }).map((_, row) => (
      <div key={row} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        {Array.from({ length: 7 }).map((_, col) => (
          <Skeleton key={col} active paragraph={{ rows: 2, width: 80 }} title={false} style={{ width: 120, minHeight: 60 }} />
        ))}
      </div>
    ))}
  </div>
);

const STORAGE_KEY_VIEW_MODE = 'schedule_calendar_view_mode';

const getInitialViewMode = (): CalendarView => {
  const cached = localStorage.getItem(STORAGE_KEY_VIEW_MODE);
  if (cached === 'day' || cached === 'week' || cached === 'month') {
    return cached;
  }
  return 'week'; // 与参考设计一致，默认周视图
};

const ScheduleCalendarPage: React.FC = () => {
  const access = useAccess();
  const canCreate = access.hasPermission?.('schedule:create') ?? false;
  const canUpdate = access.hasPermission?.('schedule:update') ?? false;

  // 状态管理
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<CalendarView>(getInitialViewMode);
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

  // Kargul 日历：拖拽直接建排班 + 排班详情弹层
  const [createScheduleOpen, setCreateScheduleOpen] = useState(false);
  const [createScheduleInitial, setCreateScheduleInitial] = useState<CreateScheduleInitial | null>(null);
  const [popoverTarget, setPopoverTarget] = useState<PopoverTarget | null>(null);

  // 加号申请弹窗状态
  const [extraQuotaOpen, setExtraQuotaOpen] = useState(false);
  const [extraQuotaScheduleId, setExtraQuotaScheduleId] = useState<string>('');
  const [extraQuotaScheduleInfo, setExtraQuotaScheduleInfo] = useState<{
    doctorName?: string;
    scheduleDate?: string;
    timeSlot?: string;
    totalSlots?: number;
    bookedSlots?: number;
  } | undefined>(undefined);

  // 批量复制状态
  const [batchCopyOpen, setBatchCopyOpen] = useState(false);

  // 导入状态
  const [importOpen, setImportOpen] = useState(false);

  // 导出状态
  const [exportLoading, setExportLoading] = useState(false);

  // 拖拽状态
  const [dragConfirmOpen, setDragConfirmOpen] = useState(false);
  const [dragParams, setDragParams] = useState<{
    scheduleId: string;
    targetDate: string;
    targetStartTime?: string;
    targetEndTime?: string;
    targetTimeSlot?: string;
  } | null>(null);
  const [dragSchedule, setDragSchedule] = useState<Schedule | null>(null);
  const [dragConflicts, setDragConflicts] = useState<DragConflictItem[] | null>(null);
  const [dragLoading, setDragLoading] = useState(false);

  // 计算日期范围
  const getDateRange = useCallback(() => {
    if (viewMode === 'day') {
      const dateStr = currentDate.format('YYYY-MM-DD');
      return { startDate: dateStr, endDate: dateStr };
    }
    if (viewMode === 'week') {
      return {
        startDate: currentDate.startOf('week').format('YYYY-MM-DD'),
        endDate: currentDate.endOf('week').format('YYYY-MM-DD'),
      };
    }
    return {
      startDate: currentDate.startOf('month').format('YYYY-MM-DD'),
      endDate: currentDate.endOf('month').format('YYYY-MM-DD'),
    };
  }, [currentDate, viewMode]);

  // 当前视图可见日期
  const visibleDays = useMemo(() => {
    if (viewMode === 'day') return [currentDate];
    const start = viewMode === 'week' ? currentDate.startOf('week') : currentDate.startOf('month').startOf('week');
    return Array.from({ length: 7 }, (_, i) => start.add(i, 'day'));
  }, [currentDate, viewMode]);

  // 排班 → 日历事件；休息日聚合为全天泳道紫色 chip
  const calEvents = useMemo(() => {
    return schedules.map(scheduleToEvent).filter((e): e is NonNullable<typeof e> => e !== null);
  }, [schedules]);

  const allDayChips = useMemo<AllDayChip[]>(() => {
    const seen = new Set<string>();
    const chips: AllDayChip[] = [];
    for (const s of schedules) {
      if (!s.isRestDay || seen.has(s.scheduleDate)) continue;
      seen.add(s.scheduleDate);
      chips.push({ id: `rest-${s.scheduleDate}`, date: s.scheduleDate, title: '休息日' });
    }
    return chips;
  }, [schedules]);

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
      message.error(ScheduleMessages.scheduleLoadFailed);
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
      message.error(ScheduleMessages.appointmentLoadFailed);
      console.error('加载预约失败', error);
    }
  }, [selectedDoctor, getDateRange]);

  // 检查指定日期是否为休息日（从排班数据中获取，后端已计算）
  const isRestDay = useCallback((dateStr: string): boolean => {
    // 检查该日期的任何排班是否标记为休息日
    return schedules.some(s => s.scheduleDate === dateStr && s.isRestDay);
  }, [schedules]);

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

  // 处理加号申请
  const handleExtraQuotaClick = (scheduleId: string) => {
    const schedule = schedules.find(s => s.id === scheduleId);
    setExtraQuotaScheduleId(scheduleId);
    setExtraQuotaScheduleInfo(schedule ? {
      doctorName: schedule.doctorName,
      scheduleDate: schedule.scheduleDate,
      timeSlot: schedule.timeSlot,
      totalSlots: schedule.totalSlots,
      bookedSlots: schedule.bookedSlots,
    } : undefined);
    setExtraQuotaOpen(true);
  };

  // 处理视图模式切换
  const handleViewModeChange = (mode: CalendarView) => {
    setViewMode(mode);
    localStorage.setItem(STORAGE_KEY_VIEW_MODE, mode);
  };

  // 处理切换到周视图
  const handleSwitchToWeek = (date: Dayjs) => {
    setCurrentDate(date);
    handleViewModeChange('week');
    setDrawerOpen(false);
  };

  // 头部翻页：日 ±1 天 / 周 ±7 天 / 月 ±1 个月
  const handleStep = (dir: -1 | 1) => {
    const unit = viewMode === 'day' ? 'day' : viewMode === 'week' ? 'week' : 'month';
    setCurrentDate((prev) => prev.add(dir, unit));
  };

  // 拖拽/点击空档直接生成排班（schedule:create 权限门控）
  const handleCreateSchedule = useCallback((p: CreatePayload) => {
    if (!canCreate) return;
    setPopoverTarget(null);
    setCreateScheduleInitial(p);
    setCreateScheduleOpen(true);
  }, [canCreate]);

  // 处理拖拽调整（打开确认弹窗，走 dragAdjust 接口 + 冲突检测）
  const handleDragAdjust = useCallback((params: {
    scheduleId: string;
    targetDate: string;
    targetStartTime?: string;
    targetEndTime?: string;
    targetTimeSlot?: string;
  }) => {
    const schedule = schedules.find(s => s.id === params.scheduleId);
    if (!schedule) return;
    setDragSchedule(schedule);
    setDragParams(params);
    setDragConflicts(null);
    setDragConfirmOpen(true);
  }, [schedules]);

  // 拖动排班到新的日期/时间 → 走既有拖拽确认（含冲突检测）
  const handleMoveSchedule = useCallback((p: MovePayload) => {
    handleDragAdjust({
      scheduleId: p.eventId,
      targetDate: p.date,
      targetStartTime: minutesToHHMM(p.start),
      targetEndTime: minutesToHHMM(p.end),
      targetTimeSlot: inferTimeSlot(p.start),
    });
  }, [handleDragAdjust]);

  // 拖拽底边缩放排班 → 同日调整起止时间
  const handleResizeSchedule = useCallback((p: MovePayload) => {
    handleDragAdjust({
      scheduleId: p.eventId,
      targetDate: p.date,
      targetStartTime: minutesToHHMM(p.start),
      targetEndTime: minutesToHHMM(p.end),
      targetTimeSlot: inferTimeSlot(p.start),
    });
  }, [handleDragAdjust]);

  // 点击事件块 → 锚点详情弹层
  const handleEventClick = useCallback((eventId: string, el: HTMLElement) => {
    const event = calEvents.find((e) => e.id === eventId);
    if (!event) return;
    setPopoverTarget({ event, anchor: el.getBoundingClientRect() });
  }, [calEvents]);

  // 批量发布排班
  const handleBatchPublish = useCallback(async (scheduleIds: string[]) => {
    try {
      const result = await scheduleApi.batchPublish(scheduleIds);
      message.success(result.message || '发布成功');
      refreshData();
    } catch (error: any) {
      message.error(error?.response?.data?.message || '发布失败');
    }
  }, [refreshData]);

  // 批量撤回排班
  const handleBatchWithdraw = useCallback(async (scheduleIds: string[], reason?: string) => {
    try {
      const result = await scheduleApi.batchWithdraw(scheduleIds, reason);
      message.success(result.message || '撤回成功');
      refreshData();
    } catch (error: any) {
      message.error(error?.response?.data?.message || '撤回失败');
    }
  }, [refreshData]);

  // 处理导出排班
  const handleExport = useCallback(async () => {
    if (!selectedDoctor?.storeId) {
      message.warning('请先选择医生');
      return;
    }
    setExportLoading(true);
    try {
      const { startDate, endDate } = getDateRange();
      await scheduleApi.exportSchedules({
        storeId: selectedDoctor.storeId,
        doctorId: selectedDoctor.id,
        startDate,
        endDate,
      });
      message.success('导出成功');
    } catch (error) {
      message.error('导出失败');
      console.error('导出排班失败', error);
    } finally {
      setExportLoading(false);
    }
  }, [selectedDoctor, getDateRange]);

  // 确认拖拽调整
  const handleDragConfirm = useCallback(async () => {
    if (!dragParams) return;

    setDragLoading(true);
    try {
      const result = await scheduleApi.dragAdjust(dragParams);

      if (result.success) {
        message.success(result.message || '排班调整成功');
        setDragConfirmOpen(false);
        setDragParams(null);
        setDragSchedule(null);
        setDragConflicts(null);
        refreshData();
      } else {
        // 有冲突信息
        if (result.conflicts?.conflicts) {
          setDragConflicts(result.conflicts.conflicts as DragConflictItem[]);
        }
        message.warning(result.message || '排班调整失败');
      }
    } catch (error: any) {
      // 后端返回 409 冲突时，解析冲突信息
      // Structured error: error.errorDetails.conflicts or legacy: error.data.conflicts
      const conflictData = error?.errorDetails?.conflicts
        || error?.data?.conflicts?.conflicts
        || error?.response?.data?.conflicts?.conflicts;
      if (conflictData) {
        setDragConflicts(conflictData as DragConflictItem[]);
        message.warning(error?.message || '存在冲突，请确认后继续');
      } else {
        message.error(error?.message || '排班调整失败');
      }
    } finally {
      setDragLoading(false);
    }
  }, [dragParams, refreshData]);

  // 取消拖拽调整
  const handleDragCancel = useCallback(() => {
    setDragConfirmOpen(false);
    setDragParams(null);
    setDragSchedule(null);
    setDragConflicts(null);
  }, []);

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

  const todayStr = dayjs().format('YYYY-MM-DD');

  return (
    <PageContainer
      title="排班日历"
      subTitle={selectedDoctor ? `${selectedDoctor.name} - ${selectedDoctor.departmentName || ''}` : '请选择医生'}
    >
      <div className="kg-root">
        {/* 医生选择器 */}
        <div style={{ marginBottom: 16 }}>
          <DoctorSelector
            selectedDoctor={selectedDoctor}
            onSelect={setSelectedDoctor}
          />
        </div>

        {selectedDoctor && (
          <>
            {/* 操作栏 */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12, gap: 8 }}>
              <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>
                导入
              </Button>
              <Button icon={<ExportOutlined />} onClick={handleExport} loading={exportLoading}>
                导出
              </Button>
              <Button icon={<CopyOutlined />} onClick={() => setBatchCopyOpen(true)}>
                批量复制
              </Button>
            </div>

            {/* Kargul 日历 */}
            <div className="kg-cal" style={{ height: 'calc(100vh - 380px)', minHeight: 560 }}>
              <CalendarHeader
                view={viewMode}
                date={currentDate}
                days={visibleDays}
                onViewChange={handleViewModeChange}
                onToday={() => setCurrentDate(dayjs())}
                onStep={handleStep}
              />

              {loading ? (
                <CalendarSkeleton />
              ) : viewMode === 'month' ? (
                <MonthView
                  date={currentDate}
                  events={calEvents}
                  allDayChips={allDayChips}
                  selectedDate={currentDate.format('YYYY-MM-DD')}
                  today={todayStr}
                  onSelectDate={setCurrentDate}
                  onEventClick={handleEventClick}
                  onChipClick={(chip) => {
                    setDrawerDate(dayjs(chip.date));
                    setDrawerOpen(true);
                  }}
                  onCreate={handleCreateSchedule}
                  onOpenDay={(d) => {
                    setCurrentDate(d);
                    handleViewModeChange('day');
                  }}
                />
              ) : (
                <TimeGrid
                  days={visibleDays}
                  events={calEvents}
                  allDayChips={allDayChips}
                  selectedDate={currentDate.format('YYYY-MM-DD')}
                  today={todayStr}
                  onSelectDate={setCurrentDate}
                  canCreate={canCreate}
                  canUpdate={canUpdate}
                  onCreate={handleCreateSchedule}
                  onMove={handleMoveSchedule}
                  onResize={handleResizeSchedule}
                  onEventClick={handleEventClick}
                  onAllDayChipClick={(chip) => {
                    setDrawerDate(dayjs(chip.date));
                    setDrawerOpen(true);
                  }}
                  onScroll={() => setPopoverTarget(null)}
                />
              )}
            </div>

            {!canCreate && !canUpdate && (
              <div
                className="kg-t12"
                style={{ marginTop: 8, color: 'var(--kg-text-placeholder)', textAlign: 'right' }}
              >
                当前账号无排班操作权限，日历为只读模式
              </div>
            )}
          </>
        )}
      </div>

      {/* 排班详情弹层（锚点定位） */}
      <SchedulePopover
        target={popoverTarget}
        onClose={() => setPopoverTarget(null)}
        onCreateAppointment={canCreate ? (schedule: Schedule) => handleCreateClick(schedule.id) : undefined}
        onOpenDay={(d) => {
          setDrawerDate(d);
          setDrawerOpen(true);
        }}
      />

      {/* 拖拽/点击空档直接创建排班 */}
      <CreateScheduleModal
        open={createScheduleOpen}
        initial={createScheduleInitial}
        doctor={selectedDoctor}
        onClose={() => setCreateScheduleOpen(false)}
        onSuccess={refreshData}
      />

      {/* 日期详情抽屉 */}
      <DayDetailDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        date={drawerDate}
        schedules={drawerDate ? getSchedulesByDate(drawerDate) : []}
        appointments={drawerDate ? getAppointmentsByDate(drawerDate) : []}
        onAppointmentClick={handleAppointmentClick}
        onCreateClick={handleCreateClick}
        onExtraQuotaClick={handleExtraQuotaClick}
        onSwitchToWeek={handleSwitchToWeek}
        onBatchPublish={handleBatchPublish}
        onBatchWithdraw={handleBatchWithdraw}
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

      {/* 拖拽确认弹窗 */}
      <DragConfirmModal
        open={dragConfirmOpen}
        schedule={dragSchedule}
        targetDate={dragParams?.targetDate || ''}
        targetStartTime={dragParams?.targetStartTime}
        targetEndTime={dragParams?.targetEndTime}
        targetTimeSlot={dragParams?.targetTimeSlot}
        onConfirm={handleDragConfirm}
        onCancel={handleDragCancel}
        loading={dragLoading}
        conflicts={dragConflicts || undefined}
      />

      {/* 批量复制排班弹窗 */}
      <BatchCopyModal
        open={batchCopyOpen}
        onClose={() => setBatchCopyOpen(false)}
        onSuccess={refreshData}
        doctorId={selectedDoctor?.id}
      />

      {/* 导入排班弹窗 */}
      <ImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onSuccess={refreshData}
      />

      {/* 加号申请弹窗 */}
      <ExtraQuotaModal
        open={extraQuotaOpen}
        onClose={() => setExtraQuotaOpen(false)}
        onSuccess={refreshData}
        scheduleId={extraQuotaScheduleId}
        scheduleInfo={extraQuotaScheduleInfo}
      />
    </PageContainer>
  );
};

export default ScheduleCalendarPage;
