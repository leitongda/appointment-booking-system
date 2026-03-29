import { PageContainer } from '@ant-design/pro-components';
import { Card, Spin, DatePicker, Select, Space, Empty, Tooltip, Tag, Button, Drawer, Descriptions, Badge, App } from 'antd';
import { useState, useEffect, useCallback, useMemo } from 'react';
import dayjs, { Dayjs } from 'dayjs';
import { scheduleApi, doctorApi, departmentApi } from '@hospital/api';
import type { Schedule, Doctor, Department } from '@hospital/shared';
import { useModel, useAccess } from '@umijs/max';
import { LeftOutlined, RightOutlined, ReloadOutlined } from '@ant-design/icons';
import { useStoreWithPermission } from '@/hooks/useStoreWithPermission';
import './gantt.less';

const { RangePicker } = DatePicker;

// 时段配置
const TIME_SLOT_CONFIG: Record<string, { label: string; color: string; startHour: number; endHour: number }> = {
  morning: { label: '上午', color: '#1890ff', startHour: 8, endHour: 12 },
  afternoon: { label: '下午', color: '#52c41a', startHour: 14, endHour: 18 },
  evening: { label: '晚上', color: '#722ed1', startHour: 19, endHour: 21 },
};

// 图例配置（只显示小写格式，避免重复）
const LEGEND_CONFIG = [
  { key: 'morning', label: '上午', color: '#1890ff' },
  { key: 'afternoon', label: '下午', color: '#52c41a' },
  { key: 'evening', label: '晚上', color: '#722ed1' },
];

// 默认时段配置（用于 fallback）
const DEFAULT_SLOT_CONFIG = { label: '未知', color: '#999', startHour: 8, endHour: 12 };

// 获取时段配置（带 fallback）
const getSlotConfig = (timeSlot: string | undefined) => {
  if (!timeSlot) return DEFAULT_SLOT_CONFIG;
  return TIME_SLOT_CONFIG[timeSlot] || DEFAULT_SLOT_CONFIG;
};

// 状态配置
const STATUS_CONFIG = {
  1: { text: '正常', color: 'success' },
  0: { text: '停诊', color: 'error' },
};

interface GanttTask {
  id: string;
  doctorId: string;
  doctorName: string;
  departmentName?: string;
  date: string;
  timeSlot: string;  // 支持 morning/afternoon/evening 和 AM/PM/NIGHT
  startTime: string;
  endTime: string;
  totalSlots: number;
  bookedSlots: number;
  status: number;
  progress: number; // 0-100
  isRestDay?: boolean; // 是否在休息日（后端计算）
}

interface DoctorRow {
  doctorId: string;
  doctorName: string;
  departmentName?: string;
  tasks: GanttTask[];
}

