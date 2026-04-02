import { setBaseURL } from '@hospital/api';
import { setupRequestInterceptor, setupResponseInterceptor } from '@/api/interceptors';

export function initApiConfig() {
  setBaseURL('/api/v1');
  setupRequestInterceptor();
  setupResponseInterceptor();
}
