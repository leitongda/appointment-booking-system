/**
 * splitChunks 总配置
 *
 * 与 cacheGroups 共同决定生产构建的代码分割行为。
 * 公共参数（minSize / maxAsyncRequests / ...）的取值与重构前保持完全一致。
 */
import { cacheGroups } from './cacheGroups';

export const getSplitChunksConfig = () => ({
  chunks: 'all',
  minSize: 20000,
  minChunks: 1,
  maxAsyncRequests: 30,
  maxInitialRequests: 30,
  automaticNameDelimiter: '-',
  cacheGroups,
});
