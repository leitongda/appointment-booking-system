// Miniapp Template Type Definitions

// ─── NavSchema — TabBar 配置 ────────────────────────────────────────────

/** TabBar 单项配置 */
export interface NavTab {
  /** 页面路径 */
  pagePath: string;
  /** Tab 显示文案 */
  text: string;
  /** 未选中状态图标资源 key */
  iconKey: string;
  /** 选中状态图标资源 key */
  activeIconKey: string;
  /** 是否为原生 Tab 页（影响导航行为） */
  isTab?: boolean;
}

/** 小程序底部 TabBar 配置 */
export interface NavSchema {
  /** Tab 列表，支持 3–4 项 */
  tabs: NavTab[];
  /** TabBar 高度，单位 rpx */
  height: number;
}

// ─── HomeModuleSchema — 首页模块 ─────────────────────────────────────────

/** 首页可用的模块类型 */
export type HomeModuleType =
  | 'banner'
  | 'quick_menu'
  | 'patient_card'
  | 'recommend_doctor'
  | 'featured_doctor'
  | 'service_showcase'
  | 'quick_action'
  | 'simple_notice'
  | 'recent_doctor'
  | 'health_service'
  | 'health_reminder'
  | 'common_service'
  | 'family_switcher'
  | 'brand_story'
  | string;

/** 首页单个模块描述 */
export interface HomeModuleSchema {
  /** 模块唯一标识 */
  id: string;
  /** 模块类型 */
  type: HomeModuleType;
  /** 是否可见 */
  visible: boolean;
  /** 排序权重，数值越小越靠前 */
  order: number;
  /** 模块特有配置，不同 type 有不同结构 */
  config: Record<string, any>;
}

// ─── DesignTokenSet — 设计 Token 覆盖 ────────────────────────────────────

/** 设计 Token 集合，用于覆盖小程序默认视觉变量 */
export interface DesignTokenSet {
  /** 主色调，如 "#1890FF" */
  primary: string;
  /** 主色柔和版（浅底色），如 "#E6F7FF" */
  primarySoft: string;
  /** 强调色 / 辅助色 */
  accent: string;
  /** 正文默认字号，单位 rpx */
  bodyFontSize: number;
  /** 大标题 / 展示文字字号，单位 rpx */
  displayFontSize: number;
  /** 中等圆角，单位 rpx */
  radiusMd: number;
  /** 大圆角，单位 rpx */
  radiusLg: number;
  /** 间距全局系数，1.0 为默认 */
  spacingMultiplier: number;
  /** 最小可触摸目标尺寸，单位 rpx */
  touchTargetMin: number;
  /** 自定义颜色扩展，key 为语义名称，value 为颜色值 */
  customColors: Record<string, string>;
}

// ─── CopyToneConfig — 文案覆盖 ──────────────────────────────────────────

/** 文案语气与标签覆盖，用于不同品牌 / 受众场景 */
export interface CopyToneConfig {
  /** 预约入口按钮文案，如 "立即预约"、"马上挂号" */
  bookingLabel: string;
  /** 就诊人称呼，如 "就诊人"、"患者" */
  patientLabel: string;
  /** 对用户称呼方式 */
  addressMode: '您' | '你' | string;
  /** 无预约时的空状态文案 */
  emptyBookingText: string;
  /** 预约成功提示语 */
  confirmSuccessText: string;
  /** 其它自定义文案覆盖 */
  custom: Record<string, string>;
}

// ─── TemplateConstraintConfig — 模板约束 ─────────────────────────────────

/** 模板运行时约束，控制页面与交互行为 */
export interface TemplateConstraintConfig {
  /** 不可替换/不可移除的页面路径列表 */
  lockedPages: string[];
  /** 是否强制启用长辈模式（大字号、高对比度等） */
  forceElderMode: boolean;
  /** 关键操作（如取消预约）是否要求二次确认 */
  confirmBeforeAction: boolean;
}

// ─── TemplateAssetSet — 资源风格 ─────────────────────────────────────────

/** 图标线条风格 */
export type IconStyle = 'filled' | 'outlined' | 'thin' | 'bold';

/** TabBar 图标风格 */
export type TabBarIconStyle = 'filled' | 'outlined';

/** 装饰元素风格 */
export type DecorationStyle = 'none' | 'minimal' | 'playful' | 'traditional' | 'floral';

/** 模板所使用的资源/风格集合 */
export interface TemplateAssetSet {
  /** 通用图标线条风格 */
  iconStyle: IconStyle;
  /** TabBar 专用图标风格 */
  tabBarIconStyle: TabBarIconStyle;
  /** 装饰元素风格 */
  decorationStyle: DecorationStyle;
}

// ─── MiniappStyleTemplate — 顶层模板定义 ──────────────────────────────────

/** 小程序样式模板完整定义 */
export interface MiniappStyleTemplate {
  /** 模板编码，全局唯一，如 "classic-blue" */
  code: string;
  /** 模板显示名称 */
  name: string;
  /** 目标受众标签，如 ["general", "elderly", "pediatric"] */
  audience: string[];
  /** 模板描述 */
  description: string;
  /** 底部 TabBar 配置 */
  navSchema: NavSchema;
  /** 首页模块列表及排列 */
  homeSchema: HomeModuleSchema[];
  /** 页面路径到页面模板标识的映射，如 { "pages/index/index": "default" } */
  pageShells: Record<string, string>;
  /** 设计 Token 覆盖 */
  designTokens: DesignTokenSet;
  /** 资源风格配置 */
  assets: TemplateAssetSet;
  /** 文案语气配置 */
  tone: CopyToneConfig;
  /** 模板约束配置 */
  constraints: TemplateConstraintConfig;
}
