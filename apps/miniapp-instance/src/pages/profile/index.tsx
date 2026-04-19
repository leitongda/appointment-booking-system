import { useTemplate } from '../../contexts/TemplateContext';
import { Suspense, lazy } from 'react';
import { ShellLoadingFallback } from '../../components/ShellLoadingFallback';
import { ShellErrorBoundary } from '../../components/ShellErrorBoundary';

// 个人中心 Shell 懒加载
const profileShells = {
  standard: lazy(() => import('../../shells/profile/ProfileStandard').then(m => ({ default: m.ProfileStandard }))),
  'profile-elderly': lazy(() => import('../../shells/profile/ProfileElderly').then(m => ({ default: m.ProfileElderly }))),
  'profile-family': lazy(() => import('../../shells/profile/ProfileFamily').then(m => ({ default: m.ProfileFamily }))),
  'profile-premium': lazy(() => import('../../shells/profile/ProfilePremium').then(m => ({ default: m.ProfilePremium }))),
  'profile-womens': lazy(() => import('../../shells/profile/ProfileWomens').then(m => ({ default: m.ProfileWomens }))),
};

export default function Profile() {
  const { template } = useTemplate();
  const variantId = template.pageShells.profile || 'standard';
  const Shell = profileShells[variantId] || profileShells.standard;

  return (
    <ShellErrorBoundary pageName="个人中心">
      <Suspense fallback={<ShellLoadingFallback />}>
        <Shell />
      </Suspense>
    </ShellErrorBoundary>
  );
}
