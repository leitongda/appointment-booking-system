/**
 * 公告详情预览页（只读）
 *
 * 展示标题、内容、浏览量、发布时间等信息
 */
import { Card, Descriptions, Spin, Tag } from 'antd';
import { PageContainer } from '@ant-design/pro-components';
import { useEffect, useState } from 'react';
import { useParams, history } from '@umijs/max';
import { contentApi } from '@hospital/api';
import type { Notice } from '@hospital/api';
import { useDict } from '@/hooks/useDict';

const NoticeDetailPage: React.FC = () => {
  const { id } = useParams();
  const [notice, setNotice] = useState<Notice | null>(null);
  const [loading, setLoading] = useState(false);
  const { options: noticeTypeOptions } = useDict('notice_type');

  useEffect(() => {
    if (id) {
      setLoading(true);
      contentApi
        .getNoticeDetail(id)
        .then((data) => setNotice(data))
        .catch(() => history.push('/content-center/content/notice'))
        .finally(() => setLoading(false));
    }
  }, [id]);

  const typeName = noticeTypeOptions.find((o) => Number(o.value) === notice?.type)?.label || '-';

  return (
    <PageContainer
      onBack={() => history.push('/content-center/content/notice')}
    >
      <Spin spinning={loading}>
        {notice && (
          <>
            <Card title="基本信息" style={{ marginBottom: 16 }}>
              <Descriptions column={2} bordered size="middle">
                <Descriptions.Item label="标题" span={2}>{notice.title}</Descriptions.Item>
                <Descriptions.Item label="类型">{typeName}</Descriptions.Item>
                <Descriptions.Item label="状态">
                  {notice.status === 1 ? <Tag color="success">已发布</Tag> : <Tag>草稿</Tag>}
                </Descriptions.Item>
                <Descriptions.Item label="浏览量">{notice.viewCount ?? 0}</Descriptions.Item>
                <Descriptions.Item label="置顶">
                  {notice.isTop ? <Tag color="red">是</Tag> : '否'}
                </Descriptions.Item>
                <Descriptions.Item label="发布时间">{notice.publishTime || '-'}</Descriptions.Item>
                <Descriptions.Item label="创建时间">{notice.createdAt}</Descriptions.Item>
              </Descriptions>
            </Card>

            <Card title="公告内容">
              <div
                className="ql-editor"
                style={{ padding: 0 }}
                dangerouslySetInnerHTML={{ __html: notice.content || '' }}
              />
            </Card>
          </>
        )}
      </Spin>
    </PageContainer>
  );
};

export default NoticeDetailPage;
