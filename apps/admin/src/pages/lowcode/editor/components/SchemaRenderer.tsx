/** Schema 渲染器 — 将 Schema 节点树渲染为 React 组件 */

import React from 'react';
import { useDraggable, useDroppable } from '@dnd-kit/react';
import { useEditorStore } from '../store';
import type { LowCodeNode } from '@hospital/shared';

/** 可拖拽节点包装 — 非 Page 节点可被拖拽用于重排序 */
function DraggableNode({
  nodeId,
  children,
}: {
  nodeId: string;
  children: React.ReactNode;
}) {
  const { ref } = useDraggable({
    id: `node-${nodeId}`,
    data: {
      type: 'existing-node',
      nodeId,
    },
  });

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      {children}
    </div>
  );
}

/** 可放置区域包装 — 容器节点的子区域可作为放置目标 */
function DroppableZone({
  parentId,
  children,
  style,
}: {
  parentId: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
}) {
  const { ref, isDropTarget } = useDroppable({
    id: `drop-${parentId}`,
    data: {
      type: 'container',
      parentId,
    },
  });

  return (
    <div
      ref={ref}
      style={{
        ...style,
        outline: isDropTarget ? '2px dashed #1677ff' : undefined,
        outlineOffset: isDropTarget ? -2 : undefined,
        background: isDropTarget ? 'rgba(22,119,255,0.04)' : undefined,
        transition: 'outline 0.15s, background 0.15s',
      }}
    >
      {children}
    </div>
  );
}

