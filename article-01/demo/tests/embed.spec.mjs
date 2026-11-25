/* global document -- used inside page.evaluate(), which runs in the browser */
// Local checks of the embed-friendly page (embed/index.html, built by build_embed.py).
// They cover level 1 (local) only: the page has not been tested inside CodeSandbox or Qiita.
import { readFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { expect, test } from '@playwright/test';

const EMBED = pathToFileURL(fileURLToPath(new URL('../embed/index.html', import.meta.url))).href;
const FULL = pathToFileURL(fileURLToPath(new URL('../order_design.html', import.meta.url))).href;
const SPEC = JSON.parse(readFileSync(new URL('../spec/order_spec.json', import.meta.url), 'utf8'));
const MSG = Object.fromEntries(SPEC.messages.map((m) => [m.id, m.text]));
const fmt = (id, ...args) => MSG[id].replace(/\{(\d)\}/g, (_, i) => args[Number(i)]);

// Expected embed area: about 700 px wide in a desktop article column, 360 px on a phone.
const EMBED_AREA = { width: 700, height: 500 };

async function open(page, url = EMBED) {
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  await page.goto(url);
  return errors;
}

const tablesOf = (page) =>
  page.evaluate(() => [...document.querySelectorAll('main table')].map((t) => t.outerHTML));

test('embed: same spec tables and preview script as order_design.html', async ({ page }) => {
  await open(page, FULL);
  const fullTables = await tablesOf(page);
  const fullScript = await page.evaluate(() => document.querySelector('body > script').textContent);
  await open(page);
  expect(await tablesOf(page)).toEqual(fullTables);
  expect(await page.evaluate(() => document.querySelector('body > script').textContent)).toBe(
    fullScript,
  );
});

test('embed: BR-002 approval flow in the embed area (VR-16, ST-04)', async ({ page }) => {
  await page.setViewportSize(EMBED_AREA);
  const errors = await open(page);
  await page.click('[data-sample="approval"]');
  await page.locator('#f-remarks').click();
  await page.locator('#f-remarks').blur();
  await expect(page.locator('#f-total')).toHaveText('1,216,600');
  await expect(page.locator('#approver-req')).toBeVisible();
  await expect(page.locator('#btn-confirm')).toBeDisabled();
  await page.selectOption('#f-approver', 'U101');
  await expect(page.locator('#btn-confirm')).toBeEnabled();
  await page.click('#btn-confirm');
  await expect(page.locator('#screen')).toHaveAttribute('data-state', 'ST-04');
  await expect(page.locator('.confirm-note')).toContainText('承認待ち');
  expect(errors).toEqual([]);
});

test('embed: required validation shows MSG-E001 on focus-out', async ({ page }) => {
  await page.setViewportSize(EMBED_AREA);
  await open(page);
  await page.click('#f-customer');
  await page.click('#f-remarks');
  await expect(page.locator('#e-customer')).toContainText(fmt('MSG-E001', '顧客コード'));
  await expect(page.locator('#btn-confirm')).toBeDisabled();
});

for (const size of [{ width: 320, height: 500 }, { width: 360, height: 500 }, EMBED_AREA]) {
  test(`embed: preview starts in the first screen, no horizontal scroll at ${size.width}px`, async ({
    page,
  }) => {
    await page.setViewportSize(size);
    await open(page);
    // The sample buttons and the start of the screen are visible without scrolling.
    await expect(page.locator('[data-sample="approval"]')).toBeInViewport();
    const top = await page.locator('#screen').evaluate((el) => el.getBoundingClientRect().top);
    expect(top).toBeLessThan(size.height * (size.width >= 640 ? 0.5 : 0.8));
    await page.click('[data-sample="error"]');
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
  });
}
