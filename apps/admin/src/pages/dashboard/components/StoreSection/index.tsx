import React, { useState, useEffect, useRef } from 'react';
import { Row, Col, Spin } from 'antd';
import { ProCard } from '@ant-design/pro-components';
import { useModel } from '@umijs/max';
import { statisticsApi } from '@hospital/api';
import type { StoreDashboardStats } from '@hospital/api';
import AppointmentStatsCard from './AppointmentStatsCard';
import UserStatsCard from './UserStatsCard';
import VisitorStatsCard from './VisitorStatsCard';
import CheckinQrcodeCard from './CheckinQrcodeCard';
import './index.less';

const StoreSection: React.FC = () => {
  const { initialState } = useModel('@@initialState');
  const currentStore = initialState?.currentStore;
  const storeId = currentStore?.id;
  const storeName = currentStore?.name;

  const [loading, setLoading] = useState(false);
  const [storeStats, setStoreStats] = useState<StoreDashboardStats | null>(null);

  // 并发锁:storeId 抖动时避免叠加请求
  const loadingRef = useRef(false);

  useEffect(() => {
    if (!storeId) return;
    const load = async () => {
      if (loadingRef.current) return;
      loadingRef.current = true;
      setLoading(true);
      try {
        const data = await statisticsApi.getStoreDashboardStats(storeId);
        setStoreStats(data);
      } catch {
        // 静默失败，不影响其他区域
      } finally {
        setLoading(false);
        loadingRef.current = false;
      }
    };
    load();
  }, [storeId]);

  if (!storeId) return null;

  return (
    <ProCard title="门店专属区域" headerBordered className="store-section">
      <Spin spinning={loading}>
        <Row gutter={[16, 16]} className="store-section-grid">
          <Col xs={24} lg={18} className="store-section-main">
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
          <Col xs={24} lg={6} className="store-section-qr">
            <CheckinQrcodeCard storeId={storeId} storeName={storeName} />
          </Col>
        </Row>
      </Spin>
    </ProCard>
  );
};

export default StoreSection;
