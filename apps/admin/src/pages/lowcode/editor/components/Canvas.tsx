/** 画布区域 — 拖拽容器 */

import React, { useState, useRef } from 'react';
import { DragDropProvider, DragOverlay } from '@dnd-kit/react';
import { Segmented, InputNumber, Slider, Switch, Tooltip, Space, Select, message } from 'antd';
import { SwapOutlined, EditOutlined } from '@ant-design/icons';
import { useEditorStore } from '../store';
import { SchemaRenderer } from './SchemaRenderer';
import { EDITOR_COLORS, EDITOR_LAYOUT, ROOT_DROP_ID } from '../constants';
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
interface DevicePreset {
  label: string;
  width: number;
  height: number;
  /** 设备像素比 */
  dpr?: number;
  /** 厂商分组（用于下拉分组展示） */
  vendor?: string;
}

const VENDOR_ORDER = ['Apple', 'Google', 'Samsung', 'H5'];
const VENDOR_LABEL: Record<string, string> = {
  Apple: 'Apple',
  Google: 'Google',
  Samsung: 'Samsung',
  H5: 'H5',
};

const DEVICE_PRESETS: DevicePreset[] = [
  { label: 'iPhone SE', width: 375, height: 667, dpr: 2, vendor: 'Apple' },
  { label: 'iPhone 14', width: 390, height: 844, dpr: 3, vendor: 'Apple' },
  { label: 'iPhone 14 Pro Max', width: 430, height: 932, dpr: 3, vendor: 'Apple' },
  { label: 'iPad', width: 768, height: 1024, dpr: 2, vendor: 'Apple' },
  { label: 'iPad Pro 11', width: 834, height: 1194, dpr: 2, vendor: 'Apple' },
  { label: 'iPad Pro 12.9', width: 1024, height: 1366, dpr: 2, vendor: 'Apple' },
  { label: 'Android (Nexus)', width: 360, height: 640, dpr: 2, vendor: 'Google' },
  { label: 'Pixel 7', width: 412, height: 915, dpr: 2.625, vendor: 'Google' },
  { label: 'Galaxy S22', width: 360, height: 780, dpr: 3, vendor: 'Samsung' },
  { label: 'H5 窄屏', width: 320, height: 568, dpr: 2, vendor: 'H5' },
];

/** 构建按厂商分组的下拉选项 */
const DEVICE_OPTIONS = VENDOR_ORDER
  .map((vendor) => {
    const presets = DEVICE_PRESETS.filter((d) => d.vendor === vendor);
    if (presets.length === 0) return null;
    return {
      label: VENDOR_LABEL[vendor] || vendor,
      title: VENDOR_LABEL[vendor] || vendor,
      options: presets.map((d) => ({ label: d.label, value: d.label })),
    };
  })
  .filter(Boolean) as { label: string; title: string; options: { label: string; value: string }[] }[];

/** 缩放级别（用于快捷按钮） */
const ZOOM_LEVELS = [25, 50, 75, 100, 125, 150, 200];
/** 常见 DPR 候选 */
const DPR_OPTIONS = [1, 2, 3];

