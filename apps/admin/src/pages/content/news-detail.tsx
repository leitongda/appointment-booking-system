/**
 * 新闻详情预览页（只读）
 *
 * 展示标题、内容、浏览量、发布时间等信息
 */
import { Card, Descriptions, Image, Spin, Tag } from 'antd';
import { PageContainer } from '@ant-design/pro-components';
import { useEffect, useState } from 'react';
import { useParams, history } from '@umijs/max';
import { contentApi } from '@hospital/api';
import type { News } from '@hospital/api';
import { useDict } from '@/hooks/useDict';

const NewsDetailPage: React.FC = () => {
  const { id } = useParams();
  const [news, setNews] = useState<News | null>(null);
  const [loading, setLoading] = useState(false);
  const { options: newsTypeOptions } = useDict('news_type');

  useEffect(() => {
    if (id) {
      setLoading(true);
      contentApi
        .getNewsDetail(id)
        .then((data) => setNews(data))
        .catch(() => history.push('/content-center/content/news'))
        .finally(() => setLoading(false));
    }
  }, [id]);

  const typeName = newsTypeOptions.find((o) => Number(o.value) === news?.type)?.label || '-';

  return (
    <PageContainer
      onBack={() => history.push('/content-center/content/news')}
    >
      <Spin spinning={loading}>
        {news && (
          <>
            <Card title="基本信息" style={{ marginBottom: 16 }}>
              <Descriptions column={2} bordered size="middle">
                <Descriptions.Item label="标题" span={2}>{news.title}</Descriptions.Item>
                <Descriptions.Item label="类型">{typeName}</Descriptions.Item>
                <Descriptions.Item label="状态">
                  {news.status === 1 ? <Tag color="success">已发布</Tag> : <Tag>草稿</Tag>}
                </Descriptions.Item>
                <Descriptions.Item label="浏览量">{news.viewCount ?? 0}</Descriptions.Item>
                <Descriptions.Item label="置顶">
                  {news.isTop ? <Tag color="red">是</Tag> : '否'}
                </Descriptions.Item>
                <Descriptions.Item label="发布时间">{news.publishTime || '-'}</Descriptions.Item>
                <Descriptions.Item label="创建时间">{news.createdAt}</Descriptions.Item>
              </Descriptions>
            </Card>

            {news.coverImage && (
              <Card title="封面图" style={{ marginBottom: 16 }}>
                <Image src={news.coverImage} width={320} />
              </Card>
            )}

            {news.summary && (
              <Card title="摘要" style={{ marginBottom: 16 }}>
                <p style={{ whiteSpace: 'pre-wrap' }}>{news.summary}</p>
              </Card>
            )}

            <Card title="正文内容">
              <div
                className="ql-editor"
                style={{ padding: 0 }}
                dangerouslySetInnerHTML={{ __html: news.content || '' }}
              />
            </Card>
          </>
        )}
      </Spin>
    </PageContainer>
  );
};

export default NewsDetailPage;
