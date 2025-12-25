import { Button, Segmented, Space } from 'antd';
import { LeftOutlined, RightOutlined, ReloadOutlined } from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import weekOfYear from 'dayjs/plugin/weekOfYear';
import type { ViewMode } from '../index';
import StatusLegend from './StatusLegend';

dayjs.extend(weekOfYear);

interface CalendarHeaderProps {
  viewMode: ViewMode;
  currentDate: Dayjs;
  onViewModeChange: (mode: ViewMode) => void;
  onDateChange: (date: Dayjs) => void;
  onRefresh: () => void;
}

const CalendarHeader: React.FC<CalendarHeaderProps> = ({
  viewMode,
  currentDate,
  onViewModeChange,
  onDateChange,
  onRefresh,
}) => {
  // 格式化日期显示
  const getDateDisplay = () => {
    if (viewMode === 'week') {
      const weekStart = currentDate.startOf('week');
      const weekEnd = currentDate.endOf('week');
      const year = weekStart.year();
      const month = weekStart.month() + 1;
      const weekOfYear = weekStart.week();
      return `${year}年${month}月 第${weekOfYear}周 (${weekStart.format('MM/DD')} - ${weekEnd.format('MM/DD')})`;
    } else {
      return currentDate.format('YYYY年MM月');
    }
  };

  // 上一周/月
  const handlePrev = () => {
    if (viewMode === 'week') {
      onDateChange(currentDate.subtract(1, 'week'));
    } else {
      onDateChange(currentDate.subtract(1, 'month'));
    }
  };

  // 下一周/月
  const handleNext = () => {
    if (viewMode === 'week') {
      onDateChange(currentDate.add(1, 'week'));
    } else {
      onDateChange(currentDate.add(1, 'month'));
    }
  };

  // 回到今天
  const handleToday = () => {
    onDateChange(dayjs());
  };

  return (
    <div className="calendar-header">
      <div className="header-left">
        <div className="date-navigation">
          <Button icon={<LeftOutlined />} onClick={handlePrev} />
          <div className="date-display">{getDateDisplay()}</div>
          <Button icon={<RightOutlined />} onClick={handleNext} />
        </div>
        <Button onClick={handleToday}>今天</Button>
      </div>

      <div className="header-right">
        <StatusLegend />
        <Space>
          <Segmented
            value={viewMode}
            onChange={(value) => onViewModeChange(value as ViewMode)}
            options={[
              { label: '周视图', value: 'week' },
              { label: '月视图', value: 'month' },
            ]}
          />
          <Button icon={<ReloadOutlined />} onClick={onRefresh}>
            刷新
          </Button>
        </Space>
      </div>
    </div>
  );
};

export default CalendarHeader;

