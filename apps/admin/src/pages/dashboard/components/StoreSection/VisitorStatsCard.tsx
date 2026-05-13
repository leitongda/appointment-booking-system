import React from 'react';
import { ProCard, StatisticCard } from '@ant-design/pro-components';
import { EyeOutlined, UserOutlined } from '@ant-design/icons';
import type { StoreDashboardStats } from '@hospital/api';

const { Statistic } = StatisticCard;

interface VisitorStatsCardProps {
  stats: StoreDashboardStats['visitors'];
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
    <ProCard hoverable>
      <StatisticCard.Group>
        <Statistic
          title="今日PV"
          value={stats?.todayPV ?? 0}
          icon={<EyeOutlined style={{ fontSize: 24, color: '#1890ff' }} />}
        />
        <Statistic
          title="今日UV"
          value={stats?.todayUV ?? 0}
          icon={<UserOutlined style={{ fontSize: 24, color: '#52c41a' }} />}
        />
        <Statistic
          title="昨日PV"
          value={stats?.yesterdayPV ?? 0}
          icon={<EyeOutlined style={{ fontSize: 24, color: '#722ed1' }} />}
        />
        <Statistic
          title="昨日UV"
          value={stats?.yesterdayUV ?? 0}
          icon={<UserOutlined style={{ fontSize: 24, color: '#52c41a' }} />}
        />
        <Statistic
          title="PV周环比"
          value={pvGrowth.text}
          suffix={<span style={{ color: pvGrowth.color, fontSize: 12 }}>{pvRate !== null && pvRate !== undefined ? (pvRate >= 0 ? '↑' : '↓') : ''}</span>}
        />
        <Statistic
          title="UV周环比"
          value={uvGrowth.text}
          suffix={<span style={{ color: uvGrowth.color, fontSize: 12 }}>{uvRate !== null && uvRate !== undefined ? (uvRate >= 0 ? '↑' : '↓') : ''}</span>}
        />
      </StatisticCard.Group>
    </ProCard>
  );
};

export default VisitorStatsCard;
