import { PageContainer } from '@ant-design/pro-components';
import { Card, Spin, DatePicker, Select, Space, Empty, Tooltip, Tag, Button, Drawer, Descriptions, Badge } from 'antd';
import { useState, useEffect, useCallback, useMemo } from 'react';
import dayjs, { Dayjs } from 'dayjs';
import { scheduleApi, doctorApi, departmentApi, storeApi } from '@hospital/api';
import type { Schedule, Doctor, Department } from '@hospital/shared';
import { useModel, useAccess } from '@umijs/max';
import { LeftOutlined, RightOutlined, ReloadOutlined, InfoCircleOutlined } from '@ant-design/icons';
import './gantt.less';

const { RangePicker } = DatePicker;

// 时段配置
const TIME_SLOT_CONFIG = {
  morning: { label: '上午', color: '#1890ff', startHour: 8, endHour: 12 },
  afternoon: { label: '下午', color: '#52c41a', startHour: 14, endHour: 18 },
  evening: { label: '晚上', color: '#722ed1', startHour: 19, endHour: 21 },
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
  timeSlot: 'morning' | 'afternoon' | 'evening';
  startTime: string;
  endTime: string;
  totalSlots: number;
  bookedSlots: number;
  status: number;
  progress: number; // 0-100
}

interface DoctorRow {
  doctorId: string;
  doctorName: string;
  departmentName?: string;
  tasks: GanttTask[];
}

const ScheduleGanttPage: React.FC = () => {
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
  const { currentUser, currentStore } = initialState ?? {};
  const access = useAccess();
  const isSuperAdmin = access.canSuperAdmin;
  const showStoreFilter = isSuperAdmin || (currentUser?.storeIds?.length ?? 0) > 1;

  // 加载科室列表
  const loadDepartments = async () => {
    try {
      const res = await departmentApi.getList({ pageSize: 100, status: 1 });
      const deptList = res.data ?? [];
      setDepartments(deptList);
      // 默认选择第一个科室
      if (deptList.length > 0 && !selectedDept) {
        setSelectedDept(deptList[0].id);
      }
    } catch (error) {
      console.error('加载科室失败', error);
    }
  };

  // 加载医生列表
  const loadDoctors = async (deptId?: string, autoSelectFirst: boolean = false) => {
    try {
      let doctorList: Doctor[] = [];
      if (deptId) {
        const data = await doctorApi.getByDepartment(deptId);
        doctorList = data ?? [];
      } else {
        const res = await doctorApi.getList({ pageSize: 100 });
        doctorList = res.data ?? [];
      }
      setDoctors(doctorList);
      // 默认选择第一个医生
      if (autoSelectFirst && doctorList.length > 0) {
        setSelectedDoctorId(doctorList[0].id);
      }
    } catch (error) {
      console.error('加载医生失败', error);
    }
  };

  // 加载排班数据
  const loadSchedules = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = {
        startDate: dateRange[0].format('YYYY-MM-DD'),
        endDate: dateRange[1].format('YYYY-MM-DD'),
        pageSize: 100, // 后端限制最大为 100
      };
      if (selectedStore) params.storeId = selectedStore;
      if (selectedDoctorId) params.doctorId = selectedDoctorId;

      const result = await scheduleApi.getList(params);
      setSchedules(result.data || []);
    } catch (error) {
      console.error('加载排班失败', error);
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
      const slotConfig = TIME_SLOT_CONFIG[schedule.timeSlot as keyof typeof TIME_SLOT_CONFIG] || TIME_SLOT_CONFIG.morning;
      const progress = schedule.totalSlots > 0 
        ? Math.round((schedule.bookedSlots / schedule.totalSlots) * 100)
        : 0;

      return {
        id: schedule.id,
        doctorId: schedule.doctorId,
        doctorName: schedule.doctorName || '未知医生',
        departmentName: schedule.departmentName,
        date: schedule.scheduleDate,
        timeSlot: schedule.timeSlot as 'morning' | 'afternoon' | 'evening',
        startTime: schedule.startTime || `${slotConfig.startHour.toString().padStart(2, '0')}:00`,
        endTime: schedule.endTime || `${slotConfig.endHour.toString().padStart(2, '0')}:00`,
        totalSlots: schedule.totalSlots,
        bookedSlots: schedule.bookedSlots,
        status: schedule.status,
        progress,
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
    const slotConfig = TIME_SLOT_CONFIG[task.timeSlot];
    const statusConfig = STATUS_CONFIG[task.status as keyof typeof STATUS_CONFIG];
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

    return (
      <div 
        key={dateStr} 
        className={`gantt-cell ${isToday ? 'today' : ''}`}
      >
        {tasksForDate.length > 0 ? (
          <div className="gantt-tasks">
            {tasksForDate.map(renderTaskBlock)}
          </div>
        ) : (
          <div className="gantt-empty">-</div>
        )}
      </div>
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
                options={[]}
                // 门店选项在实际使用中需加载
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
            {Object.entries(TIME_SLOT_CONFIG).map(([key, config]) => (
              <span key={key} className="legend-item">
                <span 
                  className="legend-color" 
                  style={{ backgroundColor: config.color }} 
                />
                {config.label}
              </span>
            ))}
            <span className="legend-item">
              <span 
                className="legend-color suspended" 
                style={{ backgroundColor: '#ff4d4f' }} 
              />
              停诊
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
        {selectedTask && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="医生">{selectedTask.doctorName}</Descriptions.Item>
            <Descriptions.Item label="科室">{selectedTask.departmentName || '-'}</Descriptions.Item>
            <Descriptions.Item label="日期">{selectedTask.date}</Descriptions.Item>
            <Descriptions.Item label="时段">
              <Tag color={TIME_SLOT_CONFIG[selectedTask.timeSlot].color}>
                {TIME_SLOT_CONFIG[selectedTask.timeSlot].label}
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
                status={STATUS_CONFIG[selectedTask.status as keyof typeof STATUS_CONFIG].color as any}
                text={STATUS_CONFIG[selectedTask.status as keyof typeof STATUS_CONFIG].text}
              />
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </PageContainer>
  );
};

export default ScheduleGanttPage;

