/**
 * ProTable 列表页 Page Object 基类
 *
 * 封装 Ant Design ProTable 的通用操作：搜索、筛选、分页、批量操作、导出等。
 * 各模块的列表页继承此类，添加模块特有的操作。
 */
import { type Page, type Locator, expect } from '@playwright/test';

export class ListPageBase {
  protected page: Page;
  protected basePath: string;

  constructor(page: Page, basePath: string) {
    this.page = page;
    this.basePath = basePath;
  }

  // ==================== 导航 ====================

  /** 导航到列表页并等待加载 */
  async goto(): Promise<void> {
    await this.page.goto(this.basePath);
    await this.page.waitForLoadState('networkidle');
    // 等待 ProTable 渲染
    await this.waitForTableReady();
  }

  /** 等待表格就绪（至少有表头或空状态） */
  async waitForTableReady(timeout = 10_000): Promise<void> {
    try {
      await this.page.waitForSelector(
        '.ant-table, .ant-pro-table, .ant-empty',
        { timeout },
      );
    } catch {
      // 页面可能没有表格（如统计页），不强制要求
    }
  }

  // ==================== 搜索 ====================

  /** 在搜索框中输入关键词并搜索 */
  async search(keyword: string, placeholder = '请输入'): Promise<void> {
    const searchInput = this.page
      .locator(
        `.ant-pro-table input[placeholder*="${placeholder}"], ` +
        `.ant-pro-table .ant-input-search input, ` +
        `input[placeholder*="搜索"], input[placeholder*="关键字"]`,
      )
      .first();

    if (await searchInput.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await searchInput.clear();
      await searchInput.fill(keyword);
      // 按回车或点击搜索按钮
      const searchBtn = this.page
        .locator('.ant-pro-table .ant-btn')
        .filter({ hasText: /查询|搜索/ })
        .first();
      if (await searchBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
        await searchBtn.click();
      } else {
        await searchInput.press('Enter');
      }
      await this.waitForTableReady();
    }
  }

  /** 点击重置按钮 */
  async resetSearch(): Promise<void> {
    const resetBtn = this.page
      .locator('.ant-pro-table .ant-btn')
      .filter({ hasText: /重置/ })
      .first();
    if (await resetBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await resetBtn.click();
      await this.waitForTableReady();
    }
  }

  // ==================== 筛选 ====================

  /** 通过 Select 下拉筛选 */
  async filterBySelect(label: string, value: string): Promise<void> {
    // 找到标签对应的 Select
    const formItem = this.page
      .locator('.ant-pro-table .ant-form-item')
      .filter({ hasText: label })
      .first();
    const select = formItem.locator('.ant-select').first();
    await select.click();
    // 选择选项
    await this.page.locator('.ant-select-dropdown').locator(`text="${value}"`).click();
    // 点击查询
    await this.clickQueryButton();
  }

  /** 通过 DatePicker 筛选日期范围 */
  async filterByDateRange(label: string, startDate: string, endDate: string): Promise<void> {
    const formItem = this.page
      .locator('.ant-pro-table .ant-form-item')
      .filter({ hasText: label })
      .first();
    const datePicker = formItem.locator('.ant-picker').first();
    await datePicker.click();
    // 填写开始日期
    const startInput = this.page.locator('.ant-picker-input input').first();
    await startInput.fill(startDate);
    await startInput.press('Enter');
    // 填写结束日期
    const endInput = this.page.locator('.ant-picker-input input').last();
    await endInput.fill(endDate);
    await endInput.press('Enter');
    // 关闭日期选择器
    await this.page.keyboard.press('Escape');
    await this.clickQueryButton();
  }

  /** 点击查询按钮 */
  async clickQueryButton(): Promise<void> {
    const queryBtn = this.page
      .locator('.ant-pro-table .ant-btn')
      .filter({ hasText: /查询|搜索/ })
      .first();
    if (await queryBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await queryBtn.click();
      await this.waitForTableReady();
    }
  }

  // ==================== 表格操作 ====================

  /** 获取表格行数 */
  async getRowCount(): Promise<number> {
    const rows = this.page.locator('.ant-table-tbody > tr.ant-table-row');
    return rows.count();
  }

  /** 获取表格第一行 */
  getFirstRow(): Locator {
    return this.page.locator('.ant-table-tbody > tr.ant-table-row').first();
  }

  /** 获取指定行的某个单元格文本 */
  async getCellText(rowIndex: number, colIndex: number): Promise<string> {
    const cell = this.page
      .locator('.ant-table-tbody > tr.ant-table-row')
      .nth(rowIndex)
      .locator('td')
      .nth(colIndex);
    return (await cell.textContent()) ?? '';
  }

  /** 点击表格行中的操作按钮 */
  async clickRowAction(
    rowIndex: number,
    actionText: string,
  ): Promise<void> {
    const row = this.page
      .locator('.ant-table-tbody > tr.ant-table-row')
      .nth(rowIndex);

    // 先尝试直接点击链接
    const link = row.locator('a').filter({ hasText: actionText });
    if (await link.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await link.click();
      return;
    }

    // 尝试点击按钮
    const btn = row.locator('button, .ant-btn').filter({ hasText: actionText });
    if (await btn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await btn.click();
      return;
    }

    // 尝试操作列的下拉菜单（更多操作）
    const moreBtn = row.locator('.ant-dropdown-trigger, .ant-btn').filter({ hasText: /更多|操作/ });
    if (await moreBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await moreBtn.click();
      await this.page.locator('.ant-dropdown').locator(`text="${actionText}"`).click();
    }
  }

