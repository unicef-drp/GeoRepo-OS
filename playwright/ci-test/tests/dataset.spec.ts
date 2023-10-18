import { test, expect } from '@playwright/test';

test('Fetch Dataset List', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Dataset' }).click();
  const pageHeader = page.locator('.AdminContentHeader-Left').first();
  await expect(pageHeader).toHaveText('Dataset');
  const createDatasetButton = page.getByLabel('Create Dataset');
  await expect(createDatasetButton).toBeVisible();
  await expect(createDatasetButton).toBeEnabled();
});