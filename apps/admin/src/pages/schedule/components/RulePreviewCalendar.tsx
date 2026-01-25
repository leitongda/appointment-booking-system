import { Calendar, Badge, Tooltip, Spin, Alert, Button, Space } from 'antd';
import { LeftOutlined, RightOutlined } from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';

dayjs.extend(isSameOrAfter);
dayjs.extend(isSameOrBefore);
import { useEffect, useState, useMemo } from 'react';
import { scheduleApi } from '@hospital/api';
import type { Schedule, BreakTime } from '@hospital/shared';
import { fetchAllData } from '@/utils/fetchAllData';
import { 
  generateSchedulePreview, 
  getDateInfo, 
  splitTimeRangeWithBreaks,
  getPeriodNameFromTime,
  calculateWorkingDuration,
  formatDuration,
} from '@hospital/shared';

// 时间格式验证正则：HH:mm
const TIME_FORMAT_REGEX = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/;

interface RulePreviewCalendarProps {
  /** 医生ID */
  doctorId?: string;
  /** 星期数组 */
  weekdays?: number[];
  /** 排班方式 */
  scheduleMode?: string;
  /** 开始时间 */
  startTime?: string;
  /** 结束时间 */
  endTime?: string;
  /** 班次数量 */
  slotCount?: number;
  /** 排除时间段 */
  breakTimes?: BreakTime[];
  /** 是否显示已有排班 */
  showExisting?: boolean;
}

interface DaySchedules {
  [date: string]: Schedule[];
}

