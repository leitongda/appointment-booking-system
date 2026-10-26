/**
 * 知识库（RAG）API —— openspec add-knowledge-base-rag
 *
 * 后端 /api/v1/knowledge/*；KB_ENABLED=false 时全部 404（页面据此提示"功能未启用"）。
 * 请求体走 BaseRequestSchema（camelCase 可直接传），query 参数按后端约定转 snake_case。
 */
import request, { getBaseURL } from '../request';
import type { PageResult } from '@hospital/shared';

export type KnowledgeDocStatus = 'pending' | 'parsing' | 'embedding' | 'ready' | 'failed';
export type KnowledgeFailedStage = 'parsing' | 'embedding';
export type KnowledgeVisibility = 'private' | 'tenant';
export type KnowledgePermission = 'owner' | 'edit' | 'read';
export type KnowledgeShareGrantee = 'admin' | 'role';
export type KnowledgeSharePermission = 'read' | 'edit';
export type KnowledgeBaseScope = 'all' | 'mine' | 'shared' | 'tenant';

export interface KnowledgeBase {
  id: string;
  tenantId?: string | null;
  name: string;
  description?: string | null;
  ownerAdminId: string;
  visibility: KnowledgeVisibility;
  embeddingModel: string;
  embeddingDims: number;
  docCount: number;
  chunkCount: number;
  createdAt?: string;
  updatedAt?: string;
  /** 当前用户对该库的级别：owner / edit / read */
  myPermission?: KnowledgePermission | null;
}

export interface KnowledgeFolder {
  id: string;
  kbId: string;
  parentId?: string | null;
  name: string;
  sortOrder: number;
  createdAt?: string;
}

export interface KnowledgeDocument {
  id: string;
  kbId: string;
  folderId?: string | null;
  title: string;
  fileName: string;
  mimeType: string;
  sizeBytes: number;
  status: KnowledgeDocStatus;
  failedStage?: KnowledgeFailedStage | null;
  errorMessage?: string | null;
  pageCount?: number | null;
  chunkCount: number;
  uploadedBy?: string | null;
  processedAt?: string | null;
  createdAt?: string;
  updatedAt?: string;
}

export interface KnowledgeChunk {
  id: string;
  docId: string;
  seq: number;
  content: string;
  pageNo?: number | null;
  section?: string | null;
  tokenCount: number;
}

export interface KnowledgeShare {
  id: string;
  kbId: string;
  granteeType: KnowledgeShareGrantee;
  granteeId: string;
  granteeName?: string | null;
  permission: KnowledgeSharePermission;
  grantedBy?: string | null;
  createdAt?: string;
}

export interface KnowledgeSearchHit {
  chunkId: string;
  docId: string;
  docTitle: string;
  kbId: string;
  pageNo?: number | null;
  section?: string | null;
  snippet: string;
  /** 余弦相似度 0–1 */
  score: number;
  /** 相对 API 路径（不含 baseURL），形如 /api/v1/knowledge/documents/{id}/file#page=N */
  previewUrl: string;
}

export interface KnowledgeSearchResult {
  hits: KnowledgeSearchHit[];
  total: number;
  tookMs: number;
}

export interface KnowledgeBaseListParams {
  scope?: KnowledgeBaseScope;
  keyword?: string;
  page?: number;
  pageSize?: number;
}

export interface KnowledgeDocumentListParams {
  folderId?: string;
  rootOnly?: boolean;
  status?: KnowledgeDocStatus;
  keyword?: string;
  page?: number;
  pageSize?: number;
}

export interface KnowledgeBaseCreateData {
  name: string;
  description?: string;
  visibility?: KnowledgeVisibility;
}

export interface KnowledgeFolderCreateData {
  name: string;
  parentId?: string | null;
  sortOrder?: number;
}

/** parentId 显式传 null = 移到根目录；不传 = 不改 */
export interface KnowledgeFolderUpdateData {
  name?: string;
  parentId?: string | null;
  sortOrder?: number;
}

/** folderId 显式传 null = 移到根目录；不传 = 不改 */
export interface KnowledgeDocumentUpdateData {
  title?: string;
  folderId?: string | null;
}

export interface KnowledgeShareCreateData {
  granteeType: KnowledgeShareGrantee;
  granteeId: string;
  permission?: KnowledgeSharePermission;
}

export interface KnowledgeSearchParams {
  query: string;
  kbIds?: string[];
  topK?: number;
}

const PREFIX = '/knowledge';

