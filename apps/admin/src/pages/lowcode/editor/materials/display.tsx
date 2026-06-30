/** 展示物料组件定义 */

import type { MaterialComponent } from '@hospital/shared';

export const displayMaterials: MaterialComponent[] = [
  {
    componentName: 'NutSwiper',
    title: '轮播',
    icon: 'PictureOutlined',
    category: 'display',
    defaultProps: {
      autoPlay: 3000,
      loop: true,
      pagination: true,
      height: '200px',
    },
    configureSchema: [
      { key: 'autoPlay', label: '自动播放间隔(ms)', type: 'number', defaultValue: 3000 },
      { key: 'loop', label: '循环播放', type: 'switch', defaultValue: true },
      { key: 'pagination', label: '显示指示器', type: 'switch', defaultValue: true },
      { key: 'height', label: '高度', type: 'input', defaultValue: '200px' },
    ],
  },
  {
    componentName: 'NutSwiperItem',
    title: '轮播项',
    icon: 'PictureOutlined',
    category: 'display',
    defaultProps: {},
    configureSchema: [],
  },
  {
    componentName: 'NutCell',
    title: '单元格',
    icon: 'UnorderedListOutlined',
    category: 'display',
    defaultProps: {
      title: '标题',
      description: '描述',
      isLink: false,
      center: false,
    },
    configureSchema: [
      { key: 'title', label: '标题', type: 'input', defaultValue: '标题' },
      { key: 'description', label: '描述', type: 'input', defaultValue: '' },
      { key: 'isLink', label: '显示箭头', type: 'switch', defaultValue: false },
      { key: 'center', label: '垂直居中', type: 'switch', defaultValue: false },
    ],
  },
  {
    componentName: 'NutCard',
    title: '卡片',
    icon: 'CreditCardOutlined',
    category: 'display',
    defaultProps: {
      title: '卡片标题',
      subTitle: '',
      description: '',
    },
    configureSchema: [
      { key: 'title', label: '标题', type: 'input', defaultValue: '卡片标题' },
      { key: 'subTitle', label: '副标题', type: 'input', defaultValue: '' },
      { key: 'description', label: '描述', type: 'textarea', defaultValue: '' },
    ],
  },
  {
    componentName: 'NutTabs',
    title: '标签页',
    icon: 'AppstoreOutlined',
    category: 'display',
    defaultProps: {
      value: '0',
    },
    configureSchema: [],
  },
  {
    componentName: 'NutTabPane',
    title: '标签面板',
    icon: 'AppstoreOutlined',
    category: 'display',
    defaultProps: {
      title: '标签',
      value: '0',
    },
    configureSchema: [
      { key: 'title', label: '标签名称', type: 'input', defaultValue: '标签' },
      { key: 'value', label: '标签值', type: 'input', defaultValue: '0' },
    ],
  },
  {
    componentName: 'NutEmpty',
    title: '空状态',
    icon: 'InboxOutlined',
    category: 'display',
    defaultProps: {
      description: '暂无数据',
    },
    configureSchema: [
      { key: 'description', label: '描述文字', type: 'input', defaultValue: '暂无数据' },
    ],
  },
  {
    componentName: 'NutIcon',
    title: '图标',
    icon: 'SmileOutlined',
    category: 'display',
    defaultProps: {
      name: 'star',
      size: '20px',
      color: 'var(--color-text)333',
    },
    configureSchema: [
      { key: 'name', label: '图标名称', type: 'input', defaultValue: 'star' },
      { key: 'size', label: '尺寸', type: 'input', defaultValue: '20px' },
      { key: 'color', label: '颜色', type: 'color', defaultValue: 'var(--color-text)333' },
    ],
  },
  {
    componentName: 'NutTag',
    title: '标签',
    icon: 'TagOutlined',
    category: 'display',
    defaultProps: {
      type: 'primary',
      text: '标签',
      color: '',
    },
    configureSchema: [
      {
        key: 'type',
        label: '类型',
        type: 'select',
        defaultValue: 'primary',
        options: [
          { label: '主要', value: 'primary' },
          { label: '成功', value: 'success' },
          { label: '危险', value: 'danger' },
          { label: '警告', value: 'warning' },
        ],
      },
      { key: 'text', label: '标签文字', type: 'input', defaultValue: '标签' },
      { key: 'color', label: '自定义颜色', type: 'color', defaultValue: '' },
    ],
  },
  {
    componentName: 'NutAvatar',
    title: '头像',
    icon: 'UserOutlined',
    category: 'display',
    defaultProps: {
      size: '40px',
      src: '',
      text: '',
    },
    configureSchema: [
      { key: 'size', label: '尺寸', type: 'input', defaultValue: '40px' },
      { key: 'src', label: '图片地址', type: 'image', defaultValue: '' },
      { key: 'text', label: '文字头像', type: 'input', defaultValue: '' },
    ],
  },
  {
    componentName: 'NutBadge',
    title: '徽标',
    icon: 'NumberOutlined',
    category: 'display',
    defaultProps: {
      value: 1,
      hidden: false,
    },
    configureSchema: [
      { key: 'value', label: '角标值', type: 'number', defaultValue: 1 },
      { key: 'hidden', label: '隐藏', type: 'switch', defaultValue: false },
    ],
  },
  {
    componentName: 'NutProgress',
    title: '进度条',
    icon: 'FieldTimeOutlined',
    category: 'display',
    defaultProps: {
      percent: 50,
      status: 'active',
      strokeWidth: '6px',
    },
    configureSchema: [
      { key: 'percent', label: '进度百分比', type: 'number', defaultValue: 50 },
      {
        key: 'status',
        label: '状态',
        type: 'select',
        defaultValue: 'active',
        options: [
          { label: '进行中', value: 'active' },
          { label: '已完成', value: 'success' },
          { label: '异常', value: 'error' },
        ],
      },
      { key: 'strokeWidth', label: '线条宽度', type: 'input', defaultValue: '6px' },
    ],
  },
  {
    componentName: 'NutDialog',
    title: '对话框',
    icon: '💬',
    category: 'display',
    defaultProps: {
      title: '提示',
      content: '这是一段内容',
      visible: false,
      confirmText: '确定',
      cancelText: '取消',
    },
    configureSchema: [
      { key: 'title', label: '标题', type: 'input', defaultValue: '提示' },
      { key: 'content', label: '内容', type: 'textarea', defaultValue: '这是一段内容' },
      { key: 'confirmText', label: '确定按钮', type: 'input', defaultValue: '确定' },
      { key: 'cancelText', label: '取消按钮', type: 'input', defaultValue: '取消' },
      { key: 'visible', label: '显示', type: 'switch', defaultValue: false },
    ],
  },
];
