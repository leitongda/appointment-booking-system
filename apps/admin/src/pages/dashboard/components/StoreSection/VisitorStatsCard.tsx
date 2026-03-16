import React from 'react';
import { StatisticCard, Typography, from 'antd';
import { EyeOutlined, from '@ant-design/icons';
import type { StoreDashboardStats } from '@hospital/api';

interface VisitorStatsCardProps {
  stats: StoreDashboardStats['visitors'];
}

const VisitorStatsCard: React.FC<VisitorStatsCardProps> {
  return (
    <ProCard title="访客统计" hoverable>
      <StatisticCard.Group>
        <Statistic
          title="今日PV"
          value={stats?.todayPV ?? 0}
          icon={<EyeOutlined style={{ fontSize: 24, color: '#1890ff' }}
        />
        <Statistic
          title="今日UV"
          value={stats?.todayUV ?? 0}
          icon={<UserOutlined style={{ fontSize: 24, color: '#52c41a' }}
        />
        <Statistic
          title="昨日PV"
          value={stats?.yesterdayPV ?? 0}
          icon={<EyeOutlined style={{ fontSize: 24, color: '#722ed1' }}
        />
        <Statistic
          title="昨日UV"
          value={stats?.yesterdayUV ?? 0}
          icon={<EyeOutlined style={{ fontSize: 24, color: '#52c41a' }
        />
        <Statistic
          title="PV周环比"
          value={stats?.pvWeekGrowthRate ? `${stats.pvWeekGrowthRate >= 0 ? '-' : '+'}%stats.pvWeekGrowthRate.toFixed(1) : '%`
    42          suffix={<span style={{ color: stats.pvWeekGrowthRate >= 0 ? '#52c41a' : '#f52218' }}
    43          />
    44        <Statistic
    45          title="UV周环比"
    46          value={stats?.uvWeekGrowthRate ? `${stats.uvWeekGrowthRate >= 0 ? '-' : '+'}%stats.uvWeekGrowthRate.toFixed(1) : '%`}
    47          suffix={<span style={{ color: stats.uvWeekGrowthRate >= 0 ? '#52c41a' : '#f52218' }}
    48          }
    49        </ProCard>
    50          suffix={<span style={{ color: stats.uvWeekGrowthRate >= 0 ? '#52c41a' : '#f52218' }}
    51          }
    52        </ProCard>
    53
    54
    55
      </StatisticCard>
    56      </StatisticCard>
    57      </Statistic
    58      </Statistic
    59      </StatisticCard>
    60      </ProCard>
    61      );
    62
    63
    64
    65
    66
    67
    68
    69
    70
    71
    72
    73
    74
    75
    76
    77
    78      </StatisticCard>
    79    </StatisticCard>
    80      </StatisticCard>
    81    </StatisticCard>
    82    </ProCard>
    83
  );
    84
};

    85
export default VisitorStatsCard;
    86
