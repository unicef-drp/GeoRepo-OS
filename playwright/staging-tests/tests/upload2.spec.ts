import { test, expect } from '@playwright/test';

test.use({
  ignoreHTTPSErrors: true,
  storageState: 'georepo-auth.json'
});

test('test', async ({ page }) => {
  await page.goto('https://localhost:51102/');
  await page.goto('https://localhost:51102/admin_boundaries/upload_wizard/?session=50&step=1&dataset=27');
});