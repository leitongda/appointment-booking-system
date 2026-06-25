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
  // 全量录制 DOM 变更开销较大，生产环境默认关闭，仅开发环境开启以便排查问题。
  // 内部含 typeof document 守卫，SSR / 非浏览器环境自动 no-op。
  initSessionRecorder({ enabled: process.env.NODE_ENV === 'development' });
}

export { apiBaseUrl };
