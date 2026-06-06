/** 低代码页面类型定义 */

// ---------------------------------------------------------------------------
// Data binding types
// ---------------------------------------------------------------------------

/** 数据源类型判别字段 */
export type DataSourceType = 'api' | 'static' | 'mock';

/** 数据源基类 */
export interface DataSourceBase {
  id: string;
  /** 数据源显示名称 */
  name?: string;
  /** 数据源类型，用于判别联合 */
  type: DataSourceType;
}

/** API 数据源定义 */
export interface ApiDataSource extends DataSourceBase {
  type: 'api';
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  url: string;
  headers?: Record<string, string>;
  params?: Record<string, any>;
  /** 从响应中提取数据的路径，如 "data.list" */
  dataPath?: string;
  /** 轮询间隔（毫秒），0 或 undefined 表示不轮询 */
  pollingInterval?: number;
  /** 是否手动触发，默认 false（页面加载时自动请求） */
  manual?: boolean;
}

/** 静态数据源定义 */
export interface StaticDataSource extends DataSourceBase {
  type: 'static';
  /** 静态数据内容 */
  data: any;
}

/** Mock 数据源定义 */
export interface MockDataSource extends DataSourceBase {
  type: 'mock';
  /** Mock 数据内容 */
  data: any;
  /** 模拟延迟（毫秒） */
  delay?: number;
}

/** 所有数据源类型的联合 */
export type DataSource = ApiDataSource | StaticDataSource | MockDataSource;

/** 事件动作类型 */
export interface EventAction {
  type: 'setData' | 'fetchApi' | 'navigate' | 'showToast' | 'updateVariable';
  payload: Record<string, any>;
}

/** 事件处理器 */
export interface EventHandler {
  event: string;
  actions: EventAction[];
}

/** 循环渲染配置 */
export interface LoopConfig {
  /** 数据源表达式，如 "{{api.users.data}}" */
  dataSource: string;
  /** 循环项变量名，默认 "item" */
  itemName?: string;
  /** 循环索引变量名，默认 "index" */
  indexName?: string;
}

/** 数据绑定配置 */
export interface DataBindingConfig {
  /** 属性到表达式的映射，如 { "text": "{{state.title}}" } */
  bindings: Record<string, string>;
  /** 关联事件 */
  events?: EventHandler[];
}

/** 页面级数据源定义 */
export type PageDataSource = ApiDataSource;

// ---------------------------------------------------------------------------
// Page status
// ---------------------------------------------------------------------------

/** 页面状态 */
export type LowCodePageStatus = 0 | 1 | 2; // draft | published | archived

/** 低代码页面 */
export interface LowCodePage {
  id: string;
  tenantId: string;
  name: string;
  slug: string;
  description?: string;
  schemaData: LowCodeSchema;
  status: LowCodePageStatus;
  thumbnailUrl?: string;
  miniappInstanceId?: string;
  createdAt: string;
  updatedAt: string;
}

/** 国际化配置 */
export interface I18nConfig {
  /** 当前语言区域码 */
  locale: string;
  /** 语言包，key -> 翻译文本 */
  messages: Record<string, string>;
}

/** 页面主题/设计系统配置 */
export interface LowCodeTheme {
  /** 主色调 */
  primaryColor?: string;
  /** 页面背景色 */
  backgroundColor?: string;
  /** 字体族 */
  fontFamily?: string;
  /** 字体大小基准 */
  fontSize?: string;
}

/** 页面 Schema 根节点 */
export interface LowCodeSchema {
  componentName: string; // 'Page'
  props: Record<string, any>;
  children: LowCodeNode[];
  /** 页面级数据源列表 */
  dataSources?: DataSource[];
  /** 页面主题/设计系统配置 */
  theme?: LowCodeTheme;
  /** 页面国际化配置 */
  i18n?: I18nConfig;
}

/** 动画/过渡效果配置 */
export interface AnimationConfig {
  /** 动画类型 */
  type?: 'fadeIn' | 'fadeOut' | 'slideIn' | 'scale';
  /** 动画持续时间（毫秒） */
  duration?: number;
  /** 动画延迟（毫秒） */
  delay?: number;
  /** 缓动函数 */
  easing?: string;
}

/** 表单验证规则 */
export interface ValidationRules {
  /** 是否必填 */
  required?: boolean;
  /** 最小长度（文本输入） */
  minLength?: number;
  /** 最大长度（文本输入） */
  maxLength?: number;
  /** 正则表达式字符串 */
  pattern?: string;
  /** 最小值（数字输入） */
  min?: number;
  /** 最大值（数字输入） */
  max?: number;
  /** 验证失败提示信息 */
  message?: string;
}

