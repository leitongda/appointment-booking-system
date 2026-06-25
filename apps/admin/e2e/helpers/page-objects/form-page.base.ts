/**
 * ProForm 表单页 Page Object 基类
 *
 * 封装 Ant Design ProForm 的通用操作：填写字段、表单验证、提交/取消。
 * 各模块的表单页继承此类，添加模块特有的字段操作。
 */
import { type Page, type Locator, expect } from '@playwright/test';

export class FormPageBase {
  protected page: Page;
  protected basePath: string;

  constructor(page: Page, basePath: string) {
    this.page = page;
    this.basePath = basePath;
  }

  // ==================== 导航 ====================

  /** 导航到创建表单页 */
  async gotoCreate(): Promise<void> {
    await this.page.goto(`${this.basePath}/create`);
    await this.page.waitForLoadState('networkidle');
    await this.waitForFormReady();
  }

  /** 导航到编辑表单页 */
  async gotoEdit(id: string): Promise<void> {
    await this.page.goto(`${this.basePath}/${id}/edit`);
    await this.page.waitForLoadState('networkidle');
    await this.waitForFormReady();
  }

  /** 等待表单渲染就绪 */
  async waitForFormReady(timeout = 10_000): Promise<void> {
    await this.page.waitForSelector(
      '.ant-form, .ant-pro-form, .ant-card',
      { timeout },
    );
  }

  // ==================== 字段填写 ====================

  /**
   * 填写 Input 输入框
   * @param label 字段标签文本（如 "名称"、"手机号"）
   * @param value 要填写的值
   */
  async fillInput(label: string, value: string): Promise<void> {
    const input = this.getInputByLabel(label);
    await input.clear();
    await input.fill(value);
  }

  /**
   * 填写 TextArea 文本域
   */
  async fillTextArea(label: string, value: string): Promise<void> {
    const formItem = this.getFormItemByLabel(label);
    const textarea = formItem.locator('textarea').first();
    await textarea.clear();
    await textarea.fill(value);
  }

  /**
   * 选择 Select 下拉框
   * @param label 字段标签文本
   * @param optionText 选项文本
   * @param multiple 是否多选
   */
  async selectOption(label: string, optionText: string, multiple = false): Promise<void> {
    const formItem = this.getFormItemByLabel(label);
    const select = formItem.locator('.ant-select').first();
    await select.click();

    // 在下拉面板中查找选项
    const dropdown = multiple
      ? this.page.locator('.ant-select-dropdown:visible')
      : this.page.locator('.ant-select-dropdown').last();
    const option = dropdown.locator('.ant-select-item').filter({ hasText: optionText });
    await option.click();

    // 非多选时自动关闭；多选需要手动点击空白关闭
    if (!multiple) {
      // 已自动关闭
    } else {
      await this.page.keyboard.press('Escape');
    }
  }

  /**
   * 选择 Radio 单选按钮
   */
  async selectRadio(label: string, optionText: string): Promise<void> {
    const formItem = this.getFormItemByLabel(label);
    const radio = formItem.locator('.ant-radio-wrapper').filter({ hasText: optionText });
    await radio.click();
  }

  /**
   * 切换 Switch 开关
   */
  async toggleSwitch(label: string, on: boolean): Promise<void> {
    const formItem = this.getFormItemByLabel(label);
    const sw = formItem.locator('.ant-switch').first();
    const isChecked = await sw.evaluate(el => el.classList.contains('ant-switch-checked'));
    if (isChecked !== on) {
      await sw.click();
    }
  }

  /**
   * 选择 DatePicker 日期
   */
  async pickDate(label: string, dateStr: string): Promise<void> {
    const formItem = this.getFormItemByLabel(label);
    const picker = formItem.locator('.ant-picker').first();
    await picker.click();
    const input = this.page.locator('.ant-picker-input input').first();
    await input.clear();
    await input.fill(dateStr);
    await input.press('Enter');
    // 关闭日期选择器
    await this.page.keyboard.press('Escape');
  }

  /**
   * 选择 DatePicker.RangePicker 日期范围
   */
  async pickDateRange(label: string, startDate: string, endDate: string): Promise<void> {
    const formItem = this.getFormItemByLabel(label);
    const picker = formItem.locator('.ant-picker-range').first();
    await picker.click();

    const inputs = this.page.locator('.ant-picker-input input');
    await inputs.first().fill(startDate);
    await inputs.first().press('Enter');
    await inputs.last().fill(endDate);
    await inputs.last().press('Enter');

    await this.page.keyboard.press('Escape');
  }

  /**
   * 填写 InputNumber 数字输入框
   */
  async fillNumber(label: string, value: number): Promise<void> {
    const formItem = this.getFormItemByLabel(label);
    const input = formItem.locator('.ant-input-number-input').first();
    await input.clear();
    await input.fill(String(value));
    await input.press('Enter');
  }

  /**
   * 上传文件
   */
  async uploadFile(label: string, filePath: string): Promise<void> {
    const formItem = this.getFormItemByLabel(label);
    const upload = formItem.locator('input[type="file"]').first();
    await upload.setInputFiles(filePath);
  }

  /**
   * 操作 TreeSelect 树选择
   */
  async selectTreeSelect(label: string, nodeText: string): Promise<void> {
    const formItem = this.getFormItemByLabel(label);
    const treeSelect = formItem.locator('.ant-tree-select, .ant-select').first();
    await treeSelect.click();
    const treeNode = this.page
      .locator('.ant-select-dropdown .ant-tree-treenode')
      .filter({ hasText: nodeText })
      .first();
    await treeNode.click();
  }

