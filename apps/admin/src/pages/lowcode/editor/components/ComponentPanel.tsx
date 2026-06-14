/** 物料面板 — 左侧组件列表 */

import React, { useState } from 'react';
import { useDraggable } from '@dnd-kit/react';
import { Card, Collapse, Input, Space, Typography } from 'antd';
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
} from '@ant-design/icons';
import { materialsByCategory, categoryLabels } from '../materials';
import { snippetTemplates } from '../materials/snippets';
import type { SnippetTemplate } from '../materials/snippets';
import type { MaterialComponent } from '@hospital/shared';

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

/** 单个可拖拽物料项 */
function DraggableMaterial({ material, onUse }: { material: MaterialComponent; onUse?: () => void }) {
  // 组件被渲染时记录使用
  React.useEffect(() => {
    onUse?.();
  }, []);

  const { ref, handle } = useDraggable({
    id: `material-${material.componentName}`,
    data: {
      type: 'new-component',
      material,
    },
  });

  return (
    <div
      ref={ref}
      {...handle}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '8px 12px',
        cursor: 'grab',
        borderRadius: 6,
        border: '1px solid #f0f0f0',
        background: '#fafafa',
        transition: 'all 0.2s',
        userSelect: 'none',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = '#1677ff';
        e.currentTarget.style.background = '#e6f4ff';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = '#f0f0f0';
        e.currentTarget.style.background = '#fafafa';
      }}
    >
      <span style={{ fontSize: 16, color: '#1677ff' }}>
        {iconMap[material.icon] || <AppstoreOutlined />}
      </span>
      <Text style={{ fontSize: 13 }}>{material.title}</Text>
    </div>
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
  const { ref, handle } = useDraggable({
    id: `snippet-${snippet.id}`,
    data: {
      type: 'snippet',
      snippet,
    },
  });

  return (
    <div
      ref={ref}
      {...handle}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '8px 12px',
        cursor: 'grab',
        borderRadius: 6,
        border: '1px solid #f0f0f0',
        background: '#fafafa',
        transition: 'all 0.2s',
        userSelect: 'none',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = '#52c41a';
        e.currentTarget.style.background = '#f6ffed';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = '#f0f0f0';
        e.currentTarget.style.background = '#fafafa';
      }}
    >
      <span style={{ fontSize: 16, color: '#52c41a' }}>
        {iconMap[snippet.icon] || <AppstoreOutlined />}
      </span>
      <div>
        <Text style={{ fontSize: 13, display: 'block' }}>{snippet.name}</Text>
        <Text type="secondary" style={{ fontSize: 11 }}>{snippet.description}</Text>
      </div>
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
    <div style={{ padding: 12 }}>
      <Input
        placeholder="搜索组件（支持名称/功能/场景）"
        prefix={<span style={{ color: '#bbb' }}>🔍</span>}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        allowClear
        size="small"
        style={{ marginBottom: 12 }}
      />

      {/* 最近使用 */}
      {!search && recentMaterials.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 12, marginBottom: 6, display: 'block' }}>
            最近使用
          </Text>
          <Space wrap size={6}>
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
            <Space direction="vertical" style={{ width: '100%' }} size={6}>
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
            items={[{
              key: 'snippets',
              label: (
                <Text strong style={{ fontSize: 13 }}>
                  模板 ({snippetTemplates.length})
                </Text>
              ),
              children: (
                <Space direction="vertical" style={{ width: '100%' }} size={6}>
                  {snippetTemplates.map((snippet) => (
                    <DraggableSnippet
                      key={snippet.id}
                      snippet={snippet}
                    />
                  ))}
                </Space>
              ),
            }]}
          />
        </div>
      )}
    </div>
  );
};
