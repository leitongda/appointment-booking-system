/**
 * 文章详情预览页（只读）
 */
import { Card, Descriptions, Image, Spin, Tag } from 'antd';
import { PageContainer } from '@ant-design/pro-components';
import { useEffect, useState } from 'react';
import { useParams, history } from '@umijs/max';
import { articleApi } from '@hospital/api';
import type { CmsArticle } from '@hospital/api';

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '草稿', color: 'default' },
  1: { text: '已发布', color: 'success' },
  2: { text: '已下线', color: 'warning' },
};

const ArticleDetailPage: React.FC = () => {
  const { id } = useParams();
  const [article, setArticle] = useState<CmsArticle | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (id) {
      setLoading(true);
      articleApi
        .getDetail(id)
        .then((data) => setArticle(data))
        .catch(() => history.push('/cms/articles'))
        .finally(() => setLoading(false));
    }
  }, [id]);

  const statusInfo = article ? STATUS_MAP[article.status] : STATUS_MAP[0];

  return (
    <PageContainer onBack={() => history.push('/cms/articles')}>
      <Spin spinning={loading}>
        {article && (
          <>
            <Card title="基本信息" style={{ marginBottom: 16 }}>
              <Descriptions column={2} bordered size="middle">
                <Descriptions.Item label="标题" span={2}>
                  {article.title}
                  {article.isTop ? <Tag color="red" style={{ marginLeft: 8 }}>置顶</Tag> : null}
                </Descriptions.Item>
                {article.subtitle && (
                  <Descriptions.Item label="副标题" span={2}>{article.subtitle}</Descriptions.Item>
                )}
                <Descriptions.Item label="状态">
                  <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="作者">{article.author || '-'}</Descriptions.Item>
                <Descriptions.Item label="来源">{article.source || '-'}</Descriptions.Item>
                <Descriptions.Item label="浏览量">{article.viewCount ?? 0}</Descriptions.Item>
                <Descriptions.Item label="发布时间">{article.publishTime || '-'}</Descriptions.Item>
                <Descriptions.Item label="创建时间">{article.createdAt}</Descriptions.Item>
              </Descriptions>
            </Card>

            {article.coverImage && (
              <Card title="封面图" style={{ marginBottom: 16 }}>
                <Image src={article.coverImage} width={320} />
              </Card>
            )}

            {article.summary && (
              <Card title="摘要" style={{ marginBottom: 16 }}>
                <p style={{ whiteSpace: 'pre-wrap' }}>{article.summary}</p>
              </Card>
            )}

            <Card title="正文内容">
              <div
                style={{ padding: 0 }}
                dangerouslySetInnerHTML={{ __html: article.content || '' }}
              />
            </Card>
          </>
        )}
      </Spin>
    </PageContainer>
  );
};

export default ArticleDetailPage;