/** Schema 组件节点 */
export interface LowCodeNode {
  id: string;
  componentName: string;
  props: Record<string, any>;
  children?: LowCodeNode[];
  /** 数据绑定配置 */
  dataBinding?: DataBindingConfig;
  /** 绑定的数据源 */
  api?: DataSource;
  /** 事件处理器列表 */
  events?: EventHandler[];
  /** 循环渲染配置 */
  loop?: LoopConfig;
  /** 可见性表达式，如 "{{state.showHeader}}" */
  visible?: string;
  /** 依赖的数据源或状态 key，用于控制刷新时机 */
  dependOn?: string[];
  /** 统一样式配置 */
  style?: Record<string, string>;
  /** 表单验证规则 */
  validationRules?: ValidationRules;
  /** 动画/过渡效果配置 */
  animation?: AnimationConfig;
  /** 命名插槽: 容器组件可定义 header/footer/content 等插槽区域 */
  slots?: Record<string, LowCodeNode[]>;
}

/** 物料组件定义 */
export interface MaterialComponent {
  componentName: string;
  title: string;
  icon: string;
  category: 'basic' | 'layout' | 'display' | 'form' | 'business';
  defaultProps: Record<string, any>;
  /** 属性面板配置 */
  configureSchema: PropertyConfig[];
}

/** 属性配置项 */
export interface PropertyConfig {
  key: string;
  label: string;
  type: 'input' | 'number' | 'select' | 'color' | 'switch' | 'textarea' | 'image' | 'date' | 'slider' | 'radio' | 'checkbox' | 'icon' | 'json';
  defaultValue?: any;
  options?: { label: string; value: any }[];
  placeholder?: string;
}

/** 创建页面请求 */
export interface LowCodePageCreateData {
  name: string;
  slug: string;
  description?: string;
  schemaData?: LowCodeSchema;
  thumbnailUrl?: string;
  miniappInstanceId?: string;
}

/** 更新页面请求 */
export interface LowCodePageUpdateData {
  name?: string;
  slug?: string;
  description?: string;
  schemaData?: Record<string, any>;
  status?: LowCodePageStatus;
  thumbnailUrl?: string;
  miniappInstanceId?: string;
}

// ---------------------------------------------------------------------------
// Deployment & versioning types
// ---------------------------------------------------------------------------

/** 构建部署状态 */
export type DeployStatus =
  | 'idle'
  | 'building'
  | 'built'
  | 'uploading'
  | 'uploaded'
  | 'auditing'
  | 'published'
  | 'failed';

/** 构建任务 */
export interface BuildJob {
  id: string;
  pageId: string;
  status: DeployStatus;
  buildLog?: string;
  artifactUrl?: string;
  startedAt?: string;
  finishedAt?: string;
  triggerSource?: string;
}

/** 发布任务 */
export interface ReleaseJob {
  id: string;
  buildJobId: string;
  version: number;
  status: 'pending' | 'released' | 'rolled_back';
  releasedAt?: string;
}

/** 页面版本历史（对应服务端 LowCodePageVersion） */
export interface PageVersion {
  id: string;
  pageId: string;
  version: number;
  schemaData: LowCodeSchema;
  changeDescription?: string;
  createdBy?: string;
  createdAt: string;
}

// ---------------------------------------------------------------------------
// Template marketplace types
// ---------------------------------------------------------------------------

/** 模板市场模板 */
export interface LowCodeTemplate {
  id: string;
  sourcePageId?: string;
  name: string;
  description?: string;
  thumbnailUrl?: string;
  category: string;
  tags: string[];
  version: string;
  isPublic: boolean;
  isOfficial: boolean;
  downloadCount: number;
  forkCount: number;
  likeCount: number;
  schemaData?: Record<string, any>;
  dataSources?: Record<string, any>[];
  authorId?: string;
  authorName?: string;
  createdAt?: string;
  updatedAt?: string;
}

/** 创建模板请求 */
export interface LowCodeTemplateCreateData {
  sourcePageId: string;
  name: string;
  category: string;
  description?: string;
  thumbnailUrl?: string;
  tags?: string[];
  isPublic?: boolean;
}

/** 更新模板元数据请求 */
export interface LowCodeTemplateUpdateData {
  name?: string;
  description?: string;
  thumbnailUrl?: string;
  category?: string;
  tags?: string[];
  isPublic?: boolean;
}

/** 模板列表查询参数 */
export interface LowCodeTemplateListParams {
  category?: string;
  keyword?: string;
  sortBy?: 'popular' | 'newest' | 'forks';
  page?: number;
  pageSize?: number;
}

/** 模板版本历史项 */
export interface LowCodeTemplateVersionItem {
  id: string;
  version: string;
  changelog?: string;
  /** 状态: 1草稿 2已发布 3已废弃 */
  status: number;
  createdAt?: string;
  createdBy?: string;
}

/** 模板版本历史列表响应 */
export interface LowCodeTemplateVersionListResponse {
  currentVersion: string;
  versions: LowCodeTemplateVersionItem[];
}

/** 模板分类项 */
export interface LowCodeTemplateCategoryItem {
  name: string;
  count: number;
}

/** Fork 结果响应 */
export interface LowCodeTemplateForkResponse {
  pageId: string;
  message: string;
}
