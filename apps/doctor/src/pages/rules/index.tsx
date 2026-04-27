import { PageContainer } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Tag, Empty, Tooltip, Typography } from 'antd';
import { doctorApi } from '@hospital/api';
import { useState } from 'react';

const { Text } = Typography;

interface ShiftTypeInfo {
  id: string;
  code: string;
  name: string;
  enabled: boolean;
}

interface RuleSetItem {
  id: string;
  name: string;
  enabled: boolean;
  priority: number;
  storeId?: string;
  storeName?: string;
  departmentId?: string;
  departmentName?: string;
  doctorId?: string;
  doctorName?: string;
  shiftTypes?: ShiftTypeInfo[];
  description?: string;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
}

const RuleSetPage: React.FC = () => {
  const [loading, setLoading] = useState(false);

  const columns: ProColumns<RuleSetItem>[] = [
    {
      title: '规则组名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
      render: (_, record) => (
        <Tooltip title={record.description || record.name}>
          <Text strong>{record.name}</Text>
        </Tooltip>
      ),
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      filters: [
        { text: '已启用', value: true },
        { text: '已禁用', value: false },
      ],
      filterMultiple: false,
      render: (_, record) => {
        if (!record.enabled) {
          return <Tag color="default">已禁用</Tag>;
        }
        if (record.isActive) {
          return <Tag color="success">生效中</Tag>;
        }
        return <Tag color="processing">已启用</Tag>;
      },
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      sorter: true,
      render: (_, record) => (
        <Text type={record.priority <= 50 ? 'danger' : undefined}>
          {record.priority}
        </Text>
      ),
    },
    {
      title: '关联班次类型',
      dataIndex: 'shiftTypes',
      key: 'shiftTypes',
      width: 200,
      render: (_, record) => {
        if (!record.shiftTypes || record.shiftTypes.length === 0) {
          return <Text type="secondary">-</Text>;
        }
        return (
          <span>
            {record.shiftTypes.map((st) => (
              <Tag key={st.id} color="blue">{st.name}</Tag>
            ))}
          </span>
        );
      },
    },
    {
      title: '适用范围',
      key: 'scope',
      width: 200,
      render: (_, record) => {
        const parts: string[] = [];
        if (record.doctorName) {
          parts.push(record.doctorName);
        }
        if (record.departmentName) {
          parts.push(record.departmentName);
        }
        if (record.storeName) {
          parts.push(record.storeName);
        }
        if (parts.length === 0) {
          return <Tag color="orange">全局</Tag>;
        }
        return <Text type="secondary">{parts.join(' / ')}</Text>;
      },
    },
    {
      title: '更新时间',
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      width: 160,
      valueType: 'dateTime',
      sorter: true,
    },
  ];

  const loadData = async (params: any) => {
    setLoading(true);
    try {
      const result = await doctorApi.getMyRuleSets({
        page: params.current || 1,
        pageSize: params.pageSize || 10,
      });
      return {
        data: result.data || [],
        total: result.total || 0,
        success: true,
      };
    } catch (error) {
      console.error('加载规则组列表失败', error);
      return {
        data: [],
        total: 0,
        success: false,
      };
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageContainer
      header={{
        title: '预约规则',
        subTitle: '查看关联的预约规则配置',
      }}
    >
      <ProTable<RuleSetItem>
        columns={columns}
        request={loadData}
        rowKey="id"
        loading={loading}
        search={false}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          pageSizeOptions: ['10', '20', '50'],
        }}
        locale={{
          emptyText: (
            <Empty
              description="暂无关联规则组，请联系管理员配置"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ),
        }}
        options={{
          density: true,
          fullScreen: true,
          reload: true,
          setting: false,
        }}
        scroll={{ x: 800 }}
      />
    </PageContainer>
  );
};

export default RuleSetPage;
