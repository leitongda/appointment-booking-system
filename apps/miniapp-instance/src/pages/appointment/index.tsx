import { useTemplate } from '../../contexts/TemplateContext';
import { Suspense, lazy } from 'react';
import { ShellLoadingFallback } from '../../components/ShellLoadingFallback';
import { ShellErrorBoundary } from '../../components/ShellErrorBoundary';

// 预约页 Shell 懒加载
const appointmentShells = {
  tabs: lazy(() => import('../../shells/appointment/AppointTabs').then(m => ({ default: m.AppointTabs }))),
  'appoint-simple': lazy(() => import('../../shells/appointment/AppointSimple').then(m => ({ default: m.AppointSimple }))),
};

export default function Appointment() {
  const { template } = useTemplate();
  const variantId = template.pageShells.appointment || 'tabs';
  const Shell = appointmentShells[variantId] || appointmentShells.tabs;

  return (
    <ShellErrorBoundary pageName="预约页">
      <Suspense fallback={<ShellLoadingFallback />}>
        <Shell />
      </Suspense>
    </ShellErrorBoundary>
  );
}
