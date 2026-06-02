/** 图层面板 — 树形展示组件层级，支持选中、拖拽排序、删除、显隐切换 */

import React, { useState, useMemo, useCallback } from 'react';
import { Tree, Tooltip, Typography, Empty, Space } from 'antd';
import {
  EyeOutlined,
  EyeInvisibleOutlined,
  DeleteOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  HolderOutlined,
  FileTextOutlined,
  PictureOutlined,
  ButtonOutlined,
  FormOutlined,
  AppstoreOutlined,
  ContainerOutlined,
  SwapOutlined,
  TableOutlined,
  CreditCardOutlined,
  ColumnWidthOutlined,
  MinusOutlined,
  SwitcherOutlined,
  EditOutlined,
  DownSquareOutlined,
  InboxOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import type { DataNode } from 'antd/es/tree';
import { useEditorStore } from '../store';
import type { LowCodeNode } from '@hospital/shared';

const { Text } = Typography;

/** 组件名 -> 图标映射 */
const COMPONENT_ICON_MAP: Record<string, React.ReactNode> = {
  Page: <ContainerOutlined />,
  NutView: <AppstoreOutlined />,
  NutText: <FileTextOutlined />,
  NutImage: <PictureOutlined />,
  NutButton: <ButtonOutlined />,
  NutDivider: <MinusOutlined />,
  NutSwiper: <SwapOutlined />,
  NutSwiperItem: <SwapOutlined />,
  NutCell: <TableOutlined />,
  NutCard: <CreditCardOutlined />,
  NutTabs: <UnorderedListOutlined />,
  NutTabPane: <UnorderedListOutlined />,
  NutEmpty: <InboxOutlined />,
  NutInput: <EditOutlined />,
  NutTextarea: <EditOutlined />,
  NutSwitch: <SwitcherOutlined />,
  NutPicker: <DownSquareOutlined />,
  NutForm: <FormOutlined />,
  NutRow: <ColumnWidthOutlined />,
  NutCol: <ColumnWidthOutlined />,
};

/** 从节点 props 中提取显示名称 */
function getDisplayName(node: LowCodeNode): string {
  const { props } = node;
  return (
    props.title ||
    props.label ||
    props.text ||
    props.placeholder ||
    props.description ||
    props.navigationBarTitleText ||
    ''
  );
}

/** 递归查找节点的父节点 */
function findParentNode(
  nodes: LowCodeNode[],
  targetId: string,
): LowCodeNode | null {
  for (const node of nodes) {
    if (node.children?.some((c) => c.id === targetId)) return node;
    if (node.children) {
      const found = findParentNode(node.children, targetId);
      if (found) return found;
    }
  }
  return null;
}

/** 单个图层节点 */
function LayerTreeNode({
  node,
  isExpanded,
  onToggleExpand,
  onToggleVisibility,
  onDelete,
  onMoveUp,
  onMoveDown,
  hiddenNodes,
}: {
  node: LowCodeNode;
  isExpanded: boolean;
  onToggleExpand: (nodeId: string) => void;
  onToggleVisibility: (nodeId: string) => void;
  onDelete: (nodeId: string) => void;
  onMoveUp: (nodeId: string) => void;
  onMoveDown: (nodeId: string) => void;
  hiddenNodes: Set<string>;
}) {
  const selectedNodeId = useEditorStore((s) => s.selectedNodeId);
  const selectNode = useEditorStore((s) => s.selectNode);

  const isSelected = selectedNodeId === node.id;
  const isHidden = hiddenNodes.has(node.id);
  const hasChildren = !!node.children?.length;
  const displayName = getDisplayName(node);
  const icon = COMPONENT_ICON_MAP[node.componentName] || <AppstoreOutlined />;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        padding: '3px 4px',
        borderRadius: 4,
        cursor: 'pointer',
        background: isSelected ? '#e6f4ff' : 'transparent',
        borderLeft: isSelected ? '2px solid #1677ff' : '2px solid transparent',
        opacity: isHidden ? 0.45 : 1,
        transition: 'background 0.12s, opacity 0.12s',
        userSelect: 'none',
        minHeight: 28,
      }}
      onClick={() => selectNode(node.id)}
      onMouseEnter={(e) => {
        if (!isSelected) e.currentTarget.style.background = '#f5f5f5';
      }}
      onMouseLeave={(e) => {
        if (!isSelected) e.currentTarget.style.background = 'transparent';
      }}
    >
      {/* 拖拽手柄 */}
      <HolderOutlined
        style={{ color: '#bbb', fontSize: 10, cursor: 'grab', flexShrink: 0 }}
        onClick={(e) => e.stopPropagation()}
      />

      {/* 展开/折叠 */}
      {hasChildren ? (
        <span
          style={{
            fontSize: 10,
            color: '#999',
            width: 14,
            textAlign: 'center',
            flexShrink: 0,
            transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
            transition: 'transform 0.15s',
            display: 'inline-block',
          }}
          onClick={(e) => {
            e.stopPropagation();
            onToggleExpand(node.id);
          }}
        >
          ▶
        </span>
      ) : (
        <span style={{ width: 14, flexShrink: 0 }} />
      )}

      {/* 组件图标 */}
      <span style={{ fontSize: 13, color: '#1677ff', flexShrink: 0 }}>
        {icon}
      </span>

      {/* 组件类型名 + 显示名称 */}
      <Text
        ellipsis
        style={{
          fontSize: 12,
          flex: 1,
          minWidth: 0,
          color: isSelected ? '#1677ff' : '#333',
        }}
      >
        {node.componentName}
        {displayName && (
          <Text type="secondary" ellipsis style={{ fontSize: 11, marginLeft: 4 }}>
            {displayName}
          </Text>
        )}
      </Text>

      {/* 操作按钮 — 仅选中时显示 */}
      {isSelected && (
        <Space size={2} style={{ flexShrink: 0 }} onClick={(e) => e.stopPropagation()}>
          <Tooltip title="上移">
            <ArrowUpOutlined
              style={{ fontSize: 11, color: '#999', cursor: 'pointer' }}
              onClick={() => onMoveUp(node.id)}
            />
          </Tooltip>
          <Tooltip title="下移">
            <ArrowDownOutlined
              style={{ fontSize: 11, color: '#999', cursor: 'pointer' }}
              onClick={() => onMoveDown(node.id)}
            />
          </Tooltip>
          <Tooltip title={isHidden ? '显示' : '隐藏'}>
            {isHidden ? (
              <EyeInvisibleOutlined
                style={{ fontSize: 11, color: '#999', cursor: 'pointer' }}
                onClick={() => onToggleVisibility(node.id)}
              />
            ) : (
              <EyeOutlined
                style={{ fontSize: 11, color: '#999', cursor: 'pointer' }}
                onClick={() => onToggleVisibility(node.id)}
              />
            )}
          </Tooltip>
          {node.componentName !== 'Page' && (
            <Tooltip title="删除">
              <DeleteOutlined
                style={{ fontSize: 11, color: '#ff4d4f', cursor: 'pointer' }}
                onClick={() => onDelete(node.id)}
              />
            </Tooltip>
          )}
        </Space>
      )}
    </div>
  );
}

