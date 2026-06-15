// ES 模块规范：export * 不会重导出 default 导出
// 需要显式重导出 default，否则 import axios from 'axios' 会失败
export { default } from '@hospital/shared/miniapp/stubs/empty-axios';
export * from '@hospital/shared/miniapp/stubs/empty-axios';
