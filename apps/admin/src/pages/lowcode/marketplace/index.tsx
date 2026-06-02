/** 模板市场 */

import React, { useState, useCallback } from 'react';
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
  Rate,
  Spin,
  Empty,
  Tooltip,
} from 'antd';
import {
  SearchOutlined,
  StarOutlined,
  ForkOutlined,
  EyeOutlined,
} from '@ant-design/icons';

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
  { value: 'rating', label: '评分最高' },
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

/** 模板数据类型 */
interface TemplateItem {
  id: string;
  name: string;
  description: string;
  category: string;
  forkCount: number;
  rating: number;
  thumbnail: string;
  author: string;
  createdAt: string;
}

/** 模拟数据 -- 后续替换为 API 调用 */
const MOCK_TEMPLATES: TemplateItem[] = [
  {
    id: '1',
    name: '通用预约挂号',
    description: '支持多科室、多医生的预约挂号模板，包含科室选择、医生排班、时间选择等完整流程。',
    category: 'appointment',
    forkCount: 128,
    rating: 4.8,
    thumbnail: '',
    author: '系统管理员',
    createdAt: '2025-12-01',
  },
  {
    id: '2',
    name: '临时挂号入口',
    description: '简洁的临时挂号页面，支持身份证快速录入、科室选择和排队信息展示。',
    category: 'registration',
    forkCount: 86,
    rating: 4.5,
    thumbnail: '',
    author: '系统管理员',
    createdAt: '2025-11-15',
  },
  {
    id: '3',
    name: '在线问诊',
    description: '图文问诊页面模板，支持症状描述、图片上传和医生匹配。',
    category: 'inquiry',
    forkCount: 64,
    rating: 4.3,
    thumbnail: '',
    author: '系统管理员',
    createdAt: '2025-10-20',
  },
  {
    id: '4',
    name: '检查报告查询',
    description: '患者自助查询检查报告的页面模板，支持按日期筛选和报告详情展示。',
    category: 'report',
    forkCount: 52,
    rating: 4.6,
    thumbnail: '',
    author: '系统管理员',
    createdAt: '2025-09-10',
  },
  {
    id: '5',
    name: '医院公告',
    description: '医院公告通知模板，支持富文本内容、置顶和分类标签。',
    category: 'notice',
    forkCount: 37,
    rating: 4.1,
    thumbnail: '',
    author: '系统管理员',
    createdAt: '2025-08-05',
  },
  {
    id: '6',
    name: '满意度调查',
    description: '患者满意度调查表单模板，支持评分、文字评价和匿名提交。',
    category: 'form',
    forkCount: 45,
    rating: 4.4,
    thumbnail: '',
    author: '系统管理员',
    createdAt: '2025-07-18',
  },
];

/** 获取分类标签颜色 */
const getCategoryColor = (category: string) => categoryColorMap[category] || 'default';

/** 获取分类中文名 */
const getCategoryLabel = (category: string) =>
  CATEGORIES.find((c) => c.key === category)?.label || category;

/** 模板卡片 */
const TemplateCard: React.FC<{ item: TemplateItem; onClick: (id: string) => void }> = ({
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
        {item.thumbnail ? (
          <img
            alt={item.name}
            src={item.thumbnail}
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
              {item.description}
            </span>
          </Tooltip>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Rate disabled allowHalf defaultValue={item.rating} style={{ fontSize: 12 }} />
            <span style={{ fontSize: 12, color: '#999' }}>{item.rating}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space size={12}>
              <span style={{ fontSize: 12, color: '#999' }}>
                <ForkOutlined /> {item.forkCount}
              </span>
              <span style={{ fontSize: 12, color: '#999' }}>{item.author}</span>
            </Space>
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
  const [sort, setSort] = useState('popular');
  const [page, setPage] = useState(1);
  const [loading] = useState(false);
  const pageSize = 12;

  /** 根据条件筛选模板 */
  const filteredTemplates = MOCK_TEMPLATES.filter((t) => {
    if (activeCategory !== 'all' && t.category !== activeCategory) return false;
    if (keyword && !t.name.includes(keyword) && !t.description.includes(keyword)) return false;
    return true;
  });

  /** 排序 */
  const sortedTemplates = [...filteredTemplates].sort((a, b) => {
    switch (sort) {
      case 'newest':
        return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
      case 'forks':
        return b.forkCount - a.forkCount;
      case 'rating':
        return b.rating - a.rating;
      case 'popular':
      default:
        return b.forkCount * 0.6 + b.rating * 10 * 0.4 - (a.forkCount * 0.6 + a.rating * 10 * 0.4);
    }
  });

  /** 分页数据 */
  const pagedTemplates = sortedTemplates.slice((page - 1) * pageSize, page * pageSize);

  const handleCardClick = useCallback((id: string) => {
    history.push(`/platform/lowcode/marketplace/detail/${id}`);
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
                  onClick={() => {
                    setActiveCategory(cat.key);
                    setPage(1);
                  }}
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
                  onChange={(e) => {
                    setKeyword(e.target.value);
                    setPage(1);
                  }}
                />
              </Col>
              <Col>
                <Select
                  value={sort}
                  onChange={(val) => {
                    setSort(val);
                    setPage(1);
                  }}
                  options={SORT_OPTIONS}
                  style={{ width: 140 }}
                />
              </Col>
            </Row>
          </Card>

          {/* 模板卡片网格 */}
          <Spin spinning={loading}>
            {pagedTemplates.length > 0 ? (
              <>
                <Row gutter={[16, 16]}>
                  {pagedTemplates.map((item) => (
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
                    total={sortedTemplates.length}
                    showSizeChanger={false}
                    showTotal={(total) => `共 ${total} 个模板`}
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
