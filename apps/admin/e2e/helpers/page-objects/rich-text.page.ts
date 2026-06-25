/**
 * 富文本编辑器 Page Object
 *
 * 封装 @wangeditor/editor 的通用操作。
 * 用于新闻、公告、科室介绍、医生简介、邮件模板等表单。
 */
import { type Page, type Locator, expect } from '@playwright/test';

export class RichTextHelper {
  constructor(private page: Page) {}

  /**
   * 获取富文本编辑器容器
   * wangEditor 使用 .w-e-text-container 作为编辑区域
   */
  getEditor(containerSelector = '.w-e-text-container'): Locator {
    return this.page.locator(containerSelector).first();
  }

  /**
   * 获取编辑器的可编辑区域
   */
  getEditableArea(): Locator {
    return this.page.locator('.w-e-text-container [contenteditable="true"]').first();
  }

  /**
   * 在富文本编辑器中输入文本
   */
  async typeText(text: string, containerSelector?: string): Promise<void> {
    const editable = this.getEditableArea();
    await editable.click();
    await editable.type(text);
  }

  /**
   * 清空编辑器内容
   */
  async clear(containerSelector?: string): Promise<void> {
    const editable = this.getEditableArea();
    await editable.click();
    // 全选并删除
    await this.page.keyboard.press('Meta+a');
    await this.page.keyboard.press('Backspace');
  }

  /**
   * 设置编辑器 HTML 内容（通过 clipboard）
   */
  async setHtml(html: string): Promise<void> {
    const editable = this.getEditableArea();
    await editable.click();
    // 全选现有内容
    await this.page.keyboard.press('Meta+a');
    // 通过 evaluate 直接设置 innerHTML
    await editable.evaluate((el, content) => {
      el.innerHTML = content;
      // 触发 input 事件让编辑器感知变化
      el.dispatchEvent(new Event('input', { bubbles: true }));
    }, html);
  }

  /**
   * 获取编辑器当前 HTML 内容
   */
  async getHtml(): Promise<string> {
    const editable = this.getEditableArea();
    return (await editable.innerHTML()) ?? '';
  }

  /**
   * 获取编辑器当前纯文本内容
   */
  async getText(): Promise<string> {
    const editable = this.getEditableArea();
    return (await editable.textContent()) ?? '';
  }

  /**
   * 点击工具栏按钮
   * @param tooltip 按钮的 tooltip 文本（如"粗体"、"斜体"、"链接"）
   */
  async clickToolbarButton(tooltip: string): Promise<void> {
    const toolbar = this.page.locator('.w-e-bar').first();
    const btn = toolbar.locator(`[data-tooltip="${tooltip}"], button[title="${tooltip}"]`).first();
    if (await btn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await btn.click();
    } else {
      // 尝试通过文本匹配
      const btnByText = toolbar.locator('button, .w-e-bar-item').filter({ hasText: tooltip }).first();
      await btnByText.click();
    }
  }

  /**
   * 插入图片（通过工具栏）
   */
  async insertImage(imageUrl: string): Promise<void> {
    await this.clickToolbarButton('图片');
    // 等待图片插入弹窗
    const modal = this.page.locator('.ant-modal:visible, .w-e-image-picker').first();
    await expect(modal).toBeVisible({ timeout: 3_000 });
    // 填写图片 URL
    const urlInput = modal.locator('input[placeholder*="图片"], input[placeholder*="URL"], input[placeholder*="http"]').first();
    if (await urlInput.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await urlInput.fill(imageUrl);
    }
    // 确认
    const confirmBtn = modal.locator('button').filter({ hasText: /确定|确认|插入/ }).first();
    if (await confirmBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await confirmBtn.click();
    }
  }

  /**
   * 插入链接
   */
  async insertLink(url: string, text?: string): Promise<void> {
    await this.clickToolbarButton('链接');
    const modal = this.page.locator('.ant-modal:visible, .w-e-link-picker').first();
    await expect(modal).toBeVisible({ timeout: 3_000 });
    // 填写链接文本
    if (text) {
      const textInput = modal.locator('input[placeholder*="文本"], input[placeholder*="文字"]').first();
      if (await textInput.isVisible({ timeout: 1_000 }).catch(() => false)) {
        await textInput.fill(text);
      }
    }
    // 填写链接 URL
    const urlInput = modal.locator('input[placeholder*="链接"], input[placeholder*="URL"], input[placeholder*="http"]').first();
    if (await urlInput.isVisible({ timeout: 1_000 }).catch(() => false)) {
      await urlInput.fill(url);
    }
    // 确认
    const confirmBtn = modal.locator('button').filter({ hasText: /确定|确认|插入/ }).first();
    if (await confirmBtn.isVisible({ timeout: 1_000 }).catch(() => false)) {
      await confirmBtn.click();
    }
  }

  /**
   * 断言编辑器包含指定文本
   */
  async expectContainsText(text: string): Promise<void> {
    const editable = this.getEditableArea();
    await expect(editable).toContainText(text);
  }

  /**
   * 断言编辑器不为空
   */
  async expectNotEmpty(): Promise<void> {
    const html = await this.getHtml();
    expect(html.trim().length).toBeGreaterThan(0);
  }
}
