import { PageContainer, ProDescriptions, ModalForm, ProFormText, ProFormSelect, ProFormDatePicker, ProFormTextArea, ProForm } from '@ant-design/pro-components';
import {
  Card,
  Tag,
  Button,
  Space,
  Spin,
  Avatar,
  Typography,
  Statistic,
  Row,
  Col,
  Table,
  Popconfirm,
  Modal,
  Form,
  InputNumber,
  Input,
  App,
} from 'antd';
import { UserOutlined, ManOutlined, WomanOutlined, PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { history, useParams, useAccess, useSearchParams } from '@umijs/max';
import { userManageApi } from '@hospital/api';
import { GENDER_MAP, GENDER_OPTIONS } from '@/constants';
import type { UserDetail, UserCard, CardCreateData, CardUpdateData, UserUpdateData } from '@hospital/api';

const { Title, Text } = Typography;

const SOURCE_MAP: Record<number, string> = {
  1: '用户添加',
  2: '管理员添加',
};

const RELATIONSHIP_OPTIONS = [
  { label: '本人', value: '本人' },
  { label: '父亲', value: '父亲' },
  { label: '母亲', value: '母亲' },
  { label: '配偶', value: '配偶' },
  { label: '子女', value: '子女' },
  { label: '其他', value: '其他' },
];

const ID_CARD_TYPE_OPTIONS = [
  { label: '居民身份证', value: 1 },
  { label: '户口簿', value: 2 },
  { label: '护照', value: 3 },
];

const UserDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { message } = App.useApp();
  const access = useAccess();
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<UserDetail | null>(null);
  const [pointModalOpen, setPointModalOpen] = useState(false);
  const [pointLoading, setPointLoading] = useState(false);
  const [pointForm] = Form.useForm();
  
  // 编辑用户状态
  const [editUserModalVisible, setEditUserModalVisible] = useState(false);
  
  // 就诊卡管理状态
  const [addCardModalVisible, setAddCardModalVisible] = useState(false);
  const [editCardModalVisible, setEditCardModalVisible] = useState(false);
  const [currentCard, setCurrentCard] = useState<UserCard | null>(null);

  useEffect(() => {
    if (id) {
      loadUser();
    }
  }, [id]);

  const loadUser = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await userManageApi.getDetail(id);
      setUser(data);
    } catch (error) {
      console.error('加载失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStatus = async (status: number) => {
    if (!id) return;
    try {
      await userManageApi.updateStatus(id, status);
      message.success(status === 0 ? '已禁用' : '已启用');
      loadUser();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleAdjustPoints = async (values: { amount: number; remark: string }) => {
    if (!id) return;
    setPointLoading(true);
    try {
      await userManageApi.adjustPoints(id, values.amount, values.remark);
      message.success('积分调整成功');
      setPointModalOpen(false);
      pointForm.resetFields();
      loadUser();
    } catch (error: any) {
      message.error(error.message || '积分调整失败');
    } finally {
      setPointLoading(false);
    }
  };

  // 编辑用户信息
  const handleEditUser = async (values: UserUpdateData) => {
    if (!id) return false;
    try {
      await userManageApi.updateUser(id, values);
      message.success('保存成功');
      setEditUserModalVisible(false);
      loadUser();
      return true;
    } catch (error: any) {
      message.error(error.message || '保存失败');
      return false;
    }
  };

  // 添加就诊卡
  const handleAddCard = async (values: CardCreateData) => {
    if (!id) return false;
    try {
      await userManageApi.createCard(id, values);
      message.success('添加成功');
      setAddCardModalVisible(false);
      loadUser();
      return true;
    } catch (error: any) {
      message.error(error.message || '添加失败');
      return false;
    }
  };

  // 编辑就诊卡
  const handleEditCard = async (values: CardUpdateData) => {
    if (!id || !currentCard) return false;
    try {
      await userManageApi.updateCard(id, currentCard.id, values);
      message.success('保存成功');
      setEditCardModalVisible(false);
      setCurrentCard(null);
      loadUser();
      return true;
    } catch (error: any) {
      message.error(error.message || '保存失败');
      return false;
    }
  };

  // 删除就诊卡
  const handleDeleteCard = async (cardId: string) => {
    if (!id) return;
    try {
      await userManageApi.deleteCard(id, cardId);
      message.success('删除成功');
      loadUser();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  // 删除用户
  const handleDeleteUser = async () => {
    if (!id) return;
    try {
      await userManageApi.deleteUser(id);
      message.success('删除成功');
      history.push('/medical-services/patient/list');
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  // 就诊卡列表列定义
  const cardColumns = [
    { title: '卡号', dataIndex: 'cardNo', key: 'cardNo', width: 150, ellipsis: true },
    { title: '姓名', dataIndex: 'name', key: 'name', width: 80 },
    {
      title: '性别',
      dataIndex: 'gender',
      key: 'gender',
      width: 60,
      render: (val: number) => GENDER_MAP[val] || '-',
    },
    { title: '年龄', dataIndex: 'age', key: 'age', width: 60, render: (val: number) => val ?? '-' },
    { title: '手机号', dataIndex: 'phone', key: 'phone', width: 120 },
    { title: '关系', dataIndex: 'relationship', key: 'relationship', width: 80 },
    {
      title: '默认',
      dataIndex: 'isDefault',
      key: 'isDefault',
      width: 60,
      render: (val: boolean) => (val ? <Tag color="blue">默认</Tag> : '-'),
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      width: 100,
      render: (val: number) => SOURCE_MAP[val || 1] || '-',
    },
    { title: '预约次数', dataIndex: 'appointmentCount', key: 'appointmentCount', width: 90 },
    { title: '爽约次数', dataIndex: 'noShowCount', key: 'noShowCount', width: 90 },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: any, record: UserCard) => (
        <Space>
          <a onClick={() => history.push(`/medical-services/patient/card/${record.id}?fromUserId=${id}`)}>查看</a>
          {access.hasPermission('patient:update') && (
            <a onClick={() => { setCurrentCard(record); setEditCardModalVisible(true); }}>
              <EditOutlined /> 编辑
            </a>
          )}
          {access.hasPermission('patient:delete') && (
            <Popconfirm
              title="确定删除该就诊卡吗？"
              description="删除后不可恢复"
              onConfirm={() => handleDeleteCard(record.id)}
            >
              <a style={{ color: '#ff4d4f' }}><DeleteOutlined /> 删除</a>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  // 就诊卡表单内容
  const CardFormContent = () => (
    <>
      <ProForm.Group>
        <ProFormText
          name="name"
          label="姓名"
          width="sm"
          rules={[{ required: true, message: '请输入姓名' }]}
          placeholder="请输入姓名"
        />
        <ProFormText
          name="phone"
          label="手机号"
          width="sm"
          rules={[
            { required: true, message: '请输入手机号' },
            { pattern: /^1\d{10}$/, message: '手机号格式不正确' },
          ]}
          placeholder="请输入手机号"
        />
      </ProForm.Group>
      <ProForm.Group>
        <ProFormSelect
          name="gender"
          label="性别"
          width="sm"
          options={GENDER_OPTIONS}
          placeholder="请选择性别"
        />
        <ProFormDatePicker
          name="birthday"
          label="出生日期"
          width="sm"
          placeholder="请选择出生日期"
        />
      </ProForm.Group>
      <ProForm.Group>
        <ProFormText
          name="idCard"
          label="身份证号"
          width="sm"
          placeholder="请输入身份证号"
        />
        <ProFormSelect
          name="idCardType"
          label="证件类型"
          width="sm"
          options={ID_CARD_TYPE_OPTIONS}
          initialValue={1}
        />
      </ProForm.Group>
      <ProForm.Group>
        <ProFormSelect
          name="relationship"
          label="与本人关系"
          width="sm"
          options={RELATIONSHIP_OPTIONS}
        />
        <ProFormText
          name="ethnicity"
          label="民族"
          width="sm"
          initialValue="汉族"
          placeholder="请输入民族"
        />
      </ProForm.Group>
      <ProForm.Group>
        <ProFormText name="province" label="省" width="sm" placeholder="请输入省份" />
        <ProFormText name="city" label="市" width="sm" placeholder="请输入城市" />
      </ProForm.Group>
      <ProForm.Group>
        <ProFormText name="district" label="区" width="sm" placeholder="请输入区县" />
        <ProFormText name="street" label="街道/社区" width="sm" placeholder="请输入街道/社区" />
      </ProForm.Group>
      <ProFormTextArea name="address" label="详细地址" placeholder="请输入详细地址" />
    </>
  );

  return (
    <PageContainer
      title="用户详情"
      extra={<Button onClick={() => history.push('/medical-services/patient/list')}>返回列表</Button>}
    >
      <Spin spinning={loading}>
        {/* 头部信息卡片 */}
        <Card style={{ marginBottom: 16 }}>
          <Row gutter={24} align="middle">
            <Col>
              <Space size="large">
                <Avatar size={80} src={user?.avatar} icon={<UserOutlined />} />
                <div>
                  <Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {user?.nickname || '微信用户'}
                    </Title>
                    {user?.gender === 1 && <ManOutlined style={{ color: '#1890ff' }} />}
                    {user?.gender === 2 && <WomanOutlined style={{ color: '#eb2f96' }} />}
                    <Text type="secondary">{user?.phone}</Text>
                    <Tag color={user?.status === 1 ? 'green' : 'red'}>
                      {user?.status === 1 ? '正常' : '禁用'}
                    </Tag>
                  </Space>
                  <div style={{ marginTop: 8 }}>
                    <Space size="large">
                      <Statistic title="就诊卡" value={user?.cardCount || 0} suffix="张" />
                      <Statistic title="预约次数" value={user?.appointmentCount || 0} />
                      <Statistic title="爽约次数" value={user?.noShowCount || 0} />
                      <Statistic title="积分" value={user?.points || 0} />
                    </Space>
                  </div>
                </div>
              </Space>
            </Col>
            <Col flex="auto" style={{ textAlign: 'right' }}>
              <Space>
                {access.hasPermission('patient:update') && (
                  <>
                    <Button icon={<EditOutlined />} onClick={() => setEditUserModalVisible(true)}>
                      编辑信息
                    </Button>
                    <Button onClick={() => setPointModalOpen(true)}>调整积分</Button>
                    {user?.status === 1 ? (
                      <Popconfirm
                        title="确定禁用该用户吗？禁用后用户将无法预约"
                        onConfirm={() => handleUpdateStatus(0)}
                      >
                        <Button danger>禁用用户</Button>
                      </Popconfirm>
                    ) : (
                      <Popconfirm
                        title="确定启用该用户吗？"
                        onConfirm={() => handleUpdateStatus(1)}
                      >
                        <Button type="primary">启用用户</Button>
                      </Popconfirm>
                    )}
                  </>
                )}
                {access.hasPermission('patient:delete') && (
                  <Popconfirm
                    title="确定删除该用户吗？"
                    description="删除后用户的所有就诊卡将被一并删除，此操作不可恢复"
                    onConfirm={handleDeleteUser}
                  >
                    <Button danger icon={<DeleteOutlined />}>删除用户</Button>
                  </Popconfirm>
                )}
              </Space>
            </Col>
          </Row>
        </Card>

        {/* 基本信息 */}
        <Card title="基本信息" style={{ marginBottom: 16 }}>
          <ProDescriptions column={3}>
            <ProDescriptions.Item label="用户ID">{user?.id}</ProDescriptions.Item>
            <ProDescriptions.Item label="手机号">{user?.phone}</ProDescriptions.Item>
            <ProDescriptions.Item label="微信昵称">{user?.nickname || '微信用户'}</ProDescriptions.Item>
            <ProDescriptions.Item label="性别">
              {user?.gender !== undefined && user?.gender !== null ? GENDER_MAP[user.gender] || '未知' : '未知'}
            </ProDescriptions.Item>
            <ProDescriptions.Item label="OpenID">
              <Text copyable={{ text: user?.openid }} ellipsis style={{ maxWidth: 200 }}>
                {user?.openid ? `${user.openid.slice(0, 8)}...` : '-'}
              </Text>
            </ProDescriptions.Item>
            <ProDescriptions.Item label="积分">{user?.points || 0}</ProDescriptions.Item>
            <ProDescriptions.Item label="状态">
              <Tag color={user?.status === 1 ? 'green' : 'red'}>
                {user?.status === 1 ? '正常' : '禁用'}
              </Tag>
            </ProDescriptions.Item>
            <ProDescriptions.Item label="注册时间">{user?.createdAt}</ProDescriptions.Item>
            <ProDescriptions.Item label="更新时间">{user?.updatedAt}</ProDescriptions.Item>
          </ProDescriptions>
        </Card>

        {/* 就诊卡列表 */}
        <Card 
          title={`就诊卡列表 (${user?.cardCount || 0}张)`}
          extra={
            access.hasPermission('patient:update') && (
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setAddCardModalVisible(true)}
              >
                添加就诊卡
              </Button>
            )
          }
        >
          <Table
            dataSource={user?.cards || []}
            columns={cardColumns}
            rowKey="id"
            pagination={false}
            scroll={{ x: 1100 }}
            size="middle"
          />
        </Card>
      </Spin>

      {/* 积分调整弹窗 */}
      <Modal
        title="调整积分"
        open={pointModalOpen}
        onCancel={() => {
          setPointModalOpen(false);
          pointForm.resetFields();
        }}
        onOk={() => pointForm.submit()}
        confirmLoading={pointLoading}
        destroyOnHidden
      >
        <Form form={pointForm} layout="vertical" onFinish={handleAdjustPoints}>
          <Form.Item
            name="amount"
            label="调整积分"
            rules={[{ required: true, message: '请输入调整积分' }]}
            extra="正数为增加，负数为减少"
          >
            <InputNumber style={{ width: '100%' }} placeholder="请输入调整积分数量" />
          </Form.Item>
          <Form.Item
            name="remark"
            label="调整原因"
            rules={[{ required: true, message: '请输入调整原因' }]}
          >
            <Input.TextArea rows={3} placeholder="请输入调整原因" maxLength={200} showCount />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑用户信息弹窗 */}
      <ModalForm
        title="编辑用户信息"
        open={editUserModalVisible}
        onOpenChange={setEditUserModalVisible}
        onFinish={handleEditUser}
        width={500}
        modalProps={{ destroyOnHidden: true }}
        initialValues={user ? {
          nickname: user.nickname,
          phone: user.phone,
          gender: user.gender,
        } : {}}
      >
        <ProFormText
          name="nickname"
          label="昵称"
          placeholder="请输入昵称"
        />
        <ProFormText
          name="phone"
          label="手机号"
          rules={[
            { pattern: /^1\d{10}$/, message: '手机号格式不正确' },
          ]}
          placeholder="请输入手机号"
        />
        <ProFormSelect
          name="gender"
          label="性别"
          options={GENDER_OPTIONS}
          placeholder="请选择性别"
        />
      </ModalForm>

      {/* 添加就诊卡弹窗 */}
      <ModalForm
        title="添加就诊卡"
        open={addCardModalVisible}
        onOpenChange={setAddCardModalVisible}
        onFinish={handleAddCard}
        width={600}
        modalProps={{ destroyOnHidden: true }}
      >
        <CardFormContent />
      </ModalForm>

      {/* 编辑就诊卡弹窗 */}
      <ModalForm
        title="编辑就诊卡"
        open={editCardModalVisible}
        onOpenChange={(open) => {
          setEditCardModalVisible(open);
          if (!open) setCurrentCard(null);
        }}
        onFinish={handleEditCard}
        width={600}
        modalProps={{ destroyOnHidden: true }}
        initialValues={currentCard ? {
          name: currentCard.name,
          phone: currentCard.phone,
          gender: currentCard.gender,
          idCard: currentCard.idCard,
          birthday: currentCard.birthday,
          relationship: currentCard.relationship,
          isDefault: currentCard.isDefault,
        } : {}}
      >
        <CardFormContent />
      </ModalForm>
    </PageContainer>
  );
};

export default UserDetailPage;