/** Canvas 组件 */
export const EditorDndProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const addNode = useEditorStore((s) => s.addNode);
  const addToRoot = useEditorStore((s) => s.addToRoot);
  const moveNode = useEditorStore((s) => s.moveNode);
  const moveToRoot = useEditorStore((s) => s.moveToRoot);
  const schema = useEditorStore((s) => s.schema);

  /** 拖拽期间计算出的插入索引 (ref 避免频繁 re-render) */
  const dropIndexRef = useRef<number | null>(null);
  /** 插入指示器的视觉状态 */
  const [indicator, setIndicator] = useState<{ top: number; width: number; left: number } | null>(null);

  const insertNodes = (nodes: LowCodeNode[], parentId: string, insertIndex: number) => {
    let index = insertIndex;
    for (const node of nodes) {
      if (parentId === ROOT_DROP_ID) {
        addToRoot(node, index);
      } else {
        addNode(node, parentId, index);
      }
      index++;
    }
  };

  return (
    <DragDropProvider
      onDragMove={({ operation }) => {
        const target = operation.target as Record<string, any> | undefined;
        const position = operation.position as unknown as { clientX: number; clientY: number } | undefined;

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

        const computedIndex = dropIndexRef.current;
        dropIndexRef.current = null;
        setIndicator(null);

        const source = event.operation.source;
        const target = event.operation.target;
        if (!source || !target) return;

        const sourceData = source.data as Record<string, any>;
        const targetData = target.data as Record<string, any>;
        const targetParentId = targetData?.type === 'container'
          ? (targetData.parentId as string | undefined)
          : undefined;
        if (!targetParentId) return;

        const getInsertIndex = (parentId: string) => {
          if (computedIndex !== null) return computedIndex;
          if (parentId === ROOT_DROP_ID) return schema.children?.length || 0;
          const parentNode = findNodeById(schema.children || [], parentId);
          return parentNode?.children?.length || 0;
        };

        if (sourceData?.type === 'new-component') {
          const material = sourceData.material as MaterialComponent;
          insertNodes(
            [createNodeFromMaterial(material)],
            targetParentId,
            getInsertIndex(targetParentId),
          );
          return;
        }

        if (sourceData?.type === 'snippet') {
          const snippetNodes = sourceData.snippet.nodes as LowCodeNode[];
          insertNodes(snippetNodes, targetParentId, getInsertIndex(targetParentId));
          return;
        }

        if (sourceData?.type === 'existing-node') {
          const nodeId = sourceData.nodeId as string;

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

          if (targetParentId !== ROOT_DROP_ID && isDescendant(schema.children || [], nodeId, targetParentId)) {
            return;
          }

          const targetIndex = getInsertIndex(targetParentId);
          if (targetParentId === ROOT_DROP_ID) {
            moveToRoot(nodeId, targetIndex);
          } else {
            moveNode(nodeId, targetParentId, targetIndex);
          }
        }
      }}
    >
      {children}
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
                  background: 'var(--color-primary-bg)',
                  border: '1px solid var(--color-primary)',
                  borderRadius: 6,
                  fontSize: 13,
                  color: 'var(--color-primary)',
                  opacity: 0.9,
                }}
              >
                {material.title}
              </div>
            );
          }
          if (data?.type === 'snippet') {
            const snippet = data.snippet;
            return (
              <div
                style={{
                  padding: '6px 12px',
                  background: 'var(--color-success-bg)',
                  border: '1px solid var(--color-success)',
                  borderRadius: 6,
                  fontSize: 13,
                  color: 'var(--color-success)',
                  opacity: 0.9,
                }}
              >
                {snippet.name}
              </div>
            );
          }
          if (data?.type === 'existing-node') {
            const node = findNodeById(
              schema.children || [],
              data.nodeId,
            );
            return (
              <div
                style={{
                  padding: '6px 12px',
                  background: 'var(--color-white)7e6',
                  border: '1px solid var(--color-warning)',
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
      {indicator && (
        <div
          style={{
            position: 'fixed',
            top: indicator.top,
            left: indicator.left,
            width: indicator.width,
            height: 2,
            background: 'var(--color-primary)',
            borderRadius: 1,
            boxShadow: '0 0 6px rgba(22,119,255,0.5)',
            zIndex: 10000,
            pointerEvents: 'none',
          }}
        />
      )}
    </DragDropProvider>
  );
};

export const Canvas: React.FC = () => {
  /** 画布缩放比例 */
  const [zoom, setZoom] = useState(100);
  /** 设备尺寸 (可自由编辑) */
  const [device, setDevice] = useState<DevicePreset>(DEVICE_PRESETS[0]);
  /** 自定义编辑宽高 */
  const [width, setWidth] = useState(DEVICE_PRESETS[0].width);
  const [height, setHeight] = useState(DEVICE_PRESETS[0].height);
  /** 横屏切换 */
  const [landscape, setLandscape] = useState(false);
  /** 设备像素比 */
  const [dpr, setDpr] = useState(DEVICE_PRESETS[0].dpr ?? 2);
  /** 自定义尺寸输入展开 */
  const [customSizeOpen, setCustomSizeOpen] = useState(false);
  const scale = zoom / 100;

  /** 应用预设设备 */
  const applyPreset = (preset: DevicePreset) => {
    setDevice(preset);
    setWidth(preset.width);
    setHeight(preset.height);
    setDpr(preset.dpr ?? 2);
    setLandscape(false);
  };

  /** 横屏时交换宽高 */
  const effectiveWidth = landscape ? height : width;
  const effectiveHeight = landscape ? width : height;

  /** 提交自定义尺寸 */
  const applyCustomSize = () => {
    if (!width || !height || width < 80 || height < 80) {
      message.warning('请输入有效的宽高（≥ 80）');
      return;
    }
    setDevice({ ...device, width, height });
  };

  return (
    <div
      style={{
        flex: 1,
        overflow: 'auto',
        background: EDITOR_COLORS.workspaceBg,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* 工具栏：缩放 + 设备切换 */}
      <div
        style={{
          minHeight: 44,
          padding: '6px 16px',
          borderBottom: `1px solid ${EDITOR_COLORS.border}`,
          background: EDITOR_COLORS.panelBg,
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
          fontSize: 12,
        }}
      >
        <span style={{ color: EDITOR_COLORS.textSecondary, whiteSpace: 'nowrap' }}>缩放</span>
        <Slider
          min={25}
          max={200}
          step={5}
          value={zoom}
          onChange={(value) => setZoom(value)}
          style={{ width: 120 }}
          tooltip={{ formatter: (v) => `${v}%` }}
        />
        <InputNumber
          size="small"
          min={25}
          max={200}
          value={zoom}
          onChange={(v) => v && setZoom(Number(v))}
          style={{ width: 60 }}
          formatter={(v) => `${v}%`}
          parser={(v) => Number(v?.replace('%', '')) as any}
        />
        <Space size={2}>
          {ZOOM_LEVELS.map((z) => (
            <a
              key={z}
              onClick={() => setZoom(z)}
              style={{
                fontSize: 11,
                color: zoom === z ? EDITOR_COLORS.primary : EDITOR_COLORS.textSecondary,
                padding: '1px 4px',
                borderRadius: 3,
                background: zoom === z ? `${EDITOR_COLORS.primary}10` : undefined,
                cursor: 'pointer',
              }}
            >
              {z}%
            </a>
          ))}
        </Space>
        <span style={{ color: EDITOR_COLORS.textSecondary, whiteSpace: 'nowrap' }}>设备</span>
        <Select
          size="small"
          style={{ minWidth: 160 }}
          value={device.label}
          showSearch
          optionFilterProp="label"
          options={DEVICE_OPTIONS}
          onChange={(value) => {
            const next = DEVICE_PRESETS.find((d) => d.label === value);
            if (next) applyPreset(next);
          }}
        />

        {/* 自定义尺寸展开/收起 */}
        <Tooltip title="自定义尺寸">
          <a
            onClick={() => setCustomSizeOpen((v) => !v)}
            style={{ color: customSizeOpen ? EDITOR_COLORS.primary : EDITOR_COLORS.textSecondary, display: 'inline-flex', alignItems: 'center' }}
          >
            <EditOutlined />
          </a>
        </Tooltip>

        {/* 横屏切换 */}
        <Tooltip title={landscape ? '切换为竖屏' : '切换为横屏'}>
          <Space size={4} style={{ display: 'inline-flex', alignItems: 'center' }}>
            <SwapOutlined style={{ color: EDITOR_COLORS.textSecondary }} />
            <Switch
              size="small"
              checked={landscape}
              onChange={(checked) => setLandscape(checked)}
            />
          </Space>
        </Tooltip>

        {/* 像素比 DPR */}
        <span style={{ color: EDITOR_COLORS.textSecondary, whiteSpace: 'nowrap' }}>DPR</span>
        <Segmented
          size="small"
          value={DPR_OPTIONS.includes(dpr) ? dpr : undefined}
          options={DPR_OPTIONS.map((v) => ({ label: `${v}`, value: v }))}
          onChange={(value) => {
            setDpr(Number(value));
          }}
        />
        <Tooltip title="精确像素比 (1–4)">
          <InputNumber
            size="small"
            min={1}
            max={4}
            step={0.125}
            style={{ width: 72 }}
            value={dpr}
            onChange={(value) => {
              if (value == null) return;
              setDpr(Number(value));
            }}
          />
        </Tooltip>

        <span
          style={{
            color: EDITOR_COLORS.textMuted,
            marginLeft: 'auto',
            minWidth: 120,
            textAlign: 'right',
            whiteSpace: 'nowrap',
          }}
        >
          {effectiveWidth} × {effectiveHeight} · DPR {dpr}
          {landscape ? ' · 横屏' : ''}
        </span>
      </div>

      {/* 自定义尺寸输入区 */}
      {customSizeOpen && (
        <div
          style={{
            padding: '8px 16px',
            borderBottom: `1px solid ${EDITOR_COLORS.border}`,
            background: EDITOR_COLORS.itemBg,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 12,
            flexWrap: 'wrap',
          }}
        >
          <span style={{ color: EDITOR_COLORS.textSecondary }}>宽度</span>
          <InputNumber
            size="small"
            min={80}
            max={4000}
            value={width}
            onChange={(v) => v && setWidth(Number(v))}
            style={{ width: 80 }}
          />
          <span style={{ color: EDITOR_COLORS.textSecondary }}>高度</span>
          <InputNumber
            size="small"
            min={80}
            max={4000}
            value={height}
            onChange={(v) => v && setHeight(Number(v))}
            style={{ width: 80 }}
          />
          <a onClick={applyCustomSize} style={{ color: EDITOR_COLORS.primary }}>
            应用
          </a>
          <Space size={6} style={{ marginLeft: 12 }}>
            {[
              { w: 320, h: 568 },
              { w: 375, h: 667 },
              { w: 414, h: 896 },
              { w: 768, h: 1024 },
              { w: 1024, h: 1366 },
            ].map((s) => (
              <a
                key={`${s.w}x${s.h}`}
                onClick={() => {
                  setWidth(s.w);
                  setHeight(s.h);
                  setDevice({ ...device, width: s.w, height: s.h });
                }}
                style={{
                  fontSize: 11,
                  color: EDITOR_COLORS.textSecondary,
                  padding: '2px 6px',
                  border: `1px solid ${EDITOR_COLORS.borderSubtle}`,
                  borderRadius: 4,
                }}
              >
                {s.w}×{s.h}
              </a>
            ))}
          </Space>
        </div>
      )}

      {/* 画布区域 */}
      <div
        style={{
          flex: 1,
          padding: EDITOR_LAYOUT.canvasPadding,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'flex-start',
        }}
      >
        <div
          style={{
            width: effectiveWidth * scale,
            minHeight: effectiveHeight * scale,
            position: 'relative',
          }}
        >
          <div
            style={{
              width: effectiveWidth,
              height: effectiveHeight,
              background: EDITOR_COLORS.panelBg,
              border: `1px solid ${EDITOR_COLORS.borderSubtle}`,
              borderRadius: EDITOR_LAYOUT.canvasRadius,
              boxShadow: '0 4px 16px rgba(15, 23, 42, 0.08)',
              overflow: 'hidden',
              position: 'relative',
              transform: `scale(${scale})`,
              transformOrigin: 'top left',
            }}
          >
            <SchemaRenderer />
          </div>
          <div
            style={{
              position: 'absolute',
              inset: 0,
              borderRadius: EDITOR_LAYOUT.canvasRadius,
              pointerEvents: 'none',
              boxShadow: `0 0 0 1px ${EDITOR_COLORS.border}`,
            }}
          />
        </div>
      </div>
    </div>
  );
};
