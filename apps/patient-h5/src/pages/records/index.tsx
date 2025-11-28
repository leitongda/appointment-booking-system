import { NavBar, List, Empty, InfiniteScroll, PullToRefresh, Skeleton, Tag } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect } from 'react';
import { medicalRecordApi } from '@hospital/api';
import type { MedicalRecordListItem } from '@hospital/api';
import styles from './index.less';

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
      <div className={styles.container}>
        <NavBar onBack={() => history.back()}>就诊记录</NavBar>
        <div style={{ padding: 16 }}>
          <Skeleton.Paragraph lineCount={5} animated />
          <Skeleton.Paragraph lineCount={5} animated />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>就诊记录</NavBar>
      
      <PullToRefresh onRefresh={handleRefresh}>
        {records.length === 0 ? (
          <Empty description="暂无就诊记录" style={{ marginTop: 100 }} />
        ) : (
          <>
            <List>
              {records.map((record) => (
                <List.Item
                  key={record.id}
                  description={
                    <div className={styles.recordInfo}>
                      <div className={styles.diagnosis}>
                        诊断：<Tag color="primary" fill="outline">{record.diagnosis}</Tag>
                      </div>
                      <div className={styles.meta}>
                        {record.departmentName} · {record.doctorName}
                      </div>
                    </div>
                  }
                  extra={
                    <div className={styles.date}>
                      {formatDate(record.visitDate)}
                    </div>
                  }
                  onClick={() => history.push(`/records/${record.id}`)}
                  arrow
                >
                  <div className={styles.recordNo}>病历号：{record.recordNo}</div>
                </List.Item>
              ))}
            </List>
            <InfiniteScroll loadMore={loadMore} hasMore={hasMore} />
          </>
        )}
      </PullToRefresh>
    </div>
  );
};

export default RecordsPage;
