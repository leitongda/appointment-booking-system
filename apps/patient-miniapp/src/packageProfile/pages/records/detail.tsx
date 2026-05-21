import { View, Text } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Loading, Empty, Tag } from '@nutui/nutui-react-taro';
import { useState, useCallback, useEffect } from 'react';
import { medicalRecordApi, examinationReportApi } from '@hospital/api';
import { useProtectedPage } from '../../../hooks/useProtectedPage';
import { useApplyThemeNavigationBar } from '../../../utils/theme';
import LoginPopup from '../../../components/LoginPopup';
import type { MedicalRecord, ExaminationReportListItem } from '@hospital/api';
import './detail.less';

const RecordDetailPage = () => {
  useApplyThemeNavigationBar();
  const router = useRouter();
  const { id } = router.params;

  const [loading, setLoading] = useState(true);
  const [record, setRecord] = useState<MedicalRecord | null>(null);
  const [reports, setReports] = useState<ExaminationReportListItem[]>([]);

  const loadRecord = useCallback(async () => {
    if (!id) {
      setLoading(false);
      return;
    }

    try {
      const data = await medicalRecordApi.getDetail(id!);
      setRecord(data);
    } catch (error: any) {
      console.error('加载就诊记录详情失败', error);
      Taro.showToast({ title: error.message || '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  }, [id]);

  const { showLoginPopup, handleLoginSuccess, handleLoginClose } = useProtectedPage({
    load: loadRecord,
    clear: () => {
      setRecord(null);
      setLoading(false);
    },
    deps: [id],
  });

  const loadReports = useCallback(async () => {
    if (!id) return;
    try {
      const data = await examinationReportApi.getByRecord(id);
      setReports(data);
    } catch (error) {
      console.error('加载检查报告失败:', error);
    }
  }, [id]);

  useEffect(() => {
    if (record) {
      loadReports();
    }
  }, [record, loadReports]);

  const formatDate = (date?: string) => {
    if (!date) return '-';
    return date.substring(0, 10);
  };

  if (loading) {
    return (
      <View className="record-detail-page loading-container">
        <Loading type="spinner">加载中...</Loading>
      </View>
    );
  }

  if (!record) {
    return (
      <View className="record-detail-page">
        <Empty description="病历不存在" />
      </View>
    );
  }

  return (
    <View className="record-detail-page">
      <View className="header">
        <Text className="date">{formatDate(record.visitDate)}</Text>
        <Text className="dept">{record.departmentName}</Text>
      </View>

      <View className="section">
        <Text className="section-title">就诊信息</Text>
        <View className="info-row">
          <Text className="label">病历号</Text>
          <Text className="value">{record.recordNo}</Text>
        </View>
        <View className="info-row">
          <Text className="label">就诊医生</Text>
          <Text className="value">{record.doctorName}</Text>
        </View>
        <View className="info-row">
          <Text className="label">患者姓名</Text>
          <Text className="value">{record.patientName}</Text>
        </View>
      </View>

      <View className="section">
        <Text className="section-title">诊疗信息</Text>
        {record.chiefComplaint && (
          <View className="info-block">
            <Text className="block-label">主诉</Text>
            <Text className="block-value">{record.chiefComplaint}</Text>
          </View>
        )}
        {record.presentIllness && (
          <View className="info-block">
            <Text className="block-label">现病史</Text>
            <Text className="block-value">{record.presentIllness}</Text>
          </View>
        )}
        {record.pastHistory && (
          <View className="info-block">
            <Text className="block-label">既往史</Text>
            <Text className="block-value">{record.pastHistory}</Text>
          </View>
        )}
        {record.allergyHistory && (
          <View className="info-block">
            <Text className="block-label">过敏史</Text>
            <Text className="block-value">{record.allergyHistory}</Text>
          </View>
        )}
        {record.physicalExam && (
          <View className="info-block">
            <Text className="block-label">体格检查</Text>
            <Text className="block-value">{record.physicalExam}</Text>
          </View>
        )}
        {record.auxiliaryExam && (
          <View className="info-block">
            <Text className="block-label">辅助检查</Text>
            <Text className="block-value">{record.auxiliaryExam}</Text>
          </View>
        )}
        <View className="info-block">
          <Text className="block-label">诊断</Text>
          <View className="block-value">
            <Tag type="primary">{record.diagnosis}</Tag>
          </View>
        </View>
        {record.treatment && (
          <View className="info-block">
            <Text className="block-label">治疗方案</Text>
            <Text className="block-value">{record.treatment}</Text>
          </View>
        )}
      </View>

      {record.prescription && (
        <View className="section">
          <Text className="section-title">处方信息</Text>
          <Text className="prescription">{record.prescription}</Text>
        </View>
      )}

      {record.advice && (
        <View className="section">
          <Text className="section-title">医嘱</Text>
          <Text className="advice">{record.advice}</Text>
        </View>
      )}

      {reports.length > 0 && (
        <View className="section">
          <Text className="section-title">检查报告</Text>
          {reports.map((report) => (
            <View
              key={report.id}
              className="report-item"
              onClick={() => {
                if (report.fileUrl) {
                  Taro.downloadFile({
                    url: report.fileUrl,
                    success: (res) => {
                      Taro.openDocument({
                        filePath: res.tempFilePath,
                        showMenu: true,
                      });
                    },
                  });
                }
              }}
            >
              <View className="report-icon">
                <Text>{report.fileType === 'application/pdf' ? 'PDF' : 'IMG'}</Text>
              </View>
              <View className="report-info">
                <Text className="report-title">{report.title}</Text>
                <Text className="report-meta">
                  {report.fileName} · {report.fileSize < 1024 * 1024
                    ? `${(report.fileSize / 1024).toFixed(1)} KB`
                    : `${(report.fileSize / 1024 / 1024).toFixed(1)} MB`}
                </Text>
              </View>
              <Text className="report-action">查看</Text>
            </View>
          ))}
        </View>
      )}

      {record.totalFee !== undefined && record.totalFee > 0 && (
        <View className="section">
          <Text className="section-title">费用信息</Text>
          <View className="info-row">
            <Text className="label">总费用</Text>
            <Text className="value fee">¥{record.totalFee.toFixed(2)}</Text>
          </View>
        </View>
      )}

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={handleLoginClose}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default RecordDetailPage;
