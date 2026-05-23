import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Drawer, Descriptions, Popconfirm, Space, Spin, message } from 'antd';
import { EyeOutlined } from '@ant-design/icons';
import { useRef, useState, useMemo } from 'react';
import { followUpApi } from '@hospital/api';
import type { FollowUpRecordListItem, FollowUpRecord } from '@hospital/api';
import dayjs from 'dayjs';

const CONDITION_MAP: Record<string, { text: string; color: string }> = {
  improved: { text: '好转', color: 'success' },
  stable: { text: '稳定', color: 'processing' },
  worsened: { text: '恶化', color: 'error' },
};

const FollowUpRecordsPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const doctorId = useMemo(() => {
    try {
      const doctor = JSON.parse(localStorage.getItem('doctor') || '{}');
      return doctor.id || doctor.doctorId || '';
    } catch {
      return '';
    }
  }, []);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<FollowUpRecord | null>(null);

  const handleView = async (id: string) => {
    setDetailLoading(true);
    setDrawerOpen(true);
    try {
      const result = await followUpApi.getRecordDetail(id);
      setCurrentRecord(result);
    } catch (error: any) {
      message.error(error.message || '加载详情失败');
      setDrawerOpen(false);
    } finally {
      setDetailLoading(false);
    }
  };

  const columns: ProColumns<FollowUpRecordListItem>[] = [
    { title: '患者', dataIndex: 'patientName', width: 100, search: false },
    {
      title: '随访日期',
      dataIndex: 'followUpDate',
      width: 120,
      valueType: 'date',
      search: false,
    },
    { title: '随访内容', dataIndex: 'content', ellipsis: true, search: false },
    {
      title: '患者状况',
      dataIndex: 'patientCondition',
      width: 80,
      search: false,
      render: (_, record) => {
        if (!record.patientCondition) return '-';
        const c = CONDITION_MAP[record.patientCondition];
        return <Tag color={c?.color}>{c?.text || record.patientCondition}</Tag>;
      },
    },
    { title: '创建时间', dataIndex: 'createdAt', width: 170, valueType: 'dateTime', search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 80,
      render: (_, record) => (
        <Button type="link" icon={<EyeOutlined />} onClick={() => handleView(record.id)}>
          查看
        </Button>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<FollowUpRecordListItem>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={false}
        request={async (params) => {
          try {
            const { current, pageSize } = params;
            const result = await followUpApi.getRecordList({
              page: current || 1,
              pageSize: pageSize || 10,
              doctorId: doctorId || undefined,
            });
            return { data: result.data, success: true, total: result.total };
          } catch (error: any) {
            message.error(error.message || '获取随访记录失败');
            return { data: [], success: false, total: 0 };
          }
        }}
      />

      <Drawer
        title="随访记录详情"
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setCurrentRecord(null);
        }}
        width={580}
      >
        <Spin spinning={detailLoading}>
          {currentRecord ? (
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="患者">{currentRecord.patientName || '-'}</Descriptions.Item>
              <Descriptions.Item label="医生">{currentRecord.doctorName || '-'}</Descriptions.Item>
              <Descriptions.Item label="随访日期">
                {currentRecord.followUpDate ? dayjs(currentRecord.followUpDate).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="患者状况">
                {currentRecord.patientCondition ? (
                  <Tag color={CONDITION_MAP[currentRecord.patientCondition]?.color}>
                    {CONDITION_MAP[currentRecord.patientCondition]?.text || currentRecord.patientCondition}
                  </Tag>
                ) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="随访内容" span={2}>{currentRecord.content || '-'}</Descriptions.Item>
              <Descriptions.Item label="下一步措施" span={2}>{currentRecord.nextAction || '-'}</Descriptions.Item>
              <Descriptions.Item label="下次随访日期">{currentRecord.nextFollowUpDate || '-'}</Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {currentRecord.createdAt ? dayjs(currentRecord.createdAt).format('YYYY-MM-DD HH:mm:ss') : '-'}
              </Descriptions.Item>
            </Descriptions>
          ) : null}
        </Spin>
      </Drawer>
    </PageContainer>
  );
};

export default FollowUpRecordsPage;
