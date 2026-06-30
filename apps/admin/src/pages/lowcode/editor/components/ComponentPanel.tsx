/** 物料面板 — 左侧组件列表 */

import React, { useState, useEffect, useCallback } from 'react';
import { useDraggable } from '@dnd-kit/react';
import { Collapse, Input, Space, Typography, Button, Popconfirm, message } from 'antd';
import {
  FontSizeOutlined,
  PictureOutlined,
  BlockOutlined,
  LineOutlined,
  BorderOuterOutlined,
  ColumnHeightOutlined,
  ColumnWidthOutlined,
  UnorderedListOutlined,
  CreditCardOutlined,
  AppstoreOutlined,
  InboxOutlined,
  EditOutlined,
  FormOutlined,
  SwitcherOutlined,
  DownSquareOutlined,
  SearchOutlined,
  DeleteOutlined,
  StarOutlined,
} from '@ant-design/icons';
import { materialsByCategory, categoryLabels } from '../materials';
import { snippetTemplates } from '../materials/snippets';
import type { SnippetTemplate } from '../materials/snippets';
import { loadCustomSnippets, deleteCustomSnippet, type CustomSnippet } from '../utils/customSnippets';
import type { MaterialComponent } from '@hospital/shared';
import { EDITOR_COLORS, EDITOR_SPACING } from '../constants';

const { Text } = Typography;

const iconMap: Record<string, React.ReactNode> = {
  FontSizeOutlined: <FontSizeOutlined />,
  PictureOutlined: <PictureOutlined />,
  ButtonOutlined: <BlockOutlined />,
  LineOutlined: <LineOutlined />,
  BorderOuterOutlined: <BorderOuterOutlined />,
  ColumnHeightOutlined: <ColumnHeightOutlined />,
  ColumnWidthOutlined: <ColumnWidthOutlined />,
  UnorderedListOutlined: <UnorderedListOutlined />,
  CreditCardOutlined: <CreditCardOutlined />,
  AppstoreOutlined: <AppstoreOutlined />,
  InboxOutlined: <InboxOutlined />,
  EditOutlined: <EditOutlined />,
  FormOutlined: <FormOutlined />,
  SwitcherOutlined: <SwitcherOutlined />,
  DownSquareOutlined: <DownSquareOutlined />,
};

interface MaterialListItemProps {
  accentColor: string;
  description?: string;
  handleProps?: React.HTMLAttributes<HTMLDivElement>;
  hoverBg: string;
  icon: React.ReactNode;
  title: string;
}

const MaterialListItem = React.forwardRef<HTMLDivElement, MaterialListItemProps>(
  ({ accentColor, description, handleProps, hoverBg, icon, title }, ref) => (
    <div
      ref={ref}
      {...handleProps}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        minHeight: 34,
        padding: '6px 8px',
        cursor: 'grab',
        borderRadius: 6,
        border: `1px solid ${EDITOR_COLORS.borderSubtle}`,
        background: EDITOR_COLORS.itemBg,
        transition: 'background 0.16s, border-color 0.16s, box-shadow 0.16s',
        userSelect: 'none',
        ...handleProps?.style,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = accentColor;
        e.currentTarget.style.background = hoverBg;
        e.currentTarget.style.boxShadow = '0 1px 4px rgba(15, 23, 42, 0.06)';
        handleProps?.onMouseEnter?.(e);
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = EDITOR_COLORS.borderSubtle;
        e.currentTarget.style.background = EDITOR_COLORS.itemBg;
        e.currentTarget.style.boxShadow = 'none';
        handleProps?.onMouseLeave?.(e);
      }}
    >
      <span style={{ fontSize: 16, color: accentColor, flexShrink: 0 }}>
        {icon}
      </span>
      <div style={{ minWidth: 0 }}>
        <Text ellipsis style={{ fontSize: 13, display: 'block', lineHeight: '18px' }}>
          {title}
        </Text>
        {description && (
          <Text type="secondary" ellipsis style={{ fontSize: 11, lineHeight: '16px', display: 'block' }}>
            {description}
          </Text>
        )}
      </div>
    </div>
  ),
);

MaterialListItem.displayName = 'MaterialListItem';

/** 单个可拖拽物料项 */
function DraggableMaterial({ material, onUse }: { material: MaterialComponent; onUse?: () => void }) {
  // 组件被渲染时记录使用
  React.useEffect(() => {
    onUse?.();
  }, []);

  const { ref, handleRef } = useDraggable({
    id: `material-${material.componentName}`,
    data: {
      type: 'new-component',
      material,
    },
  });
  const setDragRefs = React.useCallback(
    (element: HTMLDivElement | null) => {
      ref(element);
      handleRef(element);
    },
    [handleRef, ref],
  );

  return (
    <MaterialListItem
      ref={setDragRefs}
      accentColor={EDITOR_COLORS.primary}
      hoverBg={EDITOR_COLORS.itemHoverBg}
      icon={iconMap[material.icon] || <AppstoreOutlined />}
      title={material.title}
    />
  );
}

