/** 模板详情页 */

import React, { useEffect, useState } from 'react';
import { history, useParams } from '@umijs/max';
import { PageContainer } from '@ant-design/pro-components';
import {
  Card,
  Row,
  Col,
  Tag,
  Space,
  Rate,
  Button,
  Descriptions,
  Spin,
  Divider,
  message,
} from 'antd';
import {
  ForkOutlined,
  EyeOutlined,
  ArrowLeftOutlined,
  CopyOutlined,
  StarOutlined,
} from '@ant-design/icons';

/** 模板详情数据类型 */
interface TemplateDetail {
  id: string;
  name: string;
  description: string;
  category: string;
  forkCount: number;
  rating: number;
  thumbnail: string;
  author: string;
  createdAt: string;
  updatedAt: string;
  version: string;
  schemaData?: Record<string, unknown>;
}

/** 模拟详情数据 */
const MOCK_DETAIL: Record<string, TemplateDetail> = {
  '1': {
    id: '1',
    name: '通用预约挂号',
    description:
      '支持多科室、多医生的预约挂号模板，包含科室选择、医生排班、时间选择、确认预约等完整流程。适用于各类医院和诊所的在线预约场景。',
    category: 'appointment',
    forkCount: 128,
    rating: 4.8,
    thumbnail: '',
    author: '系统管理员',
    createdAt: '2025-12-01',
    updatedAt: '2025-12-20',
    version: '1.2.0',
  },
  '2': {
    id: '2',
    name: '临时挂号入口',
    description:
      '简洁的临时挂号页面，支持身份证快速录入、科室选择和排队信息展示。',
    category: 'registration',
    forkCount: 86,
    rating: 4.5,
    thumbnail: '',
    author: '系统管理员',
    createdAt: '2025-11-15',
    updatedAt: '2025-11-20',
    version: '1.0.0',
  },
};

/** 分类标签颜色 */
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

/** 分类中文名 */
const categoryLabelMap: Record<string, string> = {
  appointment: '预约挂号',
  registration: '临时挂号',
  inquiry: '问诊',
  report: '报告查询',
  notice: '公告通知',
  form: '表单收集',
  landing: '落地页',
  other: '其他',
};

/** 模板详情页 */
const TemplateDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<TemplateDetail | null>(null);

  useEffect(() => {
    // 模拟 API 请求
    setLoading(true);
    const timer = setTimeout(() => {
      const data = MOCK_DETAIL[id || ''];
      setDetail(data || null);
      setLoading(false);
    }, 300);
    return () => clearTimeout(timer);
  }, [id]);

  const handleFork = () => {
    message.success('已复制模板到我的页面，正在跳转编辑器...');
    setTimeout(() => {
      history.push('/platform/lowcode/editor/new');
    }, 1000);
  };

  if (loading) {
    return (
      <PageContainer header={{ title: '模板详情' }}>
        <div style={{ display: 'flex', justifyContent: 'center', padding: 120 }}>
          <Spin size="large" />
        </div>
      </PageContainer>
    );
  }

  if (!detail) {
    return (
      <PageContainer header={{ title: '模板详情' }}>
        <Card>
          <div style={{ textAlign: 'center', padding: 80, color: '#999' }}>
            模板不存在或已被移除
          </div>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      header={{
        title: detail.name,
        onBack: () => history.push('/platform/lowcode/marketplace'),
        extra: (
          <Space>
            <Button icon={<StarOutlined />}>收藏</Button>
            <Button type="primary" icon={<CopyOutlined />} onClick={handleFork}>
              使用模板
            </Button>
          </Space>
        ),
      }}
    >
      <Row gutter={24}>
        {/* 左侧预览 */}
        <Col span={16}>
          <Card title="模板预览" style={{ marginBottom: 16 }}>
            <div
              style={{
                height: 400,
                background: '#fafafa',
                borderRadius: 8,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px dashed #d9d9d9',
              }}
            >
              {detail.thumbnail ? (
                <img
                  src={detail.thumbnail}
                  alt={detail.name}
                  style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                />
              ) : (
                <div style={{ textAlign: 'center', color: '#bbb' }}>
                  <EyeOutlined style={{ fontSize: 48, marginBottom: 8 }} />
                  <div>预览图暂未提供</div>
                </div>
              )}
            </div>
          </Card>
        </Col>

        {/* 右侧信息 */}
        <Col span={8}>
          <Card title="模板信息" style={{ marginBottom: 16 }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="分类">
                <Tag color={categoryColorMap[detail.category] || 'default'}>
                  {categoryLabelMap[detail.category] || detail.category}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="评分">
                <Space>
                  <Rate disabled allowHalf defaultValue={detail.rating} style={{ fontSize: 14 }} />
                  <span style={{ color: '#999' }}>{detail.rating}</span>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Fork 次数">
                <Space>
                  <ForkOutlined />
                  {detail.forkCount}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="作者">{detail.author}</Descriptions.Item>
              <Descriptions.Item label="版本">{detail.version}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{detail.createdAt}</Descriptions.Item>
              <Descriptions.Item label="更新时间">{detail.updatedAt}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="模板描述">
            <p style={{ color: '#666', lineHeight: 1.8, margin: 0 }}>{detail.description}</p>
          </Card>

          <Divider />

          <Space direction="vertical" style={{ width: '100%' }}>
            <Button
              type="primary"
              block
              icon={<CopyOutlined />}
              onClick={handleFork}
            >
              使用此模板
            </Button>
            <Button
              block
              icon={<EyeOutlined />}
              onClick={() => {
                window.open(`/platform/lowcode/preview/new`, '_blank');
              }}
            >
              预览效果
            </Button>
          </Space>
        </Col>
      </Row>
    </PageContainer>
  );
};

export default TemplateDetailPage;
