import { useTemplate } from '../../contexts/TemplateContext';
import { Suspense, lazy } from 'react';
import { ShellLoadingFallback } from '../../components/ShellLoadingFallback';
import { ShellErrorBoundary } from '../../components/ShellErrorBoundary';

// 医生列表 Shell 懒加载
const doctorListShells = {
  cards: lazy(() => import('../../shells/doctor/DoctorCards').then(m => ({ default: m.DoctorCards }))),
  'doctor-large-cards': lazy(() => import('../../shells/doctor/DoctorLargeCards').then(m => ({ default: m.DoctorLargeCards }))),
  'doctor-showcase': lazy(() => import('../../shells/doctor/DoctorShowcase').then(m => ({ default: m.DoctorShowcase }))),
  'doctor-cards-soft': lazy(() => import('../../shells/doctor/DoctorCardsSoft').then(m => ({ default: m.DoctorCardsSoft }))),
};

export default function Doctor() {
  const { template } = useTemplate();
  const variantId = template.pageShells.doctorList || 'cards';
  const Shell = doctorListShells[variantId] || doctorListShells.cards;

  return (
    <ShellErrorBoundary pageName="医生列表">
      <Suspense fallback={<ShellLoadingFallback />}>
        <Shell />
      </Suspense>
    </ShellErrorBoundary>
  );
}
