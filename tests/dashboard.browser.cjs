const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs/promises');
const os = require('node:os');

(async () => {
    const browser = await chromium.launch({ channel: 'chrome', headless: true });
    const screenshotDir = process.env.SCREENSHOT_DIR || path.join(os.tmpdir(), 'syllabussync-screenshots');
    await fs.mkdir(screenshotDir, { recursive: true });
    const errors = [];
    try {
        for (const width of [1440, 1024, 390, 320]) {
            const page = await browser.newPage({ viewport: { width, height: 960 }, reducedMotion: 'reduce' });
            page.on('pageerror', error => errors.push(error.message));
            const fixture = (name, date, selected = true, time = null) => ({ name, date, time, category: selected ? 'Assessments' : 'Readings', default_selected: selected, confidence: selected ? 'high' : 'low', reason: 'Dated item in the syllabus.' });
            let calls = 0;
            let failures = 0;
            let release;
            let releasePending;
            let markPending;
            const pendingStarted = new Promise(resolve => { markPending = resolve; });
            await page.route('**/api/extract', async route => {
                calls++;
                const body = route.request().postDataBuffer().toString();
                if (body.includes('first.pdf')) {
                    await new Promise(resolve => { release = resolve; });
                    await route.fulfill({ json: { events: [fixture('Final examination', '2026-12-31', true, '23:30'), fixture('Read chapter 3', '2026-09-20', false)], warnings: [] } });
                } else if (body.includes('failed.pdf') && !failures++) {
                    await route.fulfill({ status: 502, json: { error: { message: 'Unable to extract events. Try again shortly.' } } });
                } else if (body.includes('empty.pdf')) {
                    await route.fulfill({ json: { events: [], warnings: [] } });
                } else if (body.includes('pending.pdf')) {
                    await new Promise(resolve => { releasePending = resolve; markPending(); });
                    await route.fulfill({ json: { events: [], warnings: [] } });
                } else {
                    await route.fulfill({ json: { events: [fixture('Research methods and interdisciplinary analysis final project presentation with extended title', '2026-10-01')], warnings: ['PDF page 3 was skipped. Check that page.'] } });
                }
            });
            async function shot(state) {
                await page.screenshot({ path: path.join(screenshotDir, `${width}-${state}.png`), fullPage: true });
                assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${width} ${state} has horizontal overflow`);
            }
            await page.goto(process.env.BASE_URL || 'http://127.0.0.1:5000');
            await page.locator('#page-title').waitFor();
            await page.evaluate(() => document.fonts.ready);
            assert.deepEqual(await page.evaluate(() => [...document.fonts].filter(font => font.status === 'loaded').map(font => font.family).sort()), ['Manrope', 'Sora']);
            assert.equal(await page.locator('#download').isDisabled(), true);
            await shot('ready');
            await page.locator('#upload-tab').focus();
            await page.keyboard.press('ArrowRight');
            assert.equal(await page.locator('#paste-panel').isVisible(), true);
            await page.keyboard.press('ArrowLeft');
            await page.locator('#pdf').setInputFiles([
                { name: 'first.pdf', mimeType: 'application/pdf', buffer: Buffer.from('mock') },
                { name: 'failed.pdf', mimeType: 'application/pdf', buffer: Buffer.from('mock') },
            ]);
            await page.locator('#find-events').click();
            await page.waitForFunction(() => document.querySelector('#processing-status').textContent.includes('Processing first.pdf'));
            assert.equal(await page.locator('#find-events').isDisabled(), true);
            await shot('processing');
            release();
            await page.waitForFunction(() => document.querySelector('#processing-status').textContent.includes('1 failed'));
            assert.equal(await page.locator('.schedule-row').count(), 2);
            assert.equal(await page.locator('[data-field="date"]').first().inputValue(), '2026-09-20');
            await shot('partial-error');
            const title = page.locator('[data-field="name"]').nth(1);
            await title.fill('Edited final & project #1');
            await page.locator('[data-field="date"]').nth(1).fill('2026-12-31');
            const google = new URL(await page.locator('.calendar-action').nth(1).getAttribute('href'));
            assert.equal(google.searchParams.get('text'), 'Edited final & project #1');
            assert.equal(google.searchParams.get('dates'), '20261231T233000/20270101T003000');
            await page.getByRole('button', { name: 'Retry failed.pdf', exact: true }).click();
            await page.waitForFunction(() => document.querySelectorAll('.schedule-row').length === 3);
            assert.equal(calls, 3);
            assert.equal(await title.inputValue(), 'Edited final & project #1');
            await page.locator('#pdf').setInputFiles([
                { name: 'very-long-course-filename-with-several-departments-and-a-detailed-academic-syllabus-for-the-autumn-term.pdf', mimeType: 'application/pdf', buffer: Buffer.from('mock') },
                { name: 'pending.pdf', mimeType: 'application/pdf', buffer: Buffer.from('mock') },
            ]);
            await page.locator('#find-events').click();
            await pendingStarted;
            assert.equal(await page.locator('.schedule-row').count(), 4);
            assert.equal(await page.locator('#find-events').isDisabled(), true);
            assert.equal(await title.inputValue(), 'Edited final & project #1');
            await page.locator('#select-all').check();
            await page.getByRole('checkbox', { name: 'Include all Readings events', exact: true }).uncheck();
            assert.equal(await page.locator('#rail-selected').textContent(), '3');
            const pendingDownload = page.waitForEvent('download');
            await page.locator('#download').click();
            const pendingContents = await fs.readFile(await (await pendingDownload).path(), 'utf8');
            assert.equal((pendingContents.match(/BEGIN:VEVENT/g) || []).length, 3);
            assert.match(pendingContents, /Edited final & project #1/);
            releasePending();
            await page.waitForFunction(() => !document.querySelector('#find-events').disabled);
            await page.locator('.remove-event').nth(1).click();
            assert.equal(await page.locator('.schedule-row').count(), 3);
            await page.locator('#undo-remove').click();
            assert.equal(await page.locator('.schedule-row').count(), 4);
            assert.equal(await title.inputValue(), 'Edited final & project #1');
            await page.locator('#select-all').check();
            await page.locator('#select-all').uncheck();
            assert.equal(await page.locator('#download').isDisabled(), true);
            await page.getByRole('checkbox', { name: 'Include all Assessments events', exact: true }).check();
            assert.equal(await page.locator('#rail-selected').textContent(), '3');
            await page.locator('.event-select input').first().uncheck();
            await page.locator('[data-field="name"]').first().fill('');
            await page.locator('#reminder').selectOption('15');
            const download = page.waitForEvent('download');
            await page.locator('#download').click();
            const saved = await download;
            const contents = await fs.readFile(await saved.path(), 'utf8');
            assert.match(contents, /Edited final & project #1/);
            assert.match(contents, /TRIGGER:-PT15M/);
            assert.equal((contents.match(/BEGIN:VEVENT/g) || []).length, 3);
            await page.locator('[data-field="name"]').first().fill('Read chapter 3');
            assert.equal(await page.locator('#stage-review').getAttribute('aria-current'), 'step');
            await shot('populated');
            await page.locator('[data-field="name"]').nth(1).fill('   ');
            await page.locator('#download').click();
            assert.equal(await page.locator('[data-field="name"]').nth(1).evaluate(el => el.validity.valid), false);
            while (await page.locator('.remove-event').count()) await page.locator('.remove-event').first().click();
            await shot('removed-all');
            await page.reload();
            await page.locator('#pdf').setInputFiles({ name: 'empty.pdf', mimeType: 'application/pdf', buffer: Buffer.from('mock') });
            await page.locator('#find-events').click();
            await page.waitForFunction(() => document.querySelector('.file-status')?.textContent.includes('0 events found'));
            assert.equal(await page.locator('#empty-schedule').isVisible(), true);
            await shot('empty-results');
            await page.close();
            console.log(`${width}px: batch, progress, retry, append, edits, selection, removal/Undo, validation, real ICS export, and layout passed`);
        }
        assert.deepEqual(errors, []);
        console.log(`Screenshots: ${screenshotDir}`);
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
