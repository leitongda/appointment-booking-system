/** 基础物料组件定义 */

import type { MaterialComponent } from '@hospital/shared';

export const basicMaterials: MaterialComponent[] = [
  {
    componentName: 'NutText',
    title: '文本',
    icon: 'FontSizeOutlined',
    category: 'basic',
    defaultProps: {
      text: '文本内容',
      fontSize: '14px',
      color: '#333333',
      fontWeight: 'normal',
      textAlign: 'left',
    },
    configureSchema: [
      { key: 'text', label: '文本内容', type: 'textarea' },
      { key: 'fontSize', label: '字号', type: 'input', defaultValue: '14px' },
      { key: 'color', label: '颜色', type: 'color', defaultValue: '#333333' },
      {
        key: 'fontWeight',
        label: '字重',
        type: 'select',
        defaultValue: 'normal',
        options: [
          { label: '正常', value: 'normal' },
          { label: '加粗', value: 'bold' },
        ],
      },
      {
        key: 'textAlign',
        label: '对齐',
        type: 'select',
        defaultValue: 'left',
        options: [
          { label: '左对齐', value: 'left' },
          { label: '居中', value: 'center' },
          { label: '右对齐', value: 'right' },
        ],
      },
    ],
  },
  {
    componentName: 'NutImage',
    title: '图片',
    icon: 'PictureOutlined',
    category: 'basic',
    defaultProps: {
      src: '',
      width: '100%',
      height: 'auto',
      fit: 'cover',
      borderRadius: '0',
    },
    configureSchema: [
      { key: 'src', label: '图片地址', type: 'image' },
      { key: 'width', label: '宽度', type: 'input', defaultValue: '100%' },
      { key: 'height', label: '高度', type: 'input', defaultValue: 'auto' },
      {
        key: 'fit',
        label: '填充模式',
        type: 'select',
        defaultValue: 'cover',
        options: [
          { label: '填充', value: 'contain' },
          { label: '铺满', value: 'cover' },
          { label: '拉伸', value: 'fill' },
          { label: '原图', value: 'none' },
        ],
      },
      { key: 'borderRadius', label: '圆角', type: 'input', defaultValue: '0' },
    ],
  },
  {
    componentName: 'NutButton',
    title: '按钮',
    icon: 'ButtonOutlined',
    category: 'basic',
    defaultProps: {
      text: '按钮',
      type: 'primary',
      block: false,
      disabled: false,
    },
    configureSchema: [
      { key: 'text', label: '按钮文字', type: 'input', defaultValue: '按钮' },
      {
        key: 'type',
        label: '类型',
        type: 'select',
        defaultValue: 'primary',
        options: [
          { label: '主要', value: 'primary' },
          { label: '默认', value: 'default' },
          { label: '警告', value: 'warning' },
          { label: '危险', value: 'danger' },
        ],
      },
      { key: 'block', label: '块级按钮', type: 'switch', defaultValue: false },
      { key: 'disabled', label: '禁用', type: 'switch', defaultValue: false },
    ],
  },
  {
    componentName: 'NutDivider',
    title: '分割线',
    icon: 'LineOutlined',
    category: 'basic',
    defaultProps: {
      contentPosition: 'center',
      dashed: false,
    },
    configureSchema: [
      {
        key: 'contentPosition',
        label: '位置',
        type: 'select',
        defaultValue: 'center',
        options: [
          { label: '居中', value: 'center' },
          { label: '左', value: 'left' },
          { label: '右', value: 'right' },
        ],
      },
      { key: 'dashed', label: '虚线', type: 'switch', defaultValue: false },
    ],
  },
];
