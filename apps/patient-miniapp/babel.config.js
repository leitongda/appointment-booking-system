module.exports = {
  presets: [
    ['taro', {
      framework: 'react',
      ts: true,
    }],
  ],
  plugins: [
    // NutUI 3.0.19-cpp.22 使用扁平化构建，样式已内联到组件中
    // 不需要 babel-plugin-import 进行样式按需加载
  ],
};

