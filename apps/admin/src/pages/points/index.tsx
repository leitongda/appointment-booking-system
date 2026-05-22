import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormDigit, ProFormTextArea } from '@ant-design/pro-components';
import { App, Tag, Tabs, Button, Space } from 'antd';
import { useRef, useState, useCallback, useMemo } from 'react';
import { useAccess } from '@umijs/max';
import { pointApi } from '@hospital/api';
import type { PointLogItem, PointUserItem } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import { PAGINATION_CONFIG } from '@/constants/pagination';

const TYPE_MAP: Record<number, { text: string; color: string }> = {
  1: { text: '消费', color: 'default' },
  2: { text: '充值', color: 'success' },
  3: { text: '赠送', color: 'processing' },
  4: { text: '手动调整', color: 'warning' },
};

const PointsPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const logActionRef = useRef<ActionType>();
  const userActionRef = useRef<ActionType>();
  const [activeTab, setActiveTab] = useState('logs');
  const [adjustOpen, setAdjustOpen] = useState(false);
  const [adjustUserId, setAdjustUserId] = useState<string>('');
  const [adjustUserName, setAdjustUserName] = useState<string>('');

  const handleAdjust = useCallback(async (values: any) => {
    try {
      await pointApi.adjust(adjustUserId, {
        amount: values.amount,
        remark: values.remark,
      });
      message.success('调整成功');
      setAdjustOpen(false);
      logActionRef.current?.reload();
      userActionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '调整失败');
      return false;
    }
  }, [adjustUserId, message]);

  const openAdjust = useCallback((userId: string, userName: string) => {
    setAdjustUserId(userId);
    setAdjustUserName(userName);
    setAdjustOpen(true);
  }, []);

  // 积分流水列定义
  const logColumns = useMemo<ProColumns<PointLogItem>[]>(() => [
    {
      title: '关键字',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: { placeholder: '用户姓名/手机号' },
    },
    {
      title: '类型',
      dataIndex: 'logType',
      hideInTable: true,
      valueType: 'select',
      valueEnum: {
        1: { text: '消费' },
        2: { text: '充值' },
        3: { text: '赠送' },
        4: { text: '手动调整' },
      },
    },
    {
      title: '时间范围',
      dataIndex: 'dateRange',
      hideInTable: true,
      valueType: 'dateRange',
    },
    // 表格列
    {
      title: '用户',
      dataIndex: 'userName',
      width: 120,
      search: false,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <span>{record.userName || '-'}</span>
          {record.userPhone && (
            <span style={{ fontSize: 12, color: '#999' }}>{record.userPhone}</span>
          )}
        </Space>
      ),
    },
    {
      title: '变更积分',
      dataIndex: 'changeAmount',
      width: 100,
      search: false,
      render: (_, record) => {
        const val = record.changeAmount;
        const color = val > 0 ? '#52c41a' : val < 0 ? '#ff4d4f' : '#999';
        const prefix = val > 0 ? '+' : '';
        return <span style={{ color, fontWeight: 500 }}>{prefix}{val}</span>;
      },
    },
    {
      title: '余额',
      dataIndex: 'balance',
      width: 80,
      search: false,
    },
    {
      title: '类型',
      dataIndex: 'type',
      width: 90,
      search: false,
      render: (_, record) => {
        const info = TYPE_MAP[record.type] || { text: '未知', color: 'default' };
        return <Tag color={info.color}>{info.text}</Tag>;
      },
    },
    {
      title: '备注',
      dataIndex: 'remark',
      ellipsis: true,
      search: false,
      render: (val) => val || '-',
    },
    {
      title: '操作人',
      dataIndex: 'operatorName',
      width: 80,
      search: false,
      render: (val) => val || '-',
    },
    {
      title: '时间',
      dataIndex: 'createdAt',
      width: 160,
      valueType: 'dateTime',
      search: false,
    },
  ], []);

  // 用户积分排行列定义
  const userColumns = useMemo<ProColumns<PointUserItem>[]>(() => [
    {
      title: '关键字',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: { placeholder: '用户姓名/手机号' },
    },
    {
      title: '用户姓名',
      dataIndex: 'nickname',
      width: 150,
      search: false,
      render: (val) => val || '-',
    },
    {
      title: '手机号',
      dataIndex: 'phone',
      width: 140,
      search: false,
      render: (val) => val || '-',
    },
    {
      title: '当前积分',
      dataIndex: 'points',
      width: 120,
      search: false,
      sorter: true,
      render: (val) => (
        <span style={{ fontWeight: 600, fontSize: 16 }}>{val as number}</span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      search: false,
      render: (_, record) => (
        <Tag color={record.status === 1 ? 'success' : 'default'}>
          {record.status === 1 ? '正常' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '注册时间',
      dataIndex: 'createdAt',
      width: 160,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 100,
      fixed: 'right',
      render: (_, record) => {
        if (!access.hasPermission('points:update')) return '-';
        return (
          <a onClick={() => openAdjust(record.id, record.nickname || record.phone || record.id)}>
            调整积分
          </a>
        );
      },
    },
  ], [access, openAdjust]);

  return (
    <PageContainer>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'logs',
            label: '积分流水',
            children: (
              <ProTable<PointLogItem>
                headerTitle="积分流水"
                actionRef={logActionRef}
                rowKey="id"
                columns={logColumns}
                request={async (params) => {
                  const { current, pageSize, keyword, logType, dateRange } = params;
                  return toProTableResult(await pointApi.getLogs({
                    keyword: keyword || undefined,
                    logType: logType !== undefined && logType !== '' ? Number(logType) : undefined,
                    startDate: dateRange?.[0],
                    endDate: dateRange?.[1],
                    page: current,
                    pageSize,
                  }));
                }}
                pagination={{ defaultPageSize: PAGINATION_CONFIG.DEFAULT_PAGE_SIZE }}
              />
            ),
          },
          {
            key: 'users',
            label: '用户积分',
            children: (
              <ProTable<PointUserItem>
                headerTitle="用户积分"
                actionRef={userActionRef}
                rowKey="id"
                columns={userColumns}
                request={async (params) => {
                  const { current, pageSize, keyword } = params;
                  return toProTableResult(await pointApi.getUsers({
                    keyword: keyword || undefined,
                    page: current,
                    pageSize,
                  }));
                }}
                toolBarRender={() => [
                  access.hasPermission('points:update') && (
                    <Button
                      key="adjust"
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => {
                        message.info('请在用户列表中点击"调整积分"按钮');
                      }}
                    >
                      调整积分
                    </Button>
                  ),
                ]}
                pagination={{ defaultPageSize: PAGINATION_CONFIG.DEFAULT_PAGE_SIZE }}
              />
            ),
          },
        ]}
      />

      <ModalForm
        title={`调整积分 - ${adjustUserName}`}
        open={adjustOpen}
        onOpenChange={setAdjustOpen}
        onFinish={handleAdjust}
        width={480}
        modalProps={{ destroyOnHidden: true }}
      >
        <ProFormDigit
          name="amount"
          label="调整数量"
          placeholder="正数增加，负数减少"
          rules={[
            { required: true, message: '请输入调整数量' },
            { type: 'integer', message: '请输入整数' },
          ]}
          extra="正数增加积分，负数减少积分"
        />
        <ProFormTextArea
          name="remark"
          label="调整原因"
          placeholder="请输入调整原因"
          rules={[{ required: true, message: '请输入调整原因' }]}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default PointsPage;
