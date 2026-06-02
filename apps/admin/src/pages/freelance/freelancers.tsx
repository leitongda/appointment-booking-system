import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormSelect, ProFormTextArea, ProFormDigit } from '@ant-design/pro-components';
import { Tag, Button, Popconfirm, message, Tooltip, Upload } from 'antd';
import { PlusOutlined, CopyOutlined, UploadOutlined, DownloadOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { freelancerApi } from '@hospital/api';
import type { Freelancer } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { OperationButton, OperationGroup } from '@/components/ListOperations';

const PLATFORM_MAP: Record<string, string> = {
  xiaohongshu: '小红书',
  douyin: '抖音',
  weibo: '微博',
  wechat: '微信',
  other: '其他',
};

const ACCOUNT_TYPE_MAP: Record<string, { text: string; color: string }> = {
  old: { text: '老账号', color: 'green' },
  new: { text: '新账号', color: 'orange' },
};

const FreelancersPage: React.FC = () => {
  const { actionRef, reload } = useListPage();
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<Freelancer | null>(null);

  const handleCreate = async (values: any) => {
    try {
      await freelancerApi.create(values);
      message.success('创建成功');
      setCreateOpen(false);
      reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '创建失败');
      return false;
    }
  };

  const handleUpdate = async (values: any) => {
    if (!currentRecord) return false;
    try {
      await freelancerApi.update(currentRecord.id, values);
      message.success('更新成功');
      setEditOpen(false);
      reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '更新失败');
      return false;
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await freelancerApi.delete(id);
      message.success('已禁用');
      reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const copyPortalLink = (accessToken: string) => {
    const url = `${window.location.origin}/freelance-portal?token=${accessToken}`;
    navigator.clipboard.writeText(url).then(() => {
      message.success('自助链接已复制');
    }).catch(() => {
      message.error('复制失败，请手动复制');
    });
  };

  const columns: ProColumns<Freelancer>[] = [
    { title: '姓名', dataIndex: 'name', width: 100 },
    { title: '手机号', dataIndex: 'phone', width: 120, search: false },
    { title: '平台', dataIndex: 'accountPlatform', width: 80, search: false,
      render: (_, r) => PLATFORM_MAP[r.accountPlatform] || r.accountPlatform },
    { title: '账号名', dataIndex: 'accountName', width: 120, search: false, ellipsis: true },
    { title: '账号类型', dataIndex: 'accountType', width: 90, search: false,
      render: (_, r) => {
        const t = ACCOUNT_TYPE_MAP[r.accountType] || { text: r.accountType, color: 'default' };
        return <Tag color={t.color}>{t.text}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: { 0: { text: '禁用' }, 1: { text: '正常' } },
      render: (_, r) => <Tag color={r.status === 1 ? 'green' : 'red'}>{r.status === 1 ? '正常' : '禁用'}</Tag>,
    },
    { title: '创建时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <OperationGroup>
          <OperationButton
            type="edit"
            permission="freelance:update"
            onClick={() => { setCurrentRecord(record); setEditOpen(true); }}
          />
          {record.accessToken && (
            <Tooltip title="复制自助查看链接">
              <OperationButton
                type="custom"
                permission="freelance:list"
                icon={<CopyOutlined />}
                label="链接"
                onClick={() => copyPortalLink(record.accessToken!)}
              />
            </Tooltip>
          )}
          {record.status === 1 && (
            <Popconfirm title="确定禁用此兼职人员？" onConfirm={() => handleDelete(record.id)}>
              <OperationButton type="delete" permission="freelance:delete" />
            </Popconfirm>
          )}
        </OperationGroup>
      ),
    },
  ];

  const formItems = (
    <>
      <ProFormText name="name" label="姓名" rules={[{ required: true }]} />
      <ProFormText name="phone" label="手机号" />
      <ProFormText name="accountName" label="社交媒体账号名" />
      <ProFormSelect name="accountPlatform" label="平台" initialValue="xiaohongshu"
        options={[
          { label: '小红书', value: 'xiaohongshu' },
          { label: '抖音', value: 'douyin' },
          { label: '微博', value: 'weibo' },
          { label: '微信', value: 'wechat' },
          { label: '其他', value: 'other' },
        ]}
      />
      <ProFormSelect name="accountType" label="账号类型" initialValue="old"
        options={[
          { label: '老账号', value: 'old' },
          { label: '新账号', value: 'new' },
        ]}
      />
      <ProFormTextArea name="remark" label="备注" />
    </>
  );

  return (
    <PageContainer>
      <ProTable<Freelancer>
        headerTitle="兼职人员"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(freelancerApi.getList)}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="template" icon={<DownloadOutlined />} onClick={() => {
            window.open(freelancerApi.getImportTemplateUrl(), '_blank');
          }}>
            下载模板
          </Button>,
          <Upload key="import" showUploadList={false} accept=".xlsx,.xls" beforeUpload={(file) => {
            freelancerApi.importFreelancers(file).then((res) => {
              message.success(`导入完成：成功 ${res.success_count}，失败 ${res.fail_count}，跳过 ${res.skipped_count}`);
              reload();
            }).catch((err) => {
              message.error(err.message || '导入失败');
            });
            return false;
          }}>
            <Button icon={<UploadOutlined />}>批量导入</Button>
          </Upload>,
          <Button key="create" type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            新增兼职人员
          </Button>,
        ]}
      />

      <ModalForm title="新增兼职人员" open={createOpen} onOpenChange={setCreateOpen} onFinish={handleCreate} modalProps={{ destroyOnHidden: true }}>
        {formItems}
      </ModalForm>

      <ModalForm title="编辑兼职人员" open={editOpen} onOpenChange={setEditOpen} onFinish={handleUpdate}
        modalProps={{ destroyOnHidden: true }}
        initialValues={currentRecord ? {
          name: currentRecord.name,
          phone: currentRecord.phone,
          accountName: currentRecord.accountName,
          accountPlatform: currentRecord.accountPlatform,
          accountType: currentRecord.accountType,
          remark: currentRecord.remark,
        } : undefined}
      >
        {formItems}
      </ModalForm>
    </PageContainer>
  );
};

export default FreelancersPage;
