/** 物料面板 — 左侧组件列表 */

import React, { useState, useCallback } from 'react';
import { useDraggable } from '@dnd-kit/react';
import { Collapse, Input, Space, Typography, Select } from 'antd';
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
  CalendarOutlined,
  UserOutlined,
  TagOutlined,
  SmileOutlined,
  NumberOutlined,
  CheckSquareOutlined,
  CheckCircleOutlined,
  FieldTimeOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import { displayGroups } from '../materials';
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
  SearchOutlined: <SearchOutlined />,
  CalendarOutlined: <CalendarOutlined />,
  UserOutlined: <UserOutlined />,
  TagOutlined: <TagOutlined />,
  SmileOutlined: <SmileOutlined />,
  NumberOutlined: <NumberOutlined />,
  CheckSquareOutlined: <CheckSquareOutlined />,
  CheckCircleOutlined: <CheckCircleOutlined />,
  FieldTimeOutlined: <FieldTimeOutlined />,
  ArrowLeftOutlined: <ArrowLeftOutlined />,
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

/** 物料面板 */
interface ComponentPanelProps {
  /** 外部传入的容器 ref（供 EditorTour 锚点指向物料内容区） */
  containerRef?: React.RefObject<HTMLDivElement>;
}

export const ComponentPanel: React.FC<ComponentPanelProps> = ({ containerRef }) => {
  const [search, setSearch] = useState('');
  /** 分类下拉筛选（'all' = 所有组件） */
  const [groupFilter, setGroupFilter] = useState<string>('all');
  const [recentUsed, setRecentUsed] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('lowcode-recent-components') || '[]');
    } catch {
      return [];
    }
  });

  // 记录最近使用的组件
  const trackRecent = useCallback((componentName: string) => {
    setRecentUsed((prev) => {
      const updated = [componentName, ...prev.filter((c) => c !== componentName)].slice(0, 8);
      localStorage.setItem('lowcode-recent-components', JSON.stringify(updated));
      return updated;
    });
  }, []);

  /** 按分组 + 搜索过滤后的展示分组 */
  const visibleGroups = displayGroups
    .filter((g) => groupFilter === 'all' || g.key === groupFilter)
    .map((g) => ({
      ...g,
      materials: g.materials.filter(
        (m) =>
          !search ||
          m.title.includes(search) ||
          m.componentName.toLowerCase().includes(search.toLowerCase()) ||
          (COMPONENT_KEYWORDS[m.componentName] || []).some(
            (kw) => kw.includes(search) || search.includes(kw),
          ),
      ),
    }))
    .filter((g) => g.materials.length > 0);

  // 最近使用的组件列表（跨所有分组查找）
  const recentMaterials = recentUsed
    .map((name) => displayGroups.flatMap((g) => g.materials).find((m) => m.componentName === name))
    .filter(Boolean) as MaterialComponent[];

  /** 分类下拉选项 */
  const groupOptions = [
    { label: '所有组件', value: 'all' },
    ...displayGroups.map((g) => ({ label: g.label, value: g.key })),
  ];

  return (
    <div
      ref={containerRef}
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
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        {/* 分类下拉（对齐线框图「所有组件 / 基础组件」筛选器） */}
        <Select
          size="small"
          value={groupFilter}
          onChange={setGroupFilter}
          options={groupOptions}
          style={{ width: '100%' }}
        />
        <Input
          placeholder="搜索组件（名称/功能/场景）"
          prefix={<SearchOutlined style={{ color: EDITOR_COLORS.textMuted }} />}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          allowClear
          size="small"
        />
      </div>

      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: EDITOR_SPACING.panelPadding }}>
        {/* 最近使用（仅未筛选分类 + 未搜索时展示） */}
        {!search && groupFilter === 'all' && recentMaterials.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <Text type="secondary" style={{ fontSize: 12, marginBottom: 6, display: 'block' }}>
              最近使用
            </Text>
            <Space direction="vertical" style={{ width: '100%' }} size={EDITOR_SPACING.itemGap}>
              {recentMaterials.map((m) => (
                <DraggableMaterial key={`recent-${m.componentName}`} material={m} />
              ))}
            </Space>
          </div>
        )}

        <Collapse
          ghost
          defaultActiveKey={displayGroups.map((g) => g.key)}
          size="small"
          items={visibleGroups.map(({ key, label, materials }) => ({
            key,
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
      </div>
    </div>
  );
};
