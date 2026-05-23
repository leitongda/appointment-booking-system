import { NavBar, Empty, InfiniteScroll, PullToRefresh, Skeleton, Tag } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { followUpApi } from '@hospital/api';
import type { FollowUpRecordListItem } from '@hospital/api';
import { Card, PatientPicker } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';
import { announce } from '@/components/ui/toast-live';

const CONDITION_MAP: Record<string, { text: string; color: string }> = {
  improved: { text: '好转', color: '#52c41a' },
  stable: { text: '稳定', color: '#0052FF' },
  worsened: { text: '加重', color: '#ff4d4f' },
};

const FollowUpRecordsPage: React.FC = () => {
  const [patientId, setPatientId] = useState<string | undefined>();
  const [records, setRecords] = useState<FollowUpRecordListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    loadData(true);
  }, [patientId]);

  const loadData = async (refresh = false) => {
    const currentPage = refresh ? 1 : page;
    try {
      if (refresh) setLoading(true);
      const params: any = { page: currentPage, pageSize };
      if (patientId) params.patientId = patientId;
      const result = await followUpApi.getMyPatientRecords(params);
      if (refresh) {
        setRecords(result.data);
        setPage(2);
      } else {
        setRecords((prev) => [...prev, ...result.data]);
        setPage((prev) => prev + 1);
      }
      setHasMore(result.data.length >= pageSize);
    } catch (error) {
      console.error('加载随访记录失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePatientChange = useCallback((id: string | undefined) => {
    setPatientId(id);
  }, []);

  const handleRefresh = async () => {
    await loadData(true);
    announce('随访记录已刷新');
  };

  const formatDate = (date?: string) => {
    if (!date) return '-';
    return date.substring(0, 10);
  };

  if (loading && records.length === 0) {
    return (
      <div className="min-h-screen bg-background">
        <NavBar onBack={() => history.back()} className="!bg-card border-b border-border">
          随访记录
        </NavBar>
        <div className="p-4">
          <Skeleton.Paragraph lineCount={5} animated />
          <Skeleton.Paragraph lineCount={5} animated />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <NavBar onBack={() => history.back()} className="!bg-card border-b border-border" right={<PatientPicker value={patientId} onChange={handlePatientChange} />}>
        随访记录
      </NavBar>

      <PullToRefresh onRefresh={handleRefresh}>
        <div className="p-4">
          {records.length === 0 ? (
            <div className="flex items-center justify-center h-64">
              <Empty description="暂无随访记录" />
            </div>
          ) : (
            <motion.div
              className="space-y-3"
              variants={stagger}
              initial="hidden"
              animate="visible"
            >
              {records.map((record) => (
                <motion.div
                  key={record.id}
                  variants={fadeInUp}
                  whileTap={{ scale: 0.98 }}
                >
                  <Card variant="default" padding="md" hoverable animated={false}>
                    <div className="flex justify-between items-start mb-2">
                      <p className="text-sm text-muted-foreground">
                        {record.doctorName || '未知医生'} · {formatDate(record.followUpDate || record.createdAt)}
                      </p>
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
                      <p className="text-sm text-foreground line-clamp-3 mb-2">
                        {record.content}
                      </p>
                    )}

                    {record.taskId && (
                      <div className="flex items-center gap-1 mt-2">
                        <span
                          className="text-xs text-accent cursor-pointer"
                          onClick={(e) => {
                            e.stopPropagation();
                            history.push(`/follow-up/tasks/${record.taskId}`);
                          }}
                        >
                          查看关联任务
                        </span>
                      </div>
                    )}
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          )}
          <InfiniteScroll loadMore={() => loadData()} hasMore={hasMore} />
        </div>
      </PullToRefresh>
    </div>
  );
};

export default FollowUpRecordsPage;
