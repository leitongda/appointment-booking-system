import request from '../request';
import type {
  ApprovalInstance,
  ApprovalInstanceListItem,
  ApprovalQueryParams,
  ApprovalProgress,
  FlowDefinition,
  FlowDefinitionListItem,
  PageResult,
} from '@hospital/shared';

// ============================================================
// 审批实例 API
// ============================================================

export const approvalInstanceApi = {
  /** 获取我的待办列表 */
  getMyPending: (params?: ApprovalQueryParams): Promise<PageResult<ApprovalInstanceListItem>> => {
    return request.get('/approval-instances', {
      params: {
        page: params?.page,
        page_size: params?.pageSize,
        business_type: params?.businessType,
        store_id: params?.storeId,
        view: 'pending',
      },
    });
  },

  /** 获取我的已办列表（我审批过的） */
  getMyDone: (params?: ApprovalQueryParams): Promise<PageResult<ApprovalInstanceListItem>> => {
    return request.get('/approval-instances', {
      params: {
        page: params?.page,
        page_size: params?.pageSize,
        status: params?.status,
        business_type: params?.businessType,
        store_id: params?.storeId,
        view: 'done',
      },
    });
  },

  /** 获取我发起的列表 */
  getMyInitiated: (params?: ApprovalQueryParams): Promise<PageResult<ApprovalInstanceListItem>> => {
    return request.get('/approval-instances', {
      params: {
        page: params?.page,
        page_size: params?.pageSize,
        status: params?.status,
        business_type: params?.businessType,
        store_id: params?.storeId,
        view: 'initiated',
      },
    });
  },

  /** 获取实例详情 */
  getDetail: (id: string): Promise<ApprovalInstance> => {
    return request.get(`/approval-instances/${id}`);
  },

  /** 获取审批进度 */
  getProgress: (id: string): Promise<ApprovalProgress> => {
    return request.get(`/approval-instances/${id}/progress`);
  },

  /** 审批通过 */
  approve: (instanceId: string, comment?: string): Promise<void> => {
    return request.post(`/approval-instances/${instanceId}/approve`, { comment });
  },

  /** 审批拒绝 */
  reject: (instanceId: string, comment?: string): Promise<void> => {
    return request.post(`/approval-instances/${instanceId}/reject`, { comment });
  },

  /** 转交 */
  delegate: (instanceId: string, targetUserId: string, targetUserName?: string, comment?: string): Promise<void> => {
    return request.post(`/approval-instances/${instanceId}/delegate`, {
      target_user_id: targetUserId,
      target_user_name: targetUserName,
      comment,
    });
  },

  /** 撤回 */
  withdraw: (instanceId: string): Promise<void> => {
    return request.post(`/approval-instances/${instanceId}/withdraw`);
  },

  /** 回退到指定节点 */
  rollback: (instanceId: string, targetNodeKey: string, comment?: string): Promise<void> => {
    return request.post(`/approval-instances/${instanceId}/rollback`, { targetNodeKey, comment });
  },

  /** 加签 */
  addSigner: (instanceId: string, userIds: string[], comment?: string): Promise<void> => {
    return request.post(`/approval-instances/${instanceId}/add-signer`, { userIds, comment });
  },

  /** 自由跳转 */
  jump: (instanceId: string, targetNodeKey: string, comment?: string): Promise<void> => {
    return request.post(`/approval-instances/${instanceId}/jump`, { targetNodeKey, comment });
  },

  /** 获取待办数量 */
  getPendingCount: (): Promise<{ count: number }> => {
    return request.get('/approval-instances/pending-count');
  },
};

// ============================================================
// 流程定义 API
// ============================================================

export interface FlowDefinitionCreateData {
  name: string;
  businessType: string;
  description?: string;
  formSchema?: Record<string, any>;
  callbackConfig?: Record<string, any>;
  storeId?: string;
  nodes: Array<{
    nodeKey: string;
    nodeName: string;
    nodeType: string;
    approvalMode?: string;
    assigneeType?: string;
    assigneeConfig?: Record<string, any>;
    timeoutHours?: number;
    timeoutAction?: string;
    sortOrder: number;
    positionX?: number;
    positionY?: number;
    conditions?: Array<{
      targetNodeKey: string;
      fieldName: string;
      operator: string;
      value: string;
      priority: number;
    }>;
  }>;
  edges?: Array<{
    id?: string;
    source: string;
    target: string;
    sourceHandle?: string;
    targetHandle?: string;
  }>;
}

export const approvalFlowApi = {
  /** 获取流程定义列表 */
  getList: (params?: {
    page?: number;
    pageSize?: number;
    businessType?: string;
    status?: string;
  }): Promise<PageResult<FlowDefinitionListItem>> => {
    return request.get('/approval-flows', {
      params: {
        page: params?.page,
        page_size: params?.pageSize,
        business_type: params?.businessType,
        status: params?.status,
      },
    });
  },

  /** 获取流程定义详情 */
  getDetail: (id: string): Promise<FlowDefinition> => {
    return request.get(`/approval-flows/${id}`);
  },

  /** 创建流程定义 */
  create: (data: FlowDefinitionCreateData): Promise<FlowDefinition> => {
    return request.post('/approval-flows', data);
  },

  /** 更新流程定义 */
  update: (id: string, data: Partial<FlowDefinitionCreateData>): Promise<FlowDefinition> => {
    return request.put(`/approval-flows/${id}`, data);
  },

  /** 激活流程定义 */
  activate: (id: string): Promise<FlowDefinition> => {
    return request.put(`/approval-flows/${id}/activate`);
  },

  /** 归档流程定义 */
  archive: (id: string): Promise<FlowDefinition> => {
    return request.put(`/approval-flows/${id}/archive`);
  },

  /** 删除流程定义 */
  delete: (id: string): Promise<void> => {
    return request.delete(`/approval-flows/${id}`);
  },

  /** 复制流程定义 */
  copy: (id: string): Promise<FlowDefinition> => {
    return request.post(`/approval-flows/${id}/copy`);
  },

  /** 校验流程定义 */
  validate: (id: string): Promise<{ valid: boolean; errors: string[] }> => {
    return request.post(`/approval-flows/${id}/validate`);
  },

  /** 获取流程模板列表 */
  getTemplates: (): Promise<{ items: Array<{ id: string; name: string; businessType: string; description: string; nodes: any[]; edges: any[] }> }> => {
    return request.get('/approval-flows/templates/list');
  },

  /** 导出流程定义 JSON */
  export: (id: string): Promise<any> => {
    return request.post(`/approval-flows/${id}/export`);
  },
};
