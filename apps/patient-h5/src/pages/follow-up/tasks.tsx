import { Tabs, Empty, PullToRefresh, InfiniteScroll, Skeleton, Tag } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { followUpApi } from '@hospital/api';
import type { FollowUpTaskListItem } from '@hospital/api';
import { Card, PatientPicker } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';
import { announce } from '@/components/ui/toast-live';

const STATUS_TABS = [
  { key: 'all', title: '全部' },
  { key: 'pending', title: '待随访' },
  { key: 'completed', title: '已完成' },
  { key: 'overdue', title: '已逾期' },
  { key: 'skipped', title: '已跳过' },
];

const STATUS_MAP: Record<string, { text: string; color: string }> = {
  pending: { text: '待随访', color: '#0052FF' },
  completed: { text: '已完成', color: '#52c41a' },
  overdue: { text: '已逾期', color: '#ff4d4f' },
  skipped: { text: '已跳过', color: '#999' },
};

const FollowUpTasksPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('all');
  const [patientId, setPatientId] = useState<string | undefined>();
  const [tasks, setTasks] = useState<FollowUpTaskListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    loadTasks(true);
  }, [activeTab, patientId]);

  const loadTasks = async (reset = false) => {
    const currentPage = reset ? 1 : page;
    try {
      if (reset) setLoading(true);
      const params: any = { page: currentPage, pageSize };
      if (activeTab !== 'all') params.status = activeTab;
      if (patientId) params.patientId = patientId;
      const result = await followUpApi.getMyPatientTasks(params);
      if (reset) {
        setTasks(result.data);
        setPage(2);
      } else {
        setTasks((prev) => [...prev, ...result.data]);
        setPage((prev) => prev + 1);
      }
      setHasMore(result.data.length >= pageSize);
    } catch (error) {
      console.error('加载随访任务失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePatientChange = useCallback((id: string | undefined) => {
    setPatientId(id);
  }, []);

  const handleRefresh = async () => {
    await loadTasks(true);
    announce('随访任务已刷新');
  };

  const formatDate = (date?: string) => {
    if (!date) return '-';
    return date.substring(0, 10);
  };

  if (loading && tasks.length === 0) {
    return (
      <div className="min-h-screen bg-background">
        <div className="bg-gradient-to-r from-accent to-accent-secondary px-4 pt-12 pb-4">
          <div className="flex items-center justify-between">
            <h1 className="text-white text-xl font-display">我的随访</h1>
          </div>
        </div>
        <div className="p-4">
          <Skeleton.Paragraph lineCount={5} animated />
          <Skeleton.Paragraph lineCount={5} animated />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background" role="main">
      <div className="bg-gradient-to-r from-accent to-accent-secondary px-4 pt-12 pb-4">
        <div className="flex items-center justify-between">
          <h1 className="text-white text-xl font-display">我的随访</h1>
          <PatientPicker value={patientId} onChange={handlePatientChange} />
        </div>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        className="!bg-card"
        style={{
          '--active-line-color': '#0052FF',
          '--active-title-color': '#0052FF',
        } as React.CSSProperties}
      >
        {STATUS_TABS.map((tab) => (
          <Tabs.Tab title={tab.title} key={tab.key} />
        ))}
      </Tabs>

      <PullToRefresh onRefresh={handleRefresh}>
        <div className="p-4">
          {tasks.length === 0 ? (
            <div className="flex items-center justify-center h-64" role="status">
              <Empty description="暂无随访任务" />
            </div>
          ) : (
            <motion.div
              className="space-y-3"
              variants={stagger}
              initial="hidden"
              animate="visible"
              role="list"
              aria-label="随访任务列表"
            >
              {tasks.map((task) => (
                <motion.div
                  key={task.id}
                  variants={fadeInUp}
                  whileTap={{ scale: 0.98 }}
                  role="listitem"
                >
                  <Card
                    variant="default"
                    padding="md"
                    hoverable
                    animated={false}
                    className="cursor-pointer"
                    onClick={() => history.push(`/follow-up/tasks/${task.id}`)}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">任务编号：</span>
                        <span className="font-mono text-sm text-foreground">{task.taskNo || '-'}</span>
                      </div>
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

                    {task.planName && (
                      <p className="text-sm text-foreground mb-1">
                        {task.planName}
                        {task.stepOrder != null && ` · 第${task.stepOrder}步`}
                      </p>
                    )}

                    <div className="flex items-center justify-between mt-2">
                      <p className="text-sm text-muted-foreground">
                        {task.departmentName || ''} · {task.doctorName || ''}
                      </p>
                      <span className="text-xs text-muted-foreground">
                        {formatDate(task.scheduledDate)}
                      </span>
                    </div>
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          )}
          <InfiniteScroll loadMore={() => loadTasks()} hasMore={hasMore} />
        </div>
      </PullToRefresh>
    </div>
  );
};

export default FollowUpTasksPage;
