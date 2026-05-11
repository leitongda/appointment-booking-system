import React, { useState, useEffect } from 'react';
import { Row, Col, Spin } from 'antd';
import { ProCard } from '@ant-design/pro-components';
import { useModel } from '@umijs/max';
import { statisticsApi } from '@hospital/api';
import type { StoreDashboardStats } from '@hospital/api';
import AppointmentStatsCard from './AppointmentStatsCard';
import UserStatsCard from './UserStatsCard';
import VisitorStatsCard from './VisitorStatsCard';
import CheckinQrcodeCard from './CheckinQrcodeCard';

const StoreSection: React.FC = () => {
  const { initialState } = useModel('@@initialState');
  const currentStore = initialState?.currentStore;
  const storeId = currentStore?.id;
  const storeName = currentStore?.name;

  const [loading, setLoading] = useState(false);
  const [storeStats, setStoreStats] = useState<StoreDashboardStats | null>(null);

  useEffect(() => {
    if (!storeId) return;
    const load = async () => {
      setLoading(true);
      try {
        const data = await statisticsApi.getStoreDashboardStats(storeId);
        setStoreStats(data);
      } catch {
        // 静默失败，不影响其他区域
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [storeId]);

  if (!storeId) return null;

  return (
    <ProCard title="门店专属区域" headerBordered style={{ marginBottom: 16 }}>
      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={18}>
            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <AppointmentStatsCard stats={storeStats?.appointments} />
              </Col>
              <Col xs={24} md={8}>
                <UserStatsCard stats={storeStats?.users} />
              </Col>
              <Col xs={24} md={8}>
                <VisitorStatsCard stats={storeStats?.visitors} />
              </Col>
            </Row>
          </Col>
          <Col xs={24} lg={6}>
            <CheckinQrcodeCard storeId={storeId} storeName={storeName} />
          </Col>
        </Row>
      </Spin>
    </ProCard>
  );
};

export default StoreSection;
