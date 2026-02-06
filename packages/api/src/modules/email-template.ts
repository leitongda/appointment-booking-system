import { request } from '../request';

// 邮件模板类型枚举
export type EmailTemplateType =
  | 'appointment_confirm'
  | 'appointment_remind'
  | 'appointment_cancel'
  | 'stop_clinic'
  | 'custom'
  // 事件钩子模板类型
  | 'appointment_created'
  | 'appointment_cancelled'
  | 'checkin'
  | 'call_patient'
  | 'visit_completed'
  | 'no_show'
  | 'schedule_suspended';

// 邮件模板类型选项
export const EMAIL_TEMPLATE_TYPE_OPTIONS = [
  { label: '预约确认', value: 'appointment_confirm' },
  { label: '就诊提醒', value: 'appointment_remind' },
  { label: '预约取消', value: 'appointment_cancel' },
  { label: '停诊通知（旧）', value: 'stop_clinic' },
  { label: '自定义', value: 'custom' },
  // 事件钩子模板类型
  { label: '新预约通知', value: 'appointment_created' },
  { label: '预约取消通知', value: 'appointment_cancelled' },
  { label: '签到通知', value: 'checkin' },
  { label: '叫号通知', value: 'call_patient' },
  { label: '就诊完成通知', value: 'visit_completed' },
  { label: '爽约通知', value: 'no_show' },
  { label: '停诊通知', value: 'schedule_suspended' },
];

// 邮件模板接口
export interface EmailTemplate {
  id: string;
  code: string;
  name: string;
  templateType: EmailTemplateType;
  subjectTemplate: string;
  contentTemplate: string;
  description?: string;
  status: number;
  createdAt: string;
  updatedAt: string;
}

// 邮件模板列表项
export interface EmailTemplateListItem {
  id: string;
  code: string;
  name: string;
  templateType: string;
  subjectTemplate: string;
  description?: string;
  status: number;
  createdAt: string;
  updatedAt: string;
}

// 邮件模板列表查询参数
export interface EmailTemplateListParams {
  templateType?: EmailTemplateType;
  status?: number;
  keyword?: string;
  page?: number;
  pageSize?: number;
}

// 创建邮件模板参数
export interface EmailTemplateCreateData {
  code: string;
  name: string;
  templateType: EmailTemplateType;
  subjectTemplate: string;
  contentTemplate: string;
  description?: string;
  status?: number;
}

// 更新邮件模板参数
export interface EmailTemplateUpdateData {
  name?: string;
  templateType?: EmailTemplateType;
  subjectTemplate?: string;
  contentTemplate?: string;
  description?: string;
  status?: number;
}

// 发送测试邮件参数
export interface EmailTestData {
  toEmail: string;
  variables?: Record<string, string>;
}

const PREFIX = '/email-templates';

export const emailTemplateApi = {
  // 获取邮件模板列表
  getList: (params?: EmailTemplateListParams): Promise<{
    data: EmailTemplateListItem[];
    total: number;
    page: number;
    pageSize: number;
  }> => {
    return request.get(PREFIX, {
      params: {
        template_type: params?.templateType,
        status: params?.status,
        keyword: params?.keyword,
        page: params?.page || 1,
        page_size: params?.pageSize || 10,
      },
    });
  },

  // 获取所有邮件模板（不分页）
  getAll: (status?: number): Promise<EmailTemplateListItem[]> => {
    return request.get(`${PREFIX}/all`, { params: { status } });
  },

  // 获取邮件模板详情
  getById: (id: string): Promise<EmailTemplate> => {
    return request.get(`${PREFIX}/${id}`);
  },

  // 创建邮件模板
  create: (data: EmailTemplateCreateData): Promise<EmailTemplate> => {
    return request.post(PREFIX, {
      code: data.code,
      name: data.name,
      template_type: data.templateType,
      subject_template: data.subjectTemplate,
      content_template: data.contentTemplate,
      description: data.description,
      status: data.status ?? 1,
    });
  },

  // 更新邮件模板
  update: (id: string, data: EmailTemplateUpdateData): Promise<EmailTemplate> => {
    const payload: Record<string, unknown> = {};
    if (data.name !== undefined) payload.name = data.name;
    if (data.templateType !== undefined) payload.template_type = data.templateType;
    if (data.subjectTemplate !== undefined) payload.subject_template = data.subjectTemplate;
    if (data.contentTemplate !== undefined) payload.content_template = data.contentTemplate;
    if (data.description !== undefined) payload.description = data.description;
    if (data.status !== undefined) payload.status = data.status;
    return request.put(`${PREFIX}/${id}`, payload);
  },

  // 删除邮件模板
  delete: (id: string): Promise<{ message: string }> => {
    return request.delete(`${PREFIX}/${id}`);
  },

  // 发送测试邮件
  sendTest: (id: string, data: EmailTestData): Promise<{ message: string }> => {
    return request.post(`${PREFIX}/${id}/test`, {
      to_email: data.toEmail,
      variables: data.variables,
    });
  },
};

