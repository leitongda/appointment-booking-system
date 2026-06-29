/**
 * BaseRenderer - 共享渲染逻辑
 *
 * 提供核心组件渲染逻辑，供编辑器和预览页面共用。
 * 不包含编辑器特有功能（拖拽、选中、右键菜单）。
 */

import React from 'react';
import type { LowCodeNode } from '@hospital/shared';

/** URL 校验：仅允许 http/https/data 协议 */
export function isValidImageUrl(url: string): boolean {
  if (!url) return false;
  try {
    const parsed = new URL(url, window.location.origin);
    return ['http:', 'https:', 'data:'].includes(parsed.protocol);
  } catch {
    return !url.startsWith('javascript:') && !url.startsWith('vbscript:');
  }
}

/** 渲染器属性 */
export interface BaseRendererProps {
  node: LowCodeNode;
  /** 子节点渲染器（允许外部注入，支持递归） */
  renderChild?: (node: LowCodeNode, depth: number) => React.ReactNode;
  /** 当前深度 */
  depth?: number;
}

/** 基础组件渲染 — 不含编辑器交互逻辑 */
export function renderBaseComponent(
  node: LowCodeNode,
  renderChild: (node: LowCodeNode, depth: number) => React.ReactNode,
  depth: number,
): React.ReactNode {
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
            {children?.map((child) => renderChild(child, depth + 1))}
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
            minHeight: 40,
          }}
        >
          {children?.map((child) => renderChild(child, depth + 1))}
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
          {props.src && isValidImageUrl(props.src) ? (
            <img
              src={props.src}
              alt={props.alt || '图片'}
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
                borderRadius: props.borderRadius,
              }}
            >
              {props.src ? '无效图片链接' : '图片占位'}
            </div>
          )}
        </div>
      );

    case 'NutButton':
      return (
        <div style={{ padding: '8px 12px' }}>
          <button
            type="button"
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
          {children?.map((child) => renderChild(child, depth + 1))}
        </div>
      );

    case 'NutSwiperItem':
      return (
        <div>
          {children?.map((child) => renderChild(child, depth + 1))}
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
              {children.map((child) => renderChild(child, depth + 1))}
            </div>
          )}
        </div>
      );

    case 'NutRow':
      return (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: props.gutter || 0, padding: '4px 12px' }}>
          {children?.map((child) => renderChild(child, depth + 1))}
        </div>
      );

    case 'NutCol':
      return (
        <div style={{ width: `${((props.span || 12) / 24) * 100}%`, flexShrink: 0, padding: '0 4px' }}>
          {children?.map((child) => renderChild(child, depth + 1))}
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
                {child.children?.map((grandChild) => renderChild(grandChild, depth + 1))}
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

    case 'NutInput':
      return (
        <div style={{ padding: '8px 12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
            {props.label && (
              <span style={{ fontSize: 14, color: '#333', minWidth: 60 }}>
                {props.required && <span style={{ color: '#ff4d4f', marginRight: 4 }}>*</span>}
                {props.label}
              </span>
            )}
            <input
              type="text"
              placeholder={props.placeholder || '请输入'}
              disabled={props.disabled}
              readOnly={props.readOnly}
              maxLength={props.maxLength > 0 ? props.maxLength : undefined}
              style={{
                flex: 1,
                height: 32,
                border: '1px solid #e5e5e5',
                borderRadius: 4,
                padding: '0 8px',
                fontSize: 14,
                color: '#333',
                textAlign: props.textAlign,
                background: props.disabled ? '#f5f5f5' : '#fff',
                outline: 'none',
              }}
            />
          </div>
        </div>
      );

    case 'NutTextarea':
      return (
        <div style={{ padding: '8px 12px' }}>
          <div style={{ marginBottom: 4 }}>
            {props.label && (
              <span style={{ fontSize: 14, color: '#333' }}>
                {props.required && <span style={{ color: '#ff4d4f', marginRight: 4 }}>*</span>}
                {props.label}
              </span>
            )}
          </div>
          <textarea
            placeholder={props.placeholder || '请输入'}
            disabled={props.disabled}
            readOnly={props.readOnly}
            rows={props.rows || 3}
            maxLength={props.maxLength > 0 ? props.maxLength : undefined}
            style={{
              width: '100%',
              border: '1px solid #e5e5e5',
              borderRadius: 4,
              padding: '8px',
              fontSize: 14,
              color: '#333',
              resize: props.autosize ? 'vertical' : 'none',
              background: props.disabled ? '#f5f5f5' : '#fff',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>
      );

    case 'NutSwitch':
      return (
        <div style={{ padding: '8px 12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            {props.label && <span style={{ fontSize: 14, color: '#333' }}>{props.label}</span>}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {props.activeText && <span style={{ fontSize: 12, color: '#333' }}>{props.activeText}</span>}
              <div
                style={{
                  width: 44,
                  height: 24,
                  borderRadius: 12,
                  background: props.checked ? '#1677ff' : '#e5e5e5',
                  position: 'relative',
                  cursor: props.disabled ? 'not-allowed' : 'pointer',
                  opacity: props.disabled ? 0.5 : 1,
                  transition: 'background 0.2s',
                }}
              >
                <div
                  style={{
                    width: 20,
                    height: 20,
                    borderRadius: 10,
                    background: '#fff',
                    position: 'absolute',
                    top: 2,
                    left: props.checked ? 22 : 2,
                    transition: 'left 0.2s',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                  }}
                />
              </div>
              {props.inactiveText && <span style={{ fontSize: 12, color: '#999' }}>{props.inactiveText}</span>}
            </div>
          </div>
        </div>
      );

    case 'NutPicker':
      return (
        <div style={{ padding: '8px 12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
            {props.label && (
              <span style={{ fontSize: 14, color: '#333', minWidth: 60 }}>
                {props.required && <span style={{ color: '#ff4d4f', marginRight: 4 }}>*</span>}
                {props.label}
              </span>
            )}
            <div
              style={{
                flex: 1,
                height: 32,
                border: '1px solid #e5e5e5',
                borderRadius: 4,
                padding: '0 8px',
                fontSize: 14,
                color: '#999',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                background: props.disabled ? '#f5f5f5' : '#fff',
              }}
            >
              <span>{props.placeholder || '请选择'}</span>
              <span style={{ fontSize: 12, color: '#ccc' }}>▼</span>
            </div>
          </div>
        </div>
      );

    case 'NutForm':
      return (
        <div
          style={{
            padding: props.border ? '12px' : '8px 0',
            border: props.border ? '1px solid #e5e5e5' : 'none',
            borderRadius: props.border ? 4 : 0,
            minHeight: 40,
          }}
        >
          {children?.map((child) => renderChild(child, depth + 1))}
        </div>
      );

    case 'NutCheckbox':
      return (
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
          <input type="checkbox" style={{ width: 16, height: 16 }} />
          <span style={{ fontSize: 14 }}>{props.label || '选项'}</span>
        </label>
      );

    case 'NutRadio':
      return (
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
          <input type="radio" name={props.group || 'default'} style={{ width: 16, height: 16 }} />
          <span style={{ fontSize: 14 }}>{props.label || '选项'}</span>
        </label>
      );

    case 'NutDatePicker':
      return (
        <input
          type="date"
          defaultValue={props.value || ''}
          style={{ padding: '6px 12px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 14 }}
          readOnly
        />
      );

    case 'NutCalendar':
      return (
        <div style={{ border: '1px solid #eee', borderRadius: 8, padding: 12, textAlign: 'center', color: '#999', fontSize: 12 }}>
          [日历组件]
        </div>
      );

    case 'NutSearchBar':
      return (
        <div style={{ padding: '8px 12px', background: '#f5f5f5', borderRadius: 16 }}>
          <input
            placeholder={props.placeholder || '搜索'}
            style={{ width: '100%', border: 'none', background: 'transparent', outline: 'none', fontSize: 14 }}
            readOnly
          />
        </div>
      );

    case 'NutNavBar':
      return (
        <div style={{ height: 44, borderBottom: '1px solid #eee', display: 'flex', alignItems: 'center', padding: '0 12px', fontWeight: 500 }}>
          {props.title || '导航栏'}
        </div>
      );

    case 'NutIcon':
      return (
        <span style={{ fontSize: 16, color: props.color || '#333' }}>
          [{props.name || 'icon'}]
        </span>
      );

    case 'NutTag':
      return (
        <span style={{ background: props.color || '#eee', color: props.textColor || '#333', padding: '2px 8px', borderRadius: 4, fontSize: 12 }}>
          {props.text || '标签'}
        </span>
      );

    case 'NutAvatar':
      return (
        <div style={{ width: props.size || 40, height: props.size || 40, borderRadius: '50%', background: '#ddd', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: '#999' }}>
          {props.src && isValidImageUrl(props.src) ? <img src={props.src} style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }} /> : '头像'}
        </div>
      );

    case 'NutBadge':
      return (
        <div style={{ position: 'relative', display: 'inline-block' }}>
          <span style={{ padding: '4px 8px' }}>{props.children || '内容'}</span>
          {props.value && (
            <sup style={{ position: 'absolute', top: -4, right: -8, background: '#ff4d4f', color: '#fff', borderRadius: 10, fontSize: 10, padding: '1px 4px', minWidth: 16, textAlign: 'center' }}>
              {props.value}
            </sup>
          )}
        </div>
      );

    case 'NutProgress':
      return (
        <div style={{ height: 4, background: '#eee', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${props.percentage || 0}%`, background: props.color || '#1890ff', borderRadius: 2, transition: 'width 0.3s' }} />
        </div>
      );

    // 业务组件
    case 'BizAppointmentCard':
      return (
        <div style={{ margin: '8px 12px', padding: 12, background: '#fff', borderRadius: 8, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 48, height: 48, borderRadius: '50%', background: '#e6f4ff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: '#1677ff', flexShrink: 0 }}>
              {props.avatar && isValidImageUrl(props.avatar) ? <img src={props.avatar} style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }} /> : '头像'}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 15, fontWeight: 500, color: '#333' }}>{props.doctorName || '医生'}</div>
              <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>{props.departmentName || '科室'} | {props.appointmentTime || '时间'}</div>
            </div>
            <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 4, background: props.status === 'completed' ? '#f6ffed' : props.status === 'cancelled' ? '#fff1f0' : '#e6f4ff', color: props.status === 'completed' ? '#52c41a' : props.status === 'cancelled' ? '#ff4d4f' : '#1677ff' }}>
              {props.statusText || '待就诊'}
            </span>
          </div>
        </div>
      );

    case 'BizDoctorCard':
      return (
        <div style={{ margin: '8px 12px', padding: 12, background: '#fff', borderRadius: 8, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }}>
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ width: 64, height: 64, borderRadius: 8, background: '#e6f4ff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: '#1677ff', flexShrink: 0 }}>
              {props.avatar && isValidImageUrl(props.avatar) ? <img src={props.avatar} style={{ width: '100%', height: '100%', borderRadius: 8, objectFit: 'cover' }} /> : '头像'}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 15, fontWeight: 500, color: '#333' }}>{props.doctorName || '医生'}</div>
              <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>{props.departmentName || '科室'} | {props.title || '职称'}</div>
              {props.description && <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>{props.description}</div>}
              {props.consultationFee && <div style={{ fontSize: 13, color: '#ff4d4f', marginTop: 4, fontWeight: 500 }}>¥{props.consultationFee}</div>}
            </div>
          </div>
        </div>
      );

    case 'BizDepartmentPicker':
      return (
        <div style={{ padding: '8px 12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
            {props.label && (
              <span style={{ fontSize: 14, color: '#333', minWidth: 80 }}>
                {props.required && <span style={{ color: '#ff4d4f', marginRight: 4 }}>*</span>}
                {props.label}
              </span>
            )}
            <div style={{ flex: 1, height: 32, border: '1px solid #e5e5e5', borderRadius: 4, padding: '0 8px', fontSize: 14, color: '#999', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: props.disabled ? '#f5f5f5' : '#fff' }}>
              <span>{props.placeholder || '请选择科室'}</span>
              <span style={{ fontSize: 12, color: '#ccc' }}>▼</span>
            </div>
          </div>
        </div>
      );

    case 'BizTimeSlotPicker':
      return (
        <div style={{ padding: '8px 12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
            {props.label && (
              <span style={{ fontSize: 14, color: '#333', minWidth: 80 }}>
                {props.required && <span style={{ color: '#ff4d4f', marginRight: 4 }}>*</span>}
                {props.label}
              </span>
            )}
            <div style={{ flex: 1, height: 32, border: '1px solid #e5e5e5', borderRadius: 4, padding: '0 8px', fontSize: 14, color: '#999', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: props.disabled ? '#f5f5f5' : '#fff' }}>
              <span>{props.placeholder || '请选择时间段'}</span>
              <span style={{ fontSize: 12, color: '#ccc' }}>▼</span>
            </div>
          </div>
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

/** 基础渲染器组件 — 纯渲染，无编辑器交互 */
export const BaseRenderer: React.FC<BaseRendererProps> = ({ node, renderChild, depth = 0 }) => {
  const defaultRenderChild = (child: LowCodeNode, d: number) => (
    <BaseRenderer key={child.id} node={child} renderChild={renderChild} depth={d} />
  );

  return <>{renderBaseComponent(node, renderChild || defaultRenderChild, depth)}</>;
};

export default BaseRenderer;
