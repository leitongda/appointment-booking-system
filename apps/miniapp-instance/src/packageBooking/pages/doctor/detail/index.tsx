import { useTemplate } from '../../../../contexts/TemplateContext';
import { doctorShells } from '../../../../shells/doctor';

export default function DoctorDetail() {
  const { template } = useTemplate();
  const variantId = template.pageShells.doctorDetail || 'standard';
  const Shell = doctorShells[variantId] || doctorShells['standard'];

  return <Shell />;
}