/** 单个节点渲染 */
function NodeRenderer({ node, depth = 0 }: { node: LowCodeNode; depth?: number }) {
  const selectedNodeId = useEditorStore((s) => s.selectedNodeId);
  const selectNode = useEditorStore((s) => s.selectNode);
  const isSelected = selectedNodeId === node.id;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    selectNode(node.id);
  };

  // 渲染组件映射
  const renderComponent = () => {
    switch (node.componentName) {
      case 'Page':
        return (
          <div
            style={{
              minHeight: 600,
              background: '#f5f5f5',
              padding: 0,
              position: 'relative',
            }}
          >
            {/* 模拟导航栏 */}
            <div
              style={{
                height: 44,
                background: node.props.navigationBarBackgroundColor || '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderBottom: '1px solid #eee',
                fontSize: 17,
                fontWeight: 500,
              }}
            >
              {node.props.navigationBarTitleText || '页面标题'}
            </div>
            {/* 页面内容区 */}
            <DroppableZone
              parentId={node.id}
              style={{ padding: '12px 0', minHeight: 80 }}
            >
              {node.children?.map((child) => (
                <NodeRenderer key={child.id} node={child} depth={depth + 1} />
              ))}
              {(!node.children || node.children.length === 0) && (
                <div
                  style={{
                    textAlign: 'center',
                    color: '#ccc',
                    padding: '40px 0',
                    fontSize: 13,
                  }}
                >
                  拖拽组件到此处
                </div>
              )}
            </DroppableZone>
          </div>
        );

      case 'NutView':
        return (
          <DroppableZone
            parentId={node.id}
            style={{
              padding: node.props.padding,
              margin: node.props.margin,
              backgroundColor: node.props.backgroundColor,
              borderRadius: node.props.borderRadius,
              minHeight: 40,
            }}
          >
            {node.children?.map((child) => (
              <NodeRenderer key={child.id} node={child} depth={depth + 1} />
            ))}
          </DroppableZone>
        );

      case 'NutText':
        return (
          <div
            style={{
              padding: '4px 12px',
              fontSize: node.props.fontSize,
              color: node.props.color,
              fontWeight: node.props.fontWeight,
              textAlign: node.props.textAlign,
            }}
          >
            {node.props.text || '文本'}
          </div>
        );

      case 'NutImage':
        return (
          <div style={{ padding: '4px 12px' }}>
            {node.props.src ? (
              <img
                src={node.props.src}
                alt=""
                style={{
                  width: node.props.width,
                  height: node.props.height,
                  objectFit: node.props.fit,
                  borderRadius: node.props.borderRadius,
                  display: 'block',
                }}
              />
            ) : (
              <div
                style={{
                  width: node.props.width,
                  height: node.props.height || '120px',
                  background: '#f0f0f0',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#999',
                  fontSize: 13,
                  borderRadius: node.props.borderRadius,
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
                width: node.props.block ? '100%' : 'auto',
                height: 36,
                borderRadius: 6,
                border: 'none',
                background:
                  node.props.type === 'primary'
                    ? '#1677ff'
                    : node.props.type === 'warning'
                      ? '#ff9800'
                      : node.props.type === 'danger'
                        ? '#ff4d4f'
                        : '#f5f5f5',
                color:
                  node.props.type === 'primary' ? '#fff' : '#333',
                fontSize: 14,
                cursor: 'pointer',
                opacity: node.props.disabled ? 0.5 : 1,
              }}
              disabled={node.props.disabled}
            >
              {node.props.text || '按钮'}
            </button>
          </div>
        );

      case 'NutDivider':
        return (
          <div style={{ padding: '8px 12px' }}>
            <hr
              style={{
                border: 'none',
                borderTop: node.props.dashed
                  ? '1px dashed #e5e5e5'
                  : '1px solid #e5e5e5',
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
                height: node.props.height || '200px',
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
            <DroppableZone parentId={node.id}>
              {node.children?.map((child) => (
                <NodeRenderer key={child.id} node={child} depth={depth + 1} />
              ))}
            </DroppableZone>
          </div>
        );

      case 'NutSwiperItem':
        return (
          <div>
            {node.children?.map((child) => (
              <NodeRenderer key={child.id} node={child} depth={depth + 1} />
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
              <div style={{ fontSize: 15, color: '#333' }}>
                {node.props.title || '标题'}
              </div>
              {node.props.description && (
                <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                  {node.props.description}
                </div>
              )}
            </div>
            {node.props.isLink && (
              <span style={{ color: '#ccc', fontSize: 12 }}>›</span>
            )}
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
            <div style={{ fontSize: 16, fontWeight: 500, color: '#333' }}>
              {node.props.title || '卡片标题'}
            </div>
            {node.props.subTitle && (
              <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                {node.props.subTitle}
              </div>
            )}
            {node.props.description && (
              <div style={{ fontSize: 13, color: '#666', marginTop: 8 }}>
                {node.props.description}
              </div>
            )}
            {node.children && node.children.length > 0 && (
              <DroppableZone parentId={node.id} style={{ marginTop: 8 }}>
                {node.children.map((child) => (
                  <NodeRenderer
                    key={child.id}
                    node={child}
                    depth={depth + 1}
                  />
                ))}
              </DroppableZone>
            )}
          </div>
        );

      case 'NutTabs':
        return (
          <div>
            <div
              style={{
                display: 'flex',
                borderBottom: '1px solid #eee',
                background: '#fff',
              }}
            >
              {node.children
                ?.filter((c) => c.componentName === 'NutTabPane')
                .map((child, idx) => (
                  <div
                    key={child.id}
                    style={{
                      padding: '10px 16px',
                      fontSize: 14,
                      color: idx === 0 ? '#1677ff' : '#666',
                      borderBottom:
                        idx === 0 ? '2px solid #1677ff' : '2px solid transparent',
                      cursor: 'pointer',
                    }}
                  >
                    {child.props.title || '标签'}
                  </div>
                ))}
            </div>
            {node.children
              ?.filter((c) => c.componentName === 'NutTabPane')
              .map((child, idx) => (
                <div
                  key={child.id}
                  style={{ display: idx === 0 ? 'block' : 'none' }}
                >
                  {child.children?.map((grandChild) => (
                    <NodeRenderer
                      key={grandChild.id}
                      node={grandChild}
                      depth={depth + 1}
                    />
                  ))}
                </div>
              ))}
          </div>
        );

      case 'NutTabPane':
        // 由 NutTabs 父组件处理渲染
        return null;

      case 'NutEmpty':
        return (
          <div
            style={{
              textAlign: 'center',
              padding: '40px 0',
              color: '#999',
              fontSize: 13,
            }}
          >
            {node.props.description || '暂无数据'}
          </div>
        );

      case 'NutInput':
        return (
          <div style={{ padding: '8px 12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
              {node.props.label && (
                <span style={{ fontSize: 14, color: '#333', minWidth: 60 }}>
                  {node.props.required && (
                    <span style={{ color: '#ff4d4f', marginRight: 4 }}>*</span>
                  )}
                  {node.props.label}
                </span>
              )}
              <input
                type="text"
                placeholder={node.props.placeholder || '请输入'}
                disabled={node.props.disabled}
                readOnly={node.props.readOnly}
                maxLength={node.props.maxLength > 0 ? node.props.maxLength : undefined}
                style={{
                  flex: 1,
                  height: 32,
                  border: '1px solid #e5e5e5',
                  borderRadius: 4,
                  padding: '0 8px',
                  fontSize: 14,
                  color: '#333',
                  textAlign: node.props.textAlign,
                  background: node.props.disabled ? '#f5f5f5' : '#fff',
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
              {node.props.label && (
                <span style={{ fontSize: 14, color: '#333' }}>
                  {node.props.required && (
                    <span style={{ color: '#ff4d4f', marginRight: 4 }}>*</span>
                  )}
                  {node.props.label}
                </span>
              )}
            </div>
            <textarea
              placeholder={node.props.placeholder || '请输入'}
              disabled={node.props.disabled}
              readOnly={node.props.readOnly}
              rows={node.props.rows || 3}
              maxLength={node.props.maxLength > 0 ? node.props.maxLength : undefined}
              style={{
                width: '100%',
                border: '1px solid #e5e5e5',
                borderRadius: 4,
                padding: '8px',
                fontSize: 14,
                color: '#333',
                resize: node.props.autosize ? 'vertical' : 'none',
                background: node.props.disabled ? '#f5f5f5' : '#fff',
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
              {node.props.label && (
                <span style={{ fontSize: 14, color: '#333' }}>{node.props.label}</span>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {node.props.activeText && (
                  <span style={{ fontSize: 12, color: '#333' }}>{node.props.activeText}</span>
                )}
                <div
                  style={{
                    width: 44,
                    height: 24,
                    borderRadius: 12,
                    background: node.props.checked ? '#1677ff' : '#e5e5e5',
                    position: 'relative',
                    cursor: node.props.disabled ? 'not-allowed' : 'pointer',
                    opacity: node.props.disabled ? 0.5 : 1,
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
                      left: node.props.checked ? 22 : 2,
                      transition: 'left 0.2s',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                    }}
                  />
                </div>
                {node.props.inactiveText && (
                  <span style={{ fontSize: 12, color: '#999' }}>{node.props.inactiveText}</span>
                )}
              </div>
            </div>
          </div>
        );

      case 'NutPicker':
        return (
          <div style={{ padding: '8px 12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
              {node.props.label && (
                <span style={{ fontSize: 14, color: '#333', minWidth: 60 }}>
                  {node.props.required && (
                    <span style={{ color: '#ff4d4f', marginRight: 4 }}>*</span>
                  )}
                  {node.props.label}
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
                  background: node.props.disabled ? '#f5f5f5' : '#fff',
                }}
              >
                <span>{node.props.placeholder || '请选择'}</span>
                <span style={{ fontSize: 12, color: '#ccc' }}>▼</span>
              </div>
            </div>
          </div>
        );

      case 'NutForm':
        return (
          <DroppableZone
            parentId={node.id}
            style={{
              padding: node.props.border ? '12px' : '8px 0',
              border: node.props.border ? '1px solid #e5e5e5' : 'none',
              borderRadius: node.props.border ? 4 : 0,
              minHeight: 40,
            }}
          >
            {node.children?.map((child) => (
              <NodeRenderer key={child.id} node={child} depth={depth + 1} />
            ))}
          </DroppableZone>
        );

      case 'NutRow':
        return (
          <DroppableZone
            parentId={node.id}
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: node.props.gutter || 0,
              padding: '4px 12px',
              minHeight: 30,
            }}
          >
            {node.children?.map((child) => (
              <NodeRenderer key={child.id} node={child} depth={depth + 1} />
            ))}
          </DroppableZone>
        );

      case 'NutCol':
        return (
          <DroppableZone
            parentId={node.id}
            style={{
              width: `${((node.props.span || 12) / 24) * 100}%`,
              flexShrink: 0,
              padding: '0 4px',
              minHeight: 20,
            }}
          >
            {node.children?.map((child) => (
              <NodeRenderer key={child.id} node={child} depth={depth + 1} />
            ))}
          </DroppableZone>
        );

      default:
        return (
          <div
            style={{
              padding: '8px 12px',
              color: '#999',
              fontSize: 12,
              fontStyle: 'italic',
            }}
          >
            [{node.componentName}]
          </div>
        );
    }
  };

  const content = (
    <div
      onClick={handleClick}
      style={{
        outline: isSelected ? '2px solid #1677ff' : '1px dashed transparent',
        outlineOffset: isSelected ? -1 : 0,
        position: 'relative',
        transition: 'outline 0.15s',
        cursor: 'pointer',
      }}
      data-node-id={node.id}
      data-component={node.componentName}
    >
      {isSelected && (
        <div
          style={{
            position: 'absolute',
            top: -20,
            left: 0,
            background: '#1677ff',
            color: '#fff',
            fontSize: 11,
            padding: '1px 6px',
            borderRadius: 3,
            zIndex: 10,
            whiteSpace: 'nowrap',
          }}
        >
          {node.componentName}
        </div>
      )}
      {renderComponent()}
    </div>
  );

  // Page 根节点不可拖拽，其余节点可拖拽用于重排序
  if (node.componentName === 'Page') return content;
  return <DraggableNode nodeId={node.id}>{content}</DraggableNode>;
}

/** 画布渲染入口 */
export const SchemaRenderer: React.FC = () => {
  const schema = useEditorStore((s) => s.schema);

  return (
    <div
      style={{
        background: '#fff',
        minHeight: '100%',
        position: 'relative',
      }}
    >
      <NodeRenderer node={schema as unknown as LowCodeNode} />
    </div>
  );
};
