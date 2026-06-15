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
    // 转换为同时导入对应的样式文件
    ['import', {
      libraryName: '@nutui/nutui-react-taro',
      libraryDirectory: 'dist/es/packages',
      style: true,
      camel2DashComponentName: false,
      // NutUI 3.x publishes component directories in lowercase without separators
      // (for example, PullToRefresh -> pulltorefresh).
      customName: name => `@nutui/nutui-react-taro/dist/es/packages/${name.toLowerCase()}`,
    }, '@nutui/nutui-react-taro'],
  ],
};
