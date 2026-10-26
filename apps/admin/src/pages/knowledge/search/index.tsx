/**
 * 智能检索：语义检索可见知识库，结果携带可定位的引用来源（文档 / 页码 / 章节 / 片段 / 相似度）
 */
import { PageContainer } from '@ant-design/pro-components';
import { Alert, App, Card, Empty, Input, List, Select, Space, Tag, Typography } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from '@umijs/max';
import { knowledgeApi } from '@hospital/api';
import type { KnowledgeBase, KnowledgeSearchHit, KnowledgeSearchResult } from '@hospital/api';
import DocumentPreviewDrawer from '../components/DocumentPreviewDrawer';
import type { PreviewTarget } from '../components/DocumentPreviewDrawer';
import { isFeatureDisabled } from '../shared';

const TOP_K = 10;

function scoreColor(score: number): string {
  if (score >= 0.8) return 'green';
  if (score >= 0.6) return 'blue';
  return 'default';
}

const KnowledgeSearchPage: React.FC = () => {
  const { message } = App.useApp();
  const [searchParams] = useSearchParams();
  const [bases, setBases] = useState<KnowledgeBase[]>([]);
  const [selectedKbIds, setSelectedKbIds] = useState<string[]>(() => {
    const preset = searchParams.get('kb');
    return preset ? [preset] : [];
  });
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<KnowledgeSearchResult | null>(null);
  const [alert, setAlert] = useState<{ type: 'warning' | 'error' | 'info'; text: string } | null>(null);
  const [preview, setPreview] = useState<PreviewTarget | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const page = await knowledgeApi.listBases({ scope: 'all', page: 1, pageSize: 200 });
        setBases(page.data ?? []);
      } catch (error: any) {
        if (isFeatureDisabled(error)) {
          setAlert({ type: 'info', text: '知识库功能未启用（服务端 KB_ENABLED 关闭）。' });
          return;
        }
        message.error(error?.message || '加载知识库列表失败');
      }
    })();
  }, [message]);

  const baseOptions = useMemo(
    () => bases.map((kb) => ({ value: kb.id, label: `${kb.name}（${kb.docCount} 篇）` })),
    [bases],
  );
  const baseNameById = useMemo(() => new Map(bases.map((kb) => [kb.id, kb.name])), [bases]);

  const handleSearch = async (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) return;
    setLoading(true);
    setAlert(null);
    try {
      const response = await knowledgeApi.search({
        query: trimmed,
        kbIds: selectedKbIds.length ? selectedKbIds : undefined,
        topK: TOP_K,
      });
      setResult(response);
    } catch (error: any) {
      setResult(null);
      const code = error?.errorCode as string | undefined;
      if (code === 'KB_EMBEDDING_MISMATCH') {
        setAlert({ type: 'warning', text: error?.message || '所选知识库需重建索引后方可检索' });
      } else if (code === 'KB_EMBEDDING_UNAVAILABLE') {
        setAlert({ type: 'error', text: '检索服务暂不可用，请稍后重试' });
      } else if (isFeatureDisabled(error)) {
        setAlert({ type: 'info', text: '知识库功能未启用（服务端 KB_ENABLED 关闭）。' });
      } else {
        message.error(error?.message || '检索失败');
      }
    } finally {
      setLoading(false);
    }
  };

  const openSource = async (hit: KnowledgeSearchHit) => {
    try {
      const doc = await knowledgeApi.getDocument(hit.docId);
      setPreview({ docId: doc.id, title: doc.title, mimeType: doc.mimeType, fileName: doc.fileName, pageNo: hit.pageNo });
    } catch (error: any) {
      message.error(error?.message || '打开原文失败');
    }
  };

  return (
    <PageContainer content="输入问题或关键词，系统在你可见的知识库中按语义检索，并给出可点开的引用来源。">
      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Select
            mode="multiple"
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="限定知识库（不选 = 全部可见库）"
            options={baseOptions}
            value={selectedKbIds}
            onChange={setSelectedKbIds}
            style={{ width: '100%' }}
            maxTagCount="responsive"
          />
          <Input.Search
            size="large"
            placeholder="例如：术前禁食多长时间？"
            enterButton="检索"
            loading={loading}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onSearch={handleSearch}
            maxLength={1000}
          />
        </Space>
      </Card>

      {alert ? <Alert type={alert.type} showIcon message={alert.text} style={{ marginBottom: 16 }} /> : null}

      {result ? (
        <Card
          title={
            <Space>
              <span>检索结果</span>
              <Typography.Text type="secondary">
                命中 {result.total} 条 · {result.tookMs} ms
              </Typography.Text>
            </Space>
          }
        >
          {result.hits.length === 0 ? (
            <Empty description="未找到相关内容，试试换个说法或扩大知识库范围" />
          ) : (
            <List
              itemLayout="vertical"
              dataSource={result.hits}
              renderItem={(hit, index) => (
                <List.Item
                  key={hit.chunkId}
                  actions={[
                    <a key="open" onClick={() => openSource(hit)}>
                      <FileTextOutlined /> 查看原文{hit.pageNo ? `（第 ${hit.pageNo} 页）` : ''}
                    </a>,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <Space wrap size={4}>
                        <Tag color={scoreColor(hit.score)}>{Math.round(hit.score * 100)}%</Tag>
                        <span>
                          {index + 1}. {hit.docTitle}
                        </span>
                        {baseNameById.get(hit.kbId) ? <Tag>{baseNameById.get(hit.kbId)}</Tag> : null}
                        {hit.section ? <Tag color="blue">{hit.section}</Tag> : null}
                        {hit.pageNo ? <Tag>第 {hit.pageNo} 页</Tag> : null}
                      </Space>
                    }
                  />
                  <Typography.Paragraph
                    style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}
                    ellipsis={{ rows: 4, expandable: true, symbol: '展开' }}
                  >
                    {hit.snippet}
                  </Typography.Paragraph>
                </List.Item>
              )}
            />
          )}
        </Card>
      ) : null}

      <DocumentPreviewDrawer target={preview} onClose={() => setPreview(null)} />
    </PageContainer>
  );
};

export default KnowledgeSearchPage;
