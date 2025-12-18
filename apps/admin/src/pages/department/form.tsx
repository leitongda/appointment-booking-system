import { PageContainer, ProForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSelect, ProFormSwitch, ProFormGroup } from '@ant-design/pro-components';
import { Card, App, Row, Col, Form, Divider } from 'antd';
import { useEffect, useState } from 'react';
import { history, useParams } from '@umijs/max';
import { departmentApi, storeApi } from '@hospital/api';
import type { Department, Store, DepartmentTreeNode } from '@hospital/shared';
import ImageUpload from '@/components/ImageUpload';
import RichTextEditor from '@/components/RichTextEditor';

const DepartmentFormPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [department, setDepartment] = useState<Department | null>(null);
  const [stores, setStores] = useState<Store[]>([]);
  const [departments, setDepartments] = useState<DepartmentTreeNode[]>([]);

  useEffect(() => {
    loadStores();
    loadDepartments();
    if (isEdit) {
      loadDepartment();
    }
  }, [id]);

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

  const loadDepartment = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await departmentApi.getDetail(id);
      setDepartment(data);
    } catch (error: any) {
      message.error('加载科室信息失败');
    } finally {
      setLoading(false);
    }
  };

  // 将树形结构扁平化为选项
  const flattenTreeToOptions = (nodes: DepartmentTreeNode[], level = 0): { label: string; value: string }[] => {
    const options: { label: string; value: string }[] = [];
    nodes.forEach((node) => {
      // 编辑时排除自己
      if (isEdit && node.id === id) return;
      const prefix = level > 0 ? '└'.padStart(level * 2, ' ') + ' ' : '';
      options.push({ label: prefix + node.name, value: node.id });
      if (node.children?.length) {
        options.push(...flattenTreeToOptions(node.children, level + 1));
      }
    });
    return options;
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

      if (isEdit && id) {
        await departmentApi.update(id, data);
        message.success('更新成功');
      } else {
        await departmentApi.create(data);
        message.success('创建成功');
      }
      history.push('/department/list');
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const initialValues = department ? {
    ...department,
    isHot: department.isHot === 1,
    status: department.status === 1,
    enableBanner: department.enableBanner === 1,
    enableIntro: department.enableIntro === 1,
    isFinal: department.isFinal === 1,
    isRecommended: department.isRecommended === 1,
  } : {
    sortOrder: 1,
    isHot: false,
    status: true,
    enableBanner: false,
    enableIntro: false,
    isFinal: false,
    isRecommended: false,
  };

  return (
    <PageContainer title={isEdit ? '编辑科室' : '新增科室'}>
      <ProForm
        onFinish={handleSubmit}
        initialValues={initialValues}
        submitter={{
          searchConfig: { submitText: isEdit ? '保存' : '创建' },
          resetButtonProps: { style: { display: 'none' } },
          render: (_, dom) => (
            <Row>
              <Col span={24} style={{ textAlign: 'center' }}>
                {dom}
              </Col>
            </Row>
          ),
        }}
      >
        {/* 基础信息 */}
        <Card title="基础信息" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormSelect
              name="storeId"
              label="门店选择"
              width="md"
              placeholder="请选择门店"
              options={stores.map((s) => ({ label: s.name, value: s.id }))}
              allowClear
            />
            <ProFormSelect
              name="parentId"
              label="父级分类"
              width="md"
              placeholder="顶级分类"
              options={[
                { label: '顶级分类', value: '' },
                ...flattenTreeToOptions(departments),
              ]}
              allowClear
            />
          </ProForm.Group>
          <ProForm.Group>
            <ProFormText
              name="name"
              label="科室名称"
              width="md"
              placeholder="请输入科室名称"
              rules={[{ required: true, message: '请输入科室名称' }]}
            />
            <ProFormText
              name="tag"
              label="科室标签"
              width="md"
              placeholder="请输入科室标签，如：专家科室"
            />
          </ProForm.Group>
          <ProForm.Group>
            <ProFormDigit
              name="sortOrder"
              label="排序"
              width="sm"
              placeholder="数字越大越靠前"
              min={0}
              max={9999}
              tooltip="排序数字越大越靠前"
            />
          </ProForm.Group>
          <ProFormTextArea
            name="description"
            label="描述"
            placeholder="请输入科室描述"
          />
        </Card>

        {/* 图片设置 */}
        <Card title="图片设置" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <Form.Item name="icon" label="科室图标">
              <ImageUpload
                aspectRatio="1:1"
                folder="department"
                placeholder="上传图标"
                width={100}
                height={100}
              />
            </Form.Item>
            <Form.Item name="bannerImage" label="Banner图片">
              <ImageUpload
                aspectRatio="16:9"
                folder="department"
                placeholder="上传Banner"
                width={240}
                height={135}
              />
            </Form.Item>
            <Form.Item name="introImages" label="简介图片" tooltip="支持上传简介图片">
              <ImageUpload
                aspectRatio="free"
                folder="department"
                placeholder="上传简介图"
                width={200}
                height={150}
              />
            </Form.Item>
          </ProForm.Group>
        </Card>

        {/* 详情内容 */}
        <Card title="详情内容" style={{ marginBottom: 16 }} loading={loading}>
          <Form.Item
            name="introContent"
            label="科室简介"
          >
            <RichTextEditor height={300} placeholder="请输入科室详细简介..." />
          </Form.Item>
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
        </Card>

        {/* 联系信息 */}
        <Card title="联系信息" style={{ marginBottom: 16 }} loading={loading}>
          <ProForm.Group>
            <ProFormText
              name="phone"
              label="科室电话"
              width="md"
              placeholder="请输入科室电话"
            />
            <ProFormText
              name="location"
              label="位置/楼层"
              width="md"
              placeholder="请输入位置/楼层，如：门诊楼3楼"
            />
          </ProForm.Group>
          <ProFormText
            name="workingHours"
            label="工作时间"
            width="lg"
            placeholder="请输入工作时间，如：周一至周五 8:00-17:00"
          />
        </Card>

        {/* 开关设置 */}
        <Card title="开关设置" loading={loading}>
          <ProFormGroup>
            <ProFormSwitch name="enableBanner" label="是否开放banner" />
            <ProFormSwitch name="enableIntro" label="是否开放科室简介" />
          </ProFormGroup>
          <Divider style={{ margin: '12px 0' }} />
          <ProFormGroup>
            <ProFormSwitch name="status" label="是否启用科室" />
            <ProFormSwitch
              name="isFinal"
              label="是否终极科室"
              tooltip="只有终极科室才能添加医生"
            />
          </ProFormGroup>
          <Divider style={{ margin: '12px 0' }} />
          <ProFormGroup>
            <ProFormSwitch
              name="isRecommended"
              label="是否推荐"
              tooltip="选择是则该科室名称及推荐医生将在首页展示"
            />
            <ProFormSwitch name="isHot" label="是否热门" />
          </ProFormGroup>
        </Card>
      </ProForm>
    </PageContainer>
  );
};

export default DepartmentFormPage;

