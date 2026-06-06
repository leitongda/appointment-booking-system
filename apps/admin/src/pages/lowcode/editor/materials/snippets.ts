/** 组件模板/Snippet — 常用组件组合模板，拖入画布时展开为完整组件树 */

import type { LowCodeNode } from '@hospital/shared';

export interface SnippetTemplate {
  /** 唯一标识 */
  id: string;
  /** 显示名称 */
  name: string;
  /** 描述 */
  description: string;
  /** 图标 (Ant Design icon name) */
  icon: string;
  /** 展开后的组件树 */
  nodes: LowCodeNode[];
}

/** 生成唯一节点 ID */
function nid(): string {
  return `node_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

// ---------------------------------------------------------------------------
// Snippet definitions
// ---------------------------------------------------------------------------

/** 表单组：标签 + 输入框 + 验证提示 */
function formGroupSnippet(): LowCodeNode[] {
  const formId = nid();
  const inputId = nid();
  return [
    {
      id: formId,
      componentName: 'NutForm',
      props: { border: true },
      children: [
        {
          id: inputId,
          componentName: 'NutInput',
          props: {
            label: '姓名',
            placeholder: '请输入姓名',
            required: true,
          },
        },
      ],
    },
  ];
}

/** 列表项：标题 + 描述 + 右侧箭头 */
function listItemSnippet(): LowCodeNode[] {
  return [
    {
      id: nid(),
      componentName: 'NutCell',
      props: {
        title: '列表项标题',
        description: '这是列表项的描述信息',
        isLink: true,
      },
    },
  ];
}

/** 卡片布局：图片 + 标题 + 描述 + 按钮 */
function cardLayoutSnippet(): LowCodeNode[] {
  const cardId = nid();
  return [
    {
      id: cardId,
      componentName: 'NutCard',
      props: {
        title: '卡片标题',
        subTitle: '副标题',
        description: '这是卡片的描述内容，可以放置较长的文本。',
      },
      children: [
        {
          id: nid(),
          componentName: 'NutButton',
          props: {
            text: '查看详情',
            type: 'primary',
            block: true,
          },
        },
      ],
    },
  ];
}

/** 搜索栏 + 列表 */
function searchListSnippet(): LowCodeNode[] {
  const viewId = nid();
  return [
    {
      id: viewId,
      componentName: 'NutView',
      props: {},
      children: [
        {
          id: nid(),
          componentName: 'NutSearchBar',
          props: { placeholder: '搜索内容' },
        },
        {
          id: nid(),
          componentName: 'NutCell',
          props: { title: '搜索结果项 1', isLink: true },
        },
        {
          id: nid(),
          componentName: 'NutCell',
          props: { title: '搜索结果项 2', isLink: true },
        },
      ],
    },
  ];
}

/** 标签页布局 */
function tabsLayoutSnippet(): LowCodeNode[] {
  const tabsId = nid();
  const pane1Id = nid();
  const pane2Id = nid();
  return [
    {
      id: tabsId,
      componentName: 'NutTabs',
      props: {},
      children: [
        {
          id: pane1Id,
          componentName: 'NutTabPane',
          props: { title: '标签一' },
          children: [
            {
              id: nid(),
              componentName: 'NutText',
              props: { text: '标签一的内容' },
            },
          ],
        },
        {
          id: pane2Id,
          componentName: 'NutTabPane',
          props: { title: '标签二' },
          children: [
            {
              id: nid(),
              componentName: 'NutText',
              props: { text: '标签二的内容' },
            },
          ],
        },
      ],
    },
  ];
}

/** 轮播图 */
function swiperSnippet(): LowCodeNode[] {
  const swiperId = nid();
  return [
    {
      id: swiperId,
      componentName: 'NutSwiper',
      props: { height: '200px', autoPlay: true },
      children: [
        {
          id: nid(),
          componentName: 'NutSwiperItem',
          props: {},
          children: [
            {
              id: nid(),
              componentName: 'NutImage',
              props: { width: '100%', height: '200px', fit: 'cover' },
            },
          ],
        },
        {
          id: nid(),
          componentName: 'NutSwiperItem',
          props: {},
          children: [
            {
              id: nid(),
              componentName: 'NutImage',
              props: { width: '100%', height: '200px', fit: 'cover' },
            },
          ],
        },
      ],
    },
  ];
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

export const snippetTemplates: SnippetTemplate[] = [
  {
    id: 'form-group',
    name: '表单组',
    description: '包含标签和输入框的表单组件',
    icon: 'FormOutlined',
    nodes: formGroupSnippet(),
  },
  {
    id: 'list-item',
    name: '列表项',
    description: '带标题、描述和箭头的列表单元格',
    icon: 'UnorderedListOutlined',
    nodes: listItemSnippet(),
  },
  {
    id: 'card-layout',
    name: '卡片布局',
    description: '包含标题、描述和操作按钮的卡片',
    icon: 'CreditCardOutlined',
    nodes: cardLayoutSnippet(),
  },
  {
    id: 'search-list',
    name: '搜索列表',
    description: '搜索栏 + 列表项组合',
    icon: 'AppstoreOutlined',
    nodes: searchListSnippet(),
  },
  {
    id: 'tabs-layout',
    name: '标签页',
    description: '多标签页切换布局',
    icon: 'AppstoreOutlined',
    nodes: tabsLayoutSnippet(),
  },
  {
    id: 'swiper',
    name: '轮播图',
    description: '自动播放的图片轮播组件',
    icon: 'PictureOutlined',
    nodes: swiperSnippet(),
  },
];
