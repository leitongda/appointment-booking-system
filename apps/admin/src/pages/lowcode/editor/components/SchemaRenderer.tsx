/** Schema 渲染器 — 将 Schema 节点树渲染为 React 组件 */
/* eslint-disable @typescript-eslint/no-use-before-define -- NodeRenderer 与 NodeRendererInner 相互递归渲染，声明顺序无法先定义后使用 */

import React, { useState, Component, type ReactNode, type ErrorInfo } from 'react';
import { useDraggable, useDroppable } from '@dnd-kit/react';
import { ArrowLeftOutlined, PlusOutlined } from '@ant-design/icons';
import { useEditorStore } from '../store';
import { ContextMenu } from './ContextMenu';
import { ROOT_DROP_ID } from '../constants';
import { isValidImageUrl } from './BaseRenderer';
import type { LowCodeNode } from '@hospital/shared';

// --- P0-2: NodeErrorBoundary ---
/** 节点级错误边界 — 组件渲染失败时显示红色占位符，防止整个画布白屏 */
interface NodeErrorBoundaryProps {
  componentName: string;
  children: ReactNode;
}

interface NodeErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class NodeErrorBoundary extends Component<NodeErrorBoundaryProps, NodeErrorBoundaryState> {
  constructor(props: NodeErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): Partial<NodeErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`[LowCode Editor] 组件渲染失败: ${this.props.componentName}`, error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            padding: '12px 16px',
            margin: '4px 0',
            border: '1px dashed var(--color-error)',
            borderRadius: 4,
            background: 'var(--color-white)2f0',
            color: 'var(--color-error)',
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <span style={{ fontWeight: 500 }}>[{this.props.componentName}]</span>
          <span>渲染失败：{this.state.error?.message || '未知错误'}</span>
        </div>
      );
    }
    return this.props.children;
  }
}

/** 合并样式：将 node.style 与基础样式合并 */
function mergeStyles(base: React.CSSProperties, nodeStyle?: Record<string, string>): React.CSSProperties {
  if (!nodeStyle) return base;
  const merged = { ...base };
  for (const [key, value] of Object.entries(nodeStyle)) {
    if (value) {
      (merged as any)[key] = value;
    }
  }
  return merged;
}

/** 可拖拽节点包装 — 非 Page 节点可被拖拽用于重排序 */
const DraggableNode = React.memo(function DraggableNode({
  nodeId,
  children,
  nodeStyle,
}: {
  nodeId: string;
  children: React.ReactNode;
  nodeStyle?: Record<string, string>;
}) {
  const { ref } = useDraggable({
    id: `node-${nodeId}`,
    data: {
      type: 'existing-node',
      nodeId,
    },
  });

  return (
    <div ref={ref} style={mergeStyles({ position: 'relative' }, nodeStyle)} data-node-id={nodeId}>
      {children}
    </div>
  );
});

/** 可放置区域包装 — 容器节点的子区域可作为放置目标 */
const DroppableZone = React.memo(function DroppableZone({
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
      role="group"
      aria-label="可放置区域"
      style={{
        ...style,
        outline: isDropTarget ? '2px dashed var(--color-primary)' : undefined,
        outlineOffset: isDropTarget ? -2 : undefined,
        background: isDropTarget ? 'rgba(22,119,255,0.04)' : undefined,
        transition: 'outline 0.15s, background 0.15s',
      }}
    >
      {children}
    </div>
  );
});

/** 渲染命名插槽区域 */
const SlotRenderer = React.memo(function SlotRenderer({
  node,
  slotName,
  label,
  depth,
}: {
  node: LowCodeNode;
  slotName: string;
  label: string;
  depth: number;
}) {
  const slotNodes = node.slots?.[slotName] || [];
  return (
    <DroppableZone
      parentId={`${node.id}__slot__${slotName}`}
      style={{
        minHeight: 32,
        border: '1px dashed var(--color-border)',
        borderRadius: 4,
        padding: 4,
        position: 'relative',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 2,
          left: 4,
          fontSize: 10,
          color: '#bfbfbf',
          pointerEvents: 'none',
        }}
      >
        {label}
      </div>
      {slotNodes.map((child) => (
        // eslint-disable-next-line @typescript-eslint/no-use-before-define
        <NodeRenderer key={child.id} node={child} depth={depth + 1} />
      ))}
      {slotNodes.length === 0 && (
        <div
          style={{
            textAlign: 'center',
            color: 'var(--color-border)',
            padding: '8px 0',
            fontSize: 11,
          }}
        >
          拖入{label}
        </div>
      )}
    </DroppableZone>
  );
});

