module.exports = {
  presets: [
    ['taro', {
      framework: 'react',
      ts: true,
    }],
  ],
  plugins: [
    // NutUI 样式按需加载
    // 自动将 import { Button } from '@nutui/nutui-react-taro'
    // 转换为同时导入对应的 CSS 文件
    ['import', {
      libraryName: '@nutui/nutui-react-taro',
      libraryDirectory: 'dist/es/packages',
      // 使用 style: 'css' 自动加载组件对应的 CSS 样式
      // 这会自动加载 dist/es/packages/[componentName]/style/css.js
      style: 'css',
      camel2DashComponentName: false,
    }, '@nutui/nutui-react-taro'],
  ],
};

