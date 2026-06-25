/**
 * 拖拽操作 Page Object
 *
 * 封装 @dnd-kit、HTML5 Drag API、鼠标拖拽序列。
 * 用于排班日历拖拽、低代码画布拖拽、列表排序等场景。
 */
import { type Page, type Locator } from '@playwright/test';

export class DragDropHelper {
  constructor(private page: Page) {}

  /**
   * 模拟 HTML5 Drag & Drop（适用于 @dnd-kit 和标准拖拽）
   *
   * @param source 拖拽源元素选择器
   * @param target 拖拽目标元素选择器
   * @param options 配置项
   */
  async dragTo(
    source: string | Locator,
    target: string | Locator,
    options: { steps?: number; delay?: number } = {},
  ): Promise<void> {
    const { steps = 10, delay = 0 } = options;
    const sourceEl = typeof source === 'string' ? this.page.locator(source).first() : source;
    const targetEl = typeof target === 'string' ? this.page.locator(target).first() : target;

    const sourceBox = await sourceEl.boundingBox();
    const targetBox = await targetEl.boundingBox();
    if (!sourceBox || !targetBox) throw new Error('拖拽源或目标元素不可见');

    const srcX = sourceBox.x + sourceBox.width / 2;
    const srcY = sourceBox.y + sourceBox.height / 2;
    const tgtX = targetBox.x + targetBox.width / 2;
    const tgtY = targetBox.y + targetBox.height / 2;

    // 使用 Playwright 原生拖拽 API
    await this.page.mouse.move(srcX, srcY);
    await this.page.mouse.down();
    if (delay > 0) await this.page.waitForTimeout(delay);

    // 分步移动（触发 dragover 事件需要多次 mousemove）
    for (let i = 1; i <= steps; i++) {
      const x = srcX + ((tgtX - srcX) * i) / steps;
      const y = srcY + ((tgtY - srcY) * i) / steps;
      await this.page.mouse.move(x, y);
    }

    await this.page.mouse.up();
  }

  /**
   * 使用 Playwright 内置 dragTo 方法（适用于支持 dataTransfer 的场景）
   */
  async dragToNative(
    source: string | Locator,
    target: string | Locator,
  ): Promise<void> {
    const sourceEl = typeof source === 'string' ? this.page.locator(source).first() : source;
    const targetEl = typeof target === 'string' ? this.page.locator(target).first() : target;
    await sourceEl.dragTo(targetEl);
  }

  /**
   * 通过 dispatchEvent 模拟拖拽（适用于 @dnd-kit 等需要 pointer 事件的库）
   */
  async dragToByDispatch(
    source: string | Locator,
    target: string | Locator,
  ): Promise<void> {
    const sourceEl = typeof source === 'string' ? this.page.locator(source).first() : source;
    const targetEl = typeof target === 'string' ? this.page.locator(target).first() : target;

    const sourceBox = await sourceEl.boundingBox();
    const targetBox = await targetEl.boundingBox();
    if (!sourceBox || !targetBox) throw new Error('拖拽源或目标元素不可见');

    const srcX = sourceBox.x + sourceBox.width / 2;
    const srcY = sourceBox.y + sourceBox.height / 2;
    const tgtX = targetBox.x + targetBox.width / 2;
    const tgtY = targetBox.y + targetBox.height / 2;

    // pointerdown on source
    await sourceEl.dispatchEvent('pointerdown', {
      clientX: srcX, clientY: srcY, pointerId: 1, pointerType: 'mouse', button: 0, buttons: 1,
    });

    // pointermove to target
    await this.page.mouse.move(tgtX, tgtY);

    // pointerup on target
    await targetEl.dispatchEvent('pointerup', {
      clientX: tgtX, clientY: tgtY, pointerId: 1, pointerType: 'mouse', button: 0, buttons: 0,
    });
  }

  /**
   * 排序操作：将列表中的某项从一个位置拖到另一个位置
   * 适用于 @dnd-kit/sortable 场景
   */
  async sortItem(
    itemSelector: string,
    fromIndex: number,
    toIndex: number,
  ): Promise<void> {
    const items = this.page.locator(itemSelector);
    const source = items.nth(fromIndex);
    const target = items.nth(toIndex);
    await this.dragTo(source, target, { steps: 15, delay: 200 });
  }
}
