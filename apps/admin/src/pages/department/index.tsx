import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import {
  PageContainer,
  ProTable,
  DrawerForm,
  ProFormText,
  ProFormTextArea,
  ProFormDigit,
  ProFormSelect,
  ProFormSwitch,
  ProFormGroup,
  ProFormDependency,
} from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag, Divider } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { departmentApi, storeApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Department, Store, DepartmentTreeNode } from '@hospital/shared';

const DepartmentPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Department | null>(null);
  const [stores, setStores] = useState<Store[]>([]);
  const [departments, setDepartments] = useState<DepartmentTreeNode[]>([]);

  useEffect(() => {
    loadStores();
    loadDepartments();
  }, []);

  const loadStores = async () => {
    try {
      const res = await storeApi.getList({ pageSize: 100, status: 1 });
      setStores(res.data ?? []);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

  const loadDepartments = async () => {
    try {
      const res = await departmentApi.getTree(1);
      setDepartments(res ?? []);
    } catch (error) {
      console.error('加载科室失败', error);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await departmentApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
      loadDepartments();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const data = {
        ...values,
        isHot: values.isHot ? 1 : 0,
        status: values.status ? 1 : 0,
        enableBanner: values.enableBanner ? 1 : 0,
        enableIntro: values.enableIntro ? 1 : 0,
        isFinal: values.isFinal ? 1 : 0,
        isRecommended: values.isRecommended ? 1 : 0,
      };
      if (editingRecord) {
        await departmentApi.update(editingRecord.id, data);
        message.success('更新成功');
      } else {
        await departmentApi.create(data);
        message.success('创建成功');
      }
      setDrawerOpen(false);
      setEditingRecord(null);
      actionRef.current?.reload();
      loadDepartments();
      return true;
    } catch (error: any) {
      message.error(error.message || '操作失败');
      return false;
    }
  };

  // 将树形结构扁平化为选项
  const flattenTreeToOptions = (nodes: DepartmentTreeNode[], level = 0): { label: string; value: string }[] => {
    const options: { label: string; value: string }[] = [];
    nodes.forEach((node) => {
      const prefix = level > 0 ? '└'.padStart(level * 2, ' ') + ' ' : '';
      options.push({ label: prefix + node.name, value: node.id });
      if (node.children?.length) {
        options.push(...flattenTreeToOptions(node.children, level + 1));
      }
    });
    return options;
  };

  const columns: ProColumns<Department>[] = [
    {
      title: '科室名称',
      dataIndex: 'name',
      ellipsis: true,
      width: 150,
    },
    {
      title: '所属门店',
      dataIndex: 'storeName',
      ellipsis: true,
      width: 120,
      search: false,
      render: (_, record) => record.storeName || '-',
    },
    {
      title: '门店筛选',
      dataIndex: 'storeId',
      hideInTable: true,
      valueType: 'select',
      fieldProps: {
        options: stores.map((s) => ({ label: s.name, value: s.id })),
        allowClear: true,
        placeholder: '请选择门店',
      },
    },
    {
      title: '科室标签',
      dataIndex: 'tag',
      ellipsis: true,
      width: 100,
      search: false,
      render: (_, record) => record.tag ? <Tag color="blue">{record.tag}</Tag> : '-',
    },
    {
      title: '排序',
      dataIndex: 'sortOrder',
      width: 70,
      search: false,
    },
    {
      title: '终极科室',
      dataIndex: 'isFinal',
      width: 90,
      search: false,
      render: (_, record) => (
        record.isFinal === 1 ? <Tag color="green">是</Tag> : <Tag>否</Tag>
      ),
    },
    {
      title: '推荐',
      dataIndex: 'isRecommended',
      width: 70,
      search: false,
      render: (_, record) => (
        record.isRecommended === 1 ? <Tag color="orange">推荐</Tag> : '-'
      ),
    },
    {
      title: '热门',
      dataIndex: 'isHot',
      width: 70,
      search: false,
      render: (_, record) => (
        record.isHot === 1 ? <Tag color="red">热门</Tag> : '-'
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueType: 'select',
      valueEnum: {
        1: { text: '启用', status: 'Success' },
        0: { text: '禁用', status: 'Default' },
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <a
            onClick={() => {
              setEditingRecord(record);
              setDrawerOpen(true);
            }}
          >
            编辑
          </a>
          <Popconfirm
            title="确定删除该科室吗？"
            onConfirm={() => handleDelete(record.id)}
          >
            <a style={{ color: '#ff4d4f' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const getInitialValues = () => {
    if (editingRecord) {
      return {
        ...editingRecord,
        isHot: editingRecord.isHot === 1,
        status: editingRecord.status === 1,
        enableBanner: editingRecord.enableBanner === 1,
        enableIntro: editingRecord.enableIntro === 1,
        isFinal: editingRecord.isFinal === 1,
        isRecommended: editingRecord.isRecommended === 1,
      };
    }
    return {
      sortOrder: 1,
      isHot: false,
      status: true,
      enableBanner: false,
      enableIntro: false,
      isFinal: false,
      isRecommended: false,
    };
  };

  return (
    <PageContainer>
      <ProTable<Department>
        headerTitle="科室列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1200 }}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await departmentApi.getList({
            ...rest,
            page: current,
            pageSize,
          }));
        }}
        toolBarRender={() => [
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingRecord(null);
              setDrawerOpen(true);
            }}
          >
            新增科室
          </Button>,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      <DrawerForm
        title={editingRecord ? '编辑科室' : '新增科室'}
        width={600}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        onFinish={handleSubmit}
        initialValues={getInitialValues()}
        drawerProps={{ destroyOnClose: true }}
      >
        <Divider orientation="left">基础信息</Divider>
        <ProFormSelect
          name="storeId"
          label="门店选择"
          placeholder="请选择门店"
          options={stores.map((s) => ({ label: s.name, value: s.id }))}
          allowClear
        />
        <ProFormSelect
          name="parentId"
          label="父级分类"
          placeholder="顶级分类"
          options={[
            { label: '顶级分类', value: '' },
            ...flattenTreeToOptions(departments),
          ]}
          allowClear
        />
        <ProFormText
          name="name"
          label="科室名称"
          placeholder="请输入科室名称"
          rules={[{ required: true, message: '请输入科室名称' }]}
        />
        <ProFormText
          name="tag"
          label="科室标签"
          placeholder="请输入科室标签，如：专家科室"
        />
        <ProFormDigit
          name="sortOrder"
          label="排序"
          placeholder="数字越大越靠前"
          min={0}
          max={9999}
          extra="说明：排序数字越大越靠前"
        />
        <ProFormTextArea
          name="description"
          label="描述"
          placeholder="请输入科室描述"
        />

        <Divider orientation="left">图片设置</Divider>
        <ProFormText
          name="icon"
          label="科室图标"
          placeholder="请输入科室图标URL"
        />
        <ProFormText
          name="bannerImage"
          label="Banner图片"
          placeholder="请输入Banner图片URL"
        />
        <ProFormTextArea
          name="introImages"
          label="简介图片"
          placeholder="请输入简介图片URL，多个用逗号分隔"
        />

        <Divider orientation="left">详情内容</Divider>
        <ProFormTextArea
          name="introContent"
          label="科室简介"
          placeholder="请输入科室详细简介"
          fieldProps={{ rows: 4 }}
        />
        <ProFormTextArea
          name="features"
          label="科室特色"
          placeholder="请输入科室特色，多个用逗号分隔"
        />
        <ProFormTextArea
          name="appointmentNotice"
          label="预约须知"
          placeholder="请输入预约须知"
          fieldProps={{ rows: 3 }}
        />

        <Divider orientation="left">联系信息</Divider>
        <ProFormText
          name="phone"
          label="科室电话"
          placeholder="请输入科室电话"
        />
        <ProFormText
          name="location"
          label="位置/楼层"
          placeholder="请输入位置/楼层，如：门诊楼3楼"
        />
        <ProFormText
          name="workingHours"
          label="工作时间"
          placeholder="请输入工作时间，如：周一至周五 8:00-17:00"
        />

        <Divider orientation="left">开关设置</Divider>
        <ProFormGroup>
          <ProFormSwitch name="enableBanner" label="是否开放banner" />
          <ProFormSwitch name="enableIntro" label="是否开放科室简介" />
        </ProFormGroup>
        <ProFormGroup>
          <ProFormSwitch name="status" label="是否启用科室" />
          <ProFormSwitch
            name="isFinal"
            label="是否终极科室"
            extra="说明：只有终极科室才能添加医生"
          />
        </ProFormGroup>
        <ProFormGroup>
          <ProFormSwitch
            name="isRecommended"
            label="是否推荐"
            extra="说明：选择是则该科室名称及推荐医生将在首页展示"
          />
          <ProFormSwitch name="isHot" label="是否热门" />
        </ProFormGroup>
      </DrawerForm>
    </PageContainer>
  );
};

export default DepartmentPage;
