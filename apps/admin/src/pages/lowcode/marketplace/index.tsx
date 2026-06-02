/** 模板市场 */

import React, { useState, useCallback, useEffect } from 'react';
import { history } from '@umijs/max';
import { PageContainer } from '@ant-design/pro-components';
import {
  Card,
  Row,
  Col,
  Input,
  Select,
  Pagination,
  Tag,
  Space,
  Spin,
  Empty,
  Tooltip,
  message,
} from 'antd';
import {
  SearchOutlined,
  ForkOutlined,
  EyeOutlined,
  LikeOutlined,
} from '@ant-design/icons';
import { lowcodeApi } from '@hospital/api';
import type { LowCodeTemplate } from '@hospital/api';

/** 模板分类 */
const CATEGORIES = [
  { key: 'all', label: '全部' },
  { key: 'appointment', label: '预约挂号' },
  { key: 'registration', label: '临时挂号' },
  { key: 'inquiry', label: '问诊' },
  { key: 'report', label: '报告查询' },
  { key: 'notice', label: '公告通知' },
  { key: 'form', label: '表单收集' },
  { key: 'landing', label: '落地页' },
  { key: 'other', label: '其他' },
];

/** 排序选项 */
const SORT_OPTIONS = [
  { value: 'popular', label: '最热门' },
  { value: 'newest', label: '最新' },
  { value: 'forks', label: '最多 Fork' },
];

/** 模板分类标签颜色 */
const categoryColorMap: Record<string, string> = {
  appointment: 'blue',
  registration: 'cyan',
  inquiry: 'green',
  report: 'purple',
  notice: 'orange',
  form: 'magenta',
  landing: 'geekblue',
  other: 'default',
};

/** 获取分类标签颜色 */
const getCategoryColor = (category: string) => categoryColorMap[category] || 'default';

/** 获取分类中文名 */
const getCategoryLabel = (category: string) =>
  CATEGORIES.find((c) => c.key === category)?.label || category;

/** 模板卡片 */
const TemplateCard: React.FC<{ item: LowCodeTemplate; onClick: (id: string) => void }> = ({
  item,
  onClick,
}) => (
  <Card
    hoverable
    style={{ height: '100%' }}
    onClick={() => onClick(item.id)}
    cover={
      <div
        style={{
          height: 180,
          background: '#f5f5f5',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
        }}
      >
        {item.thumbnailUrl ? (
          <img
            alt={item.name}
            src={item.thumbnailUrl}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <EyeOutlined style={{ fontSize: 36, color: '#bbb' }} />
        )}
      </div>
    }
  >
    <Card.Meta
      title={
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          <Tooltip title={item.name}>
            <span
              style={{
                display: 'block',
                fontWeight: 600,
                fontSize: 15,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {item.name}
            </span>
          </Tooltip>
          <Tag color={getCategoryColor(item.category)} style={{ marginRight: 0 }}>
            {getCategoryLabel(item.category)}
          </Tag>
        </Space>
      }
      description={
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <Tooltip title={item.description}>
            <span
              style={{
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
                color: '#666',
                fontSize: 13,
                lineHeight: '20px',
                minHeight: 40,
              }}
            >
              {item.description || '暂无描述'}
            </span>
          </Tooltip>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space size={12}>
              <span style={{ fontSize: 12, color: '#999' }}>
                <ForkOutlined /> {item.forkCount}
              </span>
              <span style={{ fontSize: 12, color: '#999' }}>
                <LikeOutlined /> {item.likeCount}
              </span>
            </Space>
            <span style={{ fontSize: 12, color: '#999' }}>{item.authorName || '未知'}</span>
          </div>
        </Space>
      }
    />
  </Card>
);

/** 模板市场页面 */
const Marketplace: React.FC = () => {
  const [activeCategory, setActiveCategory] = useState('all');
  const [keyword, setKeyword] = useState('');
  const [sort, setSort] = useState<string>('popular');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState<LowCodeTemplate[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState(false);
  const pageSize = 12;

  /** 加载模板列表 */
  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const params: Record<string, any> = {
        page,
        pageSize,
      };
      if (activeCategory !== 'all') {
        params.category = activeCategory;
      }
      if (keyword) {
        params.keyword = keyword;
      }
      if (sort) {
        params.sortBy = sort;
      }
      const result = await lowcodeApi.getTemplates(params);
      setTemplates(result.data || []);
      setTotal(result.total || 0);
    } catch {
      setError(true);
      message.error('加载模板列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, activeCategory, keyword, sort]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  /** 分类切换 */
  const handleCategoryChange = (key: string) => {
    setActiveCategory(key);
    setPage(1);
  };

  /** 搜索输入 */
  const handleKeywordChange = (value: string) => {
    setKeyword(value);
    setPage(1);
  };

  /** 排序切换 */
  const handleSortChange = (value: string) => {
    setSort(value);
    setPage(1);
  };

  /** 卡片点击 */
  const handleCardClick = useCallback((id: string) => {
    history.push(`/platform/lowcode/marketplace/${id}`);
  }, []);

  return (
    <PageContainer
      header={{
        title: '模板市场',
        subTitle: '浏览和使用社区模板，快速搭建低代码页面',
      }}
    >
      <Row gutter={24}>
        {/* 左侧分类栏 */}
        <Col span={5}>
          <Card size="small" style={{ position: 'sticky', top: 24 }}>
            <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14 }}>模板分类</div>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              {CATEGORIES.map((cat) => (
                <div
                  key={cat.key}
                  onClick={() => handleCategoryChange(cat.key)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 6,
                    cursor: 'pointer',
                    background: activeCategory === cat.key ? '#e6f4ff' : 'transparent',
                    color: activeCategory === cat.key ? '#1677ff' : '#333',
                    fontWeight: activeCategory === cat.key ? 500 : 400,
                    transition: 'all 0.2s',
                  }}
                >
                  {cat.label}
                </div>
              ))}
            </Space>
          </Card>
        </Col>

        {/* 右侧内容区 */}
        <Col span={19}>
          {/* 搜索和排序 */}
          <Card size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16} align="middle">
              <Col flex="auto">
                <Input
                  placeholder="搜索模板名称或描述"
                  prefix={<SearchOutlined style={{ color: '#bbb' }} />}
                  allowClear
                  value={keyword}
                  onChange={(e) => handleKeywordChange(e.target.value)}
                />
              </Col>
              <Col>
                <Select
                  value={sort}
                  onChange={handleSortChange}
                  options={SORT_OPTIONS}
                  style={{ width: 140 }}
                />
              </Col>
            </Row>
          </Card>

          {/* 模板卡片网格 */}
          <Spin spinning={loading}>
            {error ? (
              <Empty description="加载失败，请稍后重试" style={{ marginTop: 80 }} />
            ) : templates.length > 0 ? (
              <>
                <Row gutter={[16, 16]}>
                  {templates.map((item) => (
                    <Col key={item.id} xs={24} sm={12} md={8} lg={6}>
                      <TemplateCard item={item} onClick={handleCardClick} />
                    </Col>
                  ))}
                </Row>

                {/* 分页 */}
                <div style={{ display: 'flex', justifyContent: 'center', marginTop: 24 }}>
                  <Pagination
                    current={page}
                    pageSize={pageSize}
                    total={total}
                    showSizeChanger={false}
                    showTotal={(t) => `共 ${t} 个模板`}
                    onChange={(p) => setPage(p)}
                  />
                </div>
              </>
            ) : (
              <Empty description="暂无匹配的模板" style={{ marginTop: 80 }} />
            )}
          </Spin>
        </Col>
      </Row>
    </PageContainer>
  );
};

export default Marketplace;