/** 组件搜索关键词映射（按功能/场景分类） */
const COMPONENT_KEYWORDS: Record<string, string[]> = {
  NutText: ['文字', '标题', '段落', 'label', 'text'],
  NutImage: ['图片', '照片', '头像', 'image', 'img'],
  NutButton: ['按钮', '操作', '提交', 'button', 'btn'],
  NutDivider: ['分割线', '间距', 'divider'],
  NutSearchBar: ['搜索', '查找', 'search'],
  NutNavBar: ['导航栏', '标题栏', 'nav', 'header'],
  NutView: ['容器', '布局', 'div', 'view', 'box'],
  NutRow: ['行', '栅格', 'flex', 'row'],
  NutCol: ['列', '栅格', 'grid', 'col', 'column'],
  NutSwiper: ['轮播', '走马灯', 'swiper', 'carousel'],
  NutCell: ['单元格', '列表项', 'cell', 'list-item'],
  NutCard: ['卡片', 'card', 'panel'],
  NutTabs: ['标签页', '选项卡', 'tabs', 'tab'],
  NutEmpty: ['空状态', '无数据', 'empty'],
  NutIcon: ['图标', 'icon'],
  NutTag: ['标签', '标记', 'tag', 'badge'],
  NutAvatar: ['头像', '用户头像', 'avatar'],
  NutBadge: ['徽标', '角标', '数量', 'badge', 'count'],
  NutProgress: ['进度条', '进度', 'progress'],
  NutInput: ['输入框', '文本框', 'input', 'text'],
  NutTextarea: ['多行输入', '文本域', 'textarea'],
  NutSwitch: ['开关', '切换', 'switch', 'toggle'],
  NutPicker: ['选择器', '下拉', 'picker', 'select'],
  NutForm: ['表单', 'form'],
  NutCheckbox: ['复选框', '多选', 'checkbox'],
  NutRadio: ['单选框', '单选', 'radio'],
  NutDatePicker: ['日期选择', '日期', 'date', 'picker'],
  NutCalendar: ['日历', '日期', 'calendar'],
  BizAppointmentCard: ['预约', '挂号', ' appointment', '卡片', 'card'],
  BizDoctorCard: ['医生', 'doctor', '医师', '专家', 'card'],
  BizDepartmentPicker: ['科室', 'department', '选择器', 'picker'],
  BizTimeSlotPicker: ['时间段', 'time slot', '时间', '选择器', 'picker'],
};

/** 单个可拖拽 Snippet 项 */
function DraggableSnippet({ snippet }: { snippet: SnippetTemplate }) {
  const { ref, handleRef } = useDraggable({
    id: `snippet-${snippet.id}`,
    data: {
      type: 'snippet',
      snippet,
    },
  });
  const setDragRefs = React.useCallback(
    (element: HTMLDivElement | null) => {
      ref(element);
      handleRef(element);
    },
    [handleRef, ref],
  );

  return (
    <MaterialListItem
      ref={setDragRefs}
      accentColor="var(--color-success)"
      hoverBg="#f0fdf4"
      icon={iconMap[snippet.icon] || <AppstoreOutlined />}
      title={snippet.name}
      description={snippet.description}
    />
  );
}

/** 单个可拖拽自定义 Snippet 项 */
function DraggableCustomSnippet({ snippet, onDelete }: { snippet: CustomSnippet; onDelete: (id: string) => void }) {
  const { ref, handleRef } = useDraggable({
    id: `custom-snippet-${snippet.id}`,
    data: {
      type: 'snippet',
      snippet: {
        id: snippet.id,
        name: snippet.name,
        description: '自定义模板',
        icon: 'StarOutlined',
        nodes: snippet.nodes,
      },
    },
  });
  const setDragRefs = React.useCallback(
    (element: HTMLDivElement | null) => {
      ref(element);
      handleRef(element);
    },
    [handleRef, ref],
  );

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <div style={{ flex: 1 }}>
        <MaterialListItem
          ref={setDragRefs}
          accentColor="var(--color-warning)"
          hoverBg="var(--color-white)be6"
          icon={<StarOutlined />}
          title={snippet.name}
          description="自定义模板"
        />
      </div>
      <Popconfirm
        title="确定删除此模板？"
        onConfirm={() => onDelete(snippet.id)}
        okText="删除"
        cancelText="取消"
      >
        <Button
          type="text"
          size="small"
          icon={<DeleteOutlined />}
          style={{ color: 'var(--color-text-tertiary)', flexShrink: 0 }}
        />
      </Popconfirm>
    </div>
  );
}

