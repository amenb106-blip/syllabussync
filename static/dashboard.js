(function () {
    const HOUR_MS = 3600000;
    const DAY_MS = 86400000;

    function calendarLink(event) {
        const start = new Date(`${event.date}T${event.time || '00:00'}:00Z`);
        const end = new Date(start.getTime() + (event.time ? HOUR_MS : DAY_MS));
        const stamp = (value) => event.time
            ? value.toISOString().slice(0, 19).replace(/[-:]/g, '')
            : value.toISOString().slice(0, 10).replace(/-/g, '');
        const params = new URLSearchParams({
            action: 'TEMPLATE',
            text: event.name.trim(),
            dates: `${stamp(start)}/${stamp(end)}`,
        });
        return `https://calendar.google.com/calendar/render?${params}`;
    }

    function downloadData(events, reminder) {
        const data = new FormData();
        events.filter((event) => event.selected).forEach((event, index) => {
            data.append('name', event.name.trim());
            data.append('event_date', event.date);
            data.append('event_time', event.time || '');
            data.append('include', String(index));
        });
        data.append('reminder_minutes', reminder);
        return data;
    }

    if (typeof module !== 'undefined') module.exports = { calendarLink, downloadData };
    if (typeof document === 'undefined') return;

    const $ = (selector) => document.querySelector(selector);

    const STAGES = ['upload', 'review', 'export'];
    const TAB_KEYS = ['ArrowLeft', 'ArrowRight', 'Home', 'End'];
    const EVENT_FIELDS = ['name', 'date', 'time'];
    const FIELD_LABELS = {
        name: 'Title',
        date: 'Date',
        time: 'Time (blank for all day)',
    };

    const ICONS = {
        file: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6"/></svg>',
        calendar: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18M8 15h8M12 11v8"/></svg>',
        remove: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/></svg>',
    };

    const EVENT_ROW_MARKUP = `
        <label class="event-select"><input type="checkbox"></label>
        <div class="event-field event-title-field">
            <label class="field-label">Title</label>
            <input data-field="name" type="text" required>
            <div class="event-meta">
                <span class="category-label"></span>
                <span class="event-source"></span>
            </div>
            <details class="event-details">
                <summary>Extraction details</summary>
                <p></p>
            </details>
        </div>
        <div class="event-field event-date-field">
            <label class="field-label">Date</label>
            <input data-field="date" type="date" min="2000-01-01" max="9998-12-31" required>
        </div>
        <div class="event-field event-time-field">
            <label class="field-label">Time</label>
            <input data-field="time" type="time">
        </div>
        <div class="event-actions">
            <a class="icon-button calendar-action" target="_blank" rel="noopener noreferrer">${ICONS.calendar}<span>&#8599;</span></a>
            <button class="icon-button remove-event" type="button">${ICONS.remove}</button>
        </div>`;

    const form = $('#syllabus-form');
    const yearInput = $('#academic_start_year');
    const extractButton = $('#find-events');
    const uploadTab = $('#upload-tab');
    const pasteTab = $('#paste-tab');
    const dropZone = $('#drop-zone');
    const pdfInput = $('#pdf');
    const textInput = $('#syllabus');
    const fileList = $('#file-list');
    const statusLine = $('#processing-status');
    const progressRegion = $('#progress-region');
    const progressBar = $('#batch-progress');
    const emptySchedule = $('#empty-schedule');
    const schedule = $('#schedule');
    const groupControls = $('#group-controls');
    const eventList = $('#event-list');
    const selectAll = $('#select-all');
    const undoBar = $('#undo-bar');
    const undoMessage = $('#undo-message');
    const undoButton = $('#undo-remove');
    const reminderSelect = $('#reminder');
    const downloadButton = $('#download');
    const exportStatus = $('#export-status');

    const files = [];
    const events = [];
    const removed = [];
    let sequence = 0;
    let busy = false;
    let downloading = false;
    let mode = 'pdf';

    const byDate = (first, second) => first.date.localeCompare(second.date);
    const plural = (count, word) => `${count} ${count === 1 ? word : `${word}s`}`;

    function setStage(name) {
        for (const item of STAGES) {
            const node = $(`#stage-${item}`);
            if (item === name) node.setAttribute('aria-current', 'step');
            else node.removeAttribute('aria-current');
        }
    }

    function markScheduleEdited() {
        if (!busy) setStage(events.length ? 'review' : 'upload');
        exportStatus.textContent = '';
    }

    function setMode(nextMode) {
        if (busy) return;
        mode = nextMode;
        const pdfMode = mode === 'pdf';
        $('#upload-panel').hidden = !pdfMode;
        $('#paste-panel').hidden = pdfMode;
        for (const [tab, active] of [[uploadTab, pdfMode], [pasteTab, !pdfMode]]) {
            tab.setAttribute('aria-selected', String(active));
            tab.tabIndex = active ? 0 : -1;
        }
    }

    function modeForKey(key) {
        if (key === 'Home') return 'pdf';
        if (key === 'End') return 'text';
        return mode === 'pdf' ? 'text' : 'pdf';
    }

    function alreadyQueued(file) {
        return files.some((item) => item.file
            && item.file.name === file.name
            && item.file.size === file.size
            && item.file.lastModified === file.lastModified);
    }

    function addFiles(incoming) {
        if (busy) return;
        let added = 0;
        let rejected = 0;
        for (const file of incoming) {
            if (!/\.pdf$/i.test(file.name)) {
                rejected++;
                continue;
            }
            if (alreadyQueued(file)) continue;
            files.push({ id: ++sequence, name: file.name, file, state: 'queued', message: 'Ready to extract' });
            added++;
        }
        const skipped = rejected
            ? ` ${plural(rejected, 'non-PDF file')} ${rejected === 1 ? 'was' : 'were'} skipped.`
            : '';
        statusLine.textContent = `${plural(added, 'PDF')} added.${skipped}`;
        renderFiles();
    }

    function fileButton(item) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'text-button';
        button.disabled = busy;
        button.textContent = item.state === 'error' ? 'Retry' : 'Remove';
        button.setAttribute('aria-label', `${button.textContent} ${item.name}`);
        button.addEventListener('click', () => {
            if (item.state === 'error') {
                processFiles([item]);
                return;
            }
            files.splice(files.indexOf(item), 1);
            renderFiles();
        });
        return button;
    }

    function fileRow(item) {
        const row = document.createElement('div');
        row.className = 'file-item';
        row.dataset.state = item.state;
        row.innerHTML = `
            ${ICONS.file}
            <div class="file-description">
                <span class="file-name"></span>
                <p class="file-status"></p>
            </div>`;
        row.querySelector('.file-name').textContent = item.name;
        row.querySelector('.file-status').textContent = item.message;
        if (item.state === 'queued' || item.state === 'error') row.append(fileButton(item));
        return row;
    }

    function renderFiles() {
        fileList.replaceChildren(...files.map(fileRow));
        const done = files.filter((item) => item.state === 'done').length;
        $('#rail-files').textContent = `${done} / ${files.length}`;
    }

    function setBusy(value) {
        busy = value;
        for (const field of [extractButton, uploadTab, pasteTab, pdfInput, textInput, yearInput]) {
            field.disabled = value;
        }
        extractButton.setAttribute('aria-busy', String(value));
        extractButton.textContent = value ? 'Extracting…' : 'Extract events →';
        renderFiles();
    }

    async function extractEvents(item, year) {
        const data = new FormData();
        data.append('academic_start_year', year);
        if (item.file) data.append('pdf', item.file);
        else data.append('syllabus', item.text);

        const response = await fetch('/api/extract', { method: 'POST', body: data });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error?.message || 'Unable to extract events. Try again.');

        const extracted = result.events.map((event) => ({
            ...event,
            id: ++sequence,
            source: item.name,
            selected: event.default_selected,
            time: event.time || '',
        }));
        extracted.sort(byDate);
        events.push(...extracted);
        return { count: extracted.length, warnings: result.warnings };
    }

    function failureMessage(error) {
        const interrupted = error instanceof SyntaxError || error instanceof TypeError;
        return interrupted ? 'Connection interrupted. Retry this document.' : error.message;
    }

    async function processFiles(batch) {
        if (busy || !batch.length || !yearInput.reportValidity()) return;
        const year = yearInput.value;
        const firstBatch = events.length === 0;
        setBusy(true);
        setStage('upload');
        progressRegion.hidden = false;
        progressBar.max = batch.length;
        progressBar.value = 0;

        let failed = 0;
        for (const [index, item] of batch.entries()) {
            item.state = 'processing';
            item.message = 'Extracting events…';
            statusLine.textContent = `${index} of ${batch.length} completed · Processing ${item.name}`;
            renderFiles();
            try {
                const { count, warnings } = await extractEvents(item, year);
                item.state = 'done';
                item.message = `${plural(count, 'event')} found`
                    + (warnings.length ? ` · ${warnings.join(' ')}` : '');
                if (!item.file && textInput.value === item.text) textInput.value = '';
            } catch (error) {
                item.state = 'error';
                item.message = failureMessage(error);
                failed++;
            }
            progressBar.value = index + 1;
            renderFiles();
            if (firstBatch) events.sort(byDate);
            renderEvents();
        }

        setBusy(false);
        statusLine.textContent = `${batch.length} of ${batch.length} completed`
            + (failed ? ` · ${failed} failed. Retry the affected documents.` : '.');
        setStage(events.length ? 'review' : 'upload');
    }

    function submitPastedText() {
        const text = textInput.value.trim();
        if (!text) {
            statusLine.textContent = 'Paste syllabus text to continue.';
            textInput.focus();
            return;
        }
        const pasted = files.filter((item) => !item.file).length + 1;
        const item = {
            id: ++sequence,
            name: `Pasted syllabus ${pasted}`,
            text,
            state: 'queued',
            message: 'Ready to extract',
        };
        files.push(item);
        processFiles([item]);
    }

    function submitQueuedFiles() {
        const batch = files.filter((item) => item.state === 'queued' && item.file);
        if (!batch.length) {
            statusLine.textContent = 'Choose PDFs to extract, or retry a failed document.';
            return;
        }
        processFiles(batch);
    }

    function updateSummary() {
        const selected = events.filter((event) => event.selected).length;
        $('#event-count').textContent = events.length;
        $('#rail-events').textContent = events.length;
        $('#rail-selected').textContent = selected;
        $('#selection-count').textContent = `${selected} selected`;
        downloadButton.disabled = !selected || downloading;
        selectAll.checked = !!events.length && selected === events.length;
        selectAll.indeterminate = selected > 0 && selected < events.length;
        for (const input of groupControls.querySelectorAll('input')) {
            const group = events.filter((event) => event.category === input.dataset.category);
            const included = group.filter((event) => event.selected).length;
            input.checked = included === group.length;
            input.indeterminate = included > 0 && included < group.length;
        }
    }

    function syncSelection() {
        markScheduleEdited();
        for (const event of events) {
            const toggle = document.getElementById(`event-${event.id}`).querySelector('.event-select input');
            toggle.checked = event.selected;
        }
        updateSummary();
    }

    function validateEvent(event) {
        const row = document.getElementById(`event-${event.id}`);
        for (const key of EVENT_FIELDS) {
            const field = row.querySelector(`[data-field="${key}"]`);
            field.setCustomValidity(key === 'name' && !field.value.trim() ? 'Enter an event title.' : '');
            if (!field.reportValidity()) return false;
        }
        return true;
    }

    function removeEvent(event) {
        const index = events.indexOf(event);
        removed.push({ event, index });
        events.splice(index, 1);
        markScheduleEdited();
        undoMessage.textContent = `Removed “${event.name}”.`;
        undoBar.hidden = false;
        renderEvents();
        undoButton.focus();
    }

    function restoreLastRemoved() {
        const last = removed.pop();
        if (!last) return;
        events.splice(Math.min(last.index, events.length), 0, last.event);
        markScheduleEdited();
        undoBar.hidden = !removed.length;
        if (removed.length) {
            undoMessage.textContent = `Removed “${removed[removed.length - 1].event.name}”.`;
        }
        renderEvents();
        document.getElementById(`event-${last.event.id}-name`).focus();
    }

    function eventRow(event) {
        const row = document.createElement('article');
        row.className = 'schedule-row';
        row.id = `event-${event.id}`;
        row.innerHTML = EVENT_ROW_MARKUP;

        const toggle = row.querySelector('.event-select input');
        const link = row.querySelector('.calendar-action');
        const remove = row.querySelector('.remove-event');

        function refreshLabels() {
            toggle.setAttribute('aria-label', `Include ${event.name}`);
            remove.setAttribute('aria-label', `Remove ${event.name}`);
            link.setAttribute('aria-label', `Open ${event.name} in Google Calendar (new tab)`);
            link.title = 'Open in Google Calendar';
            try {
                link.href = calendarLink(event);
            } catch {
                link.removeAttribute('href');
            }
        }

        toggle.checked = event.selected;
        toggle.addEventListener('change', () => {
            event.selected = toggle.checked;
            markScheduleEdited();
            updateSummary();
        });

        for (const input of row.querySelectorAll('[data-field]')) {
            const key = input.dataset.field;
            input.id = `event-${event.id}-${key}`;
            input.previousElementSibling.htmlFor = input.id;
            input.setAttribute('aria-label', `${FIELD_LABELS[key]} for ${event.name}`);
            input.value = event[key];
            input.addEventListener('input', () => {
                input.setCustomValidity('');
                event[key] = input.value;
                markScheduleEdited();
                refreshLabels();
            });
        }

        row.querySelector('.category-label').textContent = event.category;
        row.querySelector('.event-source').textContent = event.source;
        row.querySelector('.event-details p').textContent = event.reason;
        remove.title = 'Remove event';
        refreshLabels();

        link.addEventListener('click', (click) => {
            if (!validateEvent(event)) click.preventDefault();
        });
        remove.addEventListener('click', () => removeEvent(event));
        return row;
    }

    function groupControl(category) {
        const label = document.createElement('label');
        label.className = 'group-select';
        const input = document.createElement('input');
        input.type = 'checkbox';
        input.dataset.category = category;
        input.setAttribute('aria-label', `Include all ${category} events`);
        input.addEventListener('change', () => {
            for (const event of events) {
                if (event.category === category) event.selected = input.checked;
            }
            syncSelection();
        });
        label.append(input, document.createTextNode(category));
        return label;
    }

    function emptyScheduleMessage(processed) {
        if (removed.length) return 'Restore a removed event with Undo, or add another syllabus.';
        if (processed) return 'No dated events found. Try another syllabus or paste its text.';
        return 'Upload a syllabus to build your schedule.';
    }

    function focusedField() {
        const active = document.activeElement;
        if (!active || !active.id.startsWith('event-')) return null;
        return { id: active.id, start: active.selectionStart, end: active.selectionEnd };
    }

    function restoreFocus(field) {
        if (!field) return;
        const active = document.getElementById(field.id);
        if (!active) return;
        active.focus({ preventScroll: true });
        if (typeof field.start === 'number') active.setSelectionRange(field.start, field.end);
    }

    function renderEvents() {
        const field = focusedField();
        const processed = files.some((item) => item.state === 'done');

        emptySchedule.hidden = events.length > 0;
        emptySchedule.querySelector('h3').textContent = processed ? 'No events to review' : 'No events yet';
        emptySchedule.querySelector('p').textContent = emptyScheduleMessage(processed);
        schedule.hidden = !events.length;
        $('#schedule-caption').textContent = events.length
            ? 'Edit inline. A blank time means all day.'
            : 'Your extracted dates will appear here.';

        const categories = [...new Set(events.map((event) => event.category))];
        groupControls.replaceChildren(...categories.map(groupControl));
        eventList.replaceChildren(...events.map(eventRow));

        updateSummary();
        restoreFocus(field);
    }

    function saveFile(blob, filename) {
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename;
        document.body.append(anchor);
        anchor.click();
        anchor.remove();
        setTimeout(() => URL.revokeObjectURL(url), 10000);
    }

    async function downloadCalendar() {
        if (downloading || !events.some((event) => event.selected)) return;
        for (const event of events.filter((item) => item.selected)) {
            if (!validateEvent(event)) return;
        }
        downloading = true;
        updateSummary();
        downloadButton.setAttribute('aria-busy', 'true');
        exportStatus.textContent = 'Preparing calendar…';
        try {
            const response = await fetch('/download', {
                method: 'POST',
                body: downloadData(events, reminderSelect.value),
            });
            const isCalendar = response.headers.get('content-type')?.includes('text/calendar');
            if (!response.ok || !isCalendar) {
                throw new Error('Unable to download the calendar. Check your events and try again.');
            }
            saveFile(await response.blob(), 'syllabus.ics');
            exportStatus.textContent = 'Calendar file prepared.';
            setStage('export');
        } catch (error) {
            exportStatus.textContent = error.message;
        } finally {
            downloading = false;
            downloadButton.setAttribute('aria-busy', 'false');
            updateSummary();
        }
    }

    uploadTab.addEventListener('click', () => setMode('pdf'));
    pasteTab.addEventListener('click', () => setMode('text'));
    for (const tab of document.querySelectorAll('.tab')) {
        tab.addEventListener('keydown', (event) => {
            if (!TAB_KEYS.includes(event.key)) return;
            event.preventDefault();
            setMode(modeForKey(event.key));
            (mode === 'pdf' ? uploadTab : pasteTab).focus();
        });
    }

    pdfInput.addEventListener('change', (event) => {
        addFiles(event.target.files);
        event.target.value = '';
    });
    for (const name of ['dragenter', 'dragover']) {
        dropZone.addEventListener(name, (event) => {
            event.preventDefault();
            if (!busy) dropZone.classList.add('drag-over');
        });
    }
    for (const name of ['dragleave', 'drop']) {
        dropZone.addEventListener(name, (event) => {
            event.preventDefault();
            dropZone.classList.remove('drag-over');
            if (name === 'drop') addFiles(event.dataTransfer.files);
        });
    }
    window.addEventListener('dragover', (event) => event.preventDefault());
    window.addEventListener('drop', (event) => event.preventDefault());

    form.addEventListener('submit', (event) => {
        event.preventDefault();
        if (busy) return;
        if (mode === 'text') submitPastedText();
        else submitQueuedFiles();
    });

    selectAll.addEventListener('change', () => {
        for (const event of events) event.selected = selectAll.checked;
        syncSelection();
    });
    undoButton.addEventListener('click', restoreLastRemoved);
    reminderSelect.addEventListener('change', markScheduleEdited);
    downloadButton.addEventListener('click', downloadCalendar);

    renderEvents();
})();
