/**
 * 知识库页面共用常量 / 工具
 */
import axios from 'axios';
import { knowledgeApi } from '@hospital/api';
import type { KnowledgeDocStatus, KnowledgePermission, KnowledgeVisibility } from '@hospital/api';
import { getStorage, getToken, STORAGE_KEYS } from '@hospital/shared';

export const STATUS_MAP: Record<KnowledgeDocStatus, { text: string; color: string }> = {
  pending: { text: '待处理', color: 'default' },
  parsing: { text: '解析中', color: 'processing' },
  embedding: { text: '向量化中', color: 'processing' },
  ready: { text: '已就绪', color: 'success' },
  failed: { text: '失败', color: 'error' },
};

export const PROCESSING_STATUSES: KnowledgeDocStatus[] = ['pending', 'parsing', 'embedding'];

export const VISIBILITY_MAP: Record<KnowledgeVisibility, { text: string; color: string }> = {
  private: { text: '私有', color: 'default' },
  tenant: { text: '租户公共', color: 'blue' },
};

export const PERMISSION_MAP: Record<KnowledgePermission, { text: string; color: string }> = {
  owner: { text: '拥有者', color: 'gold' },
  edit: { text: '可编辑', color: 'green' },
  read: { text: '只读', color: 'default' },
};

export const ACCEPT_EXTENSIONS = '.pdf,.docx,.xlsx,.txt,.md';
export const MAX_FILE_MB = 50;
export const COMPLIANCE_HINT = '请勿上传含患者个人信息的文件';
export const SUPPORTED_HINT = `支持 PDF / Word(.docx) / Excel(.xlsx) / TXT / Markdown，单文件 ≤ ${MAX_FILE_MB}MB`;

export function formatFileSize(bytes: number): string {
  if (!bytes) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** 后端 KB_ENABLED=false 时所有知识库接口返回 404「知识库功能未启用」 */
export function isFeatureDisabled(error: unknown): boolean {
  const err = error as { code?: number; message?: string } | undefined;
  return err?.code === 404 && String(err?.message ?? '').includes('未启用');
}

export function canEdit(permission?: KnowledgePermission | null): boolean {
  return permission === 'owner' || permission === 'edit';
}

export function isOwner(permission?: KnowledgePermission | null): boolean {
  return permission === 'owner';
}

/**
 * 带鉴权拉取原件（服务端做租户 + 可见性校验，key 不暴露）。
 * 走原生 axios 以保留二进制响应与头部；Authorization / X-Tenant-ID 与共享请求层保持一致。
 */
export async function fetchDocumentBlob(docId: string, download = false): Promise<Blob> {
  const token = getToken();
  const tenantId = getStorage<string>(STORAGE_KEYS.CURRENT_TENANT_ID);
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (tenantId) headers['X-Tenant-ID'] = tenantId;
  const response = await axios.get(knowledgeApi.documentFileUrl(docId, { download }), {
    responseType: 'blob',
    headers,
  });
  return response.data as Blob;
}