/** 选择状态 hook — 仅在选中状态变化时触发重渲染 */
function useNodeSelection(nodeId: string) {
  const selectedNodeId = useEditorStore((s) => s.selectedNodeId);
  const selectedNodeIds = useEditorStore((s) => s.selectedNodeIds);
  const isSelected = selectedNodeIds.length > 1
    ? selectedNodeIds.includes(nodeId)
    : selectedNodeId === nodeId;
  return { isSelected, selectedNodeIds };
}

/** 选择操作 hook — action 引用稳定，不会触发重渲染 */
function useNodeActions() {
  const selectNode = useEditorStore((s) => s.selectNode);
  const toggleNodeSelect = useEditorStore((s) => s.toggleNodeSelect);
  return { selectNode, toggleNodeSelect };
}

/** NutTabs 渲染器 — 独立组件以支持标签切换的本地状态 */
const NutTabsRenderer = React.memo(function NutTabsRenderer({
  node,
  depth,
}: {
  node: LowCodeNode;
  depth: number;
}) {
  const panes = node.children?.filter((c) => c.componentName === 'NutTabPane') ?? [];
  const [activeIdx, setActiveIdx] = useState(0);
  // 激活索引超出范围时自动回退到第一个标签
  const safeIdx = activeIdx >= panes.length ? 0 : activeIdx;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        minHeight: 0,
      }}
    >
      {/* 标签栏 */}
      <div
        style={{
          display: 'flex',
          flexShrink: 0,
          borderBottom: '1px solid var(--color-border-secondary)',
          background: 'var(--color-white)',
        }}
      >
        {panes.map((child, idx) => {
          const isActive = idx === safeIdx;
          return (
            <div
              key={child.id}
              onClick={() => setActiveIdx(idx)}
              style={{
                padding: '10px 16px',
                fontSize: 14,
                color: isActive ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                borderBottom: isActive ? '2px solid var(--color-primary)' : '2px solid transparent',
                cursor: 'pointer',
                userSelect: 'none',
              }}
            >
              {child.props.title || '标签'}
            </div>
          );
        })}
      </div>
      {/* 标签内容区 — 仅渲染激活标签，flex:1 撑满标签栏以下剩余高度 */}
      {panes.map((child, idx) => {
        if (idx !== safeIdx) return null;
        return (
          <div
            key={child.id}
            style={{
              flex: 1,
              minHeight: 40,
              display: 'flex',
              flexDirection: 'column',
              ...(child.style as React.CSSProperties | undefined),
            }}
            data-node-id={child.id}
            data-component={child.componentName}
          >
            {child.children?.map((grandChild) => (
              <NodeRenderer
                key={grandChild.id}
                node={grandChild}
                depth={depth + 1}
              />
            ))}
            {(!child.children || child.children.length === 0) && (
              <div
                style={{
                  textAlign: 'center',
                  color: 'var(--color-border)',
                  padding: '20px 0',
                  fontSize: 12,
                }}
              >
                拖入内容到「{child.props.title || '标签'}」
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
});

/** 单个节点渲染（带错误边界保护） */
const NodeRendererInner = React.memo(function NodeRendererInner({ node, depth = 0 }: { node: LowCodeNode; depth?: number }) {
  const { isSelected, selectedNodeIds } = useNodeSelection(node.id);
  const { selectNode, toggleNodeSelect } = useNodeActions();
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null);

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (e.shiftKey) {
      toggleNodeSelect(node.id);
    } else {
      selectNode(node.id);
    }
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({ x: e.clientX, y: e.clientY });
  };

  // a11y: 键盘导航支持
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      e.stopPropagation();
      if (e.shiftKey) {
        toggleNodeSelect(node.id);
      } else {
        selectNode(node.id);
      }
    }
  };

  // 渲染组件映射
  const renderComponent = () => {
    switch (node.componentName) {
      case 'Page':
        return (
          <div
            style={{
              flex: 1,
              minHeight: 0,
              background: 'var(--color-bg-layout)',
              padding: 0,
              position: 'relative',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* 模拟导航栏 */}
            <div
              style={{
                height: 44,
                flexShrink: 0,
                background: node.props.navigationBarBackgroundColor || '#ffffff',
                display: 'flex',
                alignItems: 'center',
                borderBottom: '1px solid var(--color-border-secondary)',
                fontSize: 17,
                fontWeight: 500,
                position: 'relative',
              }}
            >
              {/* 左侧返回箭头（装饰性，对齐线框图手机标题栏） */}
              <ArrowLeftOutlined
                style={{
                  position: 'absolute',
                  left: 16,
                  fontSize: 18,
                  color: 'var(--color-text)',
                  pointerEvents: 'none',
                }}
              />
              {/* 居中标题（左右留白避开返回箭头，长文本省略） */}
              <span
                style={{
                  flex: 1,
                  textAlign: 'center',
                  padding: '0 40px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {node.props.navigationBarTitleText || '页面标题'}
              </span>
            </div>
            {/* 页面内容区 — flex:1 撑满导航栏以下剩余高度 */}
            <DroppableZone
              parentId={node.id || ROOT_DROP_ID}
              style={{
                padding: '12px 0',
                flex: 1,
                minHeight: 0,
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              {node.children?.map((child) => (
                <NodeRenderer key={child.id} node={child} depth={depth + 1} />
              ))}
              {(!node.children || node.children.length === 0) && (
                <div
                  style={{
                    textAlign: 'center',
                    color: 'var(--color-text-quaternary)',
                    padding: '48px 0',
                    fontSize: 13,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 8,
                  }}
                >
                  <PlusOutlined style={{ fontSize: 24, color: 'var(--color-text-quaternary)' }} />
                  请添加自定义组件
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
            {node.slots ? (
              <>
                <SlotRenderer node={node} slotName="header" label="头部插槽" depth={depth} />
                <SlotRenderer node={node} slotName="content" label="内容插槽" depth={depth} />
                <SlotRenderer node={node} slotName="footer" label="底部插槽" depth={depth} />
              </>
            ) : (
              node.children?.map((child) => (
                <NodeRenderer key={child.id} node={child} depth={depth + 1} />
              ))
            )}
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
            {node.props.src && isValidImageUrl(node.props.src) ? (
              <img
                src={node.props.src}
                alt={node.props.alt || '图片'}
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
                  background: 'var(--color-border-secondary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--color-text-tertiary)',
                  fontSize: 13,
                  borderRadius: node.props.borderRadius,
                }}
              >
                {node.props.src ? '无效图片链接' : '图片占位'}
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
                width: node.props.block ? '100%' : 'auto',
                height: 36,
                borderRadius: 6,
                border: 'none',
                background:
                  node.props.type === 'primary'
                    ? 'var(--color-primary)'
                    : node.props.type === 'warning'
                      ? '#ff9800'
                      : node.props.type === 'danger'
                        ? 'var(--color-error)'
                        : 'var(--color-bg-layout)',
                color:
                  node.props.type === 'primary' ? 'var(--color-white)' : 'var(--color-text)',
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
                  ? '1px dashed var(--color-border)'
                  : '1px solid var(--color-border)',
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
                background: 'var(--color-border)',
                borderRadius: 8,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-text-tertiary)',
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
              borderBottom: '1px solid var(--color-bg-layout)',
              background: 'var(--color-white)',
            }}
          >
            <div>
              <div style={{ fontSize: 15, color: 'var(--color-text)' }}>
                {node.props.title || '标题'}
              </div>
              {node.props.description && (
                <div style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginTop: 4 }}>
                  {node.props.description}
                </div>
              )}
            </div>
            {node.props.isLink && (
              <span style={{ color: 'var(--color-border)', fontSize: 12 }}>›</span>
            )}
          </div>
        );

      case 'NutCard':
        return (
          <div
            style={{
              margin: '8px 12px',
              padding: 12,
              background: 'var(--color-white)',
              borderRadius: 8,
              boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
            }}
          >
            <div style={{ fontSize: 16, fontWeight: 500, color: 'var(--color-text)' }}>
              {node.props.title || '卡片标题'}
            </div>
            {node.props.subTitle && (
              <div style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginTop: 4 }}>
                {node.props.subTitle}
              </div>
            )}
            {node.props.description && (
              <div style={{ fontSize: 13, color: 'var(--color-text-secondary)', marginTop: 8 }}>
                {node.props.description}
              </div>
            )}
            {node.slots ? (
              <>
                <SlotRenderer node={node} slotName="header" label="头部插槽" depth={depth} />
                <SlotRenderer node={node} slotName="content" label="内容插槽" depth={depth} />
                <SlotRenderer node={node} slotName="footer" label="底部插槽" depth={depth} />
              </>
            ) : (
              node.children && node.children.length > 0 && (
                <DroppableZone parentId={node.id} style={{ marginTop: 8 }}>
                  {node.children.map((child) => (
                    <NodeRenderer
                      key={child.id}
                      node={child}
                      depth={depth + 1}
                    />
                  ))}
                </DroppableZone>
              )
            )}
          </div>
        );

      case 'NutTabs':
        return <NutTabsRenderer node={node} depth={depth} />;

      case 'NutTabPane':
        // 由 NutTabs 父组件处理渲染
        return null;

      case 'NutEmpty':
        return (
          <div
            style={{
              textAlign: 'center',
              padding: '40px 0',
              color: 'var(--color-text-tertiary)',
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
                <span style={{ fontSize: 14, color: 'var(--color-text)', minWidth: 60 }}>
                  {node.props.required && (
                    <span style={{ color: 'var(--color-error)', marginRight: 4 }}>*</span>
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
                  border: '1px solid var(--color-border)',
                  borderRadius: 4,
                  padding: '0 8px',
                  fontSize: 14,
                  color: 'var(--color-text)',
                  textAlign: node.props.textAlign,
                  background: node.props.disabled ? 'var(--color-bg-layout)' : 'var(--color-white)',
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
                <span style={{ fontSize: 14, color: 'var(--color-text)' }}>
                  {node.props.required && (
                    <span style={{ color: 'var(--color-error)', marginRight: 4 }}>*</span>
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
                border: '1px solid var(--color-border)',
                borderRadius: 4,
                padding: '8px',
                fontSize: 14,
                color: 'var(--color-text)',
                resize: node.props.autosize ? 'vertical' : 'none',
                background: node.props.disabled ? 'var(--color-bg-layout)' : 'var(--color-white)',
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
                <span style={{ fontSize: 14, color: 'var(--color-text)' }}>{node.props.label}</span>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {node.props.activeText && (
                  <span style={{ fontSize: 12, color: 'var(--color-text)' }}>{node.props.activeText}</span>
                )}
                <div
                  style={{
                    width: 44,
                    height: 24,
                    borderRadius: 12,
                    background: node.props.checked ? 'var(--color-primary)' : 'var(--color-border)',
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
                      background: 'var(--color-white)',
                      position: 'absolute',
                      top: 2,
                      left: node.props.checked ? 22 : 2,
                      transition: 'left 0.2s',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                    }}
                  />
                </div>
                {node.props.inactiveText && (
                  <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>{node.props.inactiveText}</span>
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
                <span style={{ fontSize: 14, color: 'var(--color-text)', minWidth: 60 }}>
                  {node.props.required && (
                    <span style={{ color: 'var(--color-error)', marginRight: 4 }}>*</span>
                  )}
                  {node.props.label}
                </span>
              )}
              <div
                style={{
                  flex: 1,
                  height: 32,
                  border: '1px solid var(--color-border)',
                  borderRadius: 4,
                  padding: '0 8px',
                  fontSize: 14,
                  color: 'var(--color-text-tertiary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  background: node.props.disabled ? 'var(--color-bg-layout)' : 'var(--color-white)',
                }}
              >
                <span>{node.props.placeholder || '请选择'}</span>
                <span style={{ fontSize: 12, color: 'var(--color-border)' }}>▼</span>
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
              border: node.props.border ? '1px solid var(--color-border)' : 'none',
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

      case 'NutSearchBar':
        return (
          <div style={{ padding: '8px 12px', background: 'var(--color-bg-layout)', borderRadius: 16 }}>
            <input
              placeholder={node.props.placeholder || '搜索'}
              style={{ width: '100%', border: 'none', background: 'transparent', outline: 'none', fontSize: 14 }}
              readOnly
            />
          </div>
        );

      case 'NutNavBar':
        return (
          <div style={{ height: 44, borderBottom: '1px solid var(--color-border-secondary)', display: 'flex', alignItems: 'center', padding: '0 12px', fontWeight: 500 }}>
            {node.props.title || '导航栏'}
          </div>
        );

      case 'NutIcon':
        return (
          <span style={{ fontSize: 16, color: node.props.color || 'var(--color-text)' }}>
            [{node.props.name || 'icon'}]
          </span>
        );

      case 'NutTag':
        return (
          <span style={{ background: node.props.color || 'var(--color-border-secondary)', color: node.props.textColor || 'var(--color-text)', padding: '2px 8px', borderRadius: 4, fontSize: 12 }}>
            {node.props.text || '标签'}
          </span>
        );

      case 'NutAvatar':
        return (
          <div style={{ width: node.props.size || 40, height: node.props.size || 40, borderRadius: '50%', background: '#ddd', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: 'var(--color-text-tertiary)' }}>
            {node.props.src && isValidImageUrl(node.props.src) ? <img src={node.props.src} style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }} /> : '头像'}
          </div>
        );

      case 'NutBadge':
        return (
          <div style={{ position: 'relative', display: 'inline-block' }}>
            <span style={{ padding: '4px 8px' }}>{node.props.children || '内容'}</span>
            {node.props.value && (
              <sup style={{ position: 'absolute', top: -4, right: -8, background: 'var(--color-error)', color: 'var(--color-white)', borderRadius: 10, fontSize: 10, padding: '1px 4px', minWidth: 16, textAlign: 'center' }}>
                {node.props.value}
              </sup>
            )}
          </div>
        );

      case 'NutProgress':
        return (
          <div style={{ height: 4, background: 'var(--color-border-secondary)', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${node.props.percentage || 0}%`, background: node.props.color || 'var(--color-primary)', borderRadius: 2, transition: 'width 0.3s' }} />
          </div>
        );

      case 'NutCheckbox':
        return (
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
            <input type="checkbox" style={{ width: 16, height: 16 }} />
            <span style={{ fontSize: 14 }}>{node.props.label || '选项'}</span>
          </label>
        );

      case 'NutRadio':
        return (
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
            <input type="radio" name={node.props.group || 'default'} style={{ width: 16, height: 16 }} />
            <span style={{ fontSize: 14 }}>{node.props.label || '选项'}</span>
          </label>
        );

      case 'NutDatePicker':
        return (
          <input
            type="date"
            defaultValue={node.props.value || ''}
            style={{ padding: '6px 12px', border: '1px solid var(--color-border)', borderRadius: 4, fontSize: 14 }}
            readOnly
          />
        );

      case 'NutCalendar':
        return (
          <div style={{ border: '1px solid var(--color-border-secondary)', borderRadius: 8, padding: 12, textAlign: 'center', color: 'var(--color-text-tertiary)', fontSize: 12 }}>
            [日历组件]
          </div>
        );

      // --- 业务组件 ---

      case 'BizAppointmentCard':
        return (
          <div style={{ margin: '8px 12px', padding: 12, background: 'var(--color-white)', borderRadius: 8, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'var(--color-primary-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: 'var(--color-primary)', flexShrink: 0 }}>
                {node.props.avatar && isValidImageUrl(node.props.avatar) ? <img src={node.props.avatar} style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }} /> : '头像'}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 15, fontWeight: 500, color: 'var(--color-text)' }}>{node.props.doctorName || '医生'}</div>
                <div style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginTop: 2 }}>{node.props.departmentName || '科室'} | {node.props.appointmentTime || '时间'}</div>
              </div>
              <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 4, background: node.props.status === 'completed' ? 'var(--color-success-bg)' : node.props.status === 'cancelled' ? 'var(--color-white)1f0' : 'var(--color-primary-bg)', color: node.props.status === 'completed' ? 'var(--color-success)' : node.props.status === 'cancelled' ? 'var(--color-error)' : 'var(--color-primary)' }}>
                {node.props.statusText || '待就诊'}
              </span>
            </div>
          </div>
        );

      case 'BizDoctorCard':
        return (
          <div style={{ margin: '8px 12px', padding: 12, background: 'var(--color-white)', borderRadius: 8, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }}>
            <div style={{ display: 'flex', gap: 12 }}>
              <div style={{ width: 64, height: 64, borderRadius: 8, background: 'var(--color-primary-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: 'var(--color-primary)', flexShrink: 0 }}>
                {node.props.avatar && isValidImageUrl(node.props.avatar) ? <img src={node.props.avatar} style={{ width: '100%', height: '100%', borderRadius: 8, objectFit: 'cover' }} /> : '头像'}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 15, fontWeight: 500, color: 'var(--color-text)' }}>{node.props.doctorName || '医生'}</div>
                <div style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginTop: 2 }}>{node.props.departmentName || '科室'} | {node.props.title || '职称'}</div>
                {node.props.description && <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 4 }}>{node.props.description}</div>}
                {node.props.consultationFee && <div style={{ fontSize: 13, color: 'var(--color-error)', marginTop: 4, fontWeight: 500 }}>¥{node.props.consultationFee}</div>}
              </div>
            </div>
          </div>
        );

      case 'BizDepartmentPicker':
        return (
          <div style={{ padding: '8px 12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
              {node.props.label && (
                <span style={{ fontSize: 14, color: 'var(--color-text)', minWidth: 80 }}>
                  {node.props.required && <span style={{ color: 'var(--color-error)', marginRight: 4 }}>*</span>}
                  {node.props.label}
                </span>
              )}
              <div style={{ flex: 1, height: 32, border: '1px solid var(--color-border)', borderRadius: 4, padding: '0 8px', fontSize: 14, color: 'var(--color-text-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: node.props.disabled ? 'var(--color-bg-layout)' : 'var(--color-white)' }}>
                <span>{node.props.placeholder || '请选择科室'}</span>
                <span style={{ fontSize: 12, color: 'var(--color-border)' }}>▼</span>
              </div>
            </div>
          </div>
        );

      case 'BizTimeSlotPicker':
        return (
          <div style={{ padding: '8px 12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
              {node.props.label && (
                <span style={{ fontSize: 14, color: 'var(--color-text)', minWidth: 80 }}>
                  {node.props.required && <span style={{ color: 'var(--color-error)', marginRight: 4 }}>*</span>}
                  {node.props.label}
                </span>
              )}
              <div style={{ flex: 1, height: 32, border: '1px solid var(--color-border)', borderRadius: 4, padding: '0 8px', fontSize: 14, color: 'var(--color-text-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: node.props.disabled ? 'var(--color-bg-layout)' : 'var(--color-white)' }}>
                <span>{node.props.placeholder || '请选择时间段'}</span>
                <span style={{ fontSize: 12, color: 'var(--color-border)' }}>▼</span>
              </div>
            </div>
          </div>
        );

      default:
        return (
          <div
            style={{
              padding: '8px 12px',
              color: 'var(--color-text-tertiary)',
              fontSize: 12,
              fontStyle: 'italic',
            }}
          >
            [{node.componentName}]
          </div>
        );
    }
  };

  const isMultiSelected = selectedNodeIds.length > 1 && selectedNodeIds.includes(node.id);

  const content = (
    <>
      <div
        onClick={handleClick}
        onContextMenu={handleContextMenu}
        onKeyDown={handleKeyDown}
        role="treeitem"
        aria-selected={isSelected || isMultiSelected}
        aria-label={`${node.componentName} 组件${node.props.text ? `: ${node.props.text}` : ''}`}
        tabIndex={isSelected ? 0 : -1}
        style={{
          outline: isSelected ? '2px solid var(--color-primary)' : isMultiSelected ? '2px solid var(--color-success)' : '1px dashed transparent',
          outlineOffset: isSelected || isMultiSelected ? -1 : 0,
          position: 'relative',
          transition: 'outline 0.15s',
          cursor: 'pointer',
          flex: 1,
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
        }}
        data-node-id={node.id}
        data-component={node.componentName}
      >
        {(isSelected || isMultiSelected) && (
          <div
            style={{
              position: 'absolute',
              top: -20,
              left: 0,
              background: isMultiSelected ? 'var(--color-success)' : 'var(--color-primary)',
              color: 'var(--color-white)',
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
      {contextMenu && (
        <ContextMenu
          nodeId={node.id}
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={() => setContextMenu(null)}
        />
      )}
    </>
  );

  // Page 根节点不可拖拽，其余节点可拖拽用于重排序
  if (node.componentName === 'Page') return content;
  return <DraggableNode nodeId={node.id} nodeStyle={node.style}>{content}</DraggableNode>;
});

/** 单个节点渲染（带错误边界保护） */
const NodeRenderer = React.memo(function NodeRenderer({ node, depth = 0 }: { node: LowCodeNode; depth?: number }) {
  return (
    <NodeErrorBoundary componentName={node.componentName}>
      <NodeRendererInner node={node} depth={depth} />
    </NodeErrorBoundary>
  );
});

/** 画布渲染入口 — 撑满 Canvas 容器（width/height 由外层 100% 提供，不再依赖百分比 minHeight） */
export const SchemaRenderer: React.FC = () => {
  const schema = useEditorStore((s) => s.schema);

  return (
    <div
      role="tree"
      aria-label="页面组件树"
      style={{
        background: 'var(--color-white)',
        width: '100%',
        height: '100%',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <NodeRenderer node={schema as unknown as LowCodeNode} />
    </div>
  );
};
