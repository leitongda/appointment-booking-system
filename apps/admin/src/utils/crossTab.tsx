import { isPublicEntryRoute, setStorage, STORAGE_KEYS } from '@hospital/shared';
import type { CrossTabEvent } from '@hospital/shared';
import { history } from '@umijs/max';
import { Button, Modal, notification } from 'antd';
import { LOGIN_PATH } from '@/constants/paths';

export function handleCrossTabEvent(event: CrossTabEvent) {
  if (isPublicEntryRoute()) return;

  switch (event.type) {
    case 'auth-change':
      if (event.action === 'logout') {
        Modal.confirm({
          title: '登录状态变更',
          content: '您已在其他页面退出登录，请重新登录。',
          okText: '重新登录',
          cancelButtonProps: { style: { display: 'none' } },
          closable: false,
          maskClosable: false,
          onOk: () => {
            Modal.destroyAll();
            window.location.href = LOGIN_PATH;
          },
        });
      } else if (event.action === 'switch-user') {
        Modal.confirm({
          title: '登录账号已变更',
          content: '检测到您在其他页面切换了登录账号，当前页面需要刷新以保持一致。',
          okText: '刷新页面',
          cancelButtonProps: { style: { display: 'none' } },
          closable: false,
          maskClosable: false,
          onOk: () => { window.location.reload(); },
        });
      }
      break;

    case 'tenant-change':
      notification.warning({
        key: 'tenant-change',
        message: '租户已切换',
        description: '当前页面需要刷新以保持一致',
        placement: 'topRight',
        duration: 15,
        btn: (
          <Button type="primary" size="small" onClick={() => {
            const { pathname, search, hash } = history.location;
            if (!/\/(create|edit)($|\/)/.test(pathname)) {
              setStorage(STORAGE_KEYS.SWITCH_REDIRECT_PATH, pathname + (search || '') + (hash || ''));
            }
            window.location.reload();
          }}>
            立即刷新
          </Button>
        ),
      });
      break;

    case 'store-change':
      notification.warning({
        key: 'store-change',
        message: '门店已切换',
        description: event.newStoreName
          ? `门店已切换为「${event.newStoreName}」，当前页面需要刷新以保持一致。`
          : '门店已切换，当前页面需要刷新以保持一致。',
        placement: 'topRight',
        duration: 15,
        btn: (
          <Button type="primary" size="small" onClick={() => {
            const { pathname, search, hash } = history.location;
            if (!/\/(create|edit)($|\/)/.test(pathname)) {
              setStorage(STORAGE_KEYS.SWITCH_REDIRECT_PATH, pathname + (search || '') + (hash || ''));
            }
            window.location.reload();
          }}>
            立即刷新
          </Button>
        ),
      });
      break;
  }
}
