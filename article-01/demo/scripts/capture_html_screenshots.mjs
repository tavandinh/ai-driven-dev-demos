// Screenshots of order_design.html for the article (real browser, Chromium via @playwright/test).
// Run from the repository root:
//   node article-01/demo/scripts/capture_html_screenshots.mjs
import { fileURLToPath, pathToFileURL } from 'node:url';
import { chromium } from '@playwright/test';

const DEMO = new URL('../', import.meta.url);
const URL_ = pathToFileURL(fileURLToPath(new URL('order_design.html', DEMO))).href;
const shot = (name) => fileURLToPath(new URL(`screenshots/${name}`, DEMO));

const browser = await chromium.launch();
async function page(width, height = 900) {
  const p = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  await p.goto(URL_);
  return p;
}
// Load a sample, then pin the dates so every screenshot is reproducible.
async function sample(p, name) {
  await p.click(`[data-sample="${name}"]`);
  await p.fill('#f-orderDate', '2026-12-01');
  await p.locator('#f-orderDate').blur();
  await p.fill('#f-delivery', name === 'error' ? '2026-12-01' : '2026-12-08');
  await p.locator('#f-delivery').blur();
}

// 1. Whole document, top of the page
let p = await page(1440, 900);
await p.screenshot({ path: shot('html-spec-top.png') });

// 2. Preview with valid data (ST-02, confirm enabled)
await sample(p, 'normal');
await p.locator('#preview').screenshot({ path: shot('html-preview-valid.png') });

// 3. Spec ID overlay
await p.check('#demo-ids');
await p.locator('#preview').screenshot({ path: shot('html-preview-spec-ids.png') });
await p.close();

// 4. Field validation errors (ST-03)
p = await page(1440);
await sample(p, 'error');
await p.locator('#preview').screenshot({ path: shot('html-validation-error.png') });
await p.close();

// 5. Error summary on confirm (BR-001 / VR-19, MSG-E011)
p = await page(1440);
await sample(p, 'normal');
await p.locator('#lines tr').nth(1).locator('button.del').click();
await p.locator('#lines tr input.code').first().fill('P-9000');
await p.locator('#lines tr input.qty').first().fill('1');
await p.locator('#f-remarks').click();
await p.locator('#f-remarks').blur();
await p.click('#btn-confirm');
await p.locator('#preview').screenshot({ path: shot('html-confirm-error-summary.png') });
await p.close();

// 6. High-value order: confirm screen (BR-002, ST-04) and completion (ST-06)
p = await page(1440);
await sample(p, 'approval');
// Approver now required (BR-002) but not chosen: 確認 stays disabled (BR-004).
// Crop from the line items down to the buttons.
{
  await p.locator('fieldset[data-area="A-04"]').evaluate((e) => e.scrollIntoView());
  const top = await p.locator('fieldset[data-area="A-04"]').boundingBox();
  const bottom = await p.locator('.scr-buttons').boundingBox();
  const screenBox = await p.locator('#screen').boundingBox();
  await p.screenshot({
    path: shot('html-approval-required.png'),
    clip: {
      x: screenBox.x,
      y: top.y - 8,
      width: screenBox.width,
      height: bottom.y + bottom.height - top.y + 16,
    },
  });
}
await p.selectOption('#f-approver', 'U101');
await p.locator('#preview').screenshot({ path: shot('html-approval-input.png') });
await p.click('#btn-confirm');
await p.locator('#preview').screenshot({ path: shot('html-approval-confirm.png') });
await p.click('#btn-register');
await p.waitForSelector('#screen[data-state="ST-06"]');
await p.locator('#preview').screenshot({ path: shot('html-approval-complete.png') });

// 7. Spec tables
await p.locator('#items').screenshot({ path: shot('html-item-definition.png') });
await p.locator('#rules').screenshot({ path: shot('html-business-rules.png') });
await p.goto(`${URL_}#BR-002`);
await p.waitForTimeout(200);
await p.screenshot({ path: shot('html-crosslink-target.png') });
await p.close();

// 8. Phone width
p = await page(320, 900);
await sample(p, 'error');
await p.locator('#preview').screenshot({ path: shot('html-mobile-320.png') });
await p.close();

await browser.close();
console.log('screenshots written');
