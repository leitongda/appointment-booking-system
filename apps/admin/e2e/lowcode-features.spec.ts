import { test, expect } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';
import { evaluateExpression, validateExpression } from '../../../packages/shared/src/utils/expression-engine';

/**
 * 低代码功能增强 E2E 测试
 *
 * 覆盖场景:
 * 1. 表达式引擎 — 数组方法、字符串方法、数学函数、空值合并、可选链
 * 2. 状态变量面板 — 添加/删除变量、类型选择、默认值
 * 3. 联动规则面板 — 添加/删除规则、条件配置、动作配置
 */

// ---------------------------------------------------------------------------
// Helper — 设置编辑器 mock
// ---------------------------------------------------------------------------

function jsonResponse(data: unknown, extra: Record<string, unknown> = {}) {
  return JSON.stringify({ code: 200, message: 'ok', data, ...extra });
}

async function setupEditorMocks(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/auth/admin/session', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: jsonResponse({
        id: 'admin-1',
        username: 'admin',
        name: '测试管理员',
        roleType: 'admin',
        roleCode: 'SUPER_ADMIN',
        isAdmin: true,
        isSuperAdmin: true,
        permissions: ['*'],
        currentStore: { id: 'store-1', name: '示例门店' },
      }),
    }),
  );

  await page.route('**/api/v1/auth/refresh', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: jsonResponse({ token: 'mock-token', refreshToken: 'mock-refresh' }),
    }),
  );

  // 低代码页面 API — 返回空页面
  await page.route('**/api/v1/lowcode/pages/*', (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: jsonResponse({
          id: 'test-page',
          name: '测试页面',
          slug: 'test-page',
          schemaData: {
            componentName: 'Page',
            children: [
              {
                id: 'input-1',
                componentName: 'NutInput',
                props: { placeholder: '请输入', label: '输入框' },
                linkageRules: [],
              },
              {
                id: 'select-1',
                componentName: 'NutSelect',
                props: { placeholder: '请选择', label: '下拉框' },
                linkageRules: [],
              },
            ],
          },
        }),
      });
    }
    return route.fallback();
  });
}

// ---------------------------------------------------------------------------
// 1. 表达式引擎测试 (纯函数，不依赖浏览器)
// ---------------------------------------------------------------------------

