/** 低代码模块独立布局 */

import React, { useEffect } from 'react';
import { Outlet, history, useLocation } from '@umijs/max';
import { getToken } from '@hospital/shared';
import { LOGIN_PATH } from '@/constants/paths';

const LowCodeLayout: React.FC = () => {
  const location = useLocation();

  useEffect(() => {
    if (!getToken()) {
      const redirect = location.pathname + (location.search || '');
      history.replace(`${LOGIN_PATH}?redirect=${encodeURIComponent(redirect)}`);
    }
  }, [location.pathname, location.search]);

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#f5f7fb',
        overflow: 'auto',
      }}
    >
      <Outlet />
    </div>
  );
};

export default LowCodeLayout;
