/** 画布区域 — 拖拽容器 */

import React from 'react';
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

/** Canvas 组件 */
export const Canvas: React.FC = () => {
  const addNode = useEditorStore((s) => s.addNode);
  const moveNode = useEditorStore((s) => s.moveNode);
  const setSchema = useEditorStore((s) => s.setSchema);
  const schema = useEditorStore((s) => s.schema);

  return (
    <div
      style={{
        flex: 1,
        overflow: 'auto',
        background: '#f0f2f5',
        padding: 16,
        display: 'flex',
        justifyContent: 'center',
      }}
    >
      <DragDropProvider
        onDragEnd={(event) => {
          if (event.canceled) return;

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

            // 查找目标父节点以获取当前 children 长度作为插入索引
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
            const parentNode = findNodeById(
              schema.children || [],
              parentId,
            );
            addNode(newNode, parentId, parentNode?.children?.length || 0);
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
                  return !!findDescendant(n.children || [], descendantId);
                }
                if (n.children) {
                  const found = isDescendant(n.children, ancestorId, descendantId);
                  if (found) return true;
                }
              }
              return false;
            };
            const findDescendant = (
              nodes: LowCodeNode[],
              id: string,
            ): LowCodeNode | null => {
              for (const n of nodes) {
                if (n.id === id) return n;
                if (n.children) {
                  const found = findDescendant(n.children, id);
                  if (found) return found;
                }
              }
              return null;
            };

            if (isDescendant(schema.children || [], nodeId, newParentId)) {
              return; // 目标是自身的子节点，忽略
            }

            // 查找目标父节点以获取插入索引
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
            const parentNode = findNodeById(
              schema.children || [],
              newParentId,
            );
            const targetIndex = parentNode?.children?.length || 0;

            moveNode(nodeId, newParentId, targetIndex);
          }
        }}
      >
        <div
          style={{
            width: 375,
            minHeight: 667,
            background: '#fff',
            borderRadius: 12,
            boxShadow: '0 2px 12px rgba(0,0,0,0.1)',
            overflow: 'hidden',
            position: 'relative',
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
      </DragDropProvider>
    </div>
  );
};
