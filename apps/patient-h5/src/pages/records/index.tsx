import { NavBar, Empty, InfiniteScroll, PullToRefresh, Skeleton } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { medicalRecordApi } from '@hospital/api';
import type { MedicalRecordListItem } from '@hospital/api';
import { Card } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

const RecordsPage: React.FC = () => {
  const [records, setRecords] = useState<MedicalRecordListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async (refresh = false) => {
    const currentPage = refresh ? 1 : page;
    
    try {
      if (refresh) {
        setLoading(true);
      }
      
      const result = await medicalRecordApi.getList({
        page: currentPage,
        pageSize,
      });
      
      if (refresh) {
        setRecords(result.data);
        setPage(2);
      } else {
        setRecords((prev) => [...prev, ...result.data]);
        setPage((prev) => prev + 1);
      }
      
      setHasMore(result.data.length >= pageSize);
    } catch (error) {
      console.error('加载数据失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    await loadData(true);
  };

  const loadMore = async () => {
    if (hasMore && !loading) {
      await loadData();
    }
  };

  const formatDate = (date?: string) => {
    if (!date) return '-';
    return date.substring(0, 10);
  };

  if (loading && records.length === 0) {
    return (
      <div className="min-h-screen bg-background">
        <NavBar 
          onBack={() => history.back()}
          className="!bg-card border-b border-border"
        >
          就诊记录
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
      <NavBar 
        onBack={() => history.back()}
        className="!bg-card border-b border-border"
      >
        就诊记录
      </NavBar>
      
      <PullToRefresh onRefresh={handleRefresh}>
        <div className="p-4">
          {records.length === 0 ? (
            <div className="flex items-center justify-center h-64">
              <Empty description="暂无就诊记录" />
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
                  <Card 
                    variant="default" 
                    padding="md"
                    hoverable
                    animated={false}
                    className="cursor-pointer"
                    onClick={() => history.push(`/records/${record.id}`)}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <span className="text-xs text-muted-foreground">病历号：</span>
                        <span className="font-mono text-sm text-foreground">{record.recordNo}</span>
                      </div>
                      <span className="text-sm text-muted-foreground">
                        {formatDate(record.visitDate)}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs text-accent bg-accent/10 px-2 py-1 rounded-full">
                        {record.diagnosis}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <p className="text-sm text-muted-foreground">
                        {record.departmentName} · {record.doctorName}
                      </p>
                      <svg 
                        className="w-5 h-5 text-muted-foreground" 
                        fill="none" 
                        stroke="currentColor" 
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          )}
          <InfiniteScroll loadMore={loadMore} hasMore={hasMore} />
        </div>
      </PullToRefresh>
    </div>
  );
};

export default RecordsPage;
