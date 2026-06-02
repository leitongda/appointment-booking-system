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
];
