/**
 * Modal / Drawer / Popconfirm 通用 Page Object
 *
 * 封装 Ant Design Modal、Drawer、Popconfirm 的通用操作。
 */
import { type Page, type Locator, expect } from '@playwright/test';

export class ModalHelper {
  constructor(private page: Page) {}

  // ==================== Modal ====================

  /** 获取最近打开的 Modal */
  getModal(): Locator {
    return this.page.locator('.ant-modal:visible').last();
  }

  /** 等待 Modal 出现 */
  async waitForModal(timeout = 5_000): Promise<Locator> {
    const modal = this.getModal();
    await expect(modal).toBeVisible({ timeout });
    return modal;
  }

  /** 点击 Modal 确认按钮 */
  async confirmModal(buttonText = '确定'): Promise<void> {
    const modal = await this.waitForModal();
    const btn = modal.locator('button').filter({ hasText: new RegExp(buttonText) }).first();
    await btn.click();
  }

  /** 点击 Modal 取消按钮 */
  async cancelModal(buttonText = '取消'): Promise<void> {
    const modal = await this.waitForModal();
    const btn = modal.locator('button').filter({ hasText: new RegExp(buttonText) }).first();
    await btn.click();
  }

  /** 关闭 Modal（点击 X） */
  async closeModal(): Promise<void> {
    const modal = this.getModal();
    const closeBtn = modal.locator('.ant-modal-close').first();
    await closeBtn.click();
  }

  /** 获取 Modal 标题文本 */
  async getModalTitle(): Promise<string> {
    const modal = this.getModal();
    const title = modal.locator('.ant-modal-title').first();
    return (await title.textContent()) ?? '';
  }

  /** 断言 Modal 标题 */
  async expectModalTitle(expected: string): Promise<void> {
    const title = await this.getModalTitle();
    expect(title).toContain(expected);
  }

  /** 在 Modal 中填写表单字段 */
  async fillModalField(label: string, value: string): Promise<void> {
    const modal = this.getModal();
    const formItem = modal.locator('.ant-form-item').filter({
      has: modal.locator('.ant-form-item-label').filter({ hasText: label }),
    });
    const input = formItem.locator('input, textarea').first();
    await input.clear();
    await input.fill(value);
  }

  /** 在 Modal 中选择 Select */
  async selectModalOption(label: string, optionText: string): Promise<void> {
    const modal = this.getModal();
    const formItem = modal.locator('.ant-form-item').filter({
      has: modal.locator('.ant-form-item-label').filter({ hasText: label }),
    });
    const select = formItem.locator('.ant-select').first();
    await select.click();
    await this.page.locator('.ant-select-dropdown:visible').locator(`text="${optionText}"`).click();
  }

  // ==================== Popconfirm ====================

  /** 确认 Popconfirm */
  async confirmPopconfirm(buttonText = '确定'): Promise<void> {
    const popconfirm = this.page.locator('.ant-popover:visible').last();
    await expect(popconfirm).toBeVisible({ timeout: 3_000 });
    const btn = popconfirm.locator('button').filter({ hasText: new RegExp(buttonText) }).first();
    await btn.click();
  }

  /** 取消 Popconfirm */
  async cancelPopconfirm(buttonText = '取消'): Promise<void> {
    const popconfirm = this.page.locator('.ant-popover:visible').last();
    const btn = popconfirm.locator('button').filter({ hasText: new RegExp(buttonText) }).first();
    await btn.click();
  }

  // ==================== Drawer ====================

  /** 获取最近打开的 Drawer */
  getDrawer(): Locator {
    return this.page.locator('.ant-drawer:visible').last();
  }

  /** 等待 Drawer 出现 */
  async waitForDrawer(timeout = 5_000): Promise<Locator> {
    const drawer = this.getDrawer();
    await expect(drawer).toBeVisible({ timeout });
    return drawer;
  }

  /** 关闭 Drawer（点击 X） */
  async closeDrawer(): Promise<void> {
    const drawer = this.getDrawer();
    const closeBtn = drawer.locator('.ant-drawer-close').first();
    await closeBtn.click();
  }

  /** 获取 Drawer 标题 */
  async getDrawerTitle(): Promise<string> {
    const drawer = this.getDrawer();
    const title = drawer.locator('.ant-drawer-title, .ant-drawer-header-title').first();
    return (await title.textContent()) ?? '';
  }

  /** 断言 Drawer 包含指定文本 */
  async expectDrawerContainsText(text: string): Promise<void> {
    const drawer = this.getDrawer();
    await expect(drawer).toContainText(text);
  }

  // ==================== Message ====================

  /** 断言成功消息 */
  async expectSuccessMessage(text?: string): Promise<void> {
    const msg = this.page.locator('.ant-message-success').first();
    await expect(msg).toBeVisible({ timeout: 5_000 });
    if (text) {
      await expect(msg).toContainText(text);
    }
  }

  /** 断言错误消息 */
  async expectErrorMessage(text?: string): Promise<void> {
    const msg = this.page.locator('.ant-message-error').first();
    await expect(msg).toBeVisible({ timeout: 5_000 });
    if (text) {
      await expect(msg).toContainText(text);
    }
  }
}
