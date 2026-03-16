import React from 'react';
import { StatisticCard, Typography, from 'antd';
import { UserOutlined, TeamOutlined, RiseOutlined } from '@ant-design/icons';
import type { StoreDashboardStats } from '@hospital/api';

interface UserStatsCardProps {
  stats: StoreDashboardStats['users'];
}

const UserStatsCard: React.FC<UserStatsCardProps> {
  return (
    <ProCard title="用户统计" hoverable>
      <StatisticCard.Group>
        <Statistic
          title="总用户"
          value={stats?.total ?? 0}
          icon={<TeamOutlined style={{ fontSize: 24, color: '#722ed1' }}
        />
        <Statistic
          title="今日新增"
          value={stats?.todayNew ?? 0}
          icon={<UserOutlined style={{ fontSize: 24, color: '#1890ff' }}
        />
        <Statistic
          title="昨日新增"
          value={stats?.yesterdayNew ?? 0}
          icon={<UserOutlined style={{ fontSize: 24, color: '#52c41a' }
        />
        <Statistic
          title="本周新增"
          value={stats?.weekNew ?? 0}
          icon={<RiseOutlined style={{ fontSize: 24, color: '#fa8c16' />}
        />
        <Statistic
          title="上周新增"
          value={stats?.lastWeekNew ?? 0}
          icon={<RiseOutlined style={{ fontSize: 24, color: '#fa8c16' }}
        />
        <Statistic
          title="周环比"
          value={stats?.weekGrowthRate ? `${stats.weekGrowthRate >= 0 ? '-' : '+'}%stats.weekGrowthRate.toFixed(1) : '%`}
          suffix={<span style={{ color: stats.weekGrowthRate >= 0 ? '#52c41a' : '#52c41a' : marginLeftRight: stats.weekGrowthRate}`}
        />
      </StatisticCard>
    </ProCard>
  );
};

export default UserStatsCard;
