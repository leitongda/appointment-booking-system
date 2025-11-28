import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Tag, Space, message, Popconfirm, Modal, Descriptions, Badge, Tabs, Statistic, List } from 'antd';
import { useRef, useState } from 'react';
import { patientApi } from '@hospital/api';
import type { PatientListItem, PatientDetail } from '@hospital/api';
import { GENDER_MAP, APPOINTMENT_STATUS_MAP, APPOINTMENT_STATUS_COLOR } from '@hospital/shared';

const PatientPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentPatient, setCurrentPatient] = useState<PatientDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'all' | 'blacklist'>('all');

  const handleViewDetail = async (record: PatientListItem) => {
    setDetailLoading(true);
    setDetailVisible(true);
    
    try {
      const detail = await patientApi.getDetail(record.id);
      setCurrentPatient(detail);
    } catch (error: any) {
      message.error(error.message || '获取详情失败');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleAddToBlacklist = async (record: PatientListItem) => {
    try {
      await patientApi.addToBlacklist(record.id);
      message.success('已加入黑名单');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleRemoveFromBlacklist = async (record: PatientListItem) => {
    try {
      await patientApi.removeFromBlacklist(record.id);
      message.success('已移出黑名单');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const columns: ProColumns<PatientListItem>[] = [
    { title: '姓名', dataIndex: 'name', width: 100 },
    { title: '手机号', dataIndex: 'phone', width: 130 },
    { 
      title: '性别', 
      dataIndex: 'gender', 
      width: 80, 
      search: false,
      render: (_, r) => GENDER_MAP[r.gender] || '未知'
    },
    { 
      title: '身份证', 
      dataIndex: 'idCard', 
      width: 180, 
      search: false,
      render: (_, r) => r.idCard ? `${r.idCard.substring(0, 6)}****${r.idCard.substring(14)}` : '-'
    },
    { 
      title: '预约次数', 
      dataIndex: 'appointmentCount', 
      width: 100, 
      search: false,
      sorter: true,
    },
    { 
      title: '爽约次数', 
      dataIndex: 'noShowCount', 
      width: 100, 
      search: false,
      render: (_, r) => (
        <span style={{ color: r.noShowCount > 2 ? '#ff4d4f' : undefined }}>
          {r.noShowCount}
        </span>
      ),
    },
    { 
      title: '状态', 
      dataIndex: 'isBlacklist', 
      width: 100,
      valueType: 'select',
      valueEnum: {
        false: { text: '正常', status: 'Success' },
        true: { text: '黑名单', status: 'Error' },
      },
      render: (_, r) => r.isBlacklist 
        ? <Badge status="error" text="黑名单" />
        : <Badge status="success" text="正常" />
    },
    { 
      title: '注册时间', 
      dataIndex: 'createdAt', 
      width: 180, 
      valueType: 'dateTime', 
      search: false,
    },
    { 
      title: '操作', 
      valueType: 'option', 
      width: 180, 
      render: (_, record) => (
        <Space>
          <a onClick={() => handleViewDetail(record)}>详情</a>
          {record.isBlacklist ? (
            <Popconfirm 
              title="确定移出黑名单吗？" 
              onConfirm={() => handleRemoveFromBlacklist(record)}
            >
              <a style={{ color: '#52c41a' }}>移出黑名单</a>
            </Popconfirm>
          ) : (
            <Popconfirm 
              title="确定加入黑名单吗？加入后该用户将无法预约。" 
              onConfirm={() => handleAddToBlacklist(record)}
            >
              <a style={{ color: '#ff4d4f' }}>加入黑名单</a>
            </Popconfirm>
          )}
        </Space>
      )
    },
  ];

  return (
    <PageContainer>
      <Tabs
        activeKey={activeTab}
        onChange={(key) => {
          setActiveTab(key as 'all' | 'blacklist');
          actionRef.current?.reload();
        }}
        items={[
          { key: 'all', label: '全部患者' },
          { key: 'blacklist', label: '黑名单' },
        ]}
      />
      
      <ProTable<PatientListItem>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        request={async (params) => {
          try {
            const { current, pageSize, name, phone, isBlacklist } = params;
            
            // 根据Tab决定是否只查黑名单
            const queryParams = {
              keyword: name || phone,
              isBlacklist: activeTab === 'blacklist' ? true : isBlacklist,
              page: current || 1,
              pageSize: pageSize || 10,
            };
            
            const result = await patientApi.getList(queryParams);
            return { 
              data: result.data || [], 
              success: true, 
              total: result.total || 0 
            };
          } catch (error: any) {
            message.error(error.message || '获取数据失败');
            return { data: [], success: false, total: 0 };
          }
        }}
      />

      <Modal
        title="患者详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={700}
        loading={detailLoading}
      >
        {currentPatient && (
          <>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="姓名">{currentPatient.name}</Descriptions.Item>
              <Descriptions.Item label="性别">{GENDER_MAP[currentPatient.gender] || '未知'}</Descriptions.Item>
              <Descriptions.Item label="手机号">{currentPatient.phone}</Descriptions.Item>
              <Descriptions.Item label="生日">{currentPatient.birthday || '-'}</Descriptions.Item>
              <Descriptions.Item label="身份证" span={2}>{currentPatient.idCard}</Descriptions.Item>
              <Descriptions.Item label="状态">
                {currentPatient.isBlacklist 
                  ? <Badge status="error" text="黑名单" />
                  : <Badge status="success" text="正常" />}
              </Descriptions.Item>
              <Descriptions.Item label="注册时间">{currentPatient.createdAt}</Descriptions.Item>
            </Descriptions>

            <div style={{ display: 'flex', gap: 16, margin: '16px 0' }}>
              <Statistic title="预约总数" value={currentPatient.statistics.appointmentCount} />
              <Statistic title="完成就诊" value={currentPatient.statistics.completedCount} valueStyle={{ color: '#52c41a' }} />
              <Statistic title="爽约次数" value={currentPatient.statistics.noShowCount} valueStyle={{ color: '#ff4d4f' }} />
            </div>

            <div style={{ marginTop: 16 }}>
              <h4>最近预约记录</h4>
              {currentPatient.recentAppointments.length === 0 ? (
                <div style={{ color: '#999', textAlign: 'center', padding: 16 }}>暂无预约记录</div>
              ) : (
                <List
                  size="small"
                  dataSource={currentPatient.recentAppointments}
                  renderItem={(item) => (
                    <List.Item>
                      <span>预约号：{item.appointmentNo}</span>
                      <Tag color={APPOINTMENT_STATUS_COLOR[item.status]}>
                        {APPOINTMENT_STATUS_MAP[item.status]}
                      </Tag>
                      <span style={{ color: '#999' }}>{item.createdAt}</span>
                    </List.Item>
                  )}
                />
              )}
            </div>
          </>
        )}
      </Modal>
    </PageContainer>
  );
};

export default PatientPage;
