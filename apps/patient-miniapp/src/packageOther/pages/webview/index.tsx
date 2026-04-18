import { WebView } from '@tarojs/components';
import { useRouter } from '@tarojs/taro';
import { useApplyThemeNavigationBar } from '../../../utils/theme';

const WebViewPage = () => {
  useApplyThemeNavigationBar();
  const router = useRouter();
  const { url } = router.params;

  const decodedUrl = url ? decodeURIComponent(url) : '';

  if (!decodedUrl) {
    return null;
  }

  return (
    <WebView src={decodedUrl} />
  );
};

export default WebViewPage;
