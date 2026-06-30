import React from 'react';
import { ProCard } from '@ant-design/pro-components';
import { UserOutlined, TeamOutlined, RiseOutlined } from '@ant-design/icons';
import type { StoreDashboardStats } from '@hospital/api';
import StatGrid from './StatGrid';

interface UserStatsCardProps {
  stats?: StoreDashboardStats['users'];
}

const UserStatsCard: React.FC<UserStatsCardProps> = ({ stats }) => {
  const growthRate = stats?.weekGrowthRate;
  const growthText = growthRate !== null && growthRate !== undefined
    ? `${growthRate >= 0 ? '+' : ''}${growthRate.toFixed(1)}%`
    : '-';
  const growthColor = growthRate !== null && growthRate !== undefined
    ? growthRate >= 0 ? 'var(--color-success)' : '#f5222d'
    : 'var(--color-text-tertiary)';
  const growthArrow = growthRate !== null && growthRate !== undefined
    ? (growthRate >= 0 ? '↑' : '↓')
    : '';

  return (
    <ProCard title="用户" hoverable className="store-section-card">
      <StatGrid
        items={[
          { key: 'total', title: '总用户', value: stats?.total ?? 0, icon: <TeamOutlined />, tone: 'purple' },
          { key: 'today', title: '今日新增', value: stats?.todayNew ?? 0, icon: <UserOutlined />, tone: 'blue' },
          { key: 'yesterday', title: '昨日新增', value: stats?.yesterdayNew ?? 0, icon: <UserOutlined />, tone: 'green' },
          { key: 'week', title: '本周新增', value: stats?.weekNew ?? 0, icon: <RiseOutlined />, tone: 'orange' },
          { key: 'last-week', title: '上周新增', value: stats?.lastWeekNew ?? 0, icon: <RiseOutlined />, tone: 'orange' },
          {
            key: 'growth',
            title: '周环比',
            value: growthText,
            suffix: <span style={{ color: growthColor }}>{growthArrow}</span>,
            tone: growthRate !== null && growthRate !== undefined && growthRate < 0 ? 'red' : 'green',
          },
        ]}
      />
    </ProCard>
  );
};

export default UserStatsCard;
