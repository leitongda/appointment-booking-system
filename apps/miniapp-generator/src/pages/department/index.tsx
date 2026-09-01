import { useTemplate } from '../../contexts/TemplateContext';
import { Suspense, lazy } from 'react';
import { ShellLoadingFallback } from '../../components/ShellLoadingFallback';
import { ShellErrorBoundary } from '../../components/ShellErrorBoundary';

// 科室页 Shell 懒加载
const departmentShells = {
  sidebar: lazy(() => import('../../shells/department/DeptSidebar').then(m => ({ default: m.DeptSidebar }))),
  'dept-large-grid': lazy(() => import('../../shells/department/DeptLargeGrid').then(m => ({ default: m.DeptLargeGrid }))),
  'dept-minimal': lazy(() => import('../../shells/department/DeptMinimal').then(m => ({ default: m.DeptMinimal }))),
  'dept-colorful': lazy(() => import('../../shells/department/DeptColorful').then(m => ({ default: m.DeptColorful }))),
  'dept-soft': lazy(() => import('../../shells/department/DeptSoft').then(m => ({ default: m.DeptSoft }))),
};

export default function Department() {
  const { template } = useTemplate();
  const variantId = template.pageShells.department || 'sidebar';
  const Shell = departmentShells[variantId] || departmentShells.sidebar;

  return (
    <ShellErrorBoundary pageName="科室页">
      <Suspense fallback={<ShellLoadingFallback />}>
        <Shell />
      </Suspense>
    </ShellErrorBoundary>
  );
}
