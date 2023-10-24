import { test, expect } from '@playwright/test';
import fs from "fs";


test('test', async ({ page }) => {
  test.setTimeout(120000);
  
  // await page.goto('/');
  // await page.getByRole('link', { name: 'Dataset' }).click();
  // // should find by Dataset Name
  // await page.getByTestId('MuiDataTableBodyCell-1-14').click();
  // await page.getByRole('tab', { name: 'UPLOAD HISTORY' }).click();
  // // should find first Upload
  // await page.getByText('54').click();
  await page.goto('/admin_boundaries/upload_wizard/?session=50&step=0&dataset=27');
  await page.locator('#input_source').fill('Upload');
  await page.locator('#input_description').fill('Upload');
  await page.getByRole('button', { name: 'Next' }).click();
  
  const locatorDropZone = page.locator('label').filter({ hasText: 'Drag and drop or click to browse for a file in one of these formats: .json, .geo' })
  await locatorDropZone.isVisible();
  await page.locator('.dzu-input').isEnabled();
  await page.waitForTimeout(3000);
  // // Read your file into a buffer.
  const buffer = fs.readFileSync('../data/adm0.geojson','utf-8');
  const buffer2 = fs.readFileSync('../data/adm1.geojson','utf-8');

  // Create the DataTransfer and File
  const dataTransfer = await page.evaluateHandle(({buffer, buffer2}) => {
      const dt = new DataTransfer();
      // Convert the buffer to a hex array
      const file = new File([buffer.toString('hex')], 'adm0.geojson', { type: 'application/geo+json' });
      dt.items.add(file);
      const file2 = new File([buffer2.toString('hex')], 'adm1.geojson', { type: 'application/geo+json' });
      dt.items.add(file2);
      return dt;
  }, {buffer,buffer2});

  await page.dispatchEvent('.dzu-input', 'drop', { dataTransfer });
  await page.waitForTimeout(3000);

  await page.getByRole('button', { name: 'Next' }).click();
  await page.locator('div').filter({ hasText: /^Language$/ }).click();
  await page.getByRole('option', { name: 'English' }).click();
  await page.getByLabel('Name Field', { exact: true }).click();
  await page.getByRole('option', { name: 'name', exact: true }).click();
  await page.locator('div').filter({ hasText: /^Type$/ }).click();
  await page.getByRole('option', { name: 'PCode' }).click();
  await page.getByLabel('Id Field', { exact: true }).click();
  await page.getByRole('option', { name: 'PCode' }).click();
  await page.getByText('User Input').first().click();
  await page.getByLabel('Location Type').click();
  await page.getByRole('option', { name: 'Country' }).click();
  await page.getByText('User Input').nth(1).click();
  await page.getByRole('button', { name: 'Save Level' }).click();
  await page.waitForTimeout(3000);
  await page.getByRole('tab', { name: 'Level 1' }).click();
  await page.locator('div').filter({ hasText: /^Language$/ }).click();
  await page.getByRole('option', { name: 'English' }).click();
  await page.getByLabel('Name Field', { exact: true }).click();
  await page.getByRole('option', { name: 'name', exact: true }).click();
  await page.locator('div').filter({ hasText: /^Type$/ }).click();
  await page.getByRole('option', { name: 'UcodeIn' }).click();
  await page.getByLabel('Id Field', { exact: true }).click();
  await page.getByRole('option', { name: 'ucode', exact: true }).click();
  await page.locator('div').filter({ hasText: /^Parent Id Field$/ }).nth(1).click();
  await page.getByRole('option', { name: 'adm0_ucode' }).click();
  await page.getByText('User Input').first().click();
  await page.getByLabel('Location Type').click();
  await page.getByRole('option', { name: 'Province' }).click();
  await page.locator('label').filter({ hasText: 'User Input' }).nth(1).click();
  await page.getByRole('button', { name: 'Save Level' }).click();
  await page.waitForTimeout(5000);
  await page.getByRole('tab', { name: 'Summary' }).click();
  await page.getByRole('button', { name: 'Import & Validate' }).click();
  await page.getByRole('button', { name: 'Validate' }).isVisible();
  await page.getByRole('button', { name: 'Validate' }).isEnabled();
  await page.getByRole('button', { name: 'Validate' }).click();
  await page.waitForTimeout(5000);
  // wait step 5
  await page.getByRole('button', { name: 'Import' }).isVisible();
  await page.getByRole('button', { name: 'Import' }).isEnabled();
  // await page.goto('https://staging-georepo.unitst.org/admin_boundaries/upload_wizard?session=54&step=4&dataset=29');
  // // should wait until there is row with Country=Somalia and Status=Show Warning
  // // click select all 
  // await page.getByRole('row', { name: 'Sort Sort Sort Sort' }).getByRole('checkbox').check();
  // await page.getByRole('button', { name: 'Import' }).click();
  // await page.goto('https://staging-georepo.unitst.org/review_list?upload=54');
  // // should wait until status=Ready To Review
  // await page.getByLabel('Batch Review').click();
  // // click select all
  // await page.getByRole('row', { name: 'Sort Sort Sort Sort Sort Status Sort Sort' }).getByRole('checkbox').check();
  // await page.getByLabel('Approve').click();
  // await page.getByRole('button', { name: 'Confirm' }).click();
});