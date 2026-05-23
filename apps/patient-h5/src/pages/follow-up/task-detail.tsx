import { NavBar, Skeleton, Toast, Empty, Tag } from 'antd-mobile';
import { history, useParams } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { followUpApi, selfReportApi } from '@hospital/api';
import type { FollowUpTask, FollowUpRecord, SelfReportListItem } from '@hospital/api';
import { Card, Button, SectionLabel } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

const STATUS_MAP: Record<string, { text: string; color: string }> = {
  pending: { text: '待随访', color: '#0052FF' },
  completed: { text: '已完成', color: '#52c41a' },
  overdue: { text: '已逾期', color: '#ff4d4f' },
  skipped: { text: '已跳过', color: '#999' },
};

const CONDITION_MAP: Record<string, { text: string; color: string }> = {
  improved: { text: '好转', color: '#52c41a' },
  stable: { text: '稳定', color: '#0052FF' },
  worsened: { text: '加重', color: '#ff4d4f' },
};

const FollowUpTaskDetailPage: React.FC = () => {
  const { id } = useParams() as { id: string };
  const [loading, setLoading] = useState(true);
  const [task, setTask] = useState<FollowUpTask | null>(null);
  const [records, setRecords] = useState<FollowUpRecord[]>([]);
  const [selfReports, setSelfReports] = useState<SelfReportListItem[]>([]);

  useEffect(() => {
    if (id) loadData();
  }, [id]);

  const loadData = async () => {
    try {
      const [taskData, recordsData, reportsData] = await Promise.all([
        followUpApi.getTaskDetail(id!),
        followUpApi.getTaskRecords(id!),
        selfReportApi.getByTask(id!).catch(() => []),
      ]);
      setTask(taskData);
      setRecords(recordsData);
      setSelfReports(reportsData);
    } catch (error: any) {
      Toast.show({ content: error.message || '加载失败', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

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
      <div className="min-h-screen bg-background">
        <NavBar onBack={() => history.back()} className="!bg-card border-b border-border">
          任务详情
        </NavBar>
        <div className="p-4">
          <Skeleton.Paragraph lineCount={10} animated />
        </div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="min-h-screen bg-background">
        <NavBar onBack={() => history.back()} className="!bg-card border-b border-border">
          任务详情
        </NavBar>
        <div className="flex items-center justify-center h-64">
          <Empty description="任务不存在" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-6">
      <NavBar onBack={() => history.back()} className="!bg-card border-b border-border">
        任务详情
      </NavBar>

      <motion.div className="p-4 space-y-4" variants={stagger} initial="hidden" animate="visible">
        {/* 状态概览 */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="md" animated={false}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-lg font-display text-foreground">随访任务</span>
              {task.status && (
                <Tag
                  color={STATUS_MAP[task.status]?.color || '#999'}
                  fill="outline"
                  style={{ '--border-radius': '12px', '--text-color': STATUS_MAP[task.status]?.color || '#999' } as React.CSSProperties}
                >
                  {STATUS_MAP[task.status]?.text || task.status}
                </Tag>
              )}
            </div>
            {task.taskNo && (
              <p className="text-sm text-muted-foreground mb-1">
                任务编号：<span className="font-mono text-foreground">{task.taskNo}</span>
              </p>
            )}
          </Card>
        </motion.div>

        {/* 任务信息 */}
        <motion.div variants={fadeInUp}>
          <SectionLabel>任务信息</SectionLabel>
          <Card variant="default" padding="md" animated={false}>
            <div className="space-y-3">
              {task.planName && (
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">随访计划</span>
                  <span className="text-sm text-foreground">
                    {task.planName}
                    {task.stepOrder != null && ` · 第${task.stepOrder}步`}
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">计划日期</span>
                <span className="text-sm text-foreground">{formatDate(task.scheduledDate)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">负责医生</span>
                <span className="text-sm text-foreground">{task.doctorName || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">科室</span>
                <span className="text-sm text-foreground">{task.departmentName || '-'}</span>
              </div>
              {task.completedAt && (
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">完成时间</span>
                  <span className="text-sm text-foreground">{formatDateTime(task.completedAt)}</span>
                </div>
              )}
              {task.skipReason && (
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">跳过原因</span>
                  <span className="text-sm text-foreground">{task.skipReason}</span>
                </div>
              )}
            </div>
          </Card>
        </motion.div>

        {/* 关联随访记录 */}
        <motion.div variants={fadeInUp}>
          <SectionLabel>随访记录 ({records.length})</SectionLabel>
          {records.length === 0 ? (
            <Card variant="default" padding="md" animated={false}>
              <div className="flex items-center justify-center py-6">
                <Empty description="暂无随访记录" />
              </div>
            </Card>
          ) : (
            <div className="space-y-3">
              {records.map((record) => (
                <Card key={record.id} variant="default" padding="md" animated={false}>
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-sm text-muted-foreground">
                      {formatDateTime(record.followUpDate || record.createdAt)}
                    </span>
                    {record.patientCondition && (
                      <Tag
                        color={CONDITION_MAP[record.patientCondition]?.color || '#999'}
                        fill="outline"
                        style={{ '--border-radius': '12px', '--text-color': CONDITION_MAP[record.patientCondition]?.color || '#999' } as React.CSSProperties}
                      >
                        {CONDITION_MAP[record.patientCondition]?.text || record.patientCondition}
                      </Tag>
                    )}
                  </div>
                  {record.content && (
                    <p className="text-sm text-foreground mb-2">{record.content}</p>
                  )}
                  {record.nextAction && (
                    <div className="mt-2 pt-2 border-t border-border">
                      <p className="text-xs text-muted-foreground mb-1">下一步措施</p>
                      <p className="text-sm text-foreground">{record.nextAction}</p>
                    </div>
                  )}
                  {record.nextFollowUpDate && (
                    <p className="text-xs text-muted-foreground mt-2">
                      下次随访：{formatDate(record.nextFollowUpDate)}
                    </p>
                  )}
                </Card>
              ))}
            </div>
          )}
        </motion.div>

        {/* 自报告数据 */}
        <motion.div variants={fadeInUp}>
          <div className="flex items-center justify-between mb-2">
            <SectionLabel className="mb-0">自报告数据 ({selfReports.length})</SectionLabel>
            <Button
              variant="primary"
              size="sm"
              onClick={() => history.push(`/follow-up/report/${id}`)}
            >
              提交自报告
            </Button>
          </div>
          {selfReports.length === 0 ? (
            <Card variant="default" padding="md" animated={false}>
              <div className="flex flex-col items-center justify-center py-6 gap-3">
                <Empty description="暂无自报告数据" />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => history.push(`/follow-up/report/${id}`)}
                >
                  立即提交
                </Button>
              </div>
            </Card>
          ) : (
            <div className="space-y-3">
              {selfReports.map((report) => (
                <Card key={report.id} variant="default" padding="md" animated={false}>
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-sm text-muted-foreground">
                      {formatDateTime(report.reportDate || report.createdAt)}
                    </span>
                    <Tag
                      color={report.status === 'reviewed' ? '#52c41a' : '#faad14'}
                      fill="outline"
                      style={{ '--border-radius': '12px' } as React.CSSProperties}
                    >
                      {report.status === 'reviewed' ? '已审核' : '待审核'}
                    </Tag>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {report.systolicBp != null && report.diastolicBp != null && (
                      <div>
                        <span className="text-muted-foreground">血压：</span>
                        <span className="text-foreground">{report.systolicBp}/{report.diastolicBp} mmHg</span>
                      </div>
                    )}
                    {report.bloodGlucose != null && (
                      <div>
                        <span className="text-muted-foreground">血糖：</span>
                        <span className="text-foreground">{report.bloodGlucose} mmol/L</span>
                      </div>
                    )}
                    {report.symptoms && (
                      <div className="col-span-2">
                        <span className="text-muted-foreground">症状：</span>
                        <span className="text-foreground">{report.symptoms}</span>
                      </div>
                    )}
                    {report.patientCondition && (
                      <div>
                        <span className="text-muted-foreground">感受：</span>
                        <span className="text-foreground">
                          {CONDITION_MAP[report.patientCondition]?.text || report.patientCondition}
                        </span>
                      </div>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </motion.div>
      </motion.div>
    </div>
  );
};

export default FollowUpTaskDetailPage;
