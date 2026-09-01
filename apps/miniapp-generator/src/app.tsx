import { PropsWithChildren } from 'react';
import { useLaunch } from '@tarojs/taro';
import { TemplateProvider } from './contexts/TemplateContext';
import './app.less';

function App({ children }: PropsWithChildren) {
  useLaunch(() => {
    console.log('[miniapp-generator] template:', process.env.TARO_APP_TEMPLATE_CODE || 'modern-general');
    console.log('[miniapp-generator] version:', process.env.TARO_APP_TEMPLATE_VERSION || '1.0.0');
  });

  return (
    <TemplateProvider>
      {children}
    </TemplateProvider>
  );
}

export default App;
