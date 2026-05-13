import { PageContainer } from '@ant-design/pro-components';
import { Card, Tag, Button, Row, Col, message, Modal, Space, Typography, Divider } from 'antd';
import { history } from '@umijs/max';
import { useState, useEffect } from 'react';
import {
  AppstoreOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  MedicineBoxOutlined,
  HeartOutlined,
  UserOutlined,
  ExperimentOutlined,
  WomanOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { miniappPlatformApi } from '@hospital/api';
import type { AppTemplate } from '@hospital/api';

const { Text, Paragraph } = Typography;

const TEMPLATE_CATEGORY_MAP: Record<string, { text: string; color: string; icon: React.ReactNode }> = {
  general: { text: '综合医疗', color: 'blue', icon: <MedicineBoxOutlined /> },
  elderly: { text: '长辈友好', color: 'orange', icon: <HeartOutlined /> },
  specialty: { text: '专科门诊', color: 'purple', icon: <ExperimentOutlined /> },
  pediatrics: { text: '儿科', color: 'cyan', icon: <UserOutlined /> },
  womens: { text: '女性健康', color: 'pink', icon: <WomanOutlined /> },
};

const TEMPLATE_STATIC_DATA: Record<string, {
  color: string;
  features: string[];
  englishName: string;
  tabs: string;
  highlights: string[];
}> = {
  'modern-general': {
    color: '#2563EB',
    englishName: 'Modern General Hospital',
    features: ['4 Tab 导航', '在线问诊', '健康档案', '报告查询', '智能导诊'],
    tabs: '首页/预约/我的/更多',
    highlights: ['现代简约设计', '完整预约流程', '支持在线支付'],
  },
  'elderly-tcm': {
    color: '#6B5235',
    englishName: 'Elderly-Friendly TCM',
    features: ['大字体设计', '中医诊疗', '康养服务', '简单操作', '电话预约'],
    tabs: '首页/服务/我的',
    highlights: ['超大按钮字体', '简洁三步预约', '中医特色服务'],
  },
  'premium-specialty': {
    color: '#5B4730',
    englishName: 'Premium Specialty Clinic',
    features: ['VIP服务', '专科诊疗', '预约管理', '会员体系', '专属客服'],
    tabs: '首页/科室/医生/会员',
    highlights: ['高端视觉设计', '会员等级体系', '一对一专属服务'],
  },
  'family-pediatrics': {
    color: '#10B981',
    englishName: 'Family Pediatrics',
    features: ['儿童健康', '家属关联', '疫苗提醒', '成长记录', '在线咨询'],
    tabs: '首页/预约/疫苗/记录',
    highlights: ['温馨可爱风格', '家属账号关联', '儿童健康档案'],
  },
  'womens-health': {
    color: '#703030',
    englishName: 'Women\'s Health Center',
    features: ['女性健康', '妇科服务', '产后康复', '健康咨询', '预约提醒'],
    tabs: '首页/服务/预约/我的',
    highlights: ['优雅柔和配色', '全周期健康管理', '产后康复追踪'],
  },
};

interface TemplateWithStatic extends AppTemplate {
  color?: string;
  features?: string[];
}

const TemplatePage: React.FC = () => {
  const [templates, setTemplates] = useState<TemplateWithStatic[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const res = await miniappPlatformApi.getTemplates({ status: 1 });
      if (res.data && res.data.length > 0) {
        const templatesWithStatic = res.data.map(t => ({
          ...t,
          ...TEMPLATE_STATIC_DATA[t.code],
        }));
        setTemplates(templatesWithStatic);
      } else {
        setTemplates(
          Object.entries(TEMPLATE_STATIC_DATA).map(([code, data]) => ({
            id: code,
            code,
            name: {
              'modern-general': '现代通用版',
              'elderly-tcm': '长辈中医版',
              'premium-specialty': '高端专科版',
              'family-pediatrics': '亲子儿科版',
              'womens-health': '女性健康版',
            }[code],
            description: {
              'modern-general': '简洁现代的设计，适合大多数医疗机构',
              'elderly-tcm': '大字号高对比度，适合中医院和老年患者',
              'premium-specialty': '品牌感强，适合专科诊所和高端机构',
              'family-pediatrics': '活泼彩色，适合儿科和儿童医院',
              'womens-health': '柔和温暖，适合妇幼保健和女性专科',
            }[code],
            category: {
              'modern-general': 'general',
              'elderly-tcm': 'elderly',
              'premium-specialty': 'specialty',
              'family-pediatrics': 'pediatrics',
              'womens-health': 'womens',
            }[code],
            ...data,
            status: 1,
            createdAt: new Date().toISOString(),
          }))
        );
      }
    } catch (error) {
      console.log('模板加载失败，使用静态数据');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectTemplate = (template: TemplateWithStatic) => {
    Modal.confirm({
      title: '确认选择模板',
      icon: <CheckCircleOutlined style={{ color: template.color }} />,
      content: (
        <div>
          <Paragraph>您即将使用以下模板创建小程序实例：</Paragraph>
          <div style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', marginBottom: '12px' }}>
            <Text strong style={{ fontSize: '16px' }}>{template.name}</Text>
            <br />
            <Text type="secondary">{TEMPLATE_STATIC_DATA[template.code]?.englishName}</Text>
          </div>
          <Paragraph type="secondary">
            确认后将进入实例配置页面，完善信息后即可开始构建小程序。
          </Paragraph>
        </div>
      ),
      okText: '确认选择',
      cancelText: '取消',
      onOk: () => {
        history.push(`/platform/miniapp-platform/instance/create?template=${template.code}`);
      },
    });
  };

  const handleViewDetail = (template: TemplateWithStatic) => {
    const staticData = TEMPLATE_STATIC_DATA[template.code];
    Modal.info({
      title: (
        <Space>
          <span style={{ color: template.color }}>●</span>
          <span>{template.name}</span>
        </Space>
      ),
      width: 520,
      icon: null,
      content: (
        <div>
          <Divider style={{ margin: '12px 0' }} />
          <Paragraph>
            <Text strong>英文名称：</Text>
            <Text>{staticData?.englishName}</Text>
          </Paragraph>
          <Paragraph>
            <Text strong>适用场景：</Text>
            <Text>{template.description}</Text>
          </Paragraph>
          <Paragraph>
            <Text strong>页面结构：</Text>
            <Text>{staticData?.tabs}</Text>
          </Paragraph>
          <Paragraph>
            <Text strong>核心功能：</Text>
          </Paragraph>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {staticData?.features.map((feature, index) => (
              <Tag key={index} color={template.category ? TEMPLATE_CATEGORY_MAP[template.category]?.color : 'blue'}>
                {feature}
              </Tag>
            ))}
          </div>
          <Divider style={{ margin: '12px 0' }} />
          <Paragraph>
            <Text strong>设计亮点：</Text>
          </Paragraph>
          <ul style={{ paddingLeft: '20px', margin: 0 }}>
            {staticData?.highlights.map((highlight, index) => (
              <li key={index}>
                <Text type="secondary">{highlight}</Text>
              </li>
            ))}
          </ul>
        </div>
      ),
    });
  };

  return (
    <PageContainer
      title="模板选择"
      subTitle="选择合适的小程序模板，快速搭建您的医疗服务"
      loading={loading}
    >
      <Row gutter={[24, 24]}>
        {templates.map((template) => {
          const categoryInfo = TEMPLATE_CATEGORY_MAP[template.category || 'general'] || { text: '其他', color: 'default', icon: <AppstoreOutlined /> };
          const staticData = TEMPLATE_STATIC_DATA[template.code];
          return (
            <Col key={template.code} xs={24} sm={12} md={8} lg={24 / 5} xl={24 / 5}>
              <Card
                hoverable
                style={{ height: '100%', borderRadius: '8px', overflow: 'hidden' }}
                styles={{ body: { padding: '16px' } }}
                cover={
                  <div
                    style={{
                      height: '100px',
                      background: `linear-gradient(135deg, ${template.color} 0%, ${template.color}dd 100%)`,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#fff',
                      padding: '16px',
                      position: 'relative',
                    }}
                  >
                    <div style={{ fontSize: '32px', marginBottom: '8px' }}>
                      {categoryInfo.icon}
                    </div>
                    <div style={{ fontSize: '16px', fontWeight: 'bold', textAlign: 'center' }}>
                      {template.name}
                    </div>
                    <div style={{ fontSize: '12px', opacity: 0.9, marginTop: '4px' }}>
                      {staticData?.englishName}
                    </div>
                  </div>
                }
              >
                <div style={{ marginTop: '12px' }}>
                  <div style={{ marginBottom: '8px' }}>
                    <Tag color={categoryInfo.color} icon={categoryInfo.icon} style={{ marginRight: '8px' }}>
                      {categoryInfo.text}
                    </Tag>
                    <Tag color={template.color} style={{ border: `1px solid ${template.color}` }}>
                      <span style={{ color: template.color }}>●</span> 主色
                    </Tag>
                  </div>
                  <p
                    style={{
                      minHeight: '42px',
                      color: '#666',
                      fontSize: '13px',
                      lineHeight: '1.5',
                      marginBottom: '12px',
                    }}
                  >
                    {template.description}
                  </p>
                  <div style={{ marginBottom: '12px' }}>
                    <Text type="secondary" style={{ fontSize: '12px' }}>核心功能：</Text>
                    <div style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                      {template.features?.slice(0, 4).map((feature, index) => (
                        <Tag key={index} color="blue" style={{ fontSize: '12px', marginBottom: '4px' }}>
                          <ThunderboltOutlined style={{ marginRight: '4px' }} />
                          {feature}
                        </Tag>
                      ))}
                    </div>
                  </div>
                  <div style={{ marginBottom: '16px' }}>
                    <Text type="secondary" style={{ fontSize: '12px' }}>页面结构：</Text>
                    <div style={{ marginTop: '4px' }}>
                      <Tag color="default" style={{ fontSize: '12px' }}>
                        <AppstoreOutlined style={{ marginRight: '4px' }} />
                        {staticData?.tabs}
                      </Tag>
                    </div>
                  </div>
                  <Divider style={{ margin: '12px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
                    <Button
                      size="small"
                      icon={<EyeOutlined />}
                      onClick={() => handleViewDetail(template)}
                      style={{ flex: 1 }}
                    >
                      预览
                    </Button>
                    <Button
                      type="primary"
                      size="small"
                      icon={<CheckCircleOutlined />}
                      onClick={() => handleSelectTemplate(template)}
                      style={{ flex: 1, background: template.color, borderColor: template.color }}
                    >
                      选择
                    </Button>
                  </div>
                </div>
              </Card>
            </Col>
          );
        })}
      </Row>
    </PageContainer>
  );
};

export default TemplatePage;
