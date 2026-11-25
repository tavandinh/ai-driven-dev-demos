/* global document, location -- used inside page.evaluate(), which runs in the browser */
// Local checks of the embed-friendly page (embed/index.html, built by build_embed.py).
// Viewport sizes stand for the width inside the CodeSandbox iframe on Qiita, not the phone width.
import { readFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { expect, test } from '@playwright/test';

const EMBED = pathToFileURL(fileURLToPath(new URL('../embed/index.html', import.meta.url))).href;
const FULL = pathToFileURL(fileURLToPath(new URL('../order_design.html', import.meta.url))).href;
const SPEC = JSON.parse(readFileSync(new URL('../spec/order_spec.json', import.meta.url), 'utf8'));
const MSG = Object.fromEntries(SPEC.messages.map((m) => [m.id, m.text]));
const fmt = (id, ...args) => MSG[id].replace(/\{(\d)\}/g, (_, i) => args[Number(i)]);

const SIZES = [
  { width: 320, height: 500 },
  { width: 360, height: 500 },
  { width: 390, height: 600 },
  { width: 700, height: 500 },
  { width: 1280, height: 800 },
];

async function open(page, url = EMBED) {
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  await page.goto(url);
  return errors;
}

const tablesOf = (page) =>
  page.evaluate(() => [...document.querySelectorAll('main table')].map((t) => t.outerHTML));
const scriptOf = (page) => page.evaluate(() => document.querySelector('body > script').textContent);
const controlsOf = (page) =>
  page.evaluate(() =>
    ['#demo-user', '#demo-ids', '#demo-state', '[data-sample]', '#screen', '#lines'].map(
      (s) => document.querySelectorAll(s).length,
    ),
  );

test('embed: same spec tables, business script and controls as order_design.html', async ({
  page,
}) => {
  await open(page, FULL);
  const [tables, script, controls] = [
    await tablesOf(page),
    await scriptOf(page),
    await controlsOf(page),
  ];
  await open(page);
  expect(await tablesOf(page)).toEqual(tables);
  expect(await scriptOf(page)).toBe(script);
  expect(await controlsOf(page)).toEqual(controls);
});

for (const size of SIZES) {
  test(`embed ${size.width}x${size.height}: compact top, BR-002 flow, no overflow, no JS error`, async ({
    page,
  }) => {
    await page.setViewportSize(size);
    const errors = await open(page);

    // 1-2. The hint is short and the sample buttons are visible and easy to tap, on one row.
    const intro = await page.locator('.embed-intro').boundingBox();
    expect(intro.height).toBeLessThanOrEqual(80);
    const buttons = page.locator('[data-sample]');
    await expect(page.locator('[data-sample="approval"]')).toBeInViewport();
    const boxes = await Promise.all([0, 1, 2].map((i) => buttons.nth(i).boundingBox()));
    expect(new Set(boxes.map((b) => Math.round(b.y))).size).toBe(1);
    for (const b of boxes) expect(b.height).toBeGreaterThanOrEqual(36);

    // 4-8. BR-002 flow.
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

    // 3. No horizontal overflow of the page, also with the error sample.
    await page.click('#btn-back');
    await page.click('[data-sample="error"]');
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);

    // 10. No JavaScript error.
    expect(errors).toEqual([]);
  });
}

test('embed 360: required validation and ID links from the collapsible panel', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 500 });
  await open(page);
  // 9a. Required validation (VR-03 / MSG-E001).
  await page.click('#f-customer');
  await page.click('#f-remarks');
  await expect(page.locator('#e-customer')).toContainText(fmt('MSG-E001', '顧客コード'));
  // 9b. The ID overlay lives in 「その他の操作」 and still links to the spec tables.
  await expect(page.locator('#demo-ids')).toBeHidden();
  await page.click('.embed-options summary');
  await page.check('#demo-ids');
  await page.locator('a.spec-badge[href="#ITM-04"]').first().click();
  expect(await page.evaluate(() => location.hash)).toBe('#ITM-04');
  await expect(page.locator('tr#ITM-04')).toBeInViewport();
  // The login user switch still drives BR-003.
  await page.selectOption('#demo-user', 'U101');
  await expect(page.locator('#f-user')).toContainText('U101');
});
