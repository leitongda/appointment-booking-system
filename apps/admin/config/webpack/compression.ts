/**
 * gzip 预压缩插件配置
 *
 * 仅压缩大于 10KB 的产物，压缩比阈值 0.8。
 */
import CompressionPlugin from 'compression-webpack-plugin';

export const applyCompressionPlugin = (config: any) => {
  config.plugin('compression-gzip').use(CompressionPlugin, [
    {
      algorithm: 'gzip',
      test: /\.(js|css|html|svg)$/,
      threshold: 10240, // 仅压缩大于 10KB 的文件
      minRatio: 0.8,
      filename: '[path][base].gz',
    },
  ]);
};
