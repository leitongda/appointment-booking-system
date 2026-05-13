import { setBaseURL } from '@hospital/api';
import { initTracker, initPerformanceMonitoring } from '@hospital/shared';
import { initApiConfig } from '@/utils/request';

const apiBaseUrl = process.env.API_BASE_URL || '/api/v1';

export function initApp() {
  setBaseURL(apiBaseUrl);
  console.log(`API base URL set: ${apiBaseUrl}`);

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
    },
  });
}

export { apiBaseUrl };
