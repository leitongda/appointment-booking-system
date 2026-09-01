import { useTemplate } from '../../../../contexts/TemplateContext';
import { Suspense, lazy } from 'react';
import { ShellLoadingFallback } from '../../../../components/ShellLoadingFallback';
import { ShellErrorBoundary } from '../../../../components/ShellErrorBoundary';

// 医生详情 Shell 懒加载
const doctorDetailShells = {
  standard: lazy(() => import('../../../../shells/doctor/DoctorDetailStandard').then(m => ({ default: m.DoctorDetailStandard }))),
  'doctor-detail-elderly': lazy(() => import('../../../../shells/doctor/DoctorDetailElderly').then(m => ({ default: m.DoctorDetailElderly }))),
  'doctor-detail-family': lazy(() => import('../../../../shells/doctor/DoctorDetailFamily').then(m => ({ default: m.DoctorDetailFamily }))),
  'doctor-detail-premium': lazy(() => import('../../../../shells/doctor/DoctorDetailPremium').then(m => ({ default: m.DoctorDetailPremium }))),
  'doctor-detail-womens': lazy(() => import('../../../../shells/doctor/DoctorDetailWomens').then(m => ({ default: m.DoctorDetailWomens }))),
};

export default function DoctorDetail() {
  const { template } = useTemplate();
  const variantId = template.pageShells.doctorDetail || 'standard';
  const Shell = doctorDetailShells[variantId] || doctorDetailShells.standard;

  return (
    <ShellErrorBoundary pageName="医生详情">
      <Suspense fallback={<ShellLoadingFallback />}>
        <Shell />
      </Suspense>
    </ShellErrorBoundary>
  );
}