/** 图层面板 */
export const LayerPanel: React.FC = () => {
  const schema = useEditorStore((s) => s.schema);
  const removeNode = useEditorStore((s) => s.removeNode);
  const moveNode = useEditorStore((s) => s.moveNode);

  /** 展开的节点 ID 集合 */
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(() => {
    // 默认展开根节点
    const keys = new Set<string>();
    // 展开 Page 的直接子节点
    return keys;
  });

  /** 隐藏的节点 ID 集合 (UI 层面的 toggle) */
  const [hiddenNodes, setHiddenNodes] = useState<Set<string>>(new Set());

  /** 切换展开/折叠 */
  const handleToggleExpand = useCallback((nodeId: string) => {
    setExpandedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }, []);

  /** 切换可见性 */
  const handleToggleVisibility = useCallback((nodeId: string) => {
    setHiddenNodes((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }, []);

  /** 删除节点 */
  const handleDelete = useCallback(
    (nodeId: string) => {
      removeNode(nodeId);
    },
    [removeNode],
  );

  /** 上移节点 (与前一个兄弟交换) */
  const handleMoveUp = useCallback(
    (nodeId: string) => {
      const parent = findParentNode(schema.children, nodeId);
      if (!parent?.children) return;
      const idx = parent.children.findIndex((c) => c.id === nodeId);
      if (idx <= 0) return;
      moveNode(nodeId, parent.id, idx - 1);
    },
    [schema.children, moveNode],
  );

  /** 下移节点 (与后一个兄弟交换) */
  const handleMoveDown = useCallback(
    (nodeId: string) => {
      const parent = findParentNode(schema.children, nodeId);
      if (!parent?.children) return;
      const idx = parent.children.findIndex((c) => c.id === nodeId);
      if (idx < 0 || idx >= parent.children.length - 1) return;
      moveNode(nodeId, parent.id, idx + 1);
    },
    [schema.children, moveNode],
  );

  /** 递归构建 antd Tree 的 treeData */
  const buildTreeData = useCallback(
    (nodes: LowCodeNode[]): DataNode[] => {
      return nodes.map((node) => {
        const hasChildren = !!node.children?.length;
        const isExpanded = expandedKeys.has(node.id);

        return {
          key: node.id,
          title: (
            <LayerTreeNode
              node={node}
              isExpanded={isExpanded}
              onToggleExpand={handleToggleExpand}
              onToggleVisibility={handleToggleVisibility}
              onDelete={handleDelete}
              onMoveUp={handleMoveUp}
              onMoveDown={handleMoveDown}
              hiddenNodes={hiddenNodes}
            />
          ),
          children: hasChildren
            ? buildTreeData(node.children!)
            : undefined,
          isLeaf: !hasChildren,
        };
      });
    },
    [
      expandedKeys,
      hiddenNodes,
      handleToggleExpand,
      handleToggleVisibility,
      handleDelete,
      handleMoveUp,
      handleMoveDown,
    ],
  );

  const treeData = useMemo(
    () => buildTreeData(schema.children || []),
    [buildTreeData, schema.children],
  );

  /** 计算组件总数 */
  const totalCount = useMemo(() => {
    let count = 0;
    const traverse = (nodes: LowCodeNode[]) => {
      for (const node of nodes) {
        count++;
        if (node.children) traverse(node.children);
      }
    };
    traverse(schema.children || []);
    return count;
  }, [schema.children]);

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* 面板标题 */}
      <div
        style={{
          padding: '8px 12px',
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Text strong style={{ fontSize: 13 }}>
          图层
        </Text>
        <Text type="secondary" style={{ fontSize: 11 }}>
          {totalCount} 个组件
        </Text>
      </div>

      {/* 树形列表 */}
      <div style={{ flex: 1, overflow: 'auto', padding: '4px 0' }}>
        {treeData.length > 0 ? (
          <Tree
            treeData={treeData}
            expandedKeys={Array.from(expandedKeys)}
            onExpand={(keys) => {
              setExpandedKeys(new Set(keys as string[]));
            }}
            blockNode
            showLine={false}
            showIcon={false}
            selectable={false}
            style={{ background: 'transparent' }}
          />
        ) : (
          <Empty
            description="暂无组件"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ marginTop: 40 }}
          />
        )}
      </div>

      {/* 底部信息 */}
      <div
        style={{
          padding: '6px 12px',
          borderTop: '1px solid #f0f0f0',
          fontSize: 11,
          color: '#999',
        }}
      >
        点击选中 | 上下箭头排序 | 拖拽至画布添加
      </div>
    </div>
  );
};
