import { setBaseURL } from '@hospital/api';
import { initTracker, getTracker, initPerformanceMonitoring } from '@hospital/shared';
import { initApiConfig } from '@/utils/request';
import { initSessionRecorder } from '@/utils/sessionRecorder';

const apiBaseUrl = process.env.API_BASE_URL || '/api/v1';

export function initApp() {
  setBaseURL(apiBaseUrl);

  initApiConfig();

  initTracker({
    apiBaseUrl: '',
    apiPath: `${apiBaseUrl}/analytics/batch`,
    platform: 'admin',
    enabled: true,
    enableInDev: true,
    batchSize: 10,
    batchInterval: 5000,
    debug: process.env.NODE_ENV === 'development',
  });

  initPerformanceMonitoring({
    report: {
      enabled: true,
      flushInterval: 30000,
      batchSize: 20,
      getSessionId: () => getTracker()?.getSessionId() ?? '',
    },
  });

  // 会话录制（rrweb）：与 behavior_log 共用 session_id。
  // 录制模式按环境区分：
  // - 开发环境：always 全量录制，便于本地排查
  // - 生产环境：error-triggered，持续录进环形缓冲但仅捕获到 JS 错误后才
  //   激活上报（30s 窗口）。这样生产环境只录出错会话，开销可控且最有诊断价值。
  // 内部含 typeof document 守卫，SSR / 非浏览器环境自动 no-op。
  initSessionRecorder({
    mode: process.env.NODE_ENV === 'development' ? 'always' : 'error-triggered',
  });
}

export { apiBaseUrl };
