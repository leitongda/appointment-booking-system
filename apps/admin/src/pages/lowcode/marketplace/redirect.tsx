/** 模板市场入口 — 重定向到列表页 */

import React from 'react';
import { Redirect } from '@umijs/max';

const MarketplaceRedirect: React.FC = () => <Redirect to="/platform/lowcode/marketplace" />;

export default MarketplaceRedirect;
