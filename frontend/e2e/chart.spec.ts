import { test, expect } from '@playwright/test';
import path from 'path';

const EVIDENCE_DIR = path.resolve(__dirname, '..', '..', '.sisyphus', 'evidence', 'e2e');

/**
 * Helper: take a named screenshot into the evidence directory.
 */
async function evidence(page: ReturnType<typeof test['info']>['page'], name: string) {
  await page.screenshot({ path: path.join(EVIDENCE_DIR, `${name}.png`), fullPage: true });
}

/**
 * Helper: select a ticker by opening the StockPicker dropdown,
 * typing in the search input, and pressing Enter.
 */
async function selectTicker(page: ReturnType<typeof test['info']>['page'], ticker: string) {
  // The StockPicker renders a <button> showing the current ticker
  // (e.g., "0700.HK — Tencent"). Click it to open the dropdown.
  const pickerButton = page.locator('button').filter({ hasText: /\.HK|\.US|選擇股票/ }).first();
  await pickerButton.click();

  // The search input inside the dropdown has autoFocus.
  // It's an <input type="text"> inside the open dropdown container.
  const searchInput = page.locator('input[type="text"][placeholder*="搜尋"], input[type="text"][placeholder*="Search"]').first();
  await searchInput.fill('');
  await searchInput.fill(ticker);
  await searchInput.press('Enter');
}

