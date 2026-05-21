/**
 * 排班甘特图页面
 * 使用 SVG 渲染，展示医生排班的时段分布和预约情况
 */

import { PageContainer } from '@ant-design/pro-components';
import { App, Card, Spin, DatePicker, Select, Space, Empty, Drawer, Descriptions, Badge, Tag, Button, theme } from 'antd';
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import dayjs, { Dayjs } from 'dayjs';
import { scheduleApi, doctorApi, departmentApi } from '@hospital/api';
import type { Schedule, Doctor, Department } from '@hospital/shared';
import { useModel, useAccess } from '@umijs/max';
import { LeftOutlined, RightOutlined, ReloadOutlined } from '@ant-design/icons';
import { useStoreWithPermission } from '@/hooks/useStoreWithPermission';
import {
  GANTT_MORNING,
  GANTT_AFTERNOON,
  GANTT_EVENING,
  GANTT_UNKNOWN,
  COLOR_DANGER,
  COLOR_SUCCESS,
  COLOR_WARNING,
} from '@/themes/scheduleColors';

const { RangePicker } = DatePicker;

// ==================== 常量定义 ====================

const TIME_SLOT_CONFIG: Record<string, { label: string; color: string; gradientStart: string; gradientEnd: string }> = {
  morning: {
    label: '上午',
    color: GANTT_MORNING,
    gradientStart: 'rgba(22, 119, 255, 0.35)',
    gradientEnd: 'rgba(22, 119, 255, 0.08)',
  },
  afternoon: {
    label: '下午',
    color: GANTT_AFTERNOON,
    gradientStart: 'rgba(82, 196, 26, 0.35)',
    gradientEnd: 'rgba(82, 196, 26, 0.08)',
  },
  evening: {
    label: '晚上',
    color: GANTT_EVENING,
    gradientStart: 'rgba(114, 46, 209, 0.35)',
    gradientEnd: 'rgba(114, 46, 209, 0.08)',
  },
};

const DEFAULT_SLOT_CONFIG = {
  label: '未知',
  color: GANTT_UNKNOWN,
  gradientStart: 'rgba(140, 140, 140, 0.35)',
  gradientEnd: 'rgba(140, 140, 140, 0.08)',
};

const getSlotConfig = (timeSlot: string | undefined) => {
  if (!timeSlot) return DEFAULT_SLOT_CONFIG;
  return TIME_SLOT_CONFIG[timeSlot] || DEFAULT_SLOT_CONFIG;
};

const STATUS_CONFIG = {
  1: { text: '正常', color: 'success' },
  0: { text: '停诊', color: 'error' },
};

// ==================== SVG 配置 ====================

const SVG_CONFIG = {
  labelWidth: 140,
  rowHeight: 48,
  barHeight: 32,
  paddingTop: 36,
  paddingBottom: 16,
  minCellWidth: 100,
};

// ==================== 类型定义 ====================

interface ScheduleTask {
  id: string;
  doctorId: string;
  doctorName: string;
  departmentName?: string;
  date: string;
  timeSlot: string;
  startTime: string;
  endTime: string;
  totalSlots: number;
  bookedSlots: number;
  status: number;
  progress: number;
  isRestDay?: boolean;
}

interface DoctorRow {
  doctorId: string;
  doctorName: string;
  departmentName?: string;
  tasks: ScheduleTask[];
}

// ==================== 主组件 ====================