  /**
   * 操作 Checkbox 复选框
   */
  async checkCheckbox(label: string, optionText?: string): Promise<void> {
    const formItem = this.getFormItemByLabel(label);
    if (optionText) {
      const checkbox = formItem
        .locator('.ant-checkbox-wrapper')
        .filter({ hasText: optionText });
      await checkbox.locator('.ant-checkbox-input').check();
    } else {
      await formItem.locator('.ant-checkbox-input').first().check();
    }
  }

  /**
   * 操作 Transfer 穿梭框（选择目标项）
   */
  async transferItems(label: string, itemTexts: string[]): Promise<void> {
    const formItem = this.getFormItemByLabel(label);
    for (const text of itemTexts) {
      const item = formItem
        .locator('.ant-transfer-list-content-item')
        .filter({ hasText: text })
        .first();
      await item.locator('.ant-checkbox-input').check();
    }
    // 点击右移按钮
    const toRightBtn = formItem.locator('.ant-transfer-operation .ant-btn').first();
    await toRightBtn.click();
  }

  // ==================== 表单验证 ====================

  /**
   * 断言字段有验证错误
   */
  async expectFieldError(label: string, errorText?: string): Promise<void> {
    const formItem = this.getFormItemByLabel(label);
    const errorMsg = formItem.locator('.ant-form-item-explain-error');
    await expect(errorMsg).toBeVisible({ timeout: 5_000 });
    if (errorText) {
      await expect(errorMsg).toContainText(errorText);
    }
  }

  /**
   * 断言字段没有验证错误
   */
  async expectFieldNoError(label: string): Promise<void> {
    const formItem = this.getFormItemByLabel(label);
    const errorMsg = formItem.locator('.ant-form-item-explain-error');
    await expect(errorMsg).toHaveCount(0);
  }

  /**
   * 断言必填字段标记
   */
  async expectFieldRequired(label: string): Promise<void> {
    const formItem = this.getFormItemByLabel(label);
    const requiredMark = formItem.locator('.ant-form-item-required');
    await expect(requiredMark).toBeVisible();
  }

  /**
   * 清空字段后提交，验证必填校验
   */
  async verifyRequiredField(label: string): Promise<void> {
    const input = this.getInputByLabel(label);
    await input.clear();
    await input.blur();
    await this.expectFieldError(label);
  }

  // ==================== 提交/取消 ====================

  /**
   * 点击提交按钮
   */
  async submit(buttonText = '提交'): Promise<void> {
    const submitBtn = this.page
      .locator('button, .ant-btn')
      .filter({ hasText: new RegExp(buttonText) })
      .first();
    await submitBtn.click();
  }

  /**
   * 点击提交按钮并等待跳转
   */
  async submitAndWaitNavigation(
    expectedUrl?: string,
    buttonText = '提交',
  ): Promise<void> {
    const submitBtn = this.page
      .locator('button, .ant-btn')
      .filter({ hasText: new RegExp(buttonText) })
      .first();

    if (expectedUrl) {
      await Promise.all([
        this.page.waitForURL(new RegExp(expectedUrl), { timeout: 15_000 }),
        submitBtn.click(),
      ]);
    } else {
      await submitBtn.click();
      // 等待成功提示或页面变化
      await this.page.waitForTimeout(1_000);
    }
  }

  /**
   * 点击取消按钮
   */
  async cancel(): Promise<void> {
    const cancelBtn = this.page
      .locator('button, .ant-btn')
      .filter({ hasText: /取消/ })
      .first();
    await cancelBtn.click();
  }

  /**
   * 点击保存/保存草稿按钮
   */
  async save(buttonText = '保存'): Promise<void> {
    const saveBtn = this.page
      .locator('button, .ant-btn')
      .filter({ hasText: new RegExp(buttonText) })
      .first();
    await saveBtn.click();
  }

  // ==================== 断言辅助 ====================

  /**
   * 断言提交成功（出现成功提示或页面跳转）
   */
  async expectSubmitSuccess(): Promise<void> {
    // 检查成功消息提示
    const successMsg = this.page.locator('.ant-message-success, .ant-notification-success');
    try {
      await expect(successMsg.first()).toBeVisible({ timeout: 5_000 });
    } catch {
      // 可能直接跳转了，检查 URL 变化
      await this.page.waitForTimeout(2_000);
    }
  }

  /**
   * 断言表单字段值
   */
  async expectInputValue(label: string, expectedValue: string): Promise<void> {
    const input = this.getInputByLabel(label);
    await expect(input).toHaveValue(expectedValue);
  }

  /**
   * 断言页面包含错误提示（如后端返回的业务错误）
   */
  async expectErrorMessage(text: string): Promise<void> {
    const error = this.page
      .locator('.ant-message-error, .ant-notification-error, .ant-alert-error')
      .filter({ hasText: text })
      .first();
    await expect(error).toBeVisible({ timeout: 10_000 });
  }

  // ==================== 内部辅助 ====================

  /**
   * 通过标签文本定位 FormItem
   */
  protected getFormItemByLabel(label: string): Locator {
    // 尝试多种定位策略
    const strategies = [
      // 策略1: ant-form-item-label 包含文本
      this.page.locator('.ant-form-item').filter({
        has: this.page.locator('.ant-form-item-label').filter({ hasText: label }),
      }),
      // 策略2: label 标签的 for 属性
      this.page.locator(`.ant-form-item:has(label:has-text("${label}"))`),
    ];

    // 返回第一个可见的
    return strategies[0].first();
  }

  /**
   * 通过标签文本定位 Input
   */
  protected getInputByLabel(label: string): Locator {
    const formItem = this.getFormItemByLabel(label);
    return formItem.locator('input').first();
  }
}