// ---------------------------------------------------------------------------
// Scenario 1: Chart renders on analyze
// ---------------------------------------------------------------------------
test.describe('PriceChart E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5173');
    // Wait for the app shell to render
    await expect(page.locator('header')).toBeVisible();
  });

  test('scenario-1: chart renders on analyze', async ({ page }) => {
    // Select a known-good ticker
    await selectTicker(page, '0700.HK');

    // Click the "技術分析" (Technical Analysis) button
    const analyzeBtn = page.getByRole('button', { name: /技術分析|Technical Analysis/ });
    await analyzeBtn.click();

    // Wait for the chart canvas to appear (ECharts renders a <canvas>)
    const chartCanvas = page.locator('canvas').first();
    await expect(chartCanvas).toBeVisible({ timeout: 15000 });

    // Verify no error message is visible
    const errorBanner = page.locator('.bg-red-900\\/30');
    await expect(errorBanner).toHaveCount(0);

    await evidence(page, 'scenario-1-chart-renders');
  });

  // ---------------------------------------------------------------------------
  // Scenario 2: Period switching — 日線 → 周線
  // ---------------------------------------------------------------------------
  test('scenario-2: period switching to weekly', async ({ page }) => {
    // Setup: ensure chart is loaded on daily
    await selectTicker(page, '0700.HK');
    await page.getByRole('button', { name: /技術分析|Technical Analysis/ }).click();
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15000 });

    // The period buttons are within the PeriodSelector component:
    // buttons with labels "分時", "5日", "日線", "周線", "月線", "季K", "年K"
    const weeklyBtn = page.getByRole('button', { name: '周線' });
    await weeklyBtn.click();

    // Wait for the chart to re-render after period change
    await page.waitForTimeout(2000);
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 10000 });

    // Verify the weekly button is now highlighted (active state: bg-blue-600)
    await expect(weeklyBtn).toHaveClass(/bg-blue-600/);

    await evidence(page, 'scenario-2-weekly-chart');
  });

  // ---------------------------------------------------------------------------
  // Scenario 3: 分時 (intraday) mode — line chart, date inputs disabled
  // ---------------------------------------------------------------------------
  test('scenario-3: intraday mode shows line chart', async ({ page }) => {
    // Setup
    await selectTicker(page, '0700.HK');
    await page.getByRole('button', { name: /技術分析|Technical Analysis/ }).click();
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15000 });

    // Click "分時" button
    const intradayBtn = page.getByRole('button', { name: '分時' });
    await intradayBtn.click();

    // Wait for chart to update
    await page.waitForTimeout(2000);
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 10000 });

    // Verify the intraday button is active
    await expect(intradayBtn).toHaveClass(/bg-blue-600/);

    // In intraday mode, date inputs should NOT be visible (disableDate: true)
    const dateInputs = page.locator('input[type="date"]');
    // They may exist as hidden or not exist at all; the PeriodSelector
    // conditionally renders them based on disableDate flag
    const periodDateInputs = page.locator('input[type="date"]');
    await expect(periodDateInputs).toHaveCount(0);

    await evidence(page, 'scenario-3-intraday-line');
  });

  // ---------------------------------------------------------------------------
  // Scenario 4: Indicator toggle — BOLL (Bollinger Bands)
  // ---------------------------------------------------------------------------
  test('scenario-4: BOLL indicator toggle', async ({ page }) => {
    // Setup: load daily chart
    await selectTicker(page, '0700.HK');
    await page.getByRole('button', { name: /技術分析|Technical Analysis/ }).click();
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15000 });

    // Switch to daily mode explicitly in case it isn't already
    const dailyBtn = page.getByRole('button', { name: '日線' });
    await dailyBtn.click();
    await page.waitForTimeout(1000);

    // The BOLL toggle is a <label> wrapping an <input type="checkbox">
    // and a <span>BOLL</span>. getByLabel should work.
    const bollCheckbox = page.getByLabel('BOLL');
    await expect(bollCheckbox).toBeVisible();

    // The BOLL checkbox should start unchecked (per defaultOverlays.bb: false)
    await expect(bollCheckbox).not.toBeChecked();

    // Check BOLL on
    await bollCheckbox.check();
    await page.waitForTimeout(1000);
    await evidence(page, 'scenario-4a-boll-on');

    // Uncheck BOLL off
    await bollCheckbox.uncheck();
    await page.waitForTimeout(1000);
    await evidence(page, 'scenario-4b-boll-off');

    // Re-check BOLL on to confirm re-enable
    await bollCheckbox.check();
    await page.waitForTimeout(1000);
    await expect(bollCheckbox).toBeChecked();
  });

  // ---------------------------------------------------------------------------
  // Scenario 5: Error state — invalid ticker
  // ---------------------------------------------------------------------------
  test('scenario-5: error state for invalid ticker', async ({ page }) => {
    // Type an invalid ticker
    await selectTicker(page, 'INVALID');

    // Click analyze
    const analyzeBtn = page.getByRole('button', { name: /技術分析|Technical Analysis/ });
    await analyzeBtn.click();

    // Wait for the error banner to appear
    const errorBanner = page.locator('.bg-red-900\\/30');
    await expect(errorBanner).toBeVisible({ timeout: 15000 });

    // Verify error message content is present (non-empty text inside the error div)
    await expect(errorBanner.locator('span')).not.toBeEmpty();

    // Chart should NOT display (placeholder or error state instead)
    const chartCanvas = page.locator('canvas');
    await expect(chartCanvas).toHaveCount(0);

    await evidence(page, 'scenario-5-error-state');
  });

  // ---------------------------------------------------------------------------
  // Scenario 6: Date range change
  // ---------------------------------------------------------------------------
  test('scenario-6: date range change updates chart', async ({ page }) => {
    // Setup: load daily chart
    await selectTicker(page, '0700.HK');
    await page.getByRole('button', { name: /技術分析|Technical Analysis/ }).click();
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15000 });

    // Switch to daily mode if needed
    await page.getByRole('button', { name: '日線' }).click();
    await page.waitForTimeout(1000);

    // The daily/周線/月線/季K/年K modes show date inputs inside the PeriodSelector
    const dateInputs = page.locator('input[type="date"]');
    await expect(dateInputs).toHaveCount(2); // startDate, endDate

    // Change start date to a year ago
    const today = new Date();
    const oneYearAgo = new Date(today);
    oneYearAgo.setFullYear(today.getFullYear() - 1);
    const oneYearAgoStr = oneYearAgo.toISOString().split('T')[0];

    // Fill in the new start date
    await dateInputs.first().fill(oneYearAgoStr);

    // Click the "套用" (Apply) button in the main App date range row
    const applyBtn = page.getByRole('button', { name: '套用' });
    await applyBtn.click();

    // Wait for chart to re-render
    await page.waitForTimeout(2000);
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 10000 });

    await evidence(page, 'scenario-6-date-range-change');
  });

  // ---------------------------------------------------------------------------
  // Scenario 7: 5日 (5-day) mode
  // ---------------------------------------------------------------------------
  test('scenario-7: 5-day mode shows line chart', async ({ page }) => {
    // Setup
    await selectTicker(page, '0700.HK');
    await page.getByRole('button', { name: /技術分析|Technical Analysis/ }).click();
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15000 });

    // Click "5日" — this period renders a line chart (not candlestick)
    const fiveDayBtn = page.getByRole('button', { name: '5日' });
    await fiveDayBtn.click();

    await page.waitForTimeout(2000);
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 10000 });

    // Verify active state
    await expect(fiveDayBtn).toHaveClass(/bg-blue-600/);

    // In 5-day mode, overlay toggles should be hidden (line chart type hides them)
    // The BOLL checkbox should not be visible
    await expect(page.getByLabel('BOLL')).toHaveCount(0);

    await evidence(page, 'scenario-7-5day-line');
  });

  // ---------------------------------------------------------------------------
  // Scenario 8: Multiple indicators toggled together
  // ---------------------------------------------------------------------------
  test('scenario-8: toggle multiple overlays simultaneously', async ({ page }) => {
    // Setup
    await selectTicker(page, '0700.HK');
    await page.getByRole('button', { name: /技術分析|Technical Analysis/ }).click();
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15000 });

    // Ensure daily mode
    await page.getByRole('button', { name: '日線' }).click();
    await page.waitForTimeout(1000);

    // Toggle on multiple indicators: MA20, BOLL, VOL
    const ma20Checkbox = page.getByLabel('MA20');
    const bollCheckbox = page.getByLabel('BOLL');
    const volCheckbox = page.getByLabel('VOL');

    await expect(ma20Checkbox).toBeVisible();
    await expect(bollCheckbox).toBeVisible();
    await expect(volCheckbox).toBeVisible();

    await ma20Checkbox.check();
    await bollCheckbox.check();
    await volCheckbox.check();

    await page.waitForTimeout(1000);

    await expect(ma20Checkbox).toBeChecked();
    await expect(bollCheckbox).toBeChecked();
    await expect(volCheckbox).toBeChecked();

    await evidence(page, 'scenario-8-multiple-overlays');
  });

  // ---------------------------------------------------------------------------
  // Scenario 9: Period cycle — verify all period buttons work
  // ---------------------------------------------------------------------------
  test('scenario-9: cycle through all period buttons', async ({ page }) => {
    // Setup
    await selectTicker(page, '0700.HK');
    await page.getByRole('button', { name: /技術分析|Technical Analysis/ }).click();
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15000 });

    const periods = [
      { label: '日線', expectLine: false },
      { label: '周線', expectLine: false },
      { label: '月線', expectLine: false },
      { label: '季K', expectLine: false },
      { label: '年K', expectLine: false },
    ];

    for (const { label } of periods) {
      const btn = page.getByRole('button', { name: label });
      await btn.click();
      await page.waitForTimeout(1500);

      // Chart should still be visible after each switch
      await expect(page.locator('canvas').first()).toBeVisible({ timeout: 8000 });

      // Active button should have bg-blue-600
      await expect(btn).toHaveClass(/bg-blue-600/);
    }

    // End on 日線 for a final screenshot
    await page.getByRole('button', { name: '日線' }).click();
    await page.waitForTimeout(1000);
    await evidence(page, 'scenario-9-daily-final');
  });
});
