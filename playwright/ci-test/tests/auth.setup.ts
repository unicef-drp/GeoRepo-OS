import {test as setup} from '@playwright/test';

const authFile = 'states/.auth/user.json';

setup('authenticate', async ({page}) => {

    await page.goto('/login/');
    await page.waitForSelector('.basic-form', {timeout: 2000});
    await page.locator('.login-app input[name="username"]').fill('admin');
    await page.locator('.login-app input[name="password"]').fill('admin');
    await page.getByRole('button', {name: 'LOG IN'}).click();
    //
    // wait until page renders Admin (Administator) in nav header
    await page.waitForSelector('.NavHeader-Username', {timeout: 5000});

    // End of authentication steps.
    await page.context().storageState({path: authFile});
});