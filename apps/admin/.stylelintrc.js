module.exports = {
  extends: [require.resolve('@umijs/lint/dist/config/stylelint')],
  rules: {
    // Less fade() 函数
    'function-no-unknown': [true, { ignoreFunctions: ['fade'] }],
    // 允许 Ant Design 组件库的类名（如 .ant-tree-iconEle）
    'selector-class-pattern': null,
  },
};
