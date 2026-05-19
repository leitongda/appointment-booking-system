/**
 * splitChunks cacheGroups 定义
 *
 * 各 cacheGroup 的 priority / test 正则 / chunks 策略与重构前保持 byte-for-byte 一致。
 * 修改任何一项前请权衡产物 chunk 名与体积影响。
 */

export const cacheGroups = {
  // antd 核心生态（antd + icons + rc-* 组件 + cssinjs + fast-color）
  antd: {
    name: 'antd-lib',
    test: /[\\/]node_modules[\\/](@ant-design[\\/](icons|cssinjs|fast-color)|antd|rc-[a-z-]+)[\\/]/,
    priority: 30,
    chunks: 'all',
  },
  // @ant-design/pro-components 单独打包
  proComponents: {
    name: 'pro-components-lib',
    test: /[\\/]node_modules[\\/]@ant-design[\\/]pro-/,
    priority: 25,
    chunks: 'all',
  },
  // @ant-design/charts 和 @antv 相关单独打包（图表库）
  charts: {
    name: 'charts-lib',
    test: /[\\/]node_modules[\\/](@ant-design[\\/]charts|@ant-design[\\/]plots|@antv)[\\/]/,
    priority: 20,
    chunks: 'async',
  },
  // 富文本编辑器 - 仅在内容管理页面使用
  wangeditor: {
    name: 'wangeditor-lib',
    test: /[\\/]node_modules[\\/]@wangeditor[\\/]/,
    priority: 22,
    chunks: 'async',
  },
  // 拖拽排序库 - 仅在医生列表和科室排序使用
  dndKit: {
    name: 'dnd-kit-lib',
    test: /[\\/]node_modules[\\/]@dnd-kit[\\/]/,
    priority: 22,
    chunks: 'async',
  },
  // 拼音转换 - 仅在门店表单使用
  pinyin: {
    name: 'pinyin-lib',
    test: /[\\/]node_modules[\\/]pinyin-pro[\\/]/,
    priority: 22,
    chunks: 'async',
  },
  // 图片裁剪 - 仅在图片上传组件使用
  imageCrop: {
    name: 'image-crop-lib',
    test: /[\\/]node_modules[\\/]react-image-crop[\\/]/,
    priority: 22,
    chunks: 'async',
  },
  // html2canvas - 间接依赖，无页面直接使用，按需加载
  html2canvas: {
    name: 'html2canvas-lib',
    test: /[\\/]node_modules[\\/]html2canvas[\\/]/,
    priority: 22,
    chunks: 'async',
  },
  // React 相关
  react: {
    name: 'react-lib',
    test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/,
    priority: 40,
    chunks: 'all',
  },
  // 路由库
  router: {
    name: 'router-lib',
    test: /[\\/]node_modules[\\/](react-router|react-router-dom|@remix-run[\\/]router|history)[\\/]/,
    priority: 15,
    chunks: 'all',
  },
  // 其他常用工具库
  utils: {
    name: 'utils-lib',
    test: /[\\/]node_modules[\\/](lodash|lodash-es|dayjs|moment)[\\/]/,
    priority: 15,
    chunks: 'all',
  },
  // 通用第三方库
  vendors: {
    name: 'vendors',
    test: /[\\/]node_modules[\\/]/,
    priority: 10,
    chunks: 'all',
    minChunks: 2,
  },
  // 公共组件
  common: {
    name: 'common',
    minChunks: 2,
    priority: 5,
    reuseExistingChunk: true,
  },
  // 公共CSS提取
  commonStyles: {
    name: 'common-styles',
    type: 'css/mini-extract',
    test: /\.css$/,
    chunks: 'all',
    minChunks: 2,
    priority: 1,
  },
};