const ScheduleGanttPage: React.FC = () => {
  const { message } = App.useApp();
  const { token } = theme.useToken();
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(800);

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
  const [selectedTask, setSelectedTask] = useState<ScheduleTask | null>(null);

  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const access = useAccess();
  const isSuperAdmin = access.canSuperAdmin;
  const showStoreFilter = isSuperAdmin || (currentUser?.storeIds?.length ?? 0) > 1;
  const { stores } = useStoreWithPermission({ enabledOnly: true });

  // 响应式宽度
  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        const width = containerRef.current.getBoundingClientRect().width;
        setContainerWidth(Math.max(width, 600));
      }
    };
    const timer = setTimeout(updateWidth, 50);
    const resizeObserver = new ResizeObserver(updateWidth);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }
    return () => {
      clearTimeout(timer);
      resizeObserver.disconnect();
    };
  }, []);

  // 加载科室列表
  const loadDepartments = async () => {
    try {
      const allDepts = await departmentApi.getAll();
      setDepartments(allDepts);
      if (allDepts.length > 0 && !selectedDept) {
        setSelectedDept(allDepts[0].id);
      }
    } catch (error) {
      console.error('加载科室失败', error);
      message.error('加载科室失败');
    }
  };

  // 加载医生列表
  const loadDoctors = async (deptId?: string, autoSelectFirst = false) => {
    try {
      let doctorList: Doctor[] = [];
      if (deptId) {
        const data = await doctorApi.getByDepartment(deptId);
        doctorList = data ?? [];
      } else {
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
      if (autoSelectFirst && doctorList.length > 0) {
        setSelectedDoctorId(doctorList[0].id);
      }
    } catch (error) {
      console.error('加载医生失败', error);
      message.error('加载医生列表失败');
    }
  };

  // 加载排班数据
  const loadSchedules = useCallback(async () => {
    setLoading(true);
    try {
      const baseParams: any = {
        startDate: dateRange[0].format('YYYY-MM-DD'),
        endDate: dateRange[1].format('YYYY-MM-DD'),
        pageSize: 100,
      };
      if (selectedStore) baseParams.storeId = selectedStore;
      if (selectedDoctorId) baseParams.doctorId = selectedDoctorId;

      const firstResult = await scheduleApi.getList({ ...baseParams, page: 1 });
      const total = firstResult.total || 0;
      let allSchedules = firstResult.data || [];

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

  // 转换排班数据为任务
  const tasks: ScheduleTask[] = useMemo(() => {
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
        timeSlot: schedule.timeSlot || 'morning',
        startTime: schedule.startTime || '08:00',
        endTime: schedule.endTime || '12:00',
        totalSlots: schedule.totalSlots,
        bookedSlots: schedule.bookedSlots,
        status: schedule.status,
        progress,
        isRestDay: schedule.isRestDay,
      };
    });
  }, [schedules]);

  // 按医生分组
  const doctorRows: DoctorRow[] = useMemo(() => {
    const doctorMap = new Map<string, DoctorRow>();
    tasks.forEach((task) => {
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
  }, [tasks]);

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

  // 计算 SVG 布局
  const layout = useMemo(() => {
    const cellWidth = Math.max(
      (containerWidth - SVG_CONFIG.labelWidth) / dateList.length,
      SVG_CONFIG.minCellWidth,
    );
    const chartWidth = cellWidth * dateList.length;
    const totalWidth = SVG_CONFIG.labelWidth + chartWidth;
    const totalHeight = SVG_CONFIG.paddingTop + doctorRows.length * SVG_CONFIG.rowHeight + SVG_CONFIG.paddingBottom;
    return { cellWidth, chartWidth, totalWidth, totalHeight };
  }, [containerWidth, dateList.length, doctorRows.length]);

  // 导航
  const navigatePrev = () => {
    setDateRange([dateRange[0].subtract(7, 'day'), dateRange[1].subtract(7, 'day')]);
  };
  const navigateNext = () => {
    setDateRange([dateRange[0].add(7, 'day'), dateRange[1].add(7, 'day')]);
  };
  const navigateToday = () => {
    setDateRange([dayjs().startOf('week'), dayjs().endOf('week')]);
  };

  // 处理任务点击
  const handleTaskClick = (task: ScheduleTask) => {
    setSelectedTask(task);
    setDrawerOpen(true);
  };

  return (
    <PageContainer title="排班甘特图">
      <Card>
        {/* 筛选器 */}
        <div style={{ marginBottom: 16, paddingBottom: 16, borderBottom: `1px solid ${token.colorBorderSecondary}` }}>
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
                value: d.id,
              }))}
            />
            <RangePicker
              value={dateRange}
              onChange={(dates) => dates && setDateRange(dates as [Dayjs, Dayjs])}
              allowClear={false}
            />
            <Space.Compact>
              <Button icon={<LeftOutlined />} onClick={navigatePrev} />
              <Button onClick={navigateToday}>本周</Button>
              <Button icon={<RightOutlined />} onClick={navigateNext} />
            </Space.Compact>
            <Button icon={<ReloadOutlined />} onClick={loadSchedules}>
              刷新
            </Button>
          </Space>
        </div>

        {/* 图例 */}
        <div style={{ marginBottom: 16, padding: '8px 16px', background: token.colorFillAlter, borderRadius: 4 }}>
          <Space size="large">
            {Object.entries(TIME_SLOT_CONFIG).map(([key, config]) => (
              <span key={key} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, color: token.colorTextSecondary }}>
                <svg width={16} height={12}>
                  <rect width={16} height={12} fill={config.gradientStart} stroke={config.color} strokeWidth={1} rx={2} />
                </svg>
                {config.label}
              </span>
            ))}
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, color: token.colorTextSecondary }}>
              <svg width={16} height={12}>
                <rect width={16} height={12} fill="rgba(255,77,79,0.2)" stroke={COLOR_DANGER} strokeWidth={1} rx={2} strokeDasharray="2 2" />
              </svg>
              停诊
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, color: token.colorTextSecondary }}>
              <svg width={16} height={12}>
                <rect width={16} height={12} fill="rgba(250,140,22,0.15)" stroke={COLOR_WARNING} strokeWidth={1} rx={2} />
              </svg>
              休息日
            </span>
          </Space>
        </div>

        {/* SVG 甘特图主体 */}
        <Spin spinning={loading}>
          {doctorRows.length > 0 ? (
            <div ref={containerRef} style={{ overflowX: layout.totalWidth > containerWidth ? 'auto' : 'visible', overflowY: 'hidden', maxWidth: '100%' }}>
              <svg width={layout.totalWidth} height={layout.totalHeight}>
                <defs>
                  {/* 时段渐变 */}
                  {Object.entries(TIME_SLOT_CONFIG).map(([key, config]) => (
                    <linearGradient key={`grad-${key}`} id={`slot-gradient-${key}`} x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor={config.gradientStart} />
                      <stop offset="100%" stopColor={config.gradientEnd} />
                    </linearGradient>
                  ))}
                  <filter id="bar-shadow" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="1" stdDeviation="1.5" floodOpacity="0.12" />
                  </filter>
                </defs>

                {/* 表头背景 */}
                <rect x={0} y={0} width={layout.totalWidth} height={SVG_CONFIG.paddingTop} fill={token.colorFillAlter} />

                {/* 垂直轴线（标签和图表之间） */}
                <line x1={SVG_CONFIG.labelWidth} y1={0} x2={SVG_CONFIG.labelWidth} y2={layout.totalHeight} stroke={token.colorBorderSecondary} strokeWidth={1} />

                {/* 日期表头 */}
                {dateList.map((date, i) => {
                  const x = SVG_CONFIG.labelWidth + i * layout.cellWidth;
                  const isToday = date.isSame(dayjs(), 'day');
                  return (
                    <g key={date.format('YYYY-MM-DD')}>
                      {/* 今天高亮 */}
                      {isToday && (
                        <rect x={x} y={0} width={layout.cellWidth} height={layout.totalHeight} fill="rgba(22,119,255,0.04)" />
                      )}
                      {/* 垂直网格线 */}
                      <line x1={x} y1={SVG_CONFIG.paddingTop} x2={x} y2={layout.totalHeight} stroke={token.colorBorderSecondary} strokeWidth={0.5} strokeDasharray="2 2" />
                      {/* 星期 */}
                      <text
                        x={x + layout.cellWidth / 2}
                        y={14}
                        textAnchor="middle"
                        fontSize={11}
                        fill={isToday ? token.colorPrimary : token.colorTextSecondary}
                        fontWeight={isToday ? 600 : 400}
                      >
                        {['日', '一', '二', '三', '四', '五', '六'][date.day()]}
                      </text>
                      {/* 日期 */}
                      <text
                        x={x + layout.cellWidth / 2}
                        y={30}
                        textAnchor="middle"
                        fontSize={12}
                        fill={isToday ? token.colorPrimary : token.colorText}
                        fontWeight={isToday ? 600 : 400}
                      >
                        {date.format('MM-DD')}
                      </text>
                    </g>
                  );
                })}

                {/* 水平轴线 */}
                <line x1={SVG_CONFIG.labelWidth} y1={SVG_CONFIG.paddingTop} x2={layout.totalWidth} y2={SVG_CONFIG.paddingTop} stroke={token.colorBorderSecondary} strokeWidth={1} />

                {/* 数据行 */}
                {doctorRows.map((doctor, rowIndex) => {
                  const y = SVG_CONFIG.paddingTop + rowIndex * SVG_CONFIG.rowHeight;
                  return (
                    <g key={doctor.doctorId}>
                      {/* 行背景（交替色） */}
                      {rowIndex % 2 === 1 && (
                        <rect x={0} y={y} width={layout.totalWidth} height={SVG_CONFIG.rowHeight} fill={token.colorFillAlter} opacity={0.3} />
                      )}
                      {/* 水平分隔线 */}
                      <line x1={0} y1={y + SVG_CONFIG.rowHeight} x2={layout.totalWidth} y2={y + SVG_CONFIG.rowHeight} stroke={token.colorBorderSecondary} strokeWidth={0.5} />
                      {/* 医生名称 */}
                      <text
                        x={SVG_CONFIG.labelWidth - 12}
                        y={y + SVG_CONFIG.rowHeight / 2 - (doctor.departmentName ? 6 : 0)}
                        textAnchor="end"
                        dominantBaseline="middle"
                        fontSize={12}
                        fill={token.colorText}
                        fontWeight={500}
                      >
                        {doctor.doctorName}
                      </text>
                      {/* 科室名称 */}
                      {doctor.departmentName && (
                        <text
                          x={SVG_CONFIG.labelWidth - 12}
                          y={y + SVG_CONFIG.rowHeight / 2 + 10}
                          textAnchor="end"
                          dominantBaseline="middle"
                          fontSize={10}
                          fill={token.colorTextSecondary}
                        >
                          {doctor.departmentName}
                        </text>
                      )}

                      {/* 日期单元格 */}
                      {dateList.map((date, colIndex) => {
                        const dateStr = date.format('YYYY-MM-DD');
                        const cellX = SVG_CONFIG.labelWidth + colIndex * layout.cellWidth;
                        const tasksForDate = doctor.tasks.filter((t) => t.date === dateStr);
                        const isRest = tasksForDate.some((t) => t.isRestDay);

                        return (
                          <g key={dateStr}>
                            {/* 休息日背景 */}
                            {isRest && (
                              <rect x={cellX + 2} y={y + 2} width={layout.cellWidth - 4} height={SVG_CONFIG.rowHeight - 4} fill="rgba(250,140,22,0.08)" rx={4} />
                            )}
                            {/* 休息日标记 */}
                            {isRest && (
                              <g>
                                <rect x={cellX + layout.cellWidth - 22} y={y + 4} width={18} height={14} fill={COLOR_WARNING} rx={2} />
                                <text x={cellX + layout.cellWidth - 13} y={y + 14} textAnchor="middle" fontSize={9} fill="#fff" fontWeight={500}>
                                  休
                                </text>
                              </g>
                            )}
                            {/* 排班任务块 */}
                            {tasksForDate.length > 0 ? (
                              tasksForDate.map((task, taskIndex) => {
                                const slotConfig = getSlotConfig(task.timeSlot);
                                const isSuspended = task.status === 0;
                                const barY = y + 6 + taskIndex * 20;
                                const barWidth = layout.cellWidth - 12;
                                const barHeight = 18;

                                if (barY + barHeight > y + SVG_CONFIG.rowHeight - 4) return null;

                                return (
                                  <g key={task.id} style={{ cursor: 'pointer' }} onClick={() => handleTaskClick(task)}>
                                    <title>
                                      {`${task.doctorName}\n${slotConfig.label}：${task.startTime} - ${task.endTime}\n号源：${task.bookedSlots}/${task.totalSlots}\n状态：${isSuspended ? '停诊' : '正常'}`}
                                    </title>
                                    {/* 任务条背景 */}
                                    <rect
                                      x={cellX + 6}
                                      y={barY}
                                      width={barWidth}
                                      height={barHeight}
                                      fill={isSuspended ? 'rgba(255,77,79,0.2)' : `url(#slot-gradient-${task.timeSlot})`}
                                      stroke={isSuspended ? COLOR_DANGER : slotConfig.color}
                                      strokeWidth={1}
                                      rx={4}
                                    />
                                    {/* 停诊斜纹 */}
                                    {isSuspended && (
                                      <clipPath id={`clip-${task.id}`}>
                                        <rect x={cellX + 6} y={barY} width={barWidth} height={barHeight} rx={4} />
                                      </clipPath>
                                    )}
                                    {/* 进度条 */}
                                    {task.progress > 0 && !isSuspended && (
                                      <rect
                                        x={cellX + 6}
                                        y={barY + barHeight - 2}
                                        width={barWidth * task.progress / 100}
                                        height={2}
                                        fill="rgba(255,255,255,0.5)"
                                        rx={1}
                                      />
                                    )}
                                    {/* 标签文字 */}
                                    {barWidth > 60 && (
                                      <text
                                        x={cellX + 12}
                                        y={barY + barHeight / 2}
                                        dominantBaseline="middle"
                                        fontSize={10}
                                        fill={isSuspended ? COLOR_DANGER : slotConfig.color}
                                        fontWeight={500}
                                        style={{ pointerEvents: 'none' }}
                                      >
                                        {slotConfig.label} {task.bookedSlots}/{task.totalSlots}
                                      </text>
                                    )}
                                  </g>
                                );
                              })
                            ) : (
                              !isRest && (
                                <text
                                  x={cellX + layout.cellWidth / 2}
                                  y={y + SVG_CONFIG.rowHeight / 2}
                                  textAnchor="middle"
                                  dominantBaseline="middle"
                                  fontSize={11}
                                  fill={token.colorTextQuaternary}
                                >
                                  -
                                </text>
                              )
                            )}
                          </g>
                        );
                      })}
                    </g>
                  );
                })}
              </svg>
            </div>
          ) : (
            <Empty description="暂无排班数据，请调整筛选条件" style={{ padding: '60px 0' }} />
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
          const slotConfig = getSlotConfig(selectedTask.timeSlot);
          const statusConfig = STATUS_CONFIG[selectedTask.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG[1];
          return (
            <Descriptions column={1} bordered size="small" items={[
              { key: '0', label: '医生', children: selectedTask.doctorName },
              { key: '1', label: '科室', children: selectedTask.departmentName || '-' },
              { key: '2', label: '日期', children: selectedTask.date },
              { key: '3', label: '时段', children: <Tag color={slotConfig.color}>{slotConfig.label}</Tag> },
              { key: '4', label: '时间', children: `${selectedTask.startTime} - ${selectedTask.endTime}` },
              { key: '5', label: '总号源', children: selectedTask.totalSlots },
              { key: '6', label: '已预约', children: selectedTask.bookedSlots },
              { key: '7', label: '剩余', children: selectedTask.totalSlots - selectedTask.bookedSlots },
              { key: '8', label: '预约率', children: (
                <span style={{ color: selectedTask.progress >= 80 ? COLOR_DANGER : COLOR_SUCCESS }}>
                  {selectedTask.progress}%
                </span>
              ) },
              { key: '9', label: '状态', children: (
                <Badge status={statusConfig.color as any} text={statusConfig.text} />
              ) },
            ]} />
          );
        })()}
      </Drawer>
    </PageContainer>
  );
};

export default ScheduleGanttPage;
