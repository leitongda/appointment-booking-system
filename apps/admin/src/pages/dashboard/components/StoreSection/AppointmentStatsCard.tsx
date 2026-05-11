import React from 'react';
import { ProCard, StatisticCard } from '@ant-design/pro-components';
import { CalendarOutlined, CheckCircleOutlined } from '@ant-design/icons';
import type { StoreDashboardStats } from '@hospital/api';

const { Statistic } = StatisticCard;

interface AppointmentStatsCardProps {
  stats: StoreDashboardStats['appointments'];
}

const AppointmentStatsCard: React.FC<AppointmentStatsCardProps> = ({ stats }) => {
  return (
    <ProCard hoverable>
      <StatisticCard.Group>
        <Statistic
          title="今日预约"
          value={stats?.todayCount ?? 0}
          icon={<CalendarOutlined style={{ fontSize: 24, color: '#1890ff' }} />}
        />
        <Statistic
          title="昨日预约"
          value={stats?.yesterdayCount ?? 0}
          icon={<CalendarOutlined style={{ fontSize: 24, color: '#722ed1' }} />}
        />
        <Statistic
          title="累计签到"
          value={stats?.totalCheckins ?? 0}
          icon={<CheckCircleOutlined style={{ fontSize: 24, color: '#52c41a' }} />}
        />
      </StatisticCard.Group>
    </ProCard>
  );
};

export default AppointmentStatsCard;
