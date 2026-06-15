import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { initTracker, initPerformanceMonitoring, getTracker } from '@hospital/shared';
import { setupAuthInterceptor } from './lib/auth';
import App from './App';
import './globals.css';

setupAuthInterceptor();

// PWA Service Worker 注册
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => { /* noop */ });
  });
}

const apiBaseUrl = '/api/v1';

initTracker({
  apiBaseUrl: '',
  apiPath: `${apiBaseUrl}/analytics/batch`,
  platform: 'h5',
  enabled: true,
  enableInDev: true,
  batchSize: 10,
  batchInterval: 5000,
  debug: import.meta.env.DEV,
});

initPerformanceMonitoring({
  report: {
    enabled: true,
    flushInterval: 30000,
    batchSize: 20,
    getSessionId: () => getTracker()?.getSessionId() ?? '',
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