  /** 点击第一行的操作按钮 */
  async clickFirstRowAction(actionText: string): Promise<void> {
    await this.clickRowAction(0, actionText);
  }

  // ==================== 分页 ====================

  /** 获取总条数（从分页组件读取） */
  async getTotalCount(): Promise<number> {
    const pagination = this.page.locator('.ant-pagination-total-text');
    if (await pagination.isVisible({ timeout: 3_000 }).catch(() => false)) {
      const text = (await pagination.textContent()) ?? '';
      const match = text.match(/(\d+)/);
      return match ? parseInt(match[1], 10) : 0;
    }
    return 0;
  }

  /** 翻到下一页 */
  async goToNextPage(): Promise<void> {
    const nextBtn = this.page.locator('.ant-pagination-next').first();
    if (await nextBtn.isEnabled()) {
      await nextBtn.click();
      await this.waitForTableReady();
    }
  }

  /** 翻到指定页 */
  async goToPage(pageNum: number): Promise<void> {
    const pageInput = this.page.locator('.ant-pagination-options-quick-jumper input').first();
    if (await pageInput.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await pageInput.fill(String(pageNum));
      await pageInput.press('Enter');
      await this.waitForTableReady();
    }
  }

  /** 修改每页条数 */
  async changePageSize(size: number): Promise<void> {
    const sizeSelector = this.page.locator('.ant-pagination-options .ant-select').first();
    if (await sizeSelector.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await sizeSelector.click();
      await this.page
        .locator('.ant-select-dropdown')
        .locator(`text="${size} 条/页"`)
        .click();
      await this.waitForTableReady();
    }
  }

  // ==================== 批量操作 ====================

  /** 选择表格行（通过 Checkbox） */
  async selectRows(...rowIndices: number[]): Promise<void> {
    for (const idx of rowIndices) {
      const checkbox = this.page
        .locator('.ant-table-tbody > tr.ant-table-row')
        .nth(idx)
        .locator('.ant-checkbox-input')
        .first();
      await checkbox.check();
    }
  }

  /** 全选 */
  async selectAll(): Promise<void> {
    const headerCheckbox = this.page
      .locator('.ant-table-thead .ant-checkbox-input')
      .first();
    await headerCheckbox.check();
  }

  /** 取消全选 */
  async deselectAll(): Promise<void> {
    const headerCheckbox = this.page
      .locator('.ant-table-thead .ant-checkbox-input')
      .first();
    if (await headerCheckbox.isChecked()) {
      await headerCheckbox.uncheck();
    }
  }

  /** 点击批量操作按钮（在表格上方的工具栏） */
  async clickBatchAction(actionText: string): Promise<void> {
    const btn = this.page
      .locator('.ant-pro-table .ant-btn, .ant-table-toolbar .ant-btn')
      .filter({ hasText: actionText })
      .first();
    await btn.click();
  }

  // ==================== 创建 ====================

  /** 点击新建按钮 */
  async clickCreate(): Promise<void> {
    const createBtn = this.page
      .locator('button, .ant-btn')
      .filter({ hasText: /新建|添加|创建|新增/ })
      .first();
    await createBtn.click();
  }

  // ==================== 导出 ====================

  /** 点击导出按钮 */
  async clickExport(): Promise<void> {
    const exportBtn = this.page
      .locator('button, .ant-btn')
      .filter({ hasText: /导出|下载/ })
      .first();
    await exportBtn.click();
  }

  // ==================== 断言辅助 ====================

  /** 断言表格不为空 */
  async expectTableNotEmpty(): Promise<void> {
    const rows = this.page.locator('.ant-table-tbody > tr.ant-table-row');
    await expect(rows.first()).toBeVisible({ timeout: 10_000 });
    expect(await rows.count()).toBeGreaterThan(0);
  }

  /** 断言表格为空或显示空状态 */
  async expectTableEmpty(): Promise<void> {
    const emptyState = this.page.locator('.ant-empty');
    const rows = this.page.locator('.ant-table-tbody > tr.ant-table-row');
    const isEmpty = await emptyState.isVisible({ timeout: 5_000 }).catch(() => false);
    const rowCount = await rows.count();
    expect(isEmpty || rowCount === 0).toBeTruthy();
  }

  /** 断言某行包含指定文本 */
  async expectRowContainsText(text: string): Promise<void> {
    const row = this.page
      .locator('.ant-table-tbody > tr.ant-table-row')
      .filter({ hasText: text })
      .first();
    await expect(row).toBeVisible({ timeout: 10_000 });
  }

  /** 断言某行不存在指定文本 */
  async expectRowNotContainsText(text: string): Promise<void> {
    const row = this.page
      .locator('.ant-table-tbody > tr.ant-table-row')
      .filter({ hasText: text });
    await expect(row).toHaveCount(0);
  }

  /** 断言分页总数 */
  async expectTotalCount(expected: number): Promise<void> {
    const total = await this.getTotalCount();
    expect(total).toBe(expected);
  }

  /** 断言页面 URL 包含指定路径 */
  async expectUrlContains(path: string): Promise<void> {
    await expect(this.page).toHaveURL(new RegExp(path));
  }
}
