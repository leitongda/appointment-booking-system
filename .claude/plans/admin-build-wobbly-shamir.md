# Admin端首屏加载优化计划

## Context

Admin端构建产物分析显示，首屏加载需要下载约1.17MB gzipped JS + 24MB字体文件。主要瓶颈在于vendors chunk过大(485KB gz)、字体未优化(24MB OTF)、以及多个页面专用库未做代码分割。

## 当前状态

| 指标 | 数值 |
|------|------|
| 首屏JS总量 | ~3.8MB raw / ~1.17MB gz |
| 字体文件 | 24MB (3个OTF文件) |
| vendors chunk | 1.5MB raw / 485KB gz |
| 登录页背景图 | 1.5MB PNG |

## 优化方案

### P0 - 高优先级 (预计减少60-70%首屏加载)

#### 1. 字体优化
**问题**: 三个OTF字体文件共24MB，全量加载
**方案**:
- 转换为WOFF2格式 (体积减少30-50%)
- 添加unicode-range子集化 (仅加载页面实际使用的字符)
- 考虑移除Medium字重，仅保留Regular和Bold
**文件**: `apps/admin/src/global.less`, `apps/admin/public/fonts/`

#### 2. vendors chunk拆分
**问题**: 1.5MB的vendors包含多个页面专用库
**方案**: 在`config.ts`添加cacheGroups，将以下库移至async chunk:
- `@wangeditor/editor` + `@wangeditor/editor-for-react` (富文本编辑器)
- `@dnd-kit/*` (拖拽排序)
- `pinyin-pro` (拼音转换)
- `react-image-crop` (图片裁剪)
**文件**: `apps/admin/config/config.ts` (splitChunks配置)

### P1 - 中优先级 (预计减少20-30%首屏加载)

#### 3. vendors chunk细分
**问题**: 剩余vendors仍过大
**方案**: 为ahooks、rc-*组件等常用库添加独立cacheGroup

#### 4. 资源提示
**问题**: 缺少preload/prefetch
**方案**: 配置`<link rel="preload">`关键JS，`<link rel="prefetch">`可能访问的页面chunk

#### 5. 背景图优化
**问题**: 登录页bg.png 1.5MB
**方案**: 转换为WebP格式 (预计减少60-80%)

### P2 - 低优先级

#### 6. 共享包优化
- `@hospital/shared` barrel exports可能导致不必要的依赖引入
- 考虑使用具体子路径导入

#### 7. CSS去重
- 多个表单页面有重复的19KB CSS chunk
- 提取为共享CSS chunk

## 预期效果

| 优化项 | 预计减少 |
|--------|---------|
| 字体优化 | 20-22MB |
| vendors拆分 | 200-300KB |
| 背景图优化 | 1MB |
| **总计** | **~23MB** |

优化后首屏加载预计从~25MB降至~2MB (gzipped ~500KB)。

## 验证方式

1. 优化前后分别运行`pnpm build:admin`对比产物大小
2. 使用Chrome DevTools Network面板测试实际加载时间
3. 使用Lighthouse测试Performance分数

## 关键文件

- `apps/admin/config/config.ts` - 构建配置
- `apps/admin/src/global.less` - 字体声明
- `apps/admin/public/fonts/` - 字体文件
- `apps/admin/public/bg.png` - 背景图
- `apps/admin/src/components/RichTextEditor/index.tsx` - wangeditor使用处
