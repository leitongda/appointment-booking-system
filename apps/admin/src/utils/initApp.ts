import { setBaseURL, getBaseURL, isTauriDesktop, applyDesktopBaseUrl } from '@hospital/api';
import { initTracker, getTracker, initPerformanceMonitoring } from '@hospital/shared';
import { initApiConfig } from '@/utils/request';
import { initSessionRecorder } from '@/utils/sessionRecorder';

const apiBaseUrl = process.env.API_BASE_URL || '/api/v1';

/**
 * 初始化上报类组件（tracker / 性能监控 / 会话录制）。
 *
 * 它们用裸 fetch / sendBeacon 按初始化时固化的 URL 字符串上报，不走 axios 实例、
 * 不受 setBaseURL 覆盖影响——桌面壳下必须等 baseURL 覆盖完成后、用 getBaseURL()
 * 返回的绝对地址初始化（打包态实测：相对路径会打向自定义协议资产，日志表现为
 * `Asset api/v1/analytics/batch not found`）。web 传构建期相对路径，与原行为一致。
 */
const initMonitoring = (base: string) => {
  initTracker({
    apiBaseUrl: base,
    apiPath: '/analytics/batch',
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
      endpoint: `${base}/performance/report`,
      flushInterval: 30000,
      batchSize: 20,
      getSessionId: () => getTracker()?.getSessionId() ?? '',
    },
  });

  initSessionRecorder({
    mode: process.env.NODE_ENV === 'development' ? 'always' : 'error-triggered',
  });
};

export function initApp() {
  setBaseURL(apiBaseUrl);

  if (isTauriDesktop()) {
    // 桌面壳：等桌面配置覆盖 baseURL 后再初始化上报组件（见 initMonitoring 注释）。
    // 覆盖完成前不丢业务请求——首个业务请求由 app.tsx getInitialState 把关，
    // 这里延迟的只是 analytics/perf 首个批次。web 端 isTauriDesktop() 恒 false。
    void applyDesktopBaseUrl().then(() => initMonitoring(getBaseURL()));
    initApiConfig();
    return;
  }

  initApiConfig();
  initMonitoring(apiBaseUrl);
}

export { apiBaseUrl };