const ScheduleGanttPage: React.FC = () => {
  const { message } = App.useApp();
  // 状态管理
  const [loading, setLoading] = useState(false);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);

  // 筛选条件
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>([
    dayjs().startOf('week'),
    dayjs().endOf('week'),
  ]);
  const [selectedStore, setSelectedStore] = useState<string>();
  const [selectedDept, setSelectedDept] = useState<string>();
  const [selectedDoctorId, setSelectedDoctorId] = useState<string>();

  // 详情抽屉
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<GanttTask | null>(null);

  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const access = useAccess();
  const isSuperAdmin = access.canSuperAdmin;
  const showStoreFilter = isSuperAdmin || (currentUser?.storeIds?.length ?? 0) > 1;
  const { stores } = useStoreWithPermission({ enabledOnly: true });

  // 加载科室列表
  const loadDepartments = async () => {
    try {
      const allDepts = await departmentApi.getAll();

      setDepartments(allDepts);
      // 默认选择第一个科室
      if (allDepts.length > 0 && !selectedDept) {
        setSelectedDept(allDepts[0].id);
      }
    } catch (error) {
      console.error('加载科室失败', error);
      message.error('加载科室失败');
    }
  };

  // 加载医生列表（分页加载所有数据）
  const loadDoctors = async (deptId?: string, autoSelectFirst: boolean = false) => {
    try {
      let doctorList: Doctor[] = [];
      if (deptId) {
        // 按科室获取（通常不分页）
        const data = await doctorApi.getByDepartment(deptId);
        doctorList = data ?? [];
      } else {
        // 分页加载所有医生
        const firstResult = await doctorApi.getList({ pageSize: 100, page: 1 });
        const total = firstResult.total || 0;
        doctorList = firstResult.data ?? [];

        if (total > 100) {
          const totalPages = Math.ceil(total / 100);
          const promises = [];
          for (let page = 2; page <= totalPages; page++) {
            promises.push(doctorApi.getList({ pageSize: 100, page }));
          }
          const results = await Promise.all(promises);
          for (const result of results) {
            doctorList = doctorList.concat(result.data ?? []);
          }
        }
      }
      setDoctors(doctorList);
      // 默认选择第一个医生
      if (autoSelectFirst && doctorList.length > 0) {
        setSelectedDoctorId(doctorList[0].id);
      }
    } catch (error) {
      console.error('加载医生失败', error);
      message.error('加载医生列表失败');
    }
  };

  // 加载排班数据（分页加载所有数据，后端会返回 isRestDay 字段）
  const loadSchedules = useCallback(async () => {
    setLoading(true);
    try {
      const baseParams: any = {
        startDate: dateRange[0].format('YYYY-MM-DD'),
        endDate: dateRange[1].format('YYYY-MM-DD'),
        pageSize: 100, // 后端限制最大为 100
      };
      if (selectedStore) baseParams.storeId = selectedStore;
      if (selectedDoctorId) baseParams.doctorId = selectedDoctorId;

      // 第一次请求获取总数
      const firstResult = await scheduleApi.getList({ ...baseParams, page: 1 });
      const total = firstResult.total || 0;
      let allSchedules = firstResult.data || [];

      // 如果有更多数据，继续请求
      if (total > 100) {
        const totalPages = Math.ceil(total / 100);
        const promises = [];
        for (let page = 2; page <= totalPages; page++) {
          promises.push(scheduleApi.getList({ ...baseParams, page }));
        }
        const results = await Promise.all(promises);
        for (const result of results) {
          allSchedules = allSchedules.concat(result.data || []);
        }
      }

      setSchedules(allSchedules);
    } catch (error) {
      console.error('加载排班失败', error);
      message.error('加载排班数据失败');
    } finally {
      setLoading(false);
    }
  }, [dateRange, selectedStore, selectedDoctorId]);

  useEffect(() => {
    loadDepartments();
    loadDoctors();
  }, []);

  useEffect(() => {
    loadSchedules();
  }, [loadSchedules]);

  useEffect(() => {
    if (selectedDept) {
      setSelectedDoctorId(undefined);
      loadDoctors(selectedDept, true);
    } else {
      loadDoctors();
    }
  }, [selectedDept]);

  // 转换排班数据为甘特图任务
  const ganttTasks: GanttTask[] = useMemo(() => {
    return schedules.map((schedule) => {
      const slotConfig = getSlotConfig(schedule.timeSlot);
      const progress = schedule.totalSlots > 0 
        ? Math.round((schedule.bookedSlots / schedule.totalSlots) * 100)
        : 0;

      return {
        id: schedule.id,
        doctorId: schedule.doctorId,
        doctorName: schedule.doctorName || '未知医生',
        departmentName: schedule.departmentName,
        date: schedule.scheduleDate,
        timeSlot: schedule.timeSlot || 'morning',  // 确保有默认值
        startTime: schedule.startTime || `${slotConfig.startHour.toString().padStart(2, '0')}:00`,
        endTime: schedule.endTime || `${slotConfig.endHour.toString().padStart(2, '0')}:00`,
        totalSlots: schedule.totalSlots,
        bookedSlots: schedule.bookedSlots,
        status: schedule.status,
        progress,
        isRestDay: schedule.isRestDay,  // 直接使用后端返回的字段
      };
    });
  }, [schedules]);

  // 按医生分组
  const doctorRows: DoctorRow[] = useMemo(() => {
    const doctorMap = new Map<string, DoctorRow>();
    
    ganttTasks.forEach((task) => {
      if (!doctorMap.has(task.doctorId)) {
        doctorMap.set(task.doctorId, {
          doctorId: task.doctorId,
          doctorName: task.doctorName,
          departmentName: task.departmentName,
          tasks: [],
        });
      }
      doctorMap.get(task.doctorId)!.tasks.push(task);
    });

    return Array.from(doctorMap.values()).sort((a, b) => 
      a.doctorName.localeCompare(b.doctorName)
    );
  }, [ganttTasks]);

  // 生成日期列表
  const dateList: Dayjs[] = useMemo(() => {
    const dates: Dayjs[] = [];
    let current = dateRange[0].clone();
    while (current.isBefore(dateRange[1]) || current.isSame(dateRange[1], 'day')) {
      dates.push(current);
      current = current.add(1, 'day');
    }
    return dates;
  }, [dateRange]);

  // 导航到上一周/下一周
  const navigatePrev = () => {
    setDateRange([
      dateRange[0].subtract(7, 'day'),
      dateRange[1].subtract(7, 'day'),
    ]);
  };

  const navigateNext = () => {
    setDateRange([
      dateRange[0].add(7, 'day'),
      dateRange[1].add(7, 'day'),
    ]);
  };

  const navigateToday = () => {
    setDateRange([
      dayjs().startOf('week'),
      dayjs().endOf('week'),
    ]);
  };

  // 处理任务点击
  const handleTaskClick = (task: GanttTask) => {
    setSelectedTask(task);
    setDrawerOpen(true);
  };

  // 渲染甘特图任务块
  const renderTaskBlock = (task: GanttTask) => {
    const slotConfig = getSlotConfig(task.timeSlot);
    const statusConfig = STATUS_CONFIG[task.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG[1];
    const isSuspended = task.status === 0;

    return (
      <Tooltip
        key={task.id}
        title={
          <div>
            <div><strong>{task.doctorName}</strong></div>
            <div>{slotConfig.label}：{task.startTime} - {task.endTime}</div>
            <div>号源：{task.bookedSlots}/{task.totalSlots}</div>
            <div>状态：{statusConfig.text}</div>
          </div>
        }
      >
        <div
          className={`gantt-task-block ${isSuspended ? 'suspended' : ''}`}
          style={{
            backgroundColor: isSuspended ? '#ff4d4f' : slotConfig.color,
            opacity: isSuspended ? 0.6 : 1,
          }}
          onClick={() => handleTaskClick(task)}
        >
          <span className="task-label">{slotConfig.label}</span>
          <span className="task-progress">{task.bookedSlots}/{task.totalSlots}</span>
          {task.progress > 0 && (
            <div 
              className="task-progress-bar" 
              style={{ width: `${task.progress}%` }}
            />
          )}
        </div>
      </Tooltip>
    );
  };

  // 渲染日期单元格
  const renderDateCell = (doctor: DoctorRow, date: Dayjs) => {
    const dateStr = date.format('YYYY-MM-DD');
    const tasksForDate = doctor.tasks.filter((t) => t.date === dateStr);
    const isToday = date.isSame(dayjs(), 'day');
    // 从排班数据中获取 isRestDay（后端已计算）
    const isRest = tasksForDate.some((t) => t.isRestDay);

    return (
      <Tooltip
        key={dateStr}
        title={isRest ? '休息日 - 该日期已设置休息，小程序端不可预约' : undefined}
      >
        <div 
          className={`gantt-cell ${isToday ? 'today' : ''} ${isRest ? 'rest-day' : ''}`}
        >
          {isRest && <div className="rest-day-badge">休</div>}
          {tasksForDate.length > 0 ? (
            <div className="gantt-tasks">
              {tasksForDate.map(renderTaskBlock)}
            </div>
          ) : (
            <div className="gantt-empty">{isRest ? '' : '-'}</div>
          )}
        </div>
      </Tooltip>
    );
  };

  return (
    <PageContainer title="排班甘特图">
      <Card className="gantt-container">
        {/* 筛选器 */}
        <div className="gantt-filters">
          <Space wrap>
            {showStoreFilter && (
              <Select
                placeholder="选择门店"
                allowClear
                style={{ width: 150 }}
                value={selectedStore}
                onChange={setSelectedStore}
                options={stores.map((s) => ({ label: s.name, value: s.id }))}
              />
            )}
            <Select
              placeholder="选择科室"
              allowClear
              style={{ width: 150 }}
              value={selectedDept}
              onChange={setSelectedDept}
              options={departments.map((d) => ({ label: d.name, value: d.id }))}
            />
            <Select
              placeholder="选择医生"
              allowClear
              showSearch
              optionFilterProp="label"
              style={{ width: 150 }}
              value={selectedDoctorId}
              onChange={setSelectedDoctorId}
              options={doctors.map((d) => ({ 
                label: `${d.name}${d.title ? ` - ${d.title}` : ''}`, 
                value: d.id 
              }))}
            />
            <RangePicker
              value={dateRange}
              onChange={(dates) => dates && setDateRange(dates as [Dayjs, Dayjs])}
              allowClear={false}
            />
            <Button.Group>
              <Button icon={<LeftOutlined />} onClick={navigatePrev} />
              <Button onClick={navigateToday}>本周</Button>
              <Button icon={<RightOutlined />} onClick={navigateNext} />
            </Button.Group>
            <Button icon={<ReloadOutlined />} onClick={loadSchedules}>
              刷新
            </Button>
          </Space>
        </div>

        {/* 图例 */}
        <div className="gantt-legend">
          <Space size="large">
            {LEGEND_CONFIG.map((item) => (
              <span key={item.key} className="legend-item">
                <span 
                  className="legend-color" 
                  style={{ backgroundColor: item.color }} 
                />
                {item.label}
              </span>
            ))}
            <span className="legend-item">
              <span 
                className="legend-color suspended" 
                style={{ backgroundColor: '#ff4d4f' }} 
              />
              停诊
            </span>
            <span className="legend-item">
              <span 
                className="legend-color rest-day" 
                style={{ backgroundColor: '#ffe7ba', border: '1px solid #fa8c16' }} 
              />
              休息日
            </span>
          </Space>
        </div>

        {/* 甘特图主体 */}
        <Spin spinning={loading}>
          {doctorRows.length > 0 ? (
            <div className="gantt-chart">
              {/* 表头 */}
              <div className="gantt-header">
                <div className="gantt-header-doctor">医生</div>
                <div className="gantt-header-dates">
                  {dateList.map((date) => (
                    <div 
                      key={date.format('YYYY-MM-DD')} 
                      className={`gantt-header-date ${date.isSame(dayjs(), 'day') ? 'today' : ''}`}
                    >
                      <div className="date-weekday">
                        {['日', '一', '二', '三', '四', '五', '六'][date.day()]}
                      </div>
                      <div className="date-day">{date.format('MM-DD')}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 数据行 */}
              <div className="gantt-body">
                {doctorRows.map((doctor) => (
                  <div key={doctor.doctorId} className="gantt-row">
                    <div className="gantt-row-doctor">
                      <div className="doctor-name">{doctor.doctorName}</div>
                      {doctor.departmentName && (
                        <div className="doctor-dept">{doctor.departmentName}</div>
                      )}
                    </div>
                    <div className="gantt-row-dates">
                      {dateList.map((date) => renderDateCell(doctor, date))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <Empty 
              description="暂无排班数据，请调整筛选条件" 
              style={{ padding: '60px 0' }}
            />
          )}
        </Spin>
      </Card>

      {/* 详情抽屉 */}
      <Drawer
        title="排班详情"
        placement="right"
        width={400}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      >
        {selectedTask && (() => {
          const taskSlotConfig = getSlotConfig(selectedTask.timeSlot);
          const taskStatusConfig = STATUS_CONFIG[selectedTask.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG[1];
          return (
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="医生">{selectedTask.doctorName}</Descriptions.Item>
              <Descriptions.Item label="科室">{selectedTask.departmentName || '-'}</Descriptions.Item>
              <Descriptions.Item label="日期">{selectedTask.date}</Descriptions.Item>
              <Descriptions.Item label="时段">
                <Tag color={taskSlotConfig.color}>
                  {taskSlotConfig.label}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="时间">
                {selectedTask.startTime} - {selectedTask.endTime}
              </Descriptions.Item>
              <Descriptions.Item label="总号源">{selectedTask.totalSlots}</Descriptions.Item>
              <Descriptions.Item label="已预约">{selectedTask.bookedSlots}</Descriptions.Item>
              <Descriptions.Item label="剩余">
                {selectedTask.totalSlots - selectedTask.bookedSlots}
              </Descriptions.Item>
              <Descriptions.Item label="预约率">
                <span style={{ color: selectedTask.progress >= 80 ? '#ff4d4f' : '#52c41a' }}>
                  {selectedTask.progress}%
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Badge 
                  status={taskStatusConfig.color as any}
                  text={taskStatusConfig.text}
                />
              </Descriptions.Item>
            </Descriptions>
          );
        })()}
      </Drawer>
    </PageContainer>
  );
};

export default ScheduleGanttPage;

