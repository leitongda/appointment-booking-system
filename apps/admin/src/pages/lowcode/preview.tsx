/** 低代码页面预览 */

import React, { useEffect, useState } from 'react';
import { useParams } from '@umijs/max';
import { Spin, Segmented, Button, Space, message } from 'antd';
import { MobileOutlined, TabletOutlined, DesktopOutlined, ReloadOutlined } from '@ant-design/icons';
import { lowcodeApi } from '@hospital/api';
import type { LowCodePage, LowCodeNode } from '@hospital/shared';

/** 设备尺寸预设 */
const deviceSizes: Record<string, { width: number; height: number; label: string }> = {
  mobile: { width: 375, height: 667, label: '手机' },
  tablet: { width: 768, height: 1024, label: '平板' },
  desktop: { width: 1200, height: 800, label: '桌面' },
};

/** 预览用的简化渲染器 — 不依赖全局 store */
function PreviewNodeRenderer({ node }: { node: LowCodeNode }) {
  const { componentName, props, children } = node;

  switch (componentName) {
    case 'Page':
      return (
        <div style={{ minHeight: 600, background: '#f5f5f5' }}>
          <div
            style={{
              height: 44,
              background: props.navigationBarBackgroundColor || '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderBottom: '1px solid #eee',
              fontSize: 17,
              fontWeight: 500,
            }}
          >
            {props.navigationBarTitleText || '页面标题'}
          </div>
          <div style={{ padding: '12px 0' }}>
            {children?.map((child) => (
              <PreviewNodeRenderer key={child.id} node={child} />
            ))}
          </div>
        </div>
      );

    case 'NutView':
      return (
        <div
          style={{
            padding: props.padding,
            margin: props.margin,
            backgroundColor: props.backgroundColor,
            borderRadius: props.borderRadius,
          }}
        >
          {children?.map((child) => (
            <PreviewNodeRenderer key={child.id} node={child} />
          ))}
        </div>
      );

    case 'NutText':
      return (
        <div
          style={{
            padding: '4px 12px',
            fontSize: props.fontSize,
            color: props.color,
            fontWeight: props.fontWeight,
            textAlign: props.textAlign,
          }}
        >
          {props.text || ''}
        </div>
      );

    case 'NutImage':
      return (
        <div style={{ padding: '4px 12px' }}>
          {props.src ? (
            <img
              src={props.src}
              alt=""
              style={{
                width: props.width,
                height: props.height,
                objectFit: props.fit,
                borderRadius: props.borderRadius,
                display: 'block',
              }}
            />
          ) : (
            <div
              style={{
                width: props.width,
                height: props.height || '120px',
                background: '#f0f0f0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#999',
                fontSize: 13,
              }}
            >
              图片占位
            </div>
          )}
        </div>
      );

    case 'NutButton':
      return (
        <div style={{ padding: '8px 12px' }}>
          <button
            style={{
              width: props.block ? '100%' : 'auto',
              height: 36,
              borderRadius: 6,
              border: 'none',
              background:
                props.type === 'primary' ? '#1677ff'
                : props.type === 'warning' ? '#ff9800'
                : props.type === 'danger' ? '#ff4d4f'
                : '#f5f5f5',
              color: props.type === 'primary' ? '#fff' : '#333',
              fontSize: 14,
              cursor: 'pointer',
              opacity: props.disabled ? 0.5 : 1,
            }}
            disabled={props.disabled}
          >
            {props.text || '按钮'}
          </button>
        </div>
      );

    case 'NutDivider':
      return (
        <div style={{ padding: '8px 12px' }}>
          <hr
            style={{
              border: 'none',
              borderTop: props.dashed ? '1px dashed #e5e5e5' : '1px solid #e5e5e5',
              margin: 0,
            }}
          />
        </div>
      );

    case 'NutSwiper':
      return (
        <div style={{ padding: '4px 12px' }}>
          <div
            style={{
              height: props.height || '200px',
              background: '#e8e8e8',
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#999',
              fontSize: 13,
            }}
          >
            轮播区域
          </div>
          {children?.map((child) => (
            <PreviewNodeRenderer key={child.id} node={child} />
          ))}
        </div>
      );

    case 'NutSwiperItem':
      return (
        <div>
          {children?.map((child) => (
            <PreviewNodeRenderer key={child.id} node={child} />
          ))}
        </div>
      );

    case 'NutCell':
      return (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px 16px',
            borderBottom: '1px solid #f5f5f5',
            background: '#fff',
          }}
        >
          <div>
            <div style={{ fontSize: 15, color: '#333' }}>{props.title || '标题'}</div>
            {props.description && (
              <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>{props.description}</div>
            )}
          </div>
          {props.isLink && <span style={{ color: '#ccc', fontSize: 12 }}>›</span>}
        </div>
      );

    case 'NutCard':
      return (
        <div
          style={{
            margin: '8px 12px',
            padding: 12,
            background: '#fff',
            borderRadius: 8,
            boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
          }}
        >
          <div style={{ fontSize: 16, fontWeight: 500, color: '#333' }}>{props.title || '卡片标题'}</div>
          {props.subTitle && <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>{props.subTitle}</div>}
          {props.description && <div style={{ fontSize: 13, color: '#666', marginTop: 8 }}>{props.description}</div>}
          {children && children.length > 0 && (
            <div style={{ marginTop: 8 }}>
              {children.map((child) => (
                <PreviewNodeRenderer key={child.id} node={child} />
              ))}
            </div>
          )}
        </div>
      );

    case 'NutRow':
      return (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: props.gutter || 0, padding: '4px 12px' }}>
          {children?.map((child) => (
            <PreviewNodeRenderer key={child.id} node={child} />
          ))}
        </div>
      );

    case 'NutCol':
      return (
        <div style={{ width: `${((props.span || 12) / 24) * 100}%`, flexShrink: 0, padding: '0 4px' }}>
          {children?.map((child) => (
            <PreviewNodeRenderer key={child.id} node={child} />
          ))}
        </div>
      );

    case 'NutTabs':
      return (
        <div>
          <div style={{ display: 'flex', borderBottom: '1px solid #eee', background: '#fff' }}>
            {children
              ?.filter((c) => c.componentName === 'NutTabPane')
              .map((child, idx) => (
                <div
                  key={child.id}
                  style={{
                    padding: '10px 16px',
                    fontSize: 14,
                    color: idx === 0 ? '#1677ff' : '#666',
                    borderBottom: idx === 0 ? '2px solid #1677ff' : '2px solid transparent',
                  }}
                >
                  {child.props.title || '标签'}
                </div>
              ))}
          </div>
          {children
            ?.filter((c) => c.componentName === 'NutTabPane')
            .map((child, idx) => (
              <div key={child.id} style={{ display: idx === 0 ? 'block' : 'none' }}>
                {child.children?.map((grandChild) => (
                  <PreviewNodeRenderer key={grandChild.id} node={grandChild} />
                ))}
              </div>
            ))}
        </div>
      );

    case 'NutTabPane':
      return null;

    case 'NutEmpty':
      return (
        <div style={{ textAlign: 'center', padding: '40px 0', color: '#999', fontSize: 13 }}>
          {props.description || '暂无数据'}
        </div>
      );

    default:
      return (
        <div style={{ padding: '8px 12px', color: '#999', fontSize: 12, fontStyle: 'italic' }}>
          [{componentName}]
        </div>
      );
  }
}

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
                <PreviewNodeRenderer node={page.schemaData as unknown as LowCodeNode} />
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
