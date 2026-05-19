/**
 * umi 代码分割配置
 *
 * 使用 depPerChunk 策略将每个 npm 包单独打包，>= minSize 的包独立成 chunk。
 */
const codeSplitting = {
  jsStrategy: 'depPerChunk' as const,
  jsStrategyOptions: {
    // 大于 50KB 的包单独打包
    minSize: 50000,
  },
};

export default codeSplitting;
