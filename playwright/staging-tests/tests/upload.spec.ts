import { test, expect } from '@playwright/test';
import fs from "fs";

// 20 seconds
const LONG_RUNNING_PROCESS_TIMEOUT = 20000;

/**
 * Run upload workflow from step 0 until batch review approval.
 * This test supports multiple revisions.
 * 
 * Change the sessionId and datasetId before running the test.
 */
test('Upload Workflow Success', async ({ page }) => {
  test.setTimeout(120000);
  const sessionId = 63;
  const datasetId = 35;
  await page.goto(`/admin_boundaries/upload_wizard/?session=${sessionId}&dataset=${datasetId}&step=0`);
  await page.locator('#input_source').fill('Upload');
  await page.locator('#input_description').fill('Upload');
  await page.getByRole('button', { name: 'Next' }).click();
  
  /* Step 2 - Upload Files */
  const locatorDropZone = page.locator('label').filter({ hasText: 'Drag and drop or click to browse for a file in one of these formats: .json, .geo' })
  await expect(locatorDropZone).toBeVisible();
  await expect(page.locator('.dzu-input')).toBeEnabled();
  await page.waitForTimeout(5000);
  const isUploadLevel0Enabled = await page.locator('input[type=checkbox]').first().isEnabled();
  if (isUploadLevel0Enabled) {
    await page.locator('input[type=checkbox]').first().check();
  } else {
    await expect(page.locator('input[type=checkbox]').first()).toBeChecked();
  }
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
  const file0 = page.locator('div').filter({ hasText: /^application\/geo\+jsonadm0\.geojsonLevel 0$/ }).first();
  await expect(file0).toBeVisible();
  const file1 = page.locator('div').filter({ hasText: /^application\/geo\+jsonadm1\.geojsonLevel 1$/ }).first();
  await expect(file1).toBeVisible();
  await page.getByRole('button', { name: 'Next' }).click();
  /* End of Step 2 - Upload Files */
  
  /* Step 3 - Attributes Mapping */
  const tab0 = page.getByRole('tab', { name: 'Level 0' });
  const tab1 = page.getByRole('tab', { name: 'Level 1' });
  const tabSummary = page.getByRole('tab', { name: 'Summary' });
  await expect(tab0).toBeVisible();
  await expect(tab1).toBeVisible();
  await expect(tabSummary).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Name Fields' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save Level' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Back', exact: true })).toBeEnabled();
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
  await expect(page.getByRole('button', { name: 'Save Level' })).toBeEnabled();
  await page.getByRole('button', { name: 'Save Level' }).click();
  await expect(page.getByRole('button', { name: 'Saving' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Save Level' })).toBeEnabled();
  await expect(tab0.getByTestId('CheckBoxIcon')).toBeVisible();
  await tab1.click();
  await expect(page.getByRole('heading', { name: 'Name Fields' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save Level' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Back', exact: true })).toBeEnabled();
  await expect(page.getByRole('heading', { name: 'Parent Id Field' })).toBeVisible();
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
  await expect(page.getByRole('button', { name: 'Save Level' })).toBeEnabled();
  await page.getByRole('button', { name: 'Save Level' }).click();
  await expect(page.getByRole('button', { name: 'Saving' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Save Level' })).toBeEnabled();
  await expect(tab1.getByTestId('CheckBoxIcon')).toBeVisible();
  await tabSummary.click();
  await expect(page.getByRole('columnheader', { name: 'Level' })).  toBeVisible();
  await expect(page.getByRole('columnheader', { name: 'File name' })).toBeVisible();
  await expect(page.getByRole('columnheader', { name: 'Feature Count' })).toBeVisible();
  await expect(page.getByRole('columnheader', { name: 'Field Mapping' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Import & Validate' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Back', exact: true })).toBeEnabled();
  const row0 = page.getByRole('row').nth(1);
  await expect(row0.getByRole('cell', { name: '0', exact: true })).toBeVisible();
  await expect(row0.getByRole('cell', { name: /^adm0(_\w+)?\.geojson$/ })).toBeVisible();
  await expect(row0.getByRole('cell', { name: '1', exact: true }).first()).toBeVisible();
  await expect(row0.getByRole('cell', { name: 'name_field (English) = name (default) id_field (PCode) = PCode (default) parent_id_field = location_type = \'Country\' privacy_level = \'4 - Highly confidential\' source_id_field =' })).toBeVisible();
  const row1 = page.getByRole('row').nth(2);
  await expect(row1.getByRole('cell', { name: '1', exact: true })).toBeVisible();
  await expect(row1.getByRole('cell', { name: /^adm1(_\w+)?\.geojson$/ })).toBeVisible();
  await expect(row1.getByRole('cell', { name: '18', exact: true }).first()).toBeVisible();
  await expect(row1.getByRole('cell', { name: 'name_field (English) = name (default) id_field (ucodeIn) = ucode (default) parent_id_field = adm0_ucode location_type = \'Province\' privacy_level = \'4 - Highly confidential\' source_id_field =' })).toBeVisible();
  await page.getByRole('button', { name: 'Import & Validate' }).click();
  /* End of Step 3 - Attributes Mapping */  

  /* Step 4 - Country Selection */
  await expect(page.getByText('Select All (1/1)')).toBeVisible({timeout: LONG_RUNNING_PROCESS_TIMEOUT});
  await expect(page.getByTestId('InfoIcon')).toBeVisible();
  if (!isUploadLevel0Enabled) {
    // first upload revision
    await expect(page.getByText('Somalia (NEW)')).toBeVisible();
    await expect(page.getByText('Default Code: SO')).toBeVisible();
  } else {
    await expect(page.getByText(/^Somalia - Revision (\d+)$/)).toBeVisible();
  }
  
  await expect(page.getByText('Total admin level 1: 18 entities')).toBeVisible();
  await expect(page.locator('#max-level-select')).toHaveText("1");
  await expect(page.locator('div').filter({ hasText: /^Country$/ }).nth(1)).toBeVisible();
  await expect(page.locator('div').filter({ hasText: /^Province$/ }).nth(1)).toBeVisible();

  await expect(page.locator('input[type=checkbox]').first()).toBeChecked();
  await expect(page.locator('input[type=checkbox]').last()).toBeChecked();
  await expect(page.getByRole('button', { name: 'Validate' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Back', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Validate' }).click();
  await expect(page.getByRole('button', { name: 'Validate' })).toBeDisabled();
  await expect(page.getByRole('heading', { name: 'Processing selected countries' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Processing selected countries'})).toBeHidden({timeout: LONG_RUNNING_PROCESS_TIMEOUT});
  /* End of Step 4 - Country Selection */

  /* Step 5 - Validation Results */
  await expect(page.getByText('Somalia')).toBeVisible({timeout: LONG_RUNNING_PROCESS_TIMEOUT});
  await expect(page.getByText('Job summary: 1 warning.')).toBeVisible();
  await expect(page.locator('input[type=checkbox]').first()).toBeChecked({checked: false});
  await expect(page.locator('input[type=checkbox]').last()).toBeChecked({checked: false});
  await expect(page.getByRole('button', { name: 'Import' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Back', exact: true })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Show Warning', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Show Warning', exact: true }).click();
  await expect(page.getByText('Error Report', {exact: true})).toBeVisible();
  await expect(page.getByText('Download Error Report', {exact: true})).toBeEnabled();
  const closeIconCount = await page.getByLabel('close').count();
  await page.getByLabel('close').first().click();
  if (closeIconCount > 1) {
    // another one is from  notification
    page.getByLabel('close').first().click();
  }
  await expect(page.getByText('Error Report', {exact: true})).toBeVisible({visible: false});

  await page.locator('input[type=checkbox]').first().check();
  await expect(page.getByRole('button', { name: 'Import' })).toBeEnabled();
  await page.getByRole('button', { name: 'Import' }).click();
  await expect(page.getByRole('button', { name: 'Import' })).toBeDisabled();
  await expect(page.getByRole('heading', { name: 'Processing selected countries' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Processing selected countries'})).toBeHidden({timeout: LONG_RUNNING_PROCESS_TIMEOUT});
  /* End of Step 5 - Validation Results */

  /* Batch Review */
  await expect(page.getByText('Somalia')).toBeVisible({timeout: LONG_RUNNING_PROCESS_TIMEOUT});
  await expect(page.getByText('Ready for Review')).toBeVisible();
  await expect(page.getByRole('button', {name:'Batch Review', exact: true})).toBeEnabled();
  await page.getByRole('button', {name:'Batch Review', exact: true}).click();
  await expect(page.getByRole('button', {name:'Cancel', exact: true})).toBeEnabled();
  await expect(page.getByRole('button', {name:'Approve', exact: true})).toBeDisabled();
  await expect(page.getByRole('button', {name:'Reject', exact: true})).toBeDisabled();
  await expect(page.getByText('0 selected ')).toBeVisible();
  await expect(page.locator('input[type=checkbox]').first()).toBeChecked({checked: false});
  await expect(page.locator('input[type=checkbox]').last()).toBeChecked({checked: false});
  await page.locator('input[type=checkbox]').first().check();
  await expect(page.getByText('1 selected ')).toBeVisible();
  await expect(page.getByRole('button', {name:'Approve', exact: true})).toBeEnabled();
  await expect(page.getByRole('button', {name:'Reject', exact: true})).toBeEnabled();
  await page.getByRole('button', {name:'Approve', exact: true}).click();
  await expect(page.getByText('Batch Approve')).toBeVisible();
  await expect(page.getByText('Are you sure you want to approve 1 entities?')).toBeVisible();
  await expect(page.getByRole('button', {name:'Confirm', exact: true})).toBeEnabled();
  await expect(page.getByRole('button', {name:'Cancel', exact: true})).toBeEnabled();
  await page.getByRole('button', {name:'Confirm', exact: true}).click();
  await expect(page.getByRole('button', {name:'Confirm', exact: true})).toBeDisabled();
  await expect(page.getByText('Batch Approve')).toBeVisible({timeout: LONG_RUNNING_PROCESS_TIMEOUT, visible: false});

  await expect(page.getByRole('button', {name:'Cancel', exact: true})).toBeHidden();
  await expect(page.getByRole('button', {name:'Approve', exact: true})).toBeHidden();
  await expect(page.getByRole('button', {name:'Reject', exact: true})).toBeHidden();
  await expect(page.getByRole('button', {name:'Batch Review', exact: true})).toBeHidden();
  await expect(page.getByText('Batch Review: ')).toBeVisible();
  await expect(page.getByRole('button', {name:'Batch Review', exact: true})).toBeVisible({timeout: LONG_RUNNING_PROCESS_TIMEOUT});
  await expect(page.getByText('Somalia')).toBeVisible();
  await expect(page.getByText('Approved', {exact: true})).toBeVisible({timeout: LONG_RUNNING_PROCESS_TIMEOUT});
  /* End of Batch Review */
});