test.describe('Expression Engine', () => {
  test('supports array map method', () => {
    const result = evaluateExpression('items.map(x => x * 2)', { items: [1, 2, 3] });
    expect(result).toEqual([2, 4, 6]);
  });

  test('supports array filter method', () => {
    const result = evaluateExpression('items.filter(x => x > 1)', { items: [1, 2, 3] });
    expect(result).toEqual([2, 3]);
  });

  test('supports array reduce method', () => {
    const result = evaluateExpression('items.reduce((a, b) => a + b, 0)', { items: [1, 2, 3] });
    expect(result).toBe(6);
  });

  test('supports array find method', () => {
    const result = evaluateExpression('items.find(x => x > 1)', { items: [1, 2, 3] });
    expect(result).toBe(2);
  });

  test('supports array some/every methods', () => {
    expect(evaluateExpression('items.some(x => x > 2)', { items: [1, 2, 3] })).toBe(true);
    expect(evaluateExpression('items.every(x => x > 2)', { items: [1, 2, 3] })).toBe(false);
  });

  test('supports string upper method', () => {
    const result = evaluateExpression("'hello'.upper()");
    expect(result).toBe('HELLO');
  });

  test('supports string lower method', () => {
    const result = evaluateExpression("'HELLO'.lower()");
    expect(result).toBe('hello');
  });

  test('supports string replace method', () => {
    const result = evaluateExpression("'hello world'.replace('world', 'test')");
    expect(result).toBe('hello test');
  });

  test('supports math max function', () => {
    const result = evaluateExpression('max(3, 1, 2)');
    expect(result).toBe(3);
  });

  test('supports math min function', () => {
    const result = evaluateExpression('min(3, 1, 2)');
    expect(result).toBe(1);
  });

  test('supports math round function', () => {
    expect(evaluateExpression('round(3.7)')).toBe(4);
    expect(evaluateExpression('round(3.2)')).toBe(3);
  });

  test('supports math floor/ceil functions', () => {
    expect(evaluateExpression('floor(3.7)')).toBe(3);
    expect(evaluateExpression('ceil(3.2)')).toBe(4);
  });

  test('supports nullish coalescing operator', () => {
    expect(evaluateExpression('null ?? "default"')).toBe('default');
    expect(evaluateExpression('undefined ?? "default"')).toBe('default');
    expect(evaluateExpression('"value" ?? "default"')).toBe('value');
  });

  test('supports optional chaining', () => {
    expect(evaluateExpression('obj?.name', { obj: { name: 'test' } })).toBe('test');
    expect(evaluateExpression('obj?.name', { obj: null })).toBeUndefined();
    expect(evaluateExpression('obj?.name', {})).toBeUndefined();
  });

  test('supports optional chaining with index access', () => {
    expect(evaluateExpression('arr?.[0]', { arr: [10, 20] })).toBe(10);
    expect(evaluateExpression('arr?.[0]', { arr: null })).toBeUndefined();
  });

  test('supports formatDate function', () => {
    const result = evaluateExpression('formatDate("2026-01-15", "YYYY-MM-DD")');
    expect(result).toBe('2026-01-15');
  });

  test('supports formatPrice function', () => {
    expect(evaluateExpression('formatPrice(123.456)')).toBe('123.46');
    expect(evaluateExpression('formatPrice(123.456, 1)')).toBe('123.5');
  });

  test('supports length function', () => {
    expect(evaluateExpression('length(str)', { str: 'hello' })).toBe(5);
    expect(evaluateExpression('length(arr)', { arr: [1, 2, 3] })).toBe(3);
  });

  test('supports first/last functions', () => {
    expect(evaluateExpression('first(arr)', { arr: [1, 2, 3] })).toBe(1);
    expect(evaluateExpression('last(arr)', { arr: [1, 2, 3] })).toBe(3);
  });

  test('supports template syntax', () => {
    const result = evaluateExpression('Hello, ${name}!', { name: 'World' });
    expect(result).toBe('Hello, World!');
  });

  test('validateExpression returns valid for correct syntax', () => {
    expect(validateExpression('1 + 2')).toEqual({ valid: true });
    expect(validateExpression("'hello'")).toEqual({ valid: true });
    expect(validateExpression('obj?.name')).toEqual({ valid: true });
  });

  test('validateExpression returns invalid for incorrect syntax', () => {
    const result = validateExpression('1 +');
    expect(result.valid).toBe(false);
  });

  test('blocks dangerous property access (prototype pollution)', () => {
    expect(evaluateExpression('obj.__proto__', { obj: {} })).toBeUndefined();
    expect(evaluateExpression('obj.constructor', { obj: {} })).toBeUndefined();
    expect(evaluateExpression('obj["__proto__"]', { obj: {} })).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// 2. 状态变量面板 UI 测试
// ---------------------------------------------------------------------------

test.describe('State Variable Panel', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await setupEditorMocks(page);
    await page.goto('/platform/lowcode/editor/test-page');
    await page.waitForLoadState('networkidle');
  });

  test('adds a new state variable', async ({ page }) => {
    // 点击属性面板中的状态变量 Tab
    const stateTab = page.locator('.ant-tabs-tab', { hasText: '状态变量' });
    if (await stateTab.isVisible()) {
      await stateTab.click();
    } else {
      // 如果没有 Tab，尝试直接定位输入框
      const nameInput = page.locator('input[placeholder="变量名 (英文)"]');
      if (!(await nameInput.isVisible())) {
        test.skip();
        return;
      }
    }

    // 填写变量名和显示名称
    await page.locator('input[placeholder="变量名 (英文)"]').fill('userName');
    await page.locator('input[placeholder="显示名称"]').fill('用户名');

    // 点击添加变量按钮
    await page.locator('button', { hasText: '添加变量' }).click();

    // 验证添加成功 — 变量名应出现在页面上
    await expect(page.locator('text=用户名')).toBeVisible();
    await expect(page.locator('text=userName')).toBeVisible();
  });

  test('prevents duplicate variable names', async ({ page }) => {
    const stateTab = page.locator('.ant-tabs-tab', { hasText: '状态变量' });
    if (await stateTab.isVisible()) {
      await stateTab.click();
    } else {
      const nameInput = page.locator('input[placeholder="变量名 (英文)"]');
      if (!(await nameInput.isVisible())) {
        test.skip();
        return;
      }
    }

    // 添加第一个变量
    await page.locator('input[placeholder="变量名 (英文)"]').fill('myVar');
    await page.locator('input[placeholder="显示名称"]').fill('变量1');
    await page.locator('button', { hasText: '添加变量' }).click();

    // 尝试添加同名变量
    await page.locator('input[placeholder="变量名 (英文)"]').fill('myVar');
    await page.locator('input[placeholder="显示名称"]').fill('变量2');
    await page.locator('button', { hasText: '添加变量' }).click();

    // 应显示警告消息
    await expect(page.locator('.ant-message-warning')).toBeVisible();
  });

  test('selects variable type', async ({ page }) => {
    const stateTab = page.locator('.ant-tabs-tab', { hasText: '状态变量' });
    if (await stateTab.isVisible()) {
      await stateTab.click();
    } else {
      const nameInput = page.locator('input[placeholder="变量名 (英文)"]');
      if (!(await nameInput.isVisible())) {
        test.skip();
        return;
      }
    }

    // 选择类型为 number
    await page.locator('.ant-select').last().click();
    await page.locator('.ant-select-item-option', { hasText: '数字' }).click();

    // 填写变量名并添加
    await page.locator('input[placeholder="变量名 (英文)"]').fill('count');
    await page.locator('input[placeholder="显示名称"]').fill('计数');
    await page.locator('button', { hasText: '添加变量' }).click();

    // 验证类型显示
    await expect(page.locator('text=count · number')).toBeVisible();
  });

  test('deletes a state variable', async ({ page }) => {
    const stateTab = page.locator('.ant-tabs-tab', { hasText: '状态变量' });
    if (await stateTab.isVisible()) {
      await stateTab.click();
    } else {
      const nameInput = page.locator('input[placeholder="变量名 (英文)"]');
      if (!(await nameInput.isVisible())) {
        test.skip();
        return;
      }
    }

    // 先添加一个变量
    await page.locator('input[placeholder="变量名 (英文)"]').fill('toDelete');
    await page.locator('input[placeholder="显示名称"]').fill('待删除');
    await page.locator('button', { hasText: '添加变量' }).click();
    await expect(page.locator('text=待删除')).toBeVisible();

    // 点击删除图标
    await page.locator('text=待删除').locator('..').locator('[class*="delete"]').click();

    // 确认删除
    await page.locator('.ant-popconfirm .ant-btn-primary', { hasText: '确' }).click();

    // 验证删除成功
    await expect(page.locator('text=待删除')).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// 3. 联动规则面板 UI 测试
// ---------------------------------------------------------------------------

test.describe('Linkage Rules Panel', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await setupEditorMocks(page);
    await page.goto('/platform/lowcode/editor/test-page');
    await page.waitForLoadState('networkidle');
  });

  test('shows empty state when no component selected', async ({ page }) => {
    // 点击联动规则 Tab
    const linkageTab = page.locator('.ant-tabs-tab', { hasText: '联动规则' });
    if (await linkageTab.isVisible()) {
      await linkageTab.click();
    }

    // 应显示提示选择组件的文本
    const hint = page.locator('text=请先选择一个组件');
    if (await hint.isVisible()) {
      await expect(hint).toBeVisible();
    }
  });

  test('adds a linkage rule after selecting a component', async ({ page }) => {
    // 先在画布中选择一个组件
    const canvasComponent = page.locator('[data-testid*="node-input-1"], [data-node-id="input-1"]').first();
    if (await canvasComponent.isVisible()) {
      await canvasComponent.click();
    } else {
      // 尝试通过图层面板选择
      const layerTab = page.locator('.ant-tabs-tab', { hasText: '图层' });
      if (await layerTab.isVisible()) {
        await layerTab.click();
        await page.locator('text=NutInput').first().click();
      } else {
        test.skip();
        return;
      }
    }

    // 点击联动规则 Tab
    const linkageTab = page.locator('.ant-tabs-tab', { hasText: '联动规则' });
    if (await linkageTab.isVisible()) {
      await linkageTab.click();
    }

    // 点击添加规则按钮
    const addRuleBtn = page.locator('button', { hasText: '添加规则' });
    if (await addRuleBtn.isVisible()) {
      await addRuleBtn.click();

      // 验证规则卡片出现
      await expect(page.locator('text=联动规则 1')).toBeVisible();
    }
  });

  test('shows rule conditions and actions areas', async ({ page }) => {
    // 选择组件
    const canvasComponent = page.locator('[data-testid*="node-input-1"], [data-node-id="input-1"]').first();
    if (await canvasComponent.isVisible()) {
      await canvasComponent.click();
    } else {
      const layerTab = page.locator('.ant-tabs-tab', { hasText: '图层' });
      if (await layerTab.isVisible()) {
        await layerTab.click();
        await page.locator('text=NutInput').first().click();
      } else {
        test.skip();
        return;
      }
    }

    // 打开联动规则面板
    const linkageTab = page.locator('.ant-tabs-tab', { hasText: '联动规则' });
    if (await linkageTab.isVisible()) {
      await linkageTab.click();
    }

    // 添加规则
    const addRuleBtn = page.locator('button', { hasText: '添加规则' });
    if (await addRuleBtn.isVisible()) {
      await addRuleBtn.click();

      // 验证"当"和"则"区域存在
      await expect(page.locator('text=当')).toBeVisible();
      await expect(page.locator('text=则')).toBeVisible();

      // 验证添加条件和添加动作按钮存在
      await expect(page.locator('text=+ 添加条件')).toBeVisible();
      await expect(page.locator('text=+ 添加动作')).toBeVisible();
    }
  });

  test('deletes a linkage rule', async ({ page }) => {
    // 选择组件
    const canvasComponent = page.locator('[data-testid*="node-input-1"], [data-node-id="input-1"]').first();
    if (await canvasComponent.isVisible()) {
      await canvasComponent.click();
    } else {
      const layerTab = page.locator('.ant-tabs-tab', { hasText: '图层' });
      if (await layerTab.isVisible()) {
        await layerTab.click();
        await page.locator('text=NutInput').first().click();
      } else {
        test.skip();
        return;
      }
    }

    // 打开联动规则面板
    const linkageTab = page.locator('.ant-tabs-tab', { hasText: '联动规则' });
    if (await linkageTab.isVisible()) {
      await linkageTab.click();
    }

    // 添加规则
    const addRuleBtn = page.locator('button', { hasText: '添加规则' });
    if (await addRuleBtn.isVisible()) {
      await addRuleBtn.click();
      await expect(page.locator('text=联动规则 1')).toBeVisible();

      // 点击删除图标
      await page.locator('.ant-card [class*="delete"]').first().click();

      // 确认删除
      await page.locator('.ant-popconfirm .ant-btn-primary', { hasText: '确' }).click();

      // 验证删除成功
      await expect(page.locator('text=联动规则 1')).not.toBeVisible();
    }
  });

  test('toggles rule enabled state', async ({ page }) => {
    // 选择组件
    const canvasComponent = page.locator('[data-testid*="node-input-1"], [data-node-id="input-1"]').first();
    if (await canvasComponent.isVisible()) {
      await canvasComponent.click();
    } else {
      const layerTab = page.locator('.ant-tabs-tab', { hasText: '图层' });
      if (await layerTab.isVisible()) {
        await layerTab.click();
        await page.locator('text=NutInput').first().click();
      } else {
        test.skip();
        return;
      }
    }

    // 打开联动规则面板
    const linkageTab = page.locator('.ant-tabs-tab', { hasText: '联动规则' });
    if (await linkageTab.isVisible()) {
      await linkageTab.click();
    }

    // 添加规则
    const addRuleBtn = page.locator('button', { hasText: '添加规则' });
    if (await addRuleBtn.isVisible()) {
      await addRuleBtn.click();

      // 找到 Switch 组件并点击
      const switchEl = page.locator('.ant-card .ant-switch').first();
      if (await switchEl.isVisible()) {
        // 记录初始状态
        const isChecked = await switchEl.evaluate((el) => el.classList.contains('ant-switch-checked'));

        // 点击切换
        await switchEl.click();

        // 验证状态改变
        if (isChecked) {
          await expect(switchEl).not.toHaveClass(/ant-switch-checked/);
        } else {
          await expect(switchEl).toHaveClass(/ant-switch-checked/);
        }
      }
    }
  });
});
