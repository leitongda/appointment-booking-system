/**
 * GuideTourButton - 顶栏操作指引按钮
 *
 * 点击后弹出指引选择下拉，选择后开始引导。
 */
import { useState, useEffect, useCallback } from 'react';
import { Button, Dropdown, Empty, Spin, message } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { guideToursApi, type GuideTourItem } from '@hospital/api';
import { t } from '@/utils/locale';

export const GuideTourButton: React.FC = () => {
  const [tours, setTours] = useState<GuideTourItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);

  const fetchTours = useCallback(async () => {
    try {
      setLoading(true);
      const items = await guideToursApi.getActive();
      setTours(items || []);
    } catch (e) {
      console.error('[GuideTourButton] 加载指引失败:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open && tours.length === 0) {
      fetchTours();
    }
  }, [open, tours.length, fetchTours]);

  const handleStartTour = (tour: GuideTourItem) => {
    // 通过 URL 参数触发指引，由 GuidedTour 组件监听
    const url = new URL(window.location.href);
    url.searchParams.set('guide', tour.code);
    window.history.replaceState({}, '', url.toString());
    // 触发 popstate 事件让 Umi 路由响应
    window.dispatchEvent(new PopStateEvent('popstate'));
    setOpen(false);
    message.info(`正在启动：${t(tour.title)}`);
  };

  const pendingTours = tours.filter((tour) => tour.progressStatus !== 1);

  return (
    <Dropdown
      open={open}
      onOpenChange={setOpen}
      dropdownRender={() => (
        <div style={{ width: 240, background: '#fff', borderRadius: 8, boxShadow: '0 6px 16px rgba(0,0,0,0.08)', padding: 8 }}>
          <div style={{ padding: '8px 12px', fontWeight: 600, fontSize: 14, borderBottom: '1px solid #f0f0f0', marginBottom: 4 }}>
            操作指引
          </div>
          {loading ? (
            <div style={{ padding: 16, textAlign: 'center' }}><Spin size="small" /></div>
          ) : pendingTours.length === 0 ? (
            <Empty description="暂无可用指引" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ padding: '16px 0' }} />
          ) : (
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {pendingTours.map((tour) => (
                <div
                  key={tour.id}
                  onClick={() => handleStartTour(tour)}
                  style={{
                    padding: '8px 12px',
                    cursor: 'pointer',
                    borderRadius: 4,
                    transition: 'background 0.2s',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = '#f5f5f5')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <div style={{ fontWeight: 500, fontSize: 13 }}>{t(tour.title)}</div>
                  {tour.description && (
                    <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>{t(tour.description)}</div>
                  )}
                  <div style={{ fontSize: 11, color: '#bbb', marginTop: 2 }}>
                    {tour.steps.length} 步 · {tour.currentStep > 0 ? `进行到第 ${tour.currentStep + 1} 步` : '未开始'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      trigger={['click']}
      placement="bottomRight"
    >
      <Button type="text" icon={<QuestionCircleOutlined />} style={{ color: '#666' }}>
        操作指引
      </Button>
    </Dropdown>
  );
};

export default GuideTourButton;
