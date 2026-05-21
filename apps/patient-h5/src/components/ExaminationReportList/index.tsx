import { useState, useEffect } from 'react';
import { Toast, Empty, SpinLoading } from 'antd-mobile';
import { examinationReportApi } from '@hospital/api';
import type { ExaminationReportListItem } from '@hospital/api';
import { Card } from '@/components/ui';

interface Props {
  appointmentId?: string;
  recordId?: string;
  patientId?: string;
}

const REPORT_TYPE_LABELS: Record<string, string> = {
  blood_test: '血液检验',
  imaging: '影像检查',
  pathology: '病理检查',
  other: '其他检查',
};

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

const getFileIcon = (fileType: string): string => {
  if (fileType === 'application/pdf') return 'PDF';
  if (fileType.startsWith('image/')) return 'IMG';
  return 'FILE';
};

export const ExaminationReportList: React.FC<Props> = ({ appointmentId, recordId, patientId }) => {
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState<ExaminationReportListItem[]>([]);

  useEffect(() => {
    loadReports();
  }, [appointmentId, recordId, patientId]);

  const loadReports = async () => {
    setLoading(true);
    try {
      let data: ExaminationReportListItem[] = [];
      if (appointmentId) {
        data = await examinationReportApi.getByAppointment(appointmentId);
      } else if (recordId) {
        data = await examinationReportApi.getByRecord(recordId);
      } else if (patientId) {
        const result = await examinationReportApi.getByPatient(patientId, { page: 1, pageSize: 50 });
        data = result.data;
      }
      setReports(data);
    } catch (error: any) {
      // 静默失败，不影响主页面
      console.error('加载检查报告失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleView = (report: ExaminationReportListItem) => {
    if (report.fileUrl) {
      window.open(report.fileUrl, '_blank');
    } else {
      Toast.show({ content: '文件链接不可用', icon: 'fail' });
    }
  };

  if (loading) {
    return (
      <Card variant="default" padding="lg">
        <div className="flex items-center justify-center py-8">
          <SpinLoading color="primary" />
        </div>
      </Card>
    );
  }

  if (reports.length === 0) {
    return null; // 没有报告时不显示此区域
  }

  return (
    <Card variant="default" padding="lg">
      <h3 className="font-semibold text-foreground mb-4">检查报告</h3>
      <div className="space-y-3">
        {reports.map((report) => (
          <div
            key={report.id}
            className="flex items-center gap-3 p-3 bg-muted rounded-xl cursor-pointer hover:bg-muted/80 transition-colors"
            onClick={() => handleView(report)}
          >
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
              <span className="text-xs font-bold text-accent">
                {getFileIcon(report.fileType)}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                {report.title}
              </p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-muted-foreground">
                  {REPORT_TYPE_LABELS[report.reportType] || report.reportType}
                </span>
                <span className="text-xs text-muted-foreground">
                  {formatFileSize(report.fileSize)}
                </span>
              </div>
            </div>
            <div className="flex-shrink-0">
              <span className="text-xs text-accent">
                {report.fileType === 'application/pdf' ? '查看' : '预览'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};

export default ExaminationReportList;
