import React from 'react';
import { ProCard, StatisticCard } from '@ant-design/pro-components';
import { UserOutlined, TeamOutlined, RiseOutlined } from '@ant-design/icons';
import type { StoreDashboardStats } from '@hospital/api';

const { Statistic } = StatisticCard;

interface UserStatsCardProps {
  stats: StoreDashboardStats['users'];
}

const UserStatsCard: React.FC<UserStatsCardProps> = ({ stats }) => {
  const growthRate = stats?.weekGrowthRate;
  const growthText = growthRate !== null && growthRate !== undefined
    ? `${growthRate >= 0 ? '+' : ''}${growthRate.toFixed(1)}%`
    : '-';
  const growthColor = growthRate !== null && growthRate !== undefined
    ? growthRate >= 0 ? '#52c41a' : '#f5222d'
    : '#999';

  return (
    <ProCard hoverable>
      <StatisticCard.Group>
        <Statistic
          title="总用户"
          value={stats?.total ?? 0}
          icon={<TeamOutlined style={{ fontSize: 24, color: '#722ed1' }} />}
        />
        <Statistic
          title="今日新增"
          value={stats?.todayNew ?? 0}
          icon={<UserOutlined style={{ fontSize: 24, color: '#1890ff' }} />}
        />
        <Statistic
          title="昨日新增"
          value={stats?.yesterdayNew ?? 0}
          icon={<UserOutlined style={{ fontSize: 24, color: '#52c41a' }} />}
        />
        <Statistic
          title="本周新增"
          value={stats?.weekNew ?? 0}
          icon={<RiseOutlined style={{ fontSize: 24, color: '#fa8c16' }} />}
        />
        <Statistic
          title="上周新增"
          value={stats?.lastWeekNew ?? 0}
          icon={<RiseOutlined style={{ fontSize: 24, color: '#fa8c16' }} />}
        />
        <Statistic
          title="周环比"
          value={growthText}
          suffix={<span style={{ color: growthColor, fontSize: 12 }}>{growthRate !== null && growthRate !== undefined ? (growthRate >= 0 ? '↑' : '↓') : ''}</span>}
        />
      </StatisticCard.Group>
    </ProCard>
  );
};

export default UserStatsCard;
