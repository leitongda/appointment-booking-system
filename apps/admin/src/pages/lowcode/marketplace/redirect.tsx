/** 模板市场入口 — 重定向到列表页 */

import React, { useEffect } from 'react';
import { history } from '@umijs/max';

const MarketplaceRedirect: React.FC = () => {
  useEffect(() => {
    history.replace('/platform/lowcode/marketplace');
  }, []);

  return null;
};

export default MarketplaceRedirect;
