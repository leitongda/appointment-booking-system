/**
 * E2E 真实后端登录辅助
 *
 * 通过后端 API 直接获取 token，注入 localStorage 模拟登录态。
 * 支持多角色切换，避免每个测试都走 UI 登录流程。
 */
import { type Page, type BrowserContext } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/** 后端 API 基础地址 */
const API_BASE = process.env.E2E_API_BASE_URL || 'http://localhost:9000';

/** Auth 状态存储路径 */
const AUTH_DIR = path.resolve(__dirname, '../.auth');
const AUTH_FILE = path.join(AUTH_DIR, 'admin.json');

/** 测试账号配置 */
export const TEST_ACCOUNTS = {
  SUPER_ADMIN: {
    phone: process.env.E2E_ADMIN_PHONE || '13800000001',
    password: process.env.E2E_ADMIN_PASSWORD || 'admin123456',
  },
  STORE_ADMIN: {
    phone: process.env.E2E_STORE_ADMIN_PHONE || '13800000002',
    password: process.env.E2E_STORE_ADMIN_PASSWORD || 'admin123456',
  },
} as const;

export type RoleType = keyof typeof TEST_ACCOUNTS;

/** 登录响应结构 */
interface LoginResult {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  admin: Record<string, unknown>;
  store: Record<string, unknown> | null;
  stores: Record<string, unknown>[];
}

/**
 * 通过后端 API 登录获取 token
 */
export async function loginViaAPI(
  role: RoleType = 'SUPER_ADMIN',
): Promise<LoginResult> {
  const account = TEST_ACCOUNTS[role];
  const response = await fetch(`${API_BASE}/api/v1/admin/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      phone: account.phone,
      password: account.password,
    }),
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(
      `登录失败 [${role}] (HTTP ${response.status}): ${errText}`,
    );
  }

  const json = await response.json();
  // 后端统一响应格式: { code: 0, data: { accessToken, refreshToken, ... } }
  const data = json.data ?? json;
  return {
    accessToken: data.accessToken ?? data.access_token,
    refreshToken: data.refreshToken ?? data.refresh_token,
    expiresIn: data.expiresIn ?? data.expires_in ?? 7200,
    admin: data.admin,
    store: data.store,
    stores: data.stores ?? [],
  };
}

/**
 * 将登录态注入 Page 的 localStorage
 */
export async function injectAuthState(
  page: Page,
  loginResult: LoginResult,
): Promise<void> {
  const { accessToken, refreshToken, admin, store, stores } = loginResult;

  await page.addInitScript(
    ([token, refresh, adminInfo, storeInfo, storesList]) => {
      localStorage.setItem('hospital_token', JSON.stringify(token));
      localStorage.setItem('hospital_refresh_token', JSON.stringify(refresh));
      localStorage.setItem(
        'hospital_user_info',
        JSON.stringify(adminInfo),
      );
      localStorage.setItem('hospital_current_tenant_id', adminInfo.tenantId || 'tenant-1');
      if (storeInfo) {
        localStorage.setItem(
          'hospital_current_store',
          JSON.stringify(storeInfo),
        );
      }
      if (storesList?.length) {
        localStorage.setItem(
          'hospital_stores',
          JSON.stringify(storesList),
        );
      }
    },
    [accessToken, refreshToken, admin, store, stores],
  );
}

/**
 * 完整登录流程：API 获取 token -> 注入 page
 */
export async function setupAuthState(
  page: Page,
  role: RoleType = 'SUPER_ADMIN',
): Promise<LoginResult> {
  const result = await loginViaAPI(role);
  await injectAuthState(page, result);
  return result;
}

/**
 * 通过 UI 执行登录（测试登录页面本身时使用）
 */
export async function loginViaUI(
  page: Page,
  credentials = TEST_ACCOUNTS.SUPER_ADMIN,
): Promise<void> {
  await page.goto('/login');
  await page.waitForLoadState('networkidle');

  // 切换到账号密码登录 tab
  const accountTab = page.locator('.ant-tabs-tab').filter({ hasText: /账号|密码/ });
  if (await accountTab.isVisible()) {
    await accountTab.click();
  }

  // 填写手机号
  const phoneInput = page.locator('input[id*="phone"], input[placeholder*="手机号"]').first();
  await phoneInput.fill(credentials.phone);

  // 填写密码
  const passwordInput = page.locator('input[type="password"]').first();
  await passwordInput.fill(credentials.password);

  // 点击登录按钮
  const loginBtn = page.locator('button').filter({ hasText: /登录|登 录/ }).first();
  await loginBtn.click();

  // 等待跳转到 dashboard
  await page.waitForURL(/\/dashboard/, { timeout: 15_000 });
}

/**
 * 持久化登录态到文件（用于 Playwright storageState）
 * 可在 global setup 中调用一次，后续所有测试复用
 */
export async function persistAuthState(
  context: BrowserContext,
  role: RoleType = 'SUPER_ADMIN',
): Promise<string> {
  fs.mkdirSync(AUTH_DIR, { recursive: true });

  const result = await loginViaAPI(role);
  const page = await context.newPage();
  await injectAuthState(page, result);

  // 访问一个页面让 localStorage 生效
  await page.goto('about:blank');

  // 保存 storageState
  await context.storageState({ path: AUTH_FILE });
  await page.close();

  return AUTH_FILE;
}
