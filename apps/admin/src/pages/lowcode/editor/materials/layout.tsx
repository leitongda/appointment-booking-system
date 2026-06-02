/** 布局物料组件定义 */

import type { MaterialComponent } from '@hospital/shared';

export const layoutMaterials: MaterialComponent[] = [
  {
    componentName: 'NutView',
    title: '布局容器',
    icon: 'BorderOuterOutlined',
    category: 'layout',
    defaultProps: {
      padding: '10px',
      margin: '0',
      backgroundColor: 'transparent',
      borderRadius: '0',
    },
    configureSchema: [
      { key: 'padding', label: '内边距', type: 'input', defaultValue: '10px' },
      { key: 'margin', label: '外边距', type: 'input', defaultValue: '0' },
      { key: 'backgroundColor', label: '背景色', type: 'color', defaultValue: 'transparent' },
      { key: 'borderRadius', label: '圆角', type: 'input', defaultValue: '0' },
    ],
  },
  {
    componentName: 'NutRow',
    title: '栅格行',
    icon: 'ColumnHeightOutlined',
    category: 'layout',
    defaultProps: {
      gutter: '0',
      justify: 'start',
      align: 'center',
    },
    configureSchema: [
      { key: 'gutter', label: '间距', type: 'number', defaultValue: 0 },
      {
        key: 'justify',
        label: '水平排列',
        type: 'select',
        defaultValue: 'start',
        options: [
          { label: '起始', value: 'start' },
          { label: '居中', value: 'center' },
          { label: '末尾', value: 'end' },
          { label: '两端对齐', value: 'between' },
        ],
      },
      {
        key: 'align',
        label: '垂直对齐',
        type: 'select',
        defaultValue: 'center',
        options: [
          { label: '顶部', value: 'start' },
          { label: '居中', value: 'center' },
          { label: '底部', value: 'end' },
        ],
      },
    ],
  },
  {
    componentName: 'NutCol',
    title: '栅格列',
    icon: 'ColumnWidthOutlined',
    category: 'layout',
    defaultProps: {
      span: 12,
    },
    configureSchema: [
      {
        key: 'span',
        label: '列宽(24分)',
        type: 'number',
        defaultValue: 12,
      },
    ],
  },
];
