import React from 'react';
import { ProCard } from '@ant-design/pro-components';
import { EyeOutlined, UserOutlined } from '@ant-design/icons';
import type { StoreDashboardStats } from '@hospital/api';
import StatGrid from './StatGrid';

interface VisitorStatsCardProps {
  stats?: StoreDashboardStats['visitors'];
}

const VisitorStatsCard: React.FC<VisitorStatsCardProps> = ({ stats }) => {
  const pvRate = stats?.pvWeekGrowthRate;
  const uvRate = stats?.uvWeekGrowthRate;

  const formatRate = (rate: number | undefined) => {
    if (rate === null || rate === undefined) return { text: '-', color: '#999' };
    return {
      text: `${rate >= 0 ? '+' : ''}${rate.toFixed(1)}%`,
      color: rate >= 0 ? '#52c41a' : '#f5222d',
    };
  };

  const pvGrowth = formatRate(pvRate);
  const uvGrowth = formatRate(uvRate);

  return (
    <ProCard title="访问" hoverable className="store-section-card">
      <StatGrid
        items={[
          { key: 'today-pv', title: '今日PV', value: stats?.todayPV ?? 0, icon: <EyeOutlined />, tone: 'blue' },
          { key: 'today-uv', title: '今日UV', value: stats?.todayUV ?? 0, icon: <UserOutlined />, tone: 'green' },
          { key: 'yesterday-pv', title: '昨日PV', value: stats?.yesterdayPV ?? 0, icon: <EyeOutlined />, tone: 'purple' },
          { key: 'yesterday-uv', title: '昨日UV', value: stats?.yesterdayUV ?? 0, icon: <UserOutlined />, tone: 'cyan' },
          {
            key: 'pv-growth',
            title: 'PV周环比',
            value: pvGrowth.text,
            suffix: <span style={{ color: pvGrowth.color }}>{pvRate !== null && pvRate !== undefined ? (pvRate >= 0 ? '↑' : '↓') : ''}</span>,
            tone: pvRate !== null && pvRate !== undefined && pvRate < 0 ? 'red' : 'green',
          },
          {
            key: 'uv-growth',
            title: 'UV周环比',
            value: uvGrowth.text,
            suffix: <span style={{ color: uvGrowth.color }}>{uvRate !== null && uvRate !== undefined ? (uvRate >= 0 ? '↑' : '↓') : ''}</span>,
            tone: uvRate !== null && uvRate !== undefined && uvRate < 0 ? 'red' : 'green',
          },
        ]}
      />
    </ProCard>
  );
};

export default VisitorStatsCard;
