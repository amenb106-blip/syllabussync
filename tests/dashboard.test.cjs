const test = require('node:test');
const assert = require('node:assert/strict');
const { calendarLink, downloadData } = require('../static/dashboard.js');

test('Google draft encodes edited titles and all-day year rollover', () => {
    const url = new URL(calendarLink({ name: 'Final & project #1 / Review', date: '2026-12-31', time: '' }));
    assert.equal(url.searchParams.get('text'), 'Final & project #1 / Review');
    assert.equal(url.searchParams.get('dates'), '20261231/20270101');
});

test('Timed drafts preserve local clock time across midnight', () => {
    const url = new URL(calendarLink({ name: 'Quiz', date: '2026-12-31', time: '23:30' }));
    assert.equal(url.searchParams.get('dates'), '20261231T233000/20270101T003000');
});

test('Draft all-day ranges handle leap day', () => {
    const url = new URL(calendarLink({ name: 'Quiz', date: '2028-02-29', time: '' }));
    assert.equal(url.searchParams.get('dates'), '20280229/20280301');
});

test('Export reindexes included rows after removal and uses edits', () => {
    const data = downloadData([
        {id: 9, name: 'Skip', date: '', selected: false},
        {id: 2, name: ' Edited final ', date: '2026-12-20', time: '09:00', selected: true},
        {id: 7, name: 'Paper', date: '2026-12-21', selected: true},
    ], '15');
    assert.deepEqual(data.getAll('include'), ['0', '1']);
    assert.deepEqual(data.getAll('name'), ['Edited final', 'Paper']);
    assert.deepEqual(data.getAll('event_time'), ['09:00', '']);
    assert.equal(data.get('reminder_minutes'), '15');
});
