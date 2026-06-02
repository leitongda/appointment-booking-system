/** 模板市场 - 模板详情页 */

import React, { useEffect, useState, useCallback } from 'react';
import { history, useParams } from '@umijs/max';
import { PageContainer } from '@ant-design/pro-components';
import {
  Card,
  Row,
  Col,
  Tag,
  Space,
  Button,
  Descriptions,
  Spin,
  Carousel,
  List,
  Statistic,
  Divider,
  Empty,
  message,
  Typography,
} from 'antd';
import {
  ForkOutlined,
  EyeOutlined,
  CopyOutlined,
  StarOutlined,
  StarFilled,
  LikeOutlined,
  DownloadOutlined,
  ClockCircleOutlined,
  UserOutlined,
  TagsOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import { lowcodeApi, favoriteApi } from '@hospital/api';
import type {
  LowCodeTemplate,
  LowCodeTemplateVersionItem,
  LowCodeTemplateCategoryItem,
} from '@hospital/api';
import ForkDialog from './ForkDialog';

const { Text, Paragraph } = Typography;

/** 模板分类标签颜色映射 */
const CATEGORY_COLOR_MAP: Record<string, string> = {
  预约挂号: 'blue',
  健康档案: 'green',
  报告查询: 'purple',
  排队叫号: 'cyan',
  科室导航: 'geekblue',
  健康宣教: 'orange',
  满意度调查: 'magenta',
  其他: 'default',
};

/** 版本状态映射 */
const VERSION_STATUS_MAP: Record<number, { text: string; color: string }> = {
  1: { text: '草稿', color: 'default' },
  2: { text: '已发布', color: 'success' },
  3: { text: '已废弃', color: 'error' },
};

/** 模板详情页 */
const TemplateDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [template, setTemplate] = useState<LowCodeTemplate | null>(null);
  const [versions, setVersions] = useState<LowCodeTemplateVersionItem[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [relatedTemplates, setRelatedTemplates] = useState<LowCodeTemplate[]>([]);
  const [relatedLoading, setRelatedLoading] = useState(false);
  const [forkDialogOpen, setForkDialogOpen] = useState(false);
  const [categories, setCategories] = useState<LowCodeTemplateCategoryItem[]>([]);
  const [isFavorited, setIsFavorited] = useState(false);
  const [favoriteId, setFavoriteId] = useState<string | undefined>();

  /** 加载模板详情 */
  const fetchTemplate = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await lowcodeApi.getTemplate(id);
      setTemplate(data);
    } catch {
      message.error('加载模板详情失败');
    } finally {
      setLoading(false);
    }
  }, [id]);

  /** 加载版本历史 */
  const fetchVersions = useCallback(async () => {
    if (!id) return;
    setVersionsLoading(true);
    try {
      const data = await lowcodeApi.getTemplateVersions(id);
      setVersions(data.versions || []);
    } catch {
      // 版本历史可能需要权限，静默处理
    } finally {
      setVersionsLoading(false);
    }
  }, [id]);

  /** 加载分类列表 */
  const fetchCategories = useCallback(async () => {
    try {
      const data = await lowcodeApi.getTemplateCategories();
      setCategories(data || []);
    } catch {
      // 静默处理
    }
  }, []);

  /** 加载相关模板（同分类） */
  const fetchRelatedTemplates = useCallback(async (category: string) => {
    setRelatedLoading(true);
    try {
      const result = await lowcodeApi.getTemplates({ category, pageSize: 4 });
      // 排除当前模板
      const filtered = (result.data || []).filter(
        (t) => t.id !== id,
      );
      setRelatedTemplates(filtered.slice(0, 3));
    } catch {
      // 静默处理
    } finally {
      setRelatedLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTemplate();
    fetchCategories();
  }, [fetchTemplate, fetchCategories]);

  useEffect(() => {
    if (template) {
      fetchVersions();
      checkFavoriteStatus(template.id);
      if (template.category) {
        fetchRelatedTemplates(template.category);
      }
    }
  }, [template, fetchVersions, fetchRelatedTemplates, checkFavoriteStatus]);

  /** Fork 模板 — 打开 ForkDialog */
  const handleFork = () => {
    setForkDialogOpen(true);
  };

  /** 预览模板 */
  const handlePreview = () => {
    if (!template) return;
    window.open(`/platform/lowcode/preview/${template.sourcePageId || template.id}`, '_blank');
  };

  /** 检查收藏状态 */
  const checkFavoriteStatus = useCallback(async (templateId: string) => {
    try {
      const result = await favoriteApi.check('template', templateId);
      setIsFavorited(result.isFavorited);
      setFavoriteId(result.favoriteId);
    } catch {
      // 静默处理
    }
  }, []);

  /** 切换收藏状态 */
  const handleToggleFavorite = async () => {
    if (!template) return;
    try {
      if (isFavorited && favoriteId) {
        await favoriteApi.remove(favoriteId);
        setIsFavorited(false);
        setFavoriteId(undefined);
        message.success('已取消收藏');
      } else {
        const result = await favoriteApi.add({ targetType: 'template', targetId: template.id });
        setIsFavorited(true);
        setFavoriteId(result.id);
        message.success('已收藏');
      }
    } catch {
      message.error('操作失败，请稍后重试');
    }
  };

  /** 获取分类中文名 */
  const getCategoryLabel = (category: string) => {
    const found = categories.find((c) => c.name === category);
    return found?.name || category;
  };

  /** 渲染预览图区域 */
  const renderPreview = () => {
    if (!template) return null;

    const images: string[] = [];
    if (template.thumbnailUrl) {
      images.push(template.thumbnailUrl);
    }

    if (images.length === 0) {
      return (
        <div
          style={{
            height: 480,
            background: '#fafafa',
            borderRadius: 8,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px dashed #d9d9d9',
          }}
        >
          <div style={{ textAlign: 'center', color: '#bbb' }}>
            <EyeOutlined style={{ fontSize: 48, marginBottom: 12 }} />
            <div>预览图暂未提供</div>
          </div>
        </div>
      );
    }

    if (images.length === 1) {
      return (
        <div
          style={{
            height: 480,
            background: '#fafafa',
            borderRadius: 8,
            overflow: 'hidden',
            border: '1px solid #f0f0f0',
          }}
        >
          <img
            src={images[0]}
            alt={template.name}
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        </div>
      );
    }

    return (
      <Carousel
        autoplay
        dots
        style={{ borderRadius: 8, overflow: 'hidden' }}
      >
        {images.map((url, index) => (
          <div key={index}>
            <div
              style={{
                height: 480,
                background: '#fafafa',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <img
                src={url}
                alt={`${template.name} 预览 ${index + 1}`}
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            </div>
          </div>
        ))}
      </Carousel>
    );
  };

  /** 渲染版本历史 */
  const renderVersionHistory = () => {
    if (versionsLoading) {
      return <Spin size="small" />;
    }

    if (versions.length === 0) {
      return <Text type="secondary">暂无版本记录</Text>;
    }

    return (
      <List
        size="small"
        dataSource={versions}
        renderItem={(item) => (
          <List.Item
            extra={
              <Tag color={VERSION_STATUS_MAP[item.status]?.color || 'default'}>
                {VERSION_STATUS_MAP[item.status]?.text || '未知'}
              </Tag>
            }
          >
            <List.Item.Meta
              avatar={<ClockCircleOutlined style={{ color: '#999', marginTop: 4 }} />}
              title={
                <Space>
                  <Text strong>v{item.version}</Text>
                  {item.createdAt && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {new Date(item.createdAt).toLocaleDateString('zh-CN')}
                    </Text>
                  )}
                </Space>
              }
              description={item.changelog || <Text type="secondary">无变更说明</Text>}
            />
          </List.Item>
        )}
      />
    );
  };

  /** 渲染相关模板 */
  const renderRelatedTemplates = () => {
    if (relatedLoading) {
      return <Spin size="small" />;
    }

    if (relatedTemplates.length === 0) {
      return <Empty description="暂无相关模板" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
    }

    return (
      <List
        grid={{ gutter: 16, column: 3 }}
        dataSource={relatedTemplates}
        renderItem={(item) => (
          <List.Item>
            <Card
              hoverable
              size="small"
              onClick={() => history.push(`/platform/lowcode/marketplace/${item.id}`)}
              style={{ cursor: 'pointer' }}
            >
              <div
                style={{
                  height: 120,
                  background: '#fafafa',
                  borderRadius: 4,
                  marginBottom: 8,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  overflow: 'hidden',
                }}
              >
                {item.thumbnailUrl ? (
                  <img
                    src={item.thumbnailUrl}
                    alt={item.name}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                ) : (
                  <EyeOutlined style={{ fontSize: 24, color: '#d9d9d9' }} />
                )}
              </div>
              <Text ellipsis style={{ fontWeight: 500 }}>
                {item.name}
              </Text>
              <div style={{ marginTop: 4 }}>
                <Space size={12}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    <ForkOutlined /> {item.forkCount}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    <LikeOutlined /> {item.likeCount}
                  </Text>
                </Space>
              </div>
            </Card>
          </List.Item>
        )}
      />
    );
  };

  /** 加载中状态 */
  if (loading) {
    return (
      <PageContainer header={{ title: '模板详情' }}>
        <div style={{ display: 'flex', justifyContent: 'center', padding: 120 }}>
          <Spin size="large" />
        </div>
      </PageContainer>
    );
  }

  /** 模板不存在 */
  if (!template) {
    return (
      <PageContainer header={{ title: '模板详情' }}>
        <Card>
          <Empty description="模板不存在或已被移除" />
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      header={{
        title: template.name,
        onBack: () => history.push('/platform/lowcode/marketplace'),
        breadcrumb: {
          items: [
            { title: '模板市场', href: '/platform/lowcode/marketplace' },
            { title: template.name },
          ],
        },
        extra: (
          <Space>
            <Button
              icon={isFavorited ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
              onClick={handleToggleFavorite}
            >
              {isFavorited ? '已收藏' : '收藏'}
            </Button>
            <Button icon={<EyeOutlined />} onClick={handlePreview}>
              预览
            </Button>
            <Button
              type="primary"
              icon={<CopyOutlined />}
              onClick={handleFork}
            >
              使用此模板
            </Button>
          </Space>
        ),
      }}
    >
      <Row gutter={24}>
        {/* 左侧: 预览 + 版本历史 + 相关模板 */}
        <Col span={16}>
          {/* 预览图 */}
          <Card title="模板预览" style={{ marginBottom: 16 }}>
            {renderPreview()}
          </Card>

          {/* 版本历史 */}
          <Card
            title={
              <Space>
                <ClockCircleOutlined />
                <span>版本历史</span>
                {template.version && (
                  <Tag color="blue">当前 v{template.version}</Tag>
                )}
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            {renderVersionHistory()}
          </Card>

          {/* 相关模板 */}
          <Card
            title={
              <Space>
                <AppstoreOutlined />
                <span>相关模板</span>
              </Space>
            }
          >
            {renderRelatedTemplates()}
          </Card>
        </Col>

        {/* 右侧: 信息 + 统计 + 操作 */}
        <Col span={8}>
          {/* 模板信息 */}
          <Card title="模板信息" style={{ marginBottom: 16 }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="分类">
                <Tag color={CATEGORY_COLOR_MAP[template.category] || 'default'}>
                  {getCategoryLabel(template.category)}
                </Tag>
              </Descriptions.Item>
              {template.isOfficial && (
                <Descriptions.Item label="来源">
                  <Tag color="gold">官方模板</Tag>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="版本">
                <Text code>v{template.version}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="作者">
                <Space>
                  <UserOutlined />
                  {template.authorName || '未知'}
                </Space>
              </Descriptions.Item>
              {template.createdAt && (
                <Descriptions.Item label="创建时间">
                  {new Date(template.createdAt).toLocaleDateString('zh-CN')}
                </Descriptions.Item>
              )}
              {template.updatedAt && (
                <Descriptions.Item label="更新时间">
                  {new Date(template.updatedAt).toLocaleDateString('zh-CN')}
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>

          {/* 标签 */}
          {template.tags && template.tags.length > 0 && (
            <Card title="标签" style={{ marginBottom: 16 }}>
              <Space wrap>
                {template.tags.map((tag) => (
                  <Tag key={tag} icon={<TagsOutlined />}>
                    {tag}
                  </Tag>
                ))}
              </Space>
            </Card>
          )}

          {/* 统计数据 */}
          <Card title="数据统计" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="Fork"
                  value={template.forkCount}
                  prefix={<ForkOutlined />}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="收藏"
                  value={template.likeCount}
                  prefix={<LikeOutlined />}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="下载"
                  value={template.downloadCount}
                  prefix={<DownloadOutlined />}
                />
              </Col>
            </Row>
          </Card>

          {/* 模板描述 */}
          <Card title="模板描述" style={{ marginBottom: 16 }}>
            <Paragraph
              style={{ color: '#666', lineHeight: 1.8, margin: 0 }}
              ellipsis={{ rows: 4, expandable: true, symbol: '展开' }}
            >
              {template.description || '暂无描述'}
            </Paragraph>
          </Card>

          <Divider />

          {/* 操作按钮 */}
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button
              type="primary"
              size="large"
              block
              icon={<CopyOutlined />}
              onClick={handleFork}
            >
              使用此模板
            </Button>
            <Button
              size="large"
              block
              icon={<EyeOutlined />}
              onClick={handlePreview}
            >
              预览效果
            </Button>
          </Space>
        </Col>
      </Row>

      <ForkDialog
        open={forkDialogOpen}
        template={template}
        onClose={() => setForkDialogOpen(false)}
      />
    </PageContainer>
  );
};

export default TemplateDetail;
