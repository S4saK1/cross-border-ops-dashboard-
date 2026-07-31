import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:3000';

test.describe('Bilingual CMS E2E', () => {
  test('login page loads', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await expect(page.locator('h1')).toContainText('跨境产品资料中英对照系统');
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.getByRole('button', { name: '登录' })).toBeVisible();
  });

  test('login with valid credentials', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.fill('input[type="email"]', 'admin@bilingual-product-cms.com');
    await page.fill('input[type="password"]', process.env.TEST_ADMIN_PASSWORD || 'admin');
    await page.click('button[type="submit"]');

    // Should redirect to dashboard
    await page.waitForURL('**/');
    await expect(page.locator('h1')).toContainText('产品管理');
  });

  test('product list renders after login', async ({ page }) => {
    // Assume already logged in via storage state or previous test
    await page.goto(`${BASE}/products`);
    await expect(page.locator('table')).toBeVisible();
  });

  test('navigate to new product page', async ({ page }) => {
    await page.goto(`${BASE}/products`);
    await page.click('text=新建产品');
    await page.waitForURL('**/products/new');
    await expect(page.locator('h1')).toContainText('新建产品');
    await expect(page.locator('input[placeholder="SKU-001"]')).toBeVisible();
  });

  test('sidebar navigation works', async ({ page }) => {
    await page.goto(`${BASE}/`);
    // Click each nav item and verify navigation
    await page.click('text=术语词典');
    await page.waitForURL('**/terms');
    await page.click('text=CSV 导出');
    await page.waitForURL('**/export');
    await page.click('text=仪表盘');
    await page.waitForURL('**/');
  });
});
