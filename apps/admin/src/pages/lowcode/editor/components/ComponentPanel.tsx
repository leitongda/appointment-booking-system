/** 物料面板 — 左侧组件列表 */

import React, { useState } from 'react';
import { useDraggable } from '@dnd-kit/react';
import { Card, Collapse, Input, Space, Typography } from 'antd';
import {
  FontSizeOutlined,
  PictureOutlined,
  ButtonOutlined,
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
import type { MaterialComponent } from '@hospital/shared';

const { Text } = Typography;

const iconMap: Record<string, React.ReactNode> = {
  FontSizeOutlined: <FontSizeOutlined />,
  PictureOutlined: <PictureOutlined />,
  ButtonOutlined: <ButtonOutlined />,
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
function DraggableMaterial({ material }: { material: MaterialComponent }) {
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

/** 物料面板 */
export const ComponentPanel: React.FC = () => {
  const [search, setSearch] = useState('');

  const filteredCategories = Object.entries(materialsByCategory).map(
    ([category, materials]) => ({
      category,
      label: categoryLabels[category] || category,
      materials: materials.filter(
        (m) =>
          !search ||
          m.title.includes(search) ||
          m.componentName.toLowerCase().includes(search.toLowerCase()),
      ),
    }),
  );

  return (
    <div style={{ padding: 12 }}>
      <Input
        placeholder="搜索组件"
        prefix={<span style={{ color: '#bbb' }}>🔍</span>}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        allowClear
        size="small"
        style={{ marginBottom: 12 }}
      />
      <Collapse
        ghost
        defaultActiveKey={Object.keys(categoryLabels)}
        size="small"
      >
        {filteredCategories.map(({ category, label, materials }) => (
          <Collapse.Panel
            key={category}
            header={
              <Text strong style={{ fontSize: 13 }}>
                {label} ({materials.length})
              </Text>
            }
          >
            <Space direction="vertical" style={{ width: '100%' }} size={6}>
              {materials.map((material) => (
                <DraggableMaterial
                  key={material.componentName}
                  material={material}
                />
              ))}
            </Space>
          </Collapse.Panel>
        ))}
      </Collapse>
    </div>
  );
};
