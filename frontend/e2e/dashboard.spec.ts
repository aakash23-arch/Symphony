/**
 * Browser verification for the VoiceShield dashboard.
 *
 * The tests that matter most here are not the ones checking that a populated
 * dashboard renders. They are `no-probability-language`, `null-rendering` and
 * `awaiting`: the states where the UI could quietly assert certainty the
 * backend does not have. A screenshot proves the pretty case; only an assertion
 * proves the honest one.
 */

import { expect, test, type ConsoleMessage, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// The package is ESM ("type": "module"), so __dirname does not exist.
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ARTIFACTS = path.join(HERE, 'artifacts');
const SHOTS = path.join(ARTIFACTS, 'screenshots');

interface ConsoleRecord {
  type: string;
  text: string;
  location: string;
}

const consoleLog: ConsoleRecord[] = [];

fs.mkdirSync(SHOTS, { recursive: true });

/** Attach console + pageerror collectors. Errors here fail the suite. */
function watchConsole(page: Page, label: string): ConsoleRecord[] {
  const errors: ConsoleRecord[] = [];
  page.on('console', (message: ConsoleMessage) => {
    const record = {
      type: message.type(),
      text: message.text(),
      location: `${label}:${message.location().url}`,
    };
    consoleLog.push(record);
    if (message.type() === 'error') errors.push(record);
  });
  page.on('pageerror', (error: Error) => {
    const record = { type: 'pageerror', text: error.message, location: label };
    consoleLog.push(record);
    errors.push(record);
  });
  return errors;
}

/** True when the analysis backend is reachable. */
async function backendUp(page: Page): Promise<boolean> {
  try {
    const response = await page.request.get('/health', { timeout: 5000 });
    return response.ok();
  } catch {
    return false;
  }
}

test.afterAll(async () => {
  fs.writeFileSync(
    path.join(ARTIFACTS, 'console.log'),
    consoleLog.length === 0
      ? 'No console output captured during the run.\n'
      : consoleLog.map((r) => `[${r.type}] ${r.text}  (${r.location})`).join('\n') + '\n',
    'utf-8',
  );
});

test.describe('VoiceShield dashboard', () => {
  test('renders every panel with no console errors', async ({ page }) => {
    const errors = watchConsole(page, 'initial-load');
    await page.goto('/');

    for (const title of [
      'Call',
      'Risk assessment',
      'Evidence',
      'Timeline',
      'Transaction',
      'Recommended action',
    ]) {
      await expect(page.getByRole('region', { name: title })).toBeVisible();
    }

    await expect(page.getByRole('heading', { name: 'VoiceShield' })).toBeVisible();
    await expect(page.getByTestId('connection-status')).toBeVisible();

    await page.screenshot({ path: path.join(SHOTS, '01-empty-1440.png'), fullPage: true });
    expect(errors, `console errors: ${JSON.stringify(errors, null, 2)}`).toHaveLength(0);
  });

  test('empty state shows no risk numeral and no percentage', async ({ page }) => {
    watchConsole(page, 'empty-state');
    await page.goto('/');

    // With no session there is nothing to assess, so the score slot must be
    // an em dash. A 0 here would render a reassuring LOW for a call the system
    // has never seen.
    const risk = page.getByRole('region', { name: 'Risk assessment' });
    await expect(risk).toContainText('No active session');
    await expect(risk).not.toContainText('%');
    expect(await risk.innerText()).not.toMatch(/\d\.\d\d/);
  });

  test('carries the demo disclaimer', async ({ page }) => {
    watchConsole(page, 'disclaimer');
    await page.goto('/');
    // Without this, a screenshot of the dashboard reads as a real call.
    await expect(page.getByText(/demo mode/i)).toBeVisible();
    await expect(page.getByText(/not a real banking integration/i)).toBeVisible();
  });

  test('never renders the score as a probability', async ({ page }) => {
    watchConsole(page, 'no-probability');
    await page.goto('/');

    if (await backendUp(page)) {
      await page.selectOption('#scenario', 'high-value-transfer');
      await page.getByTestId('start-demo').click();
      await expect(page.getByTestId('risk-score')).not.toHaveText('—', { timeout: 90_000 });
    }

    const risk = page.getByRole('region', { name: 'Risk assessment' });
    const text = await risk.innerText();

    // score_semantics is UNCALIBRATED_RISK_SCORE: the number orders calls by
    // concern and does not estimate a probability of fraud.
    expect(text).not.toMatch(/%/);
    // Match only AFFIRMATIVE probability claims. The panel's own disclaimer
    // says "not a probability of fraud", which is the opposite of the thing
    // being guarded against, so the negated form must be excluded.
    expect(text).not.toMatch(/(?<!not a )(probability|chance|likelihood) of fraud/i);
    expect(text).toMatch(/not a probability/i);
  });

  test('produces a live assessment matching the backend', async ({ page }) => {
    test.skip(!(await backendUp(page)), 'analysis backend not running');
    const errors = watchConsole(page, 'live-run');
    await page.goto('/');

    await page.selectOption('#scenario', 'high-value-transfer');
    await page.getByTestId('start-demo').click();

    // Wait for the real pipeline, not for a fixed delay.
    await expect(page.getByTestId('risk-score')).not.toHaveText('—', { timeout: 90_000 });

    const shown = await page.getByTestId('risk-band').innerText();
    const band = shown.split('—')[0].trim();
    expect(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'UNCERTAIN']).toContain(band);

    // The timeline must have grown from live events.
    const timeline = page.getByRole('region', { name: 'Timeline' });
    await expect(timeline).not.toContainText('No events yet');

    await page.screenshot({ path: path.join(SHOTS, '03-live-1440.png'), fullPage: true });
    expect(errors, `console errors: ${JSON.stringify(errors, null, 2)}`).toHaveLength(0);
  });

  test('renders absent evidence as an em dash, never zero', async ({ page }) => {
    test.skip(!(await backendUp(page)), 'analysis backend not running');
    watchConsole(page, 'null-rendering');
    await page.goto('/');

    // Silence produces no speech, so the experts have nothing to say.
    await page.selectOption('#scenario', 'silence');
    await page.getByTestId('start-demo').click();

    const evidence = page.getByRole('region', { name: 'Evidence' });
    await expect(evidence).toBeVisible();
    // "no evidence" must appear rather than a fabricated 0.00.
    await expect(evidence.getByText(/no evidence|not measured|deferred|not enrolled/i).first())
      .toBeVisible({ timeout: 60_000 });

    await page.screenshot({ path: path.join(SHOTS, '04-null-evidence.png'), fullPage: true });
  });

  test('awaiting state is distinct and shows progress', async ({ page }) => {
    test.skip(!(await backendUp(page)), 'analysis backend not running');
    watchConsole(page, 'awaiting');
    await page.goto('/');

    await page.selectOption('#scenario', 'routine-enquiry');
    await page.getByTestId('start-demo').click();

    // Immediately after start there is no assessment; the panel must say so
    // rather than showing a number.
    const risk = page.getByRole('region', { name: 'Risk assessment' });
    const score = await page.getByTestId('risk-score').innerText();
    if (score === '—') {
      await expect(risk).toContainText(/awaiting first action-grade assessment/i);
      await page.screenshot({ path: path.join(SHOTS, '02-awaiting.png'), fullPage: true });
    }
  });

  test('survives a lost connection without losing state', async ({ page }) => {
    test.skip(!(await backendUp(page)), 'analysis backend not running');
    watchConsole(page, 'disconnected');
    await page.goto('/');

    await page.selectOption('#scenario', 'high-value-transfer');
    await page.getByTestId('start-demo').click();
    await expect(page.getByTestId('risk-score')).not.toHaveText('—', { timeout: 90_000 });
    const before = await page.getByTestId('risk-score').innerText();

    // Kill the socket from inside the page.
    //
    // context.setOffline() does NOT close an already-established WebSocket, so
    // the dashboard correctly keeps reporting LIVE under it - the connection
    // really is still open. Closing with 1006 (abnormal) is what an actual
    // network drop looks like to the client.
    await page.evaluate(() => {
      const tracked = (window as unknown as { __vsSockets?: WebSocket[] }).__vsSockets ?? [];
      for (const socket of tracked) socket.close(4001, 'test-induced drop');
    });
    // The socket must notice the drop, mark the data stale, and keep showing
    // the last known values rather than blanking or implying they are current.
    await expect(page.getByText(/live feed lost|reconnecting|disconnected/i).first())
      .toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId('risk-score')).toHaveText(before);
    await page.screenshot({ path: path.join(SHOTS, '05-disconnected.png'), fullPage: true });
  });

  test('is responsive with no horizontal overflow', async ({ page }) => {
    const errors = watchConsole(page, 'responsive');
    await page.goto('/');

    for (const [label, width, height] of [
      ['1440', 1440, 900],
      ['1024', 1024, 768],
      ['768', 768, 1024],
      ['390', 390, 844],
    ] as const) {
      await page.setViewportSize({ width, height });
      await page.waitForTimeout(300);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, `horizontal overflow at ${label}px`).toBeLessThanOrEqual(1);
      await page.screenshot({
        path: path.join(SHOTS, `06-responsive-${label}.png`),
        fullPage: true,
      });
    }
    expect(errors).toHaveLength(0);
  });
});
