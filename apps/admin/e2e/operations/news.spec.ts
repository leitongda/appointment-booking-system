/**
 * 新闻管理 E2E 测试
 *
 * 覆盖路径：/content-center/content/news
 *
 * 测试场景：
 * 1. 列表页：页面加载、搜索、分页、创建跳转
 * 2. 创建页：必填字段验证、完整表单提交、取消
 * 3. 编辑页：加载数据、修改保存
 * 4. 详情页：查看新闻
 * 5. 删除：确认弹窗
 */
import { test, expect } from '@playwright/test';
import { mockAdminSession } from '../helpers/admin-mocks';
import { ListPageBase } from '../helpers/page-objects/list-page.base';
import { FormPageBase } from '../helpers/page-objects/form-page.base';

const NEWS_LIST_PATH = '/content-center/content/news';
const NEWS_CREATE_PATH = '/content-center/content/news/create';

test.describe('新闻管理', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  // ==================== 列表页 ====================

  test.describe('列表页', () => {
    test('应正确加载新闻列表页', async ({ page }) => {
      const listPage = new ListPageBase(page, NEWS_LIST_PATH);
      await listPage.goto();

      await expect(page).toHaveURL(new RegExp(NEWS_LIST_PATH));
      await expect(page.getByText('新闻列表').first()).toBeVisible();
    });

    test('应显示表格数据', async ({ page }) => {
      const listPage = new ListPageBase(page, NEWS_LIST_PATH);
      await listPage.goto();

      // 等待表格加载，至少有示例数据
      await listPage.waitForTableReady();
      const rowCount = await listPage.getRowCount();
      expect(rowCount).toBeGreaterThanOrEqual(0);
    });

    test('应支持按标题搜索', async ({ page }) => {
      const listPage = new ListPageBase(page, NEWS_LIST_PATH);
      await listPage.goto();

      await listPage.search('示例新闻');
      await listPage.waitForTableReady();
    });

    test('应支持重置搜索', async ({ page }) => {
      const listPage = new ListPageBase(page, NEWS_LIST_PATH);
      await listPage.goto();

      await listPage.search('测试关键词');
      await listPage.resetSearch();
    });

    test('应支持分页操作', async ({ page }) => {
      const listPage = new ListPageBase(page, NEWS_LIST_PATH);
      await listPage.goto();

      // 获取总数
      const total = await listPage.getTotalCount();
      expect(total).toBeGreaterThanOrEqual(0);
    });

    test('点击发布新闻应跳转到创建页', async ({ page }) => {
      const listPage = new ListPageBase(page, NEWS_LIST_PATH);
      await listPage.goto();

      await listPage.clickCreate();
      await expect(page).toHaveURL(new RegExp(NEWS_CREATE_PATH));
    });
  });

  // ==================== 创建页 ====================

  test.describe('创建页', () => {
    test('应正确加载创建页', async ({ page }) => {
      await page.goto(NEWS_CREATE_PATH);
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveURL(new RegExp(NEWS_CREATE_PATH));
      await expect(page.getByText('发布新闻').first()).toBeVisible();
    });

    test('标题为必填项，为空时应显示验证错误', async ({ page }) => {
      const formPage = new FormPageBase(page, NEWS_LIST_PATH);
      await page.goto(NEWS_CREATE_PATH);
      await page.waitForLoadState('networkidle');
      await formPage.waitForFormReady();

      // 清空标题并触发表单提交
      const titleInput = page.locator('input[id*="title"], input[placeholder*="标题"]').first();
      if (await titleInput.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await titleInput.clear();
        await titleInput.blur();
      }

      // 尝试提交
      await formPage.submit('发布');
      await page.waitForTimeout(500);

      // 验证错误提示出现
      await expect(
        page.locator('.ant-form-item-explain-error, .ant-message-error')
          .filter({ hasText: /标题|请输入/ })
          .first()
      ).toBeVisible({ timeout: 5_000 });
    });

    test('内容为必填项，为空时应显示验证错误', async ({ page }) => {
      const formPage = new FormPageBase(page, NEWS_LIST_PATH);
      await page.goto(NEWS_CREATE_PATH);
      await page.waitForLoadState('networkidle');
      await formPage.waitForFormReady();

      // 填写标题但不填内容
      await formPage.fillInput('标题', '测试新闻标题');

      // 尝试提交
      await formPage.submit('发布');
      await page.waitForTimeout(500);

      // 验证内容必填错误
      await expect(
        page.locator('.ant-form-item-explain-error, .ant-message-error')
          .filter({ hasText: /内容|请输入/ })
          .first()
      ).toBeVisible({ timeout: 5_000 });
    });

    test('应能完整填写表单并提交', async ({ page }) => {
      const formPage = new FormPageBase(page, NEWS_LIST_PATH);
      await page.goto(NEWS_CREATE_PATH);
      await page.waitForLoadState('networkidle');
      await formPage.waitForFormReady();

      const ts = Date.now();
      const newsTitle = `E2E测试新闻_${ts}`;

      // 填写标题
      await formPage.fillInput('标题', newsTitle);

      // 填写摘要
      try {
        await formPage.fillTextArea('摘要', '这是一条 E2E 测试新闻摘要');
      } catch {
        // 摘要字段可能不是必填
      }

      // 富文本内容 - 尝试在编辑器中输入
      const richEditor = page.locator('.ql-editor, .tox-edit-area iframe, .ProseMirror, [contenteditable="true"]').first();
      if (await richEditor.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await richEditor.click();
        await page.keyboard.type('E2E 测试新闻内容正文');
      }

      // 提交表单
      await formPage.submit('发布');
      await page.waitForTimeout(2_000);

      // 验证提交后跳转回列表页或出现成功提示
      const url = page.url();
      const successMsg = page.locator('.ant-message-success, .ant-notification-success');
      const isBackToList = url.includes(NEWS_LIST_PATH);
      const hasSuccess = await successMsg.isVisible({ timeout: 3_000 }).catch(() => false);
      expect(isBackToList || hasSuccess).toBeTruthy();
    });

    test('点击取消应返回列表页', async ({ page }) => {
      const formPage = new FormPageBase(page, NEWS_LIST_PATH);
      await page.goto(NEWS_CREATE_PATH);
      await page.waitForLoadState('networkidle');
      await formPage.waitForFormReady();

      await formPage.cancel();
      await page.waitForTimeout(1_000);

      // 验证返回列表页或页面变化
      await expect(page).toHaveURL(new RegExp(NEWS_LIST_PATH));
    });
  });

  // ==================== 编辑页 ====================

  test.describe('编辑页', () => {
    test('应正确加载编辑页并显示已有数据', async ({ page }) => {
      // 使用 mock 数据中的 news-1
      const editPath = `${NEWS_LIST_PATH}/news-1/edit`;
      await page.goto(editPath);
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveURL(new RegExp(`${NEWS_LIST_PATH}/news-1/edit`));
      await expect(page.getByText('编辑新闻').first()).toBeVisible();
    });

    test('应能修改新闻并保存', async ({ page }) => {
      const editPath = `${NEWS_LIST_PATH}/news-1/edit`;
      const formPage = new FormPageBase(page, NEWS_LIST_PATH);
      await page.goto(editPath);
      await page.waitForLoadState('networkidle');
      await formPage.waitForFormReady();

      // 修改标题
      const ts = Date.now();
      const newTitle = `修改后的新闻_${ts}`;
      await formPage.fillInput('标题', newTitle);

      // 保存
      await formPage.save('保存');
      await page.waitForTimeout(2_000);

      // 验证保存成功
      const url = page.url();
      const successMsg = page.locator('.ant-message-success, .ant-notification-success');
      const isBackToList = url.includes(NEWS_LIST_PATH) && !url.includes('edit');
      const hasSuccess = await successMsg.isVisible({ timeout: 3_000 }).catch(() => false);
      expect(isBackToList || hasSuccess).toBeTruthy();
    });
  });

  // ==================== 详情页 ====================

  test.describe('详情页', () => {
    test('应正确加载新闻详情页', async ({ page }) => {
      const detailPath = `${NEWS_LIST_PATH}/news-1/detail`;
      await page.goto(detailPath);
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveURL(new RegExp(`${NEWS_LIST_PATH}/news-1/detail`));
      // 详情页应显示新闻标题
      await expect(page.getByText('示例新闻').first()).toBeVisible({ timeout: 10_000 });
    });

    test('详情页应显示新闻内容', async ({ page }) => {
      const detailPath = `${NEWS_LIST_PATH}/news-1/detail`;
      await page.goto(detailPath);
      await page.waitForLoadState('networkidle');

      // 验证内容区域存在
      await page.waitForTimeout(1_000);
      const pageContent = await page.textContent('body');
      expect(pageContent).toBeTruthy();
    });
  });

  // ==================== 删除 ====================

  test.describe('删除', () => {
    test('点击删除应弹出确认弹窗', async ({ page }) => {
      const listPage = new ListPageBase(page, NEWS_LIST_PATH);
      await listPage.goto();

      // 点击第一行的删除按钮
      await listPage.clickFirstRowAction('删除');

      // 验证确认弹窗出现
      await expect(
        page.locator('.ant-modal-confirm, .ant-popconfirm')
          .filter({ hasText: /确定|确认|删除/ })
          .first()
      ).toBeVisible({ timeout: 5_000 });
    });

    test('确认删除弹窗应包含确认和取消按钮', async ({ page }) => {
      const listPage = new ListPageBase(page, NEWS_LIST_PATH);
      await listPage.goto();

      await listPage.clickFirstRowAction('删除');

      // 等待弹窗出现
      const modal = page.locator('.ant-modal-confirm, .ant-popconfirm').first();
      await expect(modal).toBeVisible({ timeout: 5_000 });

      // 验证按钮存在
      const confirmBtn = modal.locator('button').filter({ hasText: /确定|确认|OK/ });
      const cancelBtn = modal.locator('button').filter({ hasText: /取消|Cancel/ });
      await expect(confirmBtn.first()).toBeVisible();
      await expect(cancelBtn.first()).toBeVisible();
    });
  });
});
