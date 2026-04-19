import { useTemplate } from '../../contexts/TemplateContext';
import { Suspense, lazy } from 'react';
import { ShellLoadingFallback } from '../../components/ShellLoadingFallback';
import { ShellErrorBoundary } from '../../components/ShellErrorBoundary';

// 首页 Shell 使用懒加载
const homeShells = {
  standard: lazy(() => import('../../shells/home/HomeStandard').then(m => ({ default: m.HomeStandard }))),
  'home-elderly': lazy(() => import('../../shells/home/HomeElderly').then(m => ({ default: m.HomeElderly }))),
  'home-premium': lazy(() => import('../../shells/home/HomePremium').then(m => ({ default: m.HomePremium }))),
  'home-family': lazy(() => import('../../shells/home/HomeFamily').then(m => ({ default: m.HomeFamily }))),
  'home-womens': lazy(() => import('../../shells/home/HomeWomens').then(m => ({ default: m.HomeWomens }))),
};

export default function Index() {
  const { template } = useTemplate();
  const variantId = template.pageShells.home || 'standard';
  const Shell = homeShells[variantId] || homeShells.standard;

  return (
    <ShellErrorBoundary pageName="首页">
      <Suspense fallback={<ShellLoadingFallback />}>
        <Shell />
      </Suspense>
    </ShellErrorBoundary>
  );
}
