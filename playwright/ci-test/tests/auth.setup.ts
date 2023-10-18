import {test as setup} from '@playwright/test';

const authFile = 'states/.auth/user.json';
const loginWaitTime = 5000;

setup('authenticate', async ({page}) => {

    await page.goto('/');
    await page.waitForSelector('.basic-form', {timeout: loginWaitTime});
    await page.locator('.login-app input[name="username"]').fill('admin');
    await page.locator('.login-app input[name="password"]').fill('admin');
    await page.getByRole('button', {name: 'LOG IN'}).click();
    //
    // wait until page renders Admin (Administator) in nav header
    await page.waitForSelector('.NavHeader-Username', {timeout: 5000});

    // End of authentication steps.
    await page.context().storageState({path: authFile});
});