/** 画布区域 — 拖拽容器 */

import React, { useState, useRef } from 'react';
import { DragDropProvider, DragOverlay } from '@dnd-kit/react';
import { useEditorStore } from '../store';
import { SchemaRenderer } from './SchemaRenderer';
import type { LowCodeNode, MaterialComponent } from '@hospital/shared';

/** 生成唯一 ID (使用 crypto.randomUUID 如果可用) */
function generateId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `node_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

/** 从 MaterialComponent 创建 LowCodeNode */
function createNodeFromMaterial(material: MaterialComponent): LowCodeNode {
  return {
    id: generateId(),
    componentName: material.componentName,
    props: { ...material.defaultProps },
    children: [],
  };
}

/** 查找节点 (递归) */
function findNodeById(
  nodes: LowCodeNode[],
  id: string,
): LowCodeNode | null {
  for (const n of nodes) {
    if (n.id === id) return n;
    if (n.children) {
      const found = findNodeById(n.children, id);
      if (found) return found;
    }
  }
  return null;
}

/** 根据鼠标 Y 坐标计算插入索引和指示器位置 */
function computeInsertion(
  mouseClientY: number,
  containerEl: HTMLElement,
): { index: number; top: number } | null {
  const children = Array.from(
    containerEl.querySelectorAll(':scope > [data-node-id]'),
  ) as HTMLElement[];
  if (children.length === 0) {
    return { index: 0, top: 0 };
  }
  const containerRect = containerEl.getBoundingClientRect();
  for (let i = 0; i < children.length; i++) {
    const rect = children[i].getBoundingClientRect();
    if (mouseClientY < rect.top + rect.height / 2) {
      // 指示器放在当前子元素顶部 (即前一个子元素底部)
      const top = i === 0 ? 0 : rect.top - containerRect.top;
      return { index: i, top };
    }
  }
  // 鼠标在所有子元素下方 — 插入到末尾，指示器放在最后一个子元素下方
  const lastRect = children[children.length - 1].getBoundingClientRect();
  return {
    index: children.length,
    top: lastRect.bottom - containerRect.top + 2,
  };
}

/** 设备尺寸预设 */
const DEVICE_PRESETS = [
  { label: 'iPhone', width: 375, height: 667 },
  { label: 'Android', width: 360, height: 640 },
  { label: 'iPad', width: 768, height: 1024 },
];

/** 缩放级别 */
const ZOOM_LEVELS = [50, 75, 100, 125];

/** Canvas 组件 */
export const Canvas: React.FC = () => {
  const addNode = useEditorStore((s) => s.addNode);
  const moveNode = useEditorStore((s) => s.moveNode);
  const setSchema = useEditorStore((s) => s.setSchema);
  const schema = useEditorStore((s) => s.schema);

  /** 拖拽期间计算出的插入索引 (ref 避免频繁 re-render) */
  const dropIndexRef = useRef<number | null>(null);
  /** 插入指示器的视觉状态 */
  const [indicator, setIndicator] = useState<{ top: number; width: number; left: number } | null>(null);
  /** 画布缩放比例 */
  const [zoom, setZoom] = useState(100);
  /** 设备尺寸 */
  const [device, setDevice] = useState(DEVICE_PRESETS[0]);

  return (
    <div
      style={{
        flex: 1,
        overflow: 'auto',
        background: '#f0f2f5',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* 工具栏：缩放 + 设备切换 */}
      <div
        style={{
          padding: '8px 16px',
          borderBottom: '1px solid #e8e8e8',
          background: '#fff',
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          fontSize: 12,
        }}
      >
        <span style={{ color: '#666' }}>缩放:</span>
        {ZOOM_LEVELS.map((z) => (
          <a
            key={z}
            onClick={() => setZoom(z)}
            style={{
              color: zoom === z ? '#1677ff' : '#666',
              fontWeight: zoom === z ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            {z}%
          </a>
        ))}
        <span style={{ color: '#d9d9d9' }}>|</span>
        <span style={{ color: '#666' }}>设备:</span>
        {DEVICE_PRESETS.map((d) => (
          <a
            key={d.label}
            onClick={() => setDevice(d)}
            style={{
              color: device.label === d.label ? '#1677ff' : '#666',
              fontWeight: device.label === d.label ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            {d.label}
          </a>
        ))}
        <span style={{ color: '#999', marginLeft: 'auto' }}>
          {device.width} x {device.height}
        </span>
      </div>

      {/* 画布区域 */}
      <div
        style={{
          flex: 1,
          padding: 16,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'flex-start',
        }}
      >
      <DragDropProvider
        onDragMove={({ operation }) => {
          const target = operation.target as Record<string, any> | undefined;
          const position = operation.position as { clientX: number; clientY: number } | undefined;

          if (!target || !position) {
            dropIndexRef.current = null;
            setIndicator(null);
            return;
          }

          const parentId = target.data?.parentId as string | undefined;
          if (!parentId) return;

          const containerEl = document.getElementById(`drop-${parentId}`);
          if (!containerEl) return;

          const result = computeInsertion(position.clientY, containerEl);
          if (!result) return;

          dropIndexRef.current = result.index;
          const rect = containerEl.getBoundingClientRect();
          setIndicator({
            top: rect.top + result.top,
            width: rect.width,
            left: rect.left,
          });
        }}
        onDragEnd={(event) => {
          if (event.canceled) {
            dropIndexRef.current = null;
            setIndicator(null);
            return;
          }

          // 拖拽结束，清除指示器
          const computedIndex = dropIndexRef.current;
          dropIndexRef.current = null;
          setIndicator(null);

          const source = event.operation.source;
          const target = event.operation.target;
          if (!source || !target) return;

          const sourceData = source.data as Record<string, any>;
          const targetData = target.data as Record<string, any>;

          // 从物料面板拖入新组件
          if (sourceData?.type === 'new-component') {
            const material = sourceData.material as MaterialComponent;
            const newNode = createNodeFromMaterial(material);

            // 确定目标父节点: 优先使用放置目标的 parentId，否则回退到 Page 根节点
            let parentId: string;
            if (targetData?.type === 'container' && targetData.parentId) {
              parentId = targetData.parentId;
            } else {
              const rootNode = schema.children?.[0];
              if (!rootNode) {
                setSchema({
                  ...schema,
                  children: [...(schema.children || []), newNode],
                });
                return;
              }
              parentId = rootNode.id;
            }

            // 使用拖拽过程中计算的精确插入索引，回退到末尾
            let insertIndex: number;
            if (computedIndex !== null) {
              insertIndex = computedIndex;
            } else {
              const parentNode = findNodeById(schema.children || [], parentId);
              insertIndex = parentNode?.children?.length || 0;
            }
            addNode(newNode, parentId, insertIndex);
            return;
          }

          // 画布内已有节点拖拽重排序
          if (sourceData?.type === 'existing-node') {
            const nodeId = sourceData.nodeId as string;

            // 确定目标父节点
            let newParentId: string;
            if (targetData?.type === 'container' && targetData.parentId) {
              newParentId = targetData.parentId;
            } else {
              return; // 无法确定目标位置，忽略
            }

            // 防止将节点拖拽到自身内部 (包含间接子节点)
            const isDescendant = (
              nodes: LowCodeNode[],
              ancestorId: string,
              descendantId: string,
            ): boolean => {
              for (const n of nodes) {
                if (n.id === ancestorId) {
                  return !!findNodeById(n.children || [], descendantId);
                }
                if (n.children) {
                  const found = isDescendant(n.children, ancestorId, descendantId);
                  if (found) return true;
                }
              }
              return false;
            };

            if (isDescendant(schema.children || [], nodeId, newParentId)) {
              return; // 目标是自身的子节点，忽略
            }

            // 使用拖拽过程中计算的精确插入索引，回退到末尾
            let targetIndex: number;
            if (computedIndex !== null) {
              targetIndex = computedIndex;
            } else {
              const parentNode = findNodeById(schema.children || [], newParentId);
              targetIndex = parentNode?.children?.length || 0;
            }

            moveNode(nodeId, newParentId, targetIndex);
          }
        }}
      >
        <div
          style={{
            width: device.width,
            minHeight: device.height,
            background: '#fff',
            borderRadius: 12,
            boxShadow: '0 2px 12px rgba(0,0,0,0.1)',
            overflow: 'hidden',
            position: 'relative',
            transform: `scale(${zoom / 100})`,
            transformOrigin: 'top center',
          }}
        >
          <SchemaRenderer />
        </div>
        <DragOverlay>
          {(source) => {
            if (!source) return null;
            const data = source.data as Record<string, any>;
            if (data?.type === 'new-component') {
              const material = data.material as MaterialComponent;
              return (
                <div
                  style={{
                    padding: '6px 12px',
                    background: '#e6f4ff',
                    border: '1px solid #1677ff',
                    borderRadius: 6,
                    fontSize: 13,
                    color: '#1677ff',
                    opacity: 0.9,
                  }}
                >
                  {material.title}
                </div>
              );
            }
            if (data?.type === 'existing-node') {
              // 查找被拖拽节点的 componentName 用于预览
              const findNodeById = (
                nodes: LowCodeNode[],
                id: string,
              ): LowCodeNode | null => {
                for (const n of nodes) {
                  if (n.id === id) return n;
                  if (n.children) {
                    const found = findNodeById(n.children, id);
                    if (found) return found;
                  }
                }
                return null;
              };
              const node = findNodeById(
                schema.children || [],
                data.nodeId,
              );
              return (
                <div
                  style={{
                    padding: '6px 12px',
                    background: '#fff7e6',
                    border: '1px solid #faad14',
                    borderRadius: 6,
                    fontSize: 13,
                    color: '#d48806',
                    opacity: 0.9,
                  }}
                >
                  {node?.componentName || '节点'}
                </div>
              );
            }
            return null;
          }}
        </DragOverlay>
        {/* 拖拽插入位置指示器 — 蓝色横线 */}
        {indicator && (
          <div
            style={{
              position: 'fixed',
              top: indicator.top,
              left: indicator.left,
              width: indicator.width,
              height: 2,
              background: '#1677ff',
              borderRadius: 1,
              boxShadow: '0 0 6px rgba(22,119,255,0.5)',
              zIndex: 10000,
              pointerEvents: 'none',
            }}
          />
        )}
      </DragDropProvider>
      </div>
    </div>
  );
};
