/** 低代码页面预览 */

import React, { useEffect, useState } from 'react';
import { useParams } from '@umijs/max';
import { Spin, Segmented, Button, Space, message } from 'antd';
import { MobileOutlined, TabletOutlined, DesktopOutlined, ReloadOutlined } from '@ant-design/icons';
import { lowcodeApi } from '@hospital/api';
import type { LowCodePage, LowCodeNode } from '@hospital/shared';
import { BaseRenderer } from './editor/components/BaseRenderer';

/** 设备尺寸预设 */
const deviceSizes: Record<string, { width: number; height: number; label: string }> = {
  mobile: { width: 375, height: 667, label: '手机' },
  tablet: { width: 768, height: 1024, label: '平板' },
  desktop: { width: 1200, height: 800, label: '桌面' },
};

/** 页面预览 */
const LowCodePreview: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [page, setPage] = useState<LowCodePage | null>(null);
  const [loading, setLoading] = useState(true);
  const [device, setDevice] = useState<string>('mobile');

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      setLoading(true);
      try {
        const data = await lowcodeApi.getPage(id);
        setPage(data);
      } catch {
        message.error('加载页面失败');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  const size = deviceSizes[device] || deviceSizes.mobile;

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* 工具栏 */}
      <div
        style={{
          height: 48,
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          background: '#fff',
        }}
      >
        <Space>
          <span style={{ fontWeight: 500 }}>页面预览</span>
          {page && <span style={{ color: '#999' }}>— {page.name}</span>}
        </Space>
        <Space>
          <Segmented
            value={device}
            onChange={(val) => setDevice(val as string)}
            options={[
              { label: '手机', value: 'mobile', icon: <MobileOutlined /> },
              { label: '平板', value: 'tablet', icon: <TabletOutlined /> },
              { label: '桌面', value: 'desktop', icon: <DesktopOutlined /> },
            ]}
          />
          <Button icon={<ReloadOutlined />} onClick={() => window.location.reload()}>
            刷新
          </Button>
        </Space>
      </div>

      {/* 预览区域 */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'flex-start',
          padding: 24,
          background: '#f0f2f5',
          overflow: 'auto',
        }}
      >
        <Spin spinning={loading}>
          <div
            style={{
              width: size.width,
              height: size.height,
              background: '#fff',
              borderRadius: 12,
              boxShadow: '0 2px 12px rgba(0,0,0,0.1)',
              overflow: 'hidden',
            }}
          >
            {page?.schemaData ? (
              <div style={{ width: '100%', height: '100%', overflow: 'auto' }}>
                <BaseRenderer node={page.schemaData as unknown as LowCodeNode} />
              </div>
            ) : (
              <div
                style={{
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#999',
                }}
              >
                暂无内容
              </div>
            )}
          </div>
        </Spin>
      </div>
    </div>
  );
};

export default LowCodePreview;