const RulePreviewCalendar: React.FC<RulePreviewCalendarProps> = ({
  doctorId,
  weekdays = [],
  scheduleMode = 'weekly',
  startTime,
  endTime,
  slotCount = 1,
  breakTimes = [],
  showExisting = true,
}) => {
  const [loading, setLoading] = useState(false);
  const [scheduleData, setScheduleData] = useState<DaySchedules>({});
  const [currentDate, setCurrentDate] = useState<Dayjs>(dayjs());
  const [panelMode, setPanelMode] = useState<'month' | 'year'>('month');

  // 计算预览日期（根据当前面板模式计算不同范围）
  const previewDates = useMemo(() => {
    if (!weekdays.length || !scheduleMode) {
      return [];
    }

    let start: Date;
    let end: Date;
    
    if (panelMode === 'year') {
      // 年视图：计算整年
      start = currentDate.startOf('year').toDate();
      end = currentDate.endOf('year').toDate();
    } else {
      // 月视图：计算当月
      start = currentDate.startOf('month').toDate();
      end = currentDate.endOf('month').toDate();
    }

    return generateSchedulePreview(
      {
        weekdays,
        scheduleMode,
      },
      start,
      end
    );
  }, [weekdays, scheduleMode, currentDate, panelMode]);

  // 导航到上一个月/年
  const handlePrev = () => {
    if (panelMode === 'year') {
      setCurrentDate(currentDate.subtract(1, 'year'));
    } else {
      setCurrentDate(currentDate.subtract(1, 'month'));
    }
  };

  // 导航到下一个月/年
  const handleNext = () => {
    if (panelMode === 'year') {
      setCurrentDate(currentDate.add(1, 'year'));
    } else {
      setCurrentDate(currentDate.add(1, 'month'));
    }
  };

  // 计算每日工作时长
  const dailyDuration = useMemo(() => {
    if (!startTime || !endTime || !TIME_FORMAT_REGEX.test(startTime) || !TIME_FORMAT_REGEX.test(endTime)) {
      return 0;
    }
    return calculateWorkingDuration(startTime, endTime, breakTimes);
  }, [startTime, endTime, breakTimes]);

  // 加载已有排班
  useEffect(() => {
    if (!doctorId || !showExisting) {
      setScheduleData({});
      return;
    }

    const loadSchedules = async () => {
      setLoading(true);
      try {
        let startDate: string;
        let endDate: string;

        if (panelMode === 'year') {
          startDate = currentDate.startOf('year').format('YYYY-MM-DD');
          endDate = currentDate.endOf('year').format('YYYY-MM-DD');
        } else {
          startDate = currentDate.startOf('month').format('YYYY-MM-DD');
          endDate = currentDate.endOf('month').format('YYYY-MM-DD');
        }

        // 年视图可能超过100条记录，使用分页加载；月视图100条足够
        const schedules = panelMode === 'year'
          ? await fetchAllData((page, pageSize) =>
              scheduleApi.getList({ doctorId, startDate, endDate, page, pageSize })
            )
          : (await scheduleApi.getList({ doctorId, startDate, endDate, pageSize: 100 })).data ?? [];

        // 按日期分组
        const grouped: DaySchedules = {};
        schedules.forEach((schedule) => {
          const date = schedule.scheduleDate;
          if (!grouped[date]) {
            grouped[date] = [];
          }
          grouped[date].push(schedule);
        });

        setScheduleData(grouped);
      } catch (error) {
        console.error('加载排班失败', error);
      } finally {
        setLoading(false);
      }
    };

    loadSchedules();
  }, [doctorId, currentDate, showExisting, panelMode]);

  const handlePanelChange = (date: Dayjs, mode: 'month' | 'year') => {
    setCurrentDate(date);
    setPanelMode(mode);
  };

  const dateInfo = useMemo(() => getDateInfo(new Date()), []);

  const dateCellRender = (date: Dayjs) => {
    const dateStr = date.format('YYYY-MM-DD');
    const existingSchedules = scheduleData[dateStr] || [];
    const isPreviewDate = previewDates.some(
      (d) => dayjs(d).format('YYYY-MM-DD') === dateStr
    );

    const items: Array<{ type: string; content: string }> = [];

    // 已有排班
    if (existingSchedules.length > 0) {
      items.push({
        type: 'success',
        content: `已有${existingSchedules.length}个班次`,
      });
    }

    // 预览排班
    if (isPreviewDate) {
      items.push({
        type: 'processing',
        content: `将生成${slotCount}个班次`,
      });
    }

    if (items.length === 0) {
      return null;
    }

    return (
      <div style={{ fontSize: 12 }}>
        {items.map((item, index) => (
          <Tooltip
            key={index}
            title={
              <div>
                {item.type === 'success' && (
                  <div>
                    <div>已有排班：</div>
                    {existingSchedules.map((s) => (
                      <div key={s.id}>
                        {s.startTime}-{s.endTime} ({s.bookedSlots}/{s.totalSlots})
                      </div>
                    ))}
                  </div>
                )}
                {item.type === 'processing' && (
                  <div>
                    <div>将生成排班：</div>
                    {startTime && endTime && slotCount > 0 && TIME_FORMAT_REGEX.test(startTime) && TIME_FORMAT_REGEX.test(endTime) && (() => {
                      // 使用考虑排除时间的函数
                      const slots = splitTimeRangeWithBreaks(startTime, endTime, slotCount, breakTimes);
                      
                      // 按时段分组
                      const groupedByPeriod: Record<string, Array<[string, string]>> = {};
                      slots.forEach(([slotStart, slotEnd]) => {
                        const periodName = getPeriodNameFromTime(slotStart);
                        if (!groupedByPeriod[periodName]) {
                          groupedByPeriod[periodName] = [];
                        }
                        groupedByPeriod[periodName].push([slotStart, slotEnd]);
                      });
                      
                      return (
                        <div>
                          {Object.entries(groupedByPeriod).map(([period, periodSlots]) => (
                            <div key={period} style={{ marginBottom: 4 }}>
                              <div style={{ fontWeight: 'bold', color: '#1890ff' }}>{period}：</div>
                              {periodSlots.map(([slotStart, slotEnd], idx) => (
                                <div key={idx} style={{ paddingLeft: 8 }}>
                                  {slotStart}-{slotEnd}
                                </div>
                              ))}
                            </div>
                          ))}
                        </div>
                      );
                    })()}
                    {(!startTime || !endTime || !TIME_FORMAT_REGEX.test(startTime) || !TIME_FORMAT_REGEX.test(endTime)) && (
                      <div style={{ color: '#ff4d4f' }}>请设置有效的开始时间和结束时间</div>
                    )}
                  </div>
                )}
              </div>
            }
          >
            <div style={{ marginBottom: 2 }}>
              <Badge status={item.type as any} text={item.content} />
            </div>
          </Tooltip>
        ))}
      </div>
    );
  };

  // 年视图的月份单元格渲染
  const monthCellRender = (date: Dayjs) => {
    const monthStart = date.startOf('month');
    const monthEnd = date.endOf('month');
    
    // 统计该月已有排班数
    let existingCount = 0;
    Object.keys(scheduleData).forEach(dateStr => {
      const d = dayjs(dateStr);
      if (d.isSameOrAfter(monthStart, 'day') && d.isSameOrBefore(monthEnd, 'day')) {
        existingCount += scheduleData[dateStr].length;
      }
    });

    // 统计该月预览排班数
    const previewCount = previewDates.filter(d => {
      const pd = dayjs(d);
      return pd.isSameOrAfter(monthStart, 'day') && pd.isSameOrBefore(monthEnd, 'day');
    }).length;

    if (existingCount === 0 && previewCount === 0) {
      return null;
    }

    return (
      <div style={{ fontSize: 12, padding: '4px 0' }}>
        {existingCount > 0 && (
          <div style={{ marginBottom: 2 }}>
            <Badge status="success" text={`已有${existingCount}个班次`} />
          </div>
        )}
        {previewCount > 0 && (
          <div>
            <Badge status="processing" text={`将生成${previewCount * slotCount}个班次`} />
          </div>
        )}
      </div>
    );
  };

  return (
    <div>
      <Alert
        message={
          <span>
            当前日期：{dayjs().format('YYYY-MM-DD')}，
            为本月第<strong>{dateInfo.monthWeek}</strong>周，
            本周为本年<strong>{dateInfo.isOddWeek ? '奇数' : '偶数'}</strong>周（第{dateInfo.yearWeek}周）
            {dailyDuration > 0 && (
              <>
                <span style={{ marginLeft: 16 }}>|</span>
                <span style={{ marginLeft: 16 }}>
                  每日总时长：<strong>{formatDuration(dailyDuration)}</strong>
                  {breakTimes.length > 0 && (
                    <span style={{ color: '#999', marginLeft: 4 }}>
                      (已排除{breakTimes.length}个时间段)
                    </span>
                  )}
                </span>
              </>
            )}
          </span>
        }
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Spin spinning={loading}>
        <Calendar
          value={currentDate}
          onPanelChange={handlePanelChange}
          headerRender={({ value, type, onChange, onTypeChange }) => {
            const year = value.year();
            const month = value.month();
            const displayText = type === 'year' 
              ? `${year}年` 
              : `${year}年${month + 1}月`;

            return (
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                padding: '8px 16px',
                marginBottom: 8,
              }}>
                <Space>
                  <Button 
                    icon={<LeftOutlined />}
                    onClick={handlePrev}
                    size="small"
                  />
                  <span style={{ 
                    fontWeight: 600, 
                    fontSize: 16,
                    minWidth: 120,
                    textAlign: 'center',
                    display: 'inline-block',
                  }}>
                    {displayText}
                  </span>
                  <Button 
                    icon={<RightOutlined />}
                    onClick={handleNext}
                    size="small"
                  />
                </Space>
                <Space>
                  <Button
                    size="small"
                    type={type === 'month' ? 'primary' : 'default'}
                    onClick={() => onTypeChange('month')}
                  >
                    月
                  </Button>
                  <Button
                    size="small"
                    type={type === 'year' ? 'primary' : 'default'}
                    onClick={() => onTypeChange('year')}
                  >
                    年
                  </Button>
                </Space>
              </div>
            );
          }}
          cellRender={(date, info) => {
            if (info.type === 'date') {
              return dateCellRender(date);
            }
            if (info.type === 'month') {
              return monthCellRender(date);
            }
            return null;
          }}
          style={{
            background: '#fff',
            borderRadius: 8,
            padding: 16,
          }}
        />
      </Spin>

      <div style={{ marginTop: 16, fontSize: 12, color: '#666' }}>
        <div>
          <Badge status="success" text="已有排班" /> - 蓝色标记
        </div>
        <div>
          <Badge status="processing" text="将生成排班" /> - 绿色标记
        </div>
      </div>
    </div>
  );
};

export default RulePreviewCalendar;
