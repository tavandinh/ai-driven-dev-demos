/* global document -- used inside page.evaluate(), which runs in the browser */
// Behaviour tests of the interactive preview in order_design.html.
// Each test names the spec IDs (VR / BR / EV / ST) it exercises.
import { readFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { expect, test } from '@playwright/test';

const HTML = fileURLToPath(new URL('../order_design.html', import.meta.url));
const URL_ = pathToFileURL(HTML).href;
const SPEC = JSON.parse(readFileSync(new URL('../spec/order_spec.json', import.meta.url), 'utf8'));
const MSG = Object.fromEntries(SPEC.messages.map((m) => [m.id, m.text]));
const fmt = (id, ...args) => MSG[id].replace(/\{(\d)\}/g, (_, i) => args[Number(i)]);

const state = (page) => page.locator('#screen');
const line = (page, n) => page.locator('#lines tr').nth(n - 1);

async function open(page) {
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  await page.goto(URL_);
  return errors;
}

// Fill the input screen with valid data. Leaves focus outside every field.
async function fillValid(
  page,
  {
    customer = 'C00001',
    lines = [['P-1002', '3']],
    orderDate = '2026-12-01',
    delivery = '2026-12-08',
  } = {},
) {
  await page.fill('#f-orderDate', orderDate);
  await page.fill('#f-customer', customer);
  await page.fill('#f-delivery', delivery);
  await page.selectOption('#f-payment', '01');
  for (let i = 0; i < lines.length; i++) {
    if (i > 0) await page.click('#btn-addLine');
    await line(page, i + 1)
      .locator('input.code')
      .fill(lines[i][0]);
    await line(page, i + 1)
      .locator('input.qty')
      .fill(lines[i][1]);
  }
  await page.locator('#f-remarks').click();
  await page.locator('#f-remarks').blur();
}

test('EV-01 / ST-01: initial display', async ({ page }) => {
  const errors = await open(page);
  await expect(state(page)).toHaveAttribute('data-state', 'ST-01');
  await expect(page.locator('#f-orderDate')).toHaveValue(/^\d{4}-\d{2}-\d{2}$/);
  await expect(page.locator('#lines tr')).toHaveCount(1);
  await expect(line(page, 1).locator('input.qty')).toHaveValue('1');
  await expect(page.locator('#btn-confirm')).toBeDisabled();
  await expect(line(page, 1).locator('button.del')).toBeDisabled();
  await expect(page.locator('#scr-messages')).toBeHidden();
  expect(errors).toEqual([]);
});

test('VR-03 / VR-07 / VR-11: required fields show MSG-E001 on focus-out (ST-03)', async ({
  page,
}) => {
  await open(page);
  await page.click('#f-customer');
  await page.click('#f-delivery');
  await page.click('#f-remarks');
  await expect(page.locator('#e-customer')).toContainText(fmt('MSG-E001', '顧客コード'));
  await expect(page.locator('#e-customer')).toContainText('[VR-03 / MSG-E001]');
  await expect(page.locator('#e-delivery')).toContainText(fmt('MSG-E001', '希望納期'));
  await expect(page.locator('#f-customer')).toHaveAttribute('aria-invalid', 'true');
  await expect(state(page)).toHaveAttribute('data-state', 'ST-03');
  await line(page, 1).locator('input.code').click();
  await page.click('#f-remarks');
  await expect(line(page, 1).locator('.field-error').first()).toContainText('[VR-11 / MSG-E001]');
});

test('VR-04 / VR-05 / VR-06 (BR-007): customer code format, existence, suspended', async ({
  page,
}) => {
  await open(page);
  const err = page.locator('#e-customer');
  for (const [value, vr, text] of [
    ['X1234', 'VR-04', fmt('MSG-E002', '顧客コード', '「C」＋数字5桁')],
    ['C12345', 'VR-05', fmt('MSG-E003', '顧客コード')],
    ['C00099', 'VR-06', MSG['MSG-E004']],
  ]) {
    await page.fill('#f-customer', value);
    await page.click('#f-remarks');
    await expect(err).toContainText(text);
    await expect(err).toContainText(vr);
    await expect(page.locator('#f-customerName')).toHaveText('');
  }
  await page.fill('#f-customer', 'C00001');
  await page.click('#f-remarks');
  await expect(err).toHaveText('');
  await expect(page.locator('#f-customerName')).toHaveText('株式会社サンプル商事');
});

test('VR-02 / VR-08 / VR-09 (BR-005): dates', async ({ page }) => {
  await open(page);
  await page.fill('#f-orderDate', '2026-02-30');
  await page.click('#f-remarks');
  await expect(page.locator('#e-orderDate')).toContainText('[VR-02 / MSG-E002]');
  await page.fill('#f-orderDate', '2026-12-01');
  await page.fill('#f-delivery', '2026-12-01');
  await page.click('#f-remarks');
  await expect(page.locator('#e-delivery')).toContainText(MSG['MSG-E005']);
  await page.fill('#f-delivery', '2026-12-02');
  await page.click('#f-remarks');
  await expect(page.locator('#e-delivery')).toHaveText('');
});

test('VR-12 / VR-13 / VR-15: product code and quantity', async ({ page }) => {
  await open(page);
  const code = line(page, 1).locator('input.code');
  const qty = line(page, 1).locator('input.qty');
  await code.fill('P-12');
  await page.click('#f-remarks');
  await expect(line(page, 1).locator('td').nth(1)).toContainText('[VR-12 / MSG-E002]');
  await code.fill('P-5555');
  await page.click('#f-remarks');
  await expect(line(page, 1).locator('td').nth(1)).toContainText('[VR-13 / MSG-E003]');
  await code.fill('P-1002');
  await page.click('#f-remarks');
  await expect(line(page, 1).locator('.pname')).toHaveText('27インチモニター');
  for (const bad of ['0', '10000', '1.5', 'abc']) {
    await qty.fill(bad);
    await page.click('#f-remarks');
    await expect(line(page, 1).locator('td').nth(3)).toContainText(MSG['MSG-E006']);
  }
  await qty.fill('9999');
  await page.click('#f-remarks');
  await expect(line(page, 1).locator('td').nth(3).locator('.field-error')).toHaveText('');
});

test('BR-006: tax is 10% rounded down; totals', async ({ page }) => {
  await open(page);
  await fillValid(page, {
    lines: [
      ['P-1002', '3'],
      ['P-2001', '1'],
    ],
  });
  // 42,800×3 + 120,000 = 248,400; tax 24,840; total 273,240
  await expect(page.locator('#f-subtotal')).toHaveText('248,400');
  await expect(page.locator('#f-tax')).toHaveText('24,840');
  await expect(page.locator('#f-total')).toHaveText('273,240');
});

test('BR-004 / EV-08 / EV-09 / EV-11: valid order → confirm → back keeps values → register (MSG-I001)', async ({
  page,
}) => {
  await open(page);
  await fillValid(page);
  await expect(page.locator('#btn-confirm')).toBeEnabled();
  await page.click('#btn-confirm');
  await expect(state(page)).toHaveAttribute('data-state', 'ST-04');
  await expect(page.locator('#view-confirm')).toContainText('株式会社サンプル商事');
  await page.click('#btn-back');
  await expect(state(page)).toHaveAttribute('data-state', 'ST-02');
  await expect(page.locator('#f-customer')).toHaveValue('C00001');
  await page.click('#btn-confirm');
  await page.click('#btn-register');
  await expect(state(page)).toHaveAttribute('data-state', 'ST-05');
  await expect(page.locator('#btn-register')).toBeDisabled();
  await expect(state(page)).toHaveAttribute('data-state', 'ST-06');
  await expect(page.locator('#scr-messages')).toHaveText(fmt('MSG-I001', 'ORD-20261201-0001'));
  await expect(page.locator('#view-done')).toContainText('受注確定');
  await page.click('#btn-new');
  await expect(state(page)).toHaveAttribute('data-state', 'ST-01');
});

test('BR-002: total exactly 1,000,000 needs an approver (MSG-I002); 869,000 does not', async ({
  page,
}) => {
  await open(page);
  // 909,091 + tax 90,909 = 1,000,000 → approval required
  await fillValid(page, { lines: [['P-3001', '1']] });
  await expect(page.locator('#f-total')).toHaveText('1,000,000');
  await expect(page.locator('#approver-req')).toBeVisible();
  await expect(page.locator('#btn-confirm')).toBeDisabled();
  await page.selectOption('#f-approver', 'U101');
  await expect(page.locator('#btn-confirm')).toBeEnabled();
  await page.click('#btn-confirm');
  await expect(page.locator('.confirm-note')).toContainText('承認待ち');
  await page.click('#btn-register');
  await expect(page.locator('#scr-messages')).toHaveText(
    fmt('MSG-I002', 'ORD-20261201-0001', '佐藤 花子'),
  );
  await expect(page.locator('#view-done')).toContainText('承認待ち');

  // Below the threshold: 158,000×5 = 790,000 + 79,000 = 869,000 → not required
  await page.click('#btn-new');
  await fillValid(page, { lines: [['P-1001', '5']] });
  await expect(page.locator('#f-total')).toHaveText('869,000');
  await expect(page.locator('#approver-req')).toBeHidden();
  await expect(page.locator('#btn-confirm')).toBeEnabled();
});

test('VR-16: a missing approver above the threshold is reported on confirm path', async ({
  page,
}) => {
  await open(page);
  await fillValid(page, { lines: [['P-1001', '7']] });
  await page.selectOption('#f-approver', 'U102');
  await page.selectOption('#f-approver', '');
  await expect(page.locator('#e-approver')).toContainText(MSG['MSG-E007']);
});

test('BR-003 / VR-17: the logged-in manager cannot approve their own order', async ({ page }) => {
  await open(page);
  await page.selectOption('#demo-user', 'U101');
  await fillValid(page, { lines: [['P-1001', '7']] });
  await page.selectOption('#f-approver', 'U101');
  await expect(page.locator('#e-approver')).toContainText(MSG['MSG-E008']);
  await expect(page.locator('#btn-confirm')).toBeDisabled();
  await page.selectOption('#f-approver', 'U102');
  await expect(page.locator('#e-approver')).toHaveText('');
  await expect(page.locator('#btn-confirm')).toBeEnabled();
});

test('BR-001 / VR-19: a zero total is rejected on confirm with MSG-E010 and MSG-E011', async ({
  page,
}) => {
  await open(page);
  await fillValid(page, { lines: [['P-9000', '1']] });
  await expect(page.locator('#btn-confirm')).toBeEnabled();
  await page.click('#btn-confirm');
  await expect(state(page)).toHaveAttribute('data-state', 'ST-03');
  await expect(page.locator('#scr-messages')).toContainText(fmt('MSG-E011', '1'));
  await expect(page.locator('#scr-messages')).toContainText(MSG['MSG-E010']);
});

test('VR-18: remarks over 200 characters', async ({ page }) => {
  await open(page);
  await page.fill('#f-remarks', 'あ'.repeat(201));
  await page.click('#f-customer');
  await expect(page.locator('#e-remarks')).toContainText(MSG['MSG-E009']);
  await expect(page.locator('#remarks-count')).toHaveText('201 / 200文字');
});

test('EV-05 / EV-06: 1 to 5 lines', async ({ page }) => {
  await open(page);
  for (let i = 0; i < 4; i++) await page.click('#btn-addLine');
  await expect(page.locator('#lines tr')).toHaveCount(5);
  await expect(page.locator('#btn-addLine')).toBeDisabled();
  for (let i = 0; i < 4; i++) await line(page, 1).locator('button.del').click();
  await expect(page.locator('#lines tr')).toHaveCount(1);
  await expect(line(page, 1).locator('button.del')).toBeDisabled();
});

test('EV-10: clear asks MSG-Q001 and returns to ST-01', async ({ page }) => {
  await open(page);
  await fillValid(page);
  let asked = '';
  page.once('dialog', (d) => {
    asked = d.message();
    d.accept();
  });
  await page.click('#btn-clear');
  expect(asked).toBe(MSG['MSG-Q001']);
  await expect(state(page)).toHaveAttribute('data-state', 'ST-01');
  await expect(page.locator('#f-customer')).toHaveValue('');
});

test('spec consistency: parameters in the tables match the rule text', async ({ page }) => {
  await open(page);
  const br2 = page.locator('#BR-002');
  await expect(br2).toHaveAttribute('data-threshold', '1000000');
  await expect(br2).toContainText('1,000,000 円以上');
  await expect(page.locator('#VR-15')).toHaveAttribute('data-max', '9999');
  await expect(page.locator('#VR-18')).toHaveAttribute('data-max', '200');
  // Every ID link in the document points at an existing anchor.
  const broken = await page.evaluate(() =>
    [...document.querySelectorAll('a[href^="#"]')]
      .map((a) => a.getAttribute('href').slice(1))
      .filter((id) => id && !document.getElementById(id)),
  );
  expect(broken).toEqual([]);
});

for (const width of [320, 375, 768, 1024, 1440]) {
  test(`responsive: no horizontal page scroll at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await open(page);
    await page.click('[data-sample="error"]');
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
  });
}
