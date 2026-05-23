import { View, Text } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Loading, Empty, Tag, Button } from '@nutui/nutui-react-taro';
import { useState, useCallback } from 'react';
import { followUpApi, selfReportApi } from '@hospital/api';
import { useProtectedPage } from '../../../hooks/useProtectedPage';
import { useApplyThemeNavigationBar } from '../../../utils/theme';
import LoginPopup from '../../../components/LoginPopup';
import type { FollowUpTask, FollowUpRecord, SelfReportListItem } from '@hospital/api';
import './detail.less';

const STATUS_MAP: Record<string, { text: string; type: string }> = {
  pending: { text: '待随访', type: 'primary' },
  completed: { text: '已完成', type: 'success' },
  overdue: { text: '已逾期', type: 'danger' },
  skipped: { text: '已跳过', type: 'default' },
};

const CONDITION_MAP: Record<string, { text: string; type: string }> = {
  improved: { text: '好转', type: 'success' },
  stable: { text: '稳定', type: 'primary' },
  worsened: { text: '加重', type: 'danger' },
};

const FollowUpDetailPage = () => {
  useApplyThemeNavigationBar();
  const router = useRouter();
  const { id } = router.params;

  const [loading, setLoading] = useState(true);
  const [task, setTask] = useState<FollowUpTask | null>(null);
  const [records, setRecords] = useState<FollowUpRecord[]>([]);
  const [selfReports, setSelfReports] = useState<SelfReportListItem[]>([]);

  const loadDetail = useCallback(async () => {
    if (!id) {
      setLoading(false);
      return;
    }
    try {
      const [taskData, recordsData, reportsData] = await Promise.all([
        followUpApi.getTaskDetail(id),
        followUpApi.getTaskRecords(id),
        selfReportApi.getByTask(id).catch(() => []),
      ]);
      setTask(taskData);
      setRecords(recordsData);
      setSelfReports(reportsData);
    } catch (error: any) {
      console.error('加载随访详情失败', error);
      Taro.showToast({ title: error.message || '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  }, [id]);

  const { showLoginPopup, handleLoginSuccess, handleLoginClose } = useProtectedPage({
    load: loadDetail,
    clear: () => {
      setTask(null);
      setRecords([]);
      setSelfReports([]);
      setLoading(false);
    },
    deps: [id],
  });

  const formatDate = (date?: string) => {
    if (!date) return '-';
    return date.substring(0, 10);
  };

  const formatDateTime = (date?: string) => {
    if (!date) return '-';
    return date.replace('T', ' ').substring(0, 16);
  };

  if (loading) {
    return (
      <View className="follow-up-detail-page loading-container">
        <Loading type="spinner">加载中...</Loading>
      </View>
    );
  }

  if (!task) {
    return (
      <View className="follow-up-detail-page">
        <Empty description="任务不存在" />
      </View>
    );
  }

  const statusInfo = STATUS_MAP[task.status || ''] || { text: task.status || '-', type: 'default' };

  return (
    <View className="follow-up-detail-page">
      {/* 状态概览 */}
      <View className="status-card">
        <View className="status-header">
          <Text className="status-title">随访任务</Text>
          <Tag type={statusInfo.type as any} plain>{statusInfo.text}</Tag>
        </View>
        {task.taskNo && (
          <Text className="task-no">编号：{task.taskNo}</Text>
        )}
      </View>

      {/* 任务信息 */}
      <View className="section">
        <Text className="section-title">任务信息</Text>
        <View className="info-card">
          {task.planName && (
            <View className="info-row">
              <Text className="label">随访计划</Text>
              <Text className="value">
                {task.planName}{task.stepOrder != null ? ` · 第${task.stepOrder}步` : ''}
              </Text>
            </View>
          )}
          <View className="info-row">
            <Text className="label">计划日期</Text>
            <Text className="value">{formatDate(task.scheduledDate)}</Text>
          </View>
          <View className="info-row">
            <Text className="label">负责医生</Text>
            <Text className="value">{task.doctorName || '-'}</Text>
          </View>
          <View className="info-row">
            <Text className="label">科室</Text>
            <Text className="value">{task.departmentName || '-'}</Text>
          </View>
          {task.completedAt && (
            <View className="info-row">
              <Text className="label">完成时间</Text>
              <Text className="value">{formatDateTime(task.completedAt)}</Text>
            </View>
          )}
          {task.skipReason && (
            <View className="info-row">
              <Text className="label">跳过原因</Text>
              <Text className="value">{task.skipReason}</Text>
            </View>
          )}
        </View>
      </View>

      {/* 关联记录 */}
      <View className="section">
        <Text className="section-title">随访记录 ({records.length})</Text>
        {records.length === 0 ? (
          <View className="info-card empty-card">
            <Empty description="暂无随访记录" />
          </View>
        ) : (
          records.map((record) => {
            const conditionInfo = record.patientCondition
              ? CONDITION_MAP[record.patientCondition] || { text: record.patientCondition, type: 'default' }
              : null;
            return (
              <View key={record.id} className="info-card record-item">
                <View className="record-header">
                  <Text className="record-date">{formatDateTime(record.followUpDate || record.createdAt)}</Text>
                  {conditionInfo && (
                    <Tag type={conditionInfo.type as any} plain>{conditionInfo.text}</Tag>
                  )}
                </View>
                {record.content && (
                  <Text className="record-content">{record.content}</Text>
                )}
                {record.nextAction && (
                  <View className="next-action">
                    <Text className="next-label">下一步措施</Text>
                    <Text className="next-value">{record.nextAction}</Text>
                  </View>
                )}
                {record.nextFollowUpDate && (
                  <Text className="next-date">下次随访：{formatDate(record.nextFollowUpDate)}</Text>
                )}
              </View>
            );
          })
        )}
      </View>

      {/* 自报告数据 */}
      <View className="section">
        <View className="section-header">
          <Text className="section-title">自报告数据 ({selfReports.length})</Text>
          {task.status === 'pending' && (
            <Button
              type="primary"
              size="small"
              onClick={() => Taro.navigateTo({ url: `/packageProfile/pages/follow-up/report?taskId=${id}` })}
            >
              提交自报告
            </Button>
          )}
        </View>
        {selfReports.length === 0 ? (
          <View className="info-card empty-card">
            <Empty description="暂无自报告数据" />
          </View>
        ) : (
          selfReports.map((report) => (
            <View key={report.id} className="info-card report-item">
              <View className="report-header">
                <Text className="report-date">{formatDate(report.reportDate || report.createdAt)}</Text>
                <Tag type={report.status === 'reviewed' ? 'success' : 'warning'} plain>
                  {report.status === 'reviewed' ? '已审核' : '待审核'}
                </Tag>
              </View>
              <View className="vitals-grid">
                {report.systolicBp != null && report.diastolicBp != null && (
                  <View className="vital-item">
                    <Text className="vital-label">血压</Text>
                    <Text className="vital-value">{report.systolicBp}/{report.diastolicBp}</Text>
                    <Text className="vital-unit">mmHg</Text>
                  </View>
                )}
                {report.bloodGlucose != null && (
                  <View className="vital-item">
                    <Text className="vital-label">血糖</Text>
                    <Text className="vital-value">{report.bloodGlucose}</Text>
                    <Text className="vital-unit">mmol/L</Text>
                  </View>
                )}
              </View>
              {report.symptoms && (
                <Text className="report-symptoms">症状：{report.symptoms}</Text>
              )}
            </View>
          ))
        )}
      </View>

      <LoginPopup
        visible={showLoginPopup}
        onClose={handleLoginClose}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default FollowUpDetailPage;
