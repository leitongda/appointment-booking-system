import { WebView } from '@tarojs/components';
import { useRouter } from '@tarojs/taro';

const WebViewPage = () => {
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

