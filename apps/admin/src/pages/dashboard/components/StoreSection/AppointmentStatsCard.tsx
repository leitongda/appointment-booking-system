import React from 'react';
import { ProCard } from '@ant-design/pro-components';
import { CalendarOutlined, CheckCircleOutlined } from '@ant-design/icons';
import type { StoreDashboardStats } from '@hospital/api';
import StatGrid from './StatGrid';

interface AppointmentStatsCardProps {
  stats?: StoreDashboardStats['appointments'];
}

const AppointmentStatsCard: React.FC<AppointmentStatsCardProps> = ({ stats }) => {
  return (
    <ProCard title="预约" hoverable className="store-section-card">
      <StatGrid
        items={[
          {
            key: 'today',
            title: '今日预约',
            value: stats?.todayCount ?? 0,
            icon: <CalendarOutlined />,
            tone: 'blue',
          },
          {
            key: 'yesterday',
            title: '昨日预约',
            value: stats?.yesterdayCount ?? 0,
            icon: <CalendarOutlined />,
            tone: 'purple',
          },
          {
            key: 'checkins',
            title: '累计签到',
            value: stats?.totalCheckins ?? 0,
            icon: <CheckCircleOutlined />,
            tone: 'green',
          },
        ]}
      />
    </ProCard>
  );
};

export default AppointmentStatsCard;
