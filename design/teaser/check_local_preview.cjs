// Regression: a direct file:// preview must not depend on ESM or JSON fetches.
// Requires Playwright for development only; no test tools ship to visitors.
const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_BIN || '/usr/bin/google-chrome',
    headless: true,
    args: ['--no-sandbox'],
  });
  try {
    const page = await browser.newPage({ reducedMotion: 'reduce' });
    const requests = [], errors = [];
    page.on('request', request => requests.push(request.url()));
    page.on('pageerror', error => errors.push(error.message));
    const url = process.argv[2] || pathToFileURL(path.resolve(__dirname, '../../index.html')).href;
    await page.goto(url);
    assert(!requests.some(url => url.includes('teaser-viewer.bundle.js')));
    await page.locator('[data-explore]').click();
    await page.waitForFunction(() => {
      const host = document.querySelector('.teaser-explorer');
      return !!host.querySelector('canvas') && host.querySelector('.viewer-status').hidden;
    });
    assert.equal(await page.locator('canvas').count(), 1);
    assert.equal(await page.locator('.viewer-tile').count(), 8);
    assert(await page.locator('[data-teaser-real]').isVisible());
    await page.locator('[data-whole]').click();
    assert.equal(await page.locator('[data-follow]').getAttribute('aria-pressed'), 'false');
    await page.locator('[data-follow]').click();
    await page.locator('[data-close]').click();
    await page.locator('[data-explore]').click();
    assert.equal(requests.filter(url => url.includes('teaser-viewer.bundle.js')).length, 1);
    assert(!requests.some(url => /teaser-domains\.json|teaser-motion\.mjs|vendor\/three/.test(url)));
    assert.deepEqual(errors, []);
    console.log('PASS: local-file viewer, lazy single-file loading, eight terrains, persistent left video, cached reopening.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
