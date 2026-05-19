/**
 * MFSU（Module Federation Speed Up）配置
 *
 * `react-image-crop` 通过 splitChunks.cacheGroups.imageCrop 单独打包，因此从 mfsu 中排除以避免重复处理。
 * 本地 workspace 包在开发中会频繁变更，排除 MFSU 可避免预构建缓存落后于源码导出。
 * 二者绑定，调整时请同步检查 `webpack/cacheGroups.ts`。
 */
const mfsu = {
  strategy: 'normal' as const,
  exclude: ['react-image-crop', '@hospital/shared', '@hospital/api'],
};

export default mfsu;