/** 物料面板 */
export const ComponentPanel: React.FC = () => {
  const [search, setSearch] = useState('');
  const [recentUsed, setRecentUsed] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('lowcode-recent-components') || '[]');
    } catch {
      return [];
    }
  });
  const [customSnippets, setCustomSnippets] = useState<CustomSnippet[]>([]);

  // 加载自定义 snippets
  const refreshCustomSnippets = useCallback(() => {
    setCustomSnippets(loadCustomSnippets());
  }, []);

  useEffect(() => {
    refreshCustomSnippets();
    // 监听 storage 事件，跨 tab 同步
    const handleStorage = (e: StorageEvent) => {
      if (e.key?.includes('lowcode-custom-snippets')) {
        refreshCustomSnippets();
      }
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, [refreshCustomSnippets]);

  // 删除自定义 snippet
  const handleDeleteCustomSnippet = useCallback((id: string) => {
    deleteCustomSnippet(id);
    refreshCustomSnippets();
    message.success('已删除 Snippet');
  }, [refreshCustomSnippets]);

  // 记录最近使用的组件
  const trackRecent = (componentName: string) => {
    const updated = [componentName, ...recentUsed.filter((c) => c !== componentName)].slice(0, 8);
    setRecentUsed(updated);
    localStorage.setItem('lowcode-recent-components', JSON.stringify(updated));
  };

  const filteredCategories = Object.entries(materialsByCategory).map(
    ([category, materials]) => ({
      category,
      label: categoryLabels[category] || category,
      materials: materials.filter(
        (m) =>
          !search ||
          m.title.includes(search) ||
          m.componentName.toLowerCase().includes(search.toLowerCase()) ||
          (COMPONENT_KEYWORDS[m.componentName] || []).some(
            (kw) => kw.includes(search) || search.includes(kw),
          ),
      ),
    }),
  );

  // 最近使用的组件列表
  const recentMaterials = recentUsed
    .map((name) => {
      for (const materials of Object.values(materialsByCategory)) {
        const found = materials.find((m) => m.componentName === name);
        if (found) return found;
      }
      return null;
    })
    .filter(Boolean);

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        background: EDITOR_COLORS.panelBg,
      }}
    >
      <div
        style={{
          padding: EDITOR_SPACING.panelPadding,
          paddingBottom: 8,
          borderBottom: `1px solid ${EDITOR_COLORS.borderSubtle}`,
          flexShrink: 0,
        }}
      >
        <Input
          placeholder="搜索组件（支持名称/功能/场景）"
          prefix={<SearchOutlined style={{ color: EDITOR_COLORS.textMuted }} />}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          allowClear
          size="small"
        />
      </div>

      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: EDITOR_SPACING.panelPadding }}>

      {/* 最近使用 */}
      {!search && recentMaterials.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 12, marginBottom: 6, display: 'block' }}>
            最近使用
          </Text>
          <Space direction="vertical" style={{ width: '100%' }} size={EDITOR_SPACING.itemGap}>
            {recentMaterials.map((m) => (
              <DraggableMaterial
                key={`recent-${m!.componentName}`}
                material={m!}
              />
            ))}
          </Space>
        </div>
      )}

      <Collapse
        ghost
        defaultActiveKey={Object.keys(categoryLabels)}
        size="small"
        items={filteredCategories.map(({ category, label, materials }) => ({
          key: category,
          label: (
            <Text strong style={{ fontSize: 13 }}>
              {label} ({materials.length})
            </Text>
          ),
          children: (
            <Space direction="vertical" style={{ width: '100%' }} size={EDITOR_SPACING.itemGap}>
              {materials.map((material) => (
                <DraggableMaterial
                  key={material.componentName}
                  material={material}
                  onUse={() => trackRecent(material.componentName)}
                />
              ))}
            </Space>
          ),
        }))}
      />

      {/* 模板/Snippet 面板 */}
      {!search && (
        <div style={{ marginTop: 12 }}>
          <Collapse
            ghost
            defaultActiveKey={[]}
            size="small"
            items={[
              {
                key: 'snippets',
                label: (
                  <Text strong style={{ fontSize: 13 }}>
                    模板 ({snippetTemplates.length})
                  </Text>
                ),
                children: (
                  <Space direction="vertical" style={{ width: '100%' }} size={EDITOR_SPACING.itemGap}>
                    {snippetTemplates.map((snippet) => (
                      <DraggableSnippet
                        key={snippet.id}
                        snippet={snippet}
                      />
                    ))}
                  </Space>
                ),
              },
              ...(customSnippets.length > 0 ? [{
                key: 'custom-snippets',
                label: (
                  <Text strong style={{ fontSize: 13 }}>
                    <StarOutlined style={{ marginRight: 4, color: 'var(--color-warning)' }} />
                    我的模板 ({customSnippets.length})
                  </Text>
                ),
                children: (
                  <Space direction="vertical" style={{ width: '100%' }} size={EDITOR_SPACING.itemGap}>
                    {customSnippets.map((snippet) => (
                      <DraggableCustomSnippet
                        key={snippet.id}
                        snippet={snippet}
                        onDelete={handleDeleteCustomSnippet}
                      />
                    ))}
                  </Space>
                ),
              }] : []),
            ]}
          />
        </div>
      )}
      </div>
    </div>
  );
};
