import { Card, Skeleton, Space } from 'antd';
import type { FC } from 'react';

interface ListPageSkeletonProps {
  filterCount?: number;
  rowCount?: number;
}

const ListPageSkeleton: FC<ListPageSkeletonProps> = ({
  filterCount = 4,
  rowCount = 6,
}) => {
  return (
    <Card bordered={false}>
      <Space wrap size={12} style={{ width: '100%', marginBottom: 24 }}>
        {Array.from({ length: filterCount }).map((_, index) => (
          <Skeleton.Input
            key={index}
            active
            size="small"
            style={{ width: index === 0 ? 200 : 160 }}
          />
        ))}
      </Space>

      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 24 }}>
        <Skeleton.Input active style={{ width: 160, height: 32 }} />
        <div style={{ display: 'flex', gap: 12 }}>
          <Skeleton.Input active style={{ width: 120, height: 32 }} />
          <Skeleton.Input active style={{ width: 96, height: 32 }} />
        </div>
      </div>

      <div style={{ display: 'grid', gap: 12 }}>
        {Array.from({ length: rowCount }).map((_, index) => (
          <Skeleton
            key={index}
            active
            title={false}
            paragraph={{ rows: 1, width: ['18%', '14%', '12%', '16%', '10%', '12%', '12%'] }}
          />
        ))}
      </div>
    </Card>
  );
};

export default ListPageSkeleton;
