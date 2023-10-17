import { test, expect } from '@playwright/test';


test('Fetch View List', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Views', exact: true }).click();
  const pageHeader = page.locator('.AdminContentHeader-Left').first();
  await expect(pageHeader).toHaveText('Views');
  const addViewButton = page.getByLabel('Add View');
  await expect(addViewButton).toBeVisible();
  await expect(addViewButton).toBeEnabled();
});