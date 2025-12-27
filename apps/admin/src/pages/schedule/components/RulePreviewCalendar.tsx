import { Calendar, Badge, Tooltip, Spin, Alert } from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { useEffect, useState, useMemo } from 'react';
import { scheduleApi } from '@hospital/api';
import type { Schedule } from '@hospital/shared';
import { generateSchedulePreview, getDateInfo, splitTimeRange, WEEKDAY_MAP } from '@hospital/shared';

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
  showExisting = true,
}) => {
  const [loading, setLoading] = useState(false);
  const [scheduleData, setScheduleData] = useState<DaySchedules>({});
  const [currentMonth, setCurrentMonth] = useState<Dayjs>(dayjs());

  // 计算预览日期
  const previewDates = useMemo(() => {
    if (!weekdays.length || !scheduleMode) {
      return [];
    }

    const start = currentMonth.startOf('month').toDate();
    const end = currentMonth.endOf('month').toDate();

    return generateSchedulePreview(
      {
        weekdays,
        scheduleMode,
      },
      start,
      end
    );
  }, [weekdays, scheduleMode, currentMonth]);

  // 加载已有排班
  useEffect(() => {
    if (!doctorId || !showExisting) {
      setScheduleData({});
      return;
    }

    const loadSchedules = async () => {
      setLoading(true);
      try {
        const startDate = currentMonth.startOf('month').format('YYYY-MM-DD');
        const endDate = currentMonth.endOf('month').format('YYYY-MM-DD');

        const result = await scheduleApi.getList({
          doctorId,
          startDate,
          endDate,
          pageSize: 100,
        });

        // 按日期分组
        const grouped: DaySchedules = {};
        (result.data ?? []).forEach((schedule) => {
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
  }, [doctorId, currentMonth, showExisting]);

  const handlePanelChange = (date: Dayjs) => {
    setCurrentMonth(date);
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
                      const slots = splitTimeRange(startTime, endTime, slotCount);
                      return (
                        <div>
                          {slots.map(([slotStart, slotEnd], idx) => (
                            <div key={idx}>班次{idx + 1}: {slotStart}-{slotEnd}</div>
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

  return (
    <div>
      <Alert
        message={
          <span>
            当前日期：{dayjs().format('YYYY-MM-DD')}，
            为本月第<strong>{dateInfo.monthWeek}</strong>周，
            本周为本年<strong>{dateInfo.isOddWeek ? '奇数' : '偶数'}</strong>周（第{dateInfo.yearWeek}周）
          </span>
        }
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Spin spinning={loading}>
        <Calendar
          onPanelChange={handlePanelChange}
          cellRender={(date, info) => {
            if (info.type === 'date') {
              return dateCellRender(date);
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