export const knowledgeApi = {
  // ---------- 知识库 ----------
  listBases: (params?: KnowledgeBaseListParams): Promise<PageResult<KnowledgeBase>> =>
    request.get(`${PREFIX}/bases`, {
      params: {
        scope: params?.scope,
        keyword: params?.keyword,
        page: params?.page,
        page_size: params?.pageSize,
      },
    }),
  createBase: (data: KnowledgeBaseCreateData): Promise<KnowledgeBase> => request.post(`${PREFIX}/bases`, data),
  getBase: (kbId: string): Promise<KnowledgeBase> => request.get(`${PREFIX}/bases/${kbId}`),
  updateBase: (kbId: string, data: Partial<KnowledgeBaseCreateData>): Promise<KnowledgeBase> =>
    request.patch(`${PREFIX}/bases/${kbId}`, data),
  deleteBase: (kbId: string): Promise<void> => request.delete(`${PREFIX}/bases/${kbId}`),

  // ---------- 目录 ----------
  listFolders: (kbId: string): Promise<KnowledgeFolder[]> => request.get(`${PREFIX}/bases/${kbId}/folders`),
  createFolder: (kbId: string, data: KnowledgeFolderCreateData): Promise<KnowledgeFolder> =>
    request.post(`${PREFIX}/bases/${kbId}/folders`, data),
  updateFolder: (folderId: string, data: KnowledgeFolderUpdateData): Promise<KnowledgeFolder> =>
    request.patch(`${PREFIX}/folders/${folderId}`, data),
  deleteFolder: (folderId: string): Promise<void> => request.delete(`${PREFIX}/folders/${folderId}`),

  // ---------- 文档 ----------
  listDocuments: (kbId: string, params?: KnowledgeDocumentListParams): Promise<PageResult<KnowledgeDocument>> =>
    request.get(`${PREFIX}/bases/${kbId}/documents`, {
      params: {
        folder_id: params?.folderId,
        root_only: params?.rootOnly,
        status: params?.status,
        keyword: params?.keyword,
        page: params?.page,
        page_size: params?.pageSize,
      },
    }),
  uploadDocument: (
    kbId: string,
    file: File,
    options?: { folderId?: string | null; title?: string },
  ): Promise<KnowledgeDocument> => {
    const formData = new FormData();
    formData.append('file', file);
    if (options?.folderId) formData.append('folder_id', options.folderId);
    if (options?.title) formData.append('title', options.title);
    return request.post(`${PREFIX}/bases/${kbId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  getDocument: (docId: string): Promise<KnowledgeDocument> => request.get(`${PREFIX}/documents/${docId}`),
  updateDocument: (docId: string, data: KnowledgeDocumentUpdateData): Promise<KnowledgeDocument> =>
    request.patch(`${PREFIX}/documents/${docId}`, data),
  deleteDocument: (docId: string): Promise<void> => request.delete(`${PREFIX}/documents/${docId}`),
  retryDocument: (docId: string): Promise<KnowledgeDocument> => request.post(`${PREFIX}/documents/${docId}/retry`),
  listChunks: (docId: string, params?: { page?: number; pageSize?: number }): Promise<PageResult<KnowledgeChunk>> =>
    request.get(`${PREFIX}/documents/${docId}/chunks`, {
      params: { page: params?.page, page_size: params?.pageSize },
    }),
  /**
   * 原件下载/预览的绝对地址（需带 Authorization 头请求，见 admin 端 fetchDocumentBlob）。
   * key 不对外暴露，所有访问经服务端租户 + 可见性校验。
   */
  documentFileUrl: (docId: string, options?: { download?: boolean }): string => {
    const base = `${getBaseURL()}${PREFIX}/documents/${docId}/file`;
    return options?.download ? `${base}?download=true` : base;
  },

  // ---------- 共享 ----------
  listShares: (kbId: string): Promise<KnowledgeShare[]> => request.get(`${PREFIX}/bases/${kbId}/shares`),
  addShare: (kbId: string, data: KnowledgeShareCreateData): Promise<KnowledgeShare> =>
    request.post(`${PREFIX}/bases/${kbId}/shares`, data),
  removeShare: (shareId: string): Promise<void> => request.delete(`${PREFIX}/shares/${shareId}`),

  // ---------- 检索 ----------
  search: (params: KnowledgeSearchParams): Promise<KnowledgeSearchResult> => request.post(`${PREFIX}/search`, params),
};
