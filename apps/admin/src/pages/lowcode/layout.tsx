/** 低代码模块独立布局 */

import React, { useEffect } from 'react';
import { Outlet, history, useLocation } from '@umijs/max';
import { getToken, rememberReturnPath } from '@hospital/shared';
import { LOGIN_PATH } from '@/constants/paths';

const LowCodeLayout: React.FC = () => {
  const location = useLocation();

  useEffect(() => {
    if (!getToken()) {
      // 无 token 跳登录前，统一通过 rememberReturnPath 写入 LAST_PATH，
      // 与全站其它「跳登录」入口保持一致的回跳机制。
      // （旧实现用 ?redirect= query 参数，但登录页只消费 LAST_PATH，不读 ?redirect=，
      //  导致该路径的回跳目标被静默丢弃。）
      // 注：低代码编辑器/预览页路径含 :id，登录页的 isSafeReturnPath 会按「不稳定路径」
      // 拒绝回跳 —— 这是预期行为（编辑器会话可能已失效），用户会落到默认落地页。
      rememberReturnPath(location.pathname, location.search || undefined);
      history.replace(LOGIN_PATH);
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
