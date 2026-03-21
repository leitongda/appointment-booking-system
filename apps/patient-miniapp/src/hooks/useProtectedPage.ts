import { DependencyList, useCallback, useEffect, useState } from 'react';
import Taro from '@tarojs/taro';
import { AUTH_EVENTS, getToken, subscribeAuthChange } from '@/utils/auth';

interface UseProtectedPageOptions {
  load: () => Promise<void> | void;
  clear?: () => void;
  deps?: DependencyList;
}

export const useProtectedPage = ({
  load,
  clear,
  deps = [],
}: UseProtectedPageOptions) => {
  const [showLoginPopup, setShowLoginPopup] = useState(false);

  const handleRequireLogin = useCallback(() => {
    setShowLoginPopup(true);
  }, []);

  const ensureAuthenticated = useCallback(async () => {
    if (!getToken()) {
      handleRequireLogin();
      return false;
    }

    await load();
    return true;
  }, [handleRequireLogin, load]);

  const handleLoginSuccess = useCallback(() => {
    setShowLoginPopup(false);
    void ensureAuthenticated();
  }, [ensureAuthenticated]);

  const handleLoginClose = useCallback(() => {
    setShowLoginPopup(false);
    if (!getToken()) {
      Taro.navigateBack().catch(() => {
        Taro.switchTab({ url: '/pages/index/index' });
      });
    }
  }, []);

  useEffect(() => {
    void ensureAuthenticated();
  }, [ensureAuthenticated, ...deps]);

  useEffect(() => {
    return subscribeAuthChange((payload) => {
      if (payload.type === AUTH_EVENTS.LOGIN || payload.type === AUTH_EVENTS.UPDATED) {
        void ensureAuthenticated();
        return;
      }

      if (payload.type === AUTH_EVENTS.LOGOUT || payload.type === AUTH_EVENTS.EXPIRED) {
        clear?.();
        setShowLoginPopup(true);
      }
    });
  }, [clear, ensureAuthenticated]);

  return {
    showLoginPopup,
    setShowLoginPopup,
    ensureAuthenticated,
    handleLoginSuccess,
    handleLoginClose,
    handleRequireLogin,
  };
};
