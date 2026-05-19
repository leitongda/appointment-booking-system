/**
 * Webpack 链式配置入口
 *
 * 仅在生产环境注入 gzip 预压缩与 splitChunks，开发环境不做任何修改。
 */
import { IS_PROD } from '../constants/env';
import { applyCompressionPlugin } from './compression';
import { getSplitChunksConfig } from './splitChunks';

const chainWebpack = (config: any) => {
  if (!IS_PROD) return;

  applyCompressionPlugin(config);
  config.optimization.splitChunks(getSplitChunksConfig());
};

export default chainWebpack;
