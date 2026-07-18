(function () {
    'use strict';

    const cfg = window.CV_EDITOR_CONFIG;
    let state = cfg.initialData;
    let renderTimer = null;
    let dirty = false;

    const form = document.getElementById('cvForm');
    const previewFrame = document.getElementById('previewFrame');
    const saveStatus = document.getElementById('saveStatus');
    const saveBtn = document.getElementById('saveBtn');
    const previewBtn = document.getElementById('previewBtn');
    const photoPreview = document.getElementById('photoPreview');
    const photoFileInput = document.getElementById('photoFileInput');
    const photoRemoveBtn = document.getElementById('photoRemoveBtn');
    const photoUploadStatus = document.getElementById('photoUploadStatus');
    const MAX_PHOTO_BYTES = 1 * 1024 * 1024;

    // ---------- path helpers ----------
    function getPath(obj, path) {
        return path.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj);
    }
    function setPath(obj, path, value) {
        const keys = path.split('.');
        let cur = obj;
        for (let i = 0; i < keys.length - 1; i++) {
            if (cur[keys[i]] == null) cur[keys[i]] = {};
            cur = cur[keys[i]];
        }
        cur[keys[keys.length - 1]] = value;
    }

    function markDirty() {
        dirty = true;
        saveStatus.textContent = 'Non enregistré';
        saveStatus.style.color = '#fbbf24';
    }
    function markSaved() {
        dirty = false;
        saveStatus.textContent = 'Enregistré';
        saveStatus.style.color = '#86efac';
        setTimeout(() => { if (!dirty) saveStatus.textContent = ''; }, 2000);
    }

    // ---------- API ----------
    async function apiPostJson(url, body) {
        const res = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': cfg.csrfToken,
            },
            body: JSON.stringify(body),
        });
        return res.json();
    }

    // ---------- preview ----------
    function scheduleRender() {
        clearTimeout(renderTimer);
        renderTimer = setTimeout(renderPreview, 250);
    }

    async function renderPreview() {
        const result = await apiPostJson(cfg.endpoints.render, { data: state });
        const doc = `<!DOCTYPE html><html><head><meta charset="UTF-8">
            <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/7.0.1/css/all.min.css">
            <link rel="stylesheet" href="/static/cv_templates/classic_sidebar/style.css">
            </head><body>${result.html || ''}</body></html>`;
        previewFrame.srcdoc = doc;
    }

    // ---------- static field binding ----------
    function bindStaticFields() {
        form.querySelectorAll('[data-path]').forEach((el) => {
            const path = el.getAttribute('data-path');
            el.value = getPath(state, path) ?? '';
            el.oninput = () => {
                setPath(state, path, el.value);
                markDirty();
                scheduleRender();
            };
        });
    }

    // ---------- repeat-list ----------
    function buildRepeatLists() {
        form.querySelectorAll('.repeat-list').forEach((container) => {
            const path = container.getAttribute('data-list');
            const fields = container.getAttribute('data-fields').split(',');
            const placeholders = container.getAttribute('data-placeholders').split(',');
            renderRepeatList(container, path, fields, placeholders);
        });
    }

    function renderRepeatList(container, path, fields, placeholders) {
        container.innerHTML = '';
        const arr = getPath(state, path) || [];
        arr.forEach((item, idx) => {
            const row = document.createElement('div');
            row.className = 'repeat-row';
            fields.forEach((f, fi) => {
                const input = document.createElement('input');
                input.type = 'text';
                input.placeholder = placeholders[fi] || '';
                input.value = item[f] || '';
                input.oninput = () => {
                    arr[idx][f] = input.value;
                    markDirty();
                    scheduleRender();
                };
                row.appendChild(input);
            });
            const rm = document.createElement('button');
            rm.type = 'button';
            rm.className = 'remove-btn';
            rm.innerHTML = '<i class="fa-solid fa-trash"></i>';
            rm.onclick = () => {
                arr.splice(idx, 1);
                markDirty();
                renderRepeatList(container, path, fields, placeholders);
                scheduleRender();
            };
            row.appendChild(rm);
            container.appendChild(row);
        });
    }

    // ---------- repeat-simple ----------
    function buildRepeatSimples() {
        form.querySelectorAll('.repeat-simple').forEach((container) => {
            const path = container.getAttribute('data-list');
            const placeholder = container.getAttribute('data-placeholder') || '';
            renderRepeatSimple(container, path, placeholder);
        });
    }

    function renderRepeatSimple(container, path, placeholder) {
        container.innerHTML = '';
        const arr = getPath(state, path) || [];
        arr.forEach((val, idx) => {
            const row = document.createElement('div');
            row.className = 'repeat-row';
            const input = document.createElement('input');
            input.type = 'text';
            input.placeholder = placeholder;
            input.value = val || '';
            input.oninput = () => {
                arr[idx] = input.value;
                markDirty();
                scheduleRender();
            };
            const rm = document.createElement('button');
            rm.type = 'button';
            rm.className = 'remove-btn';
            rm.innerHTML = '<i class="fa-solid fa-trash"></i>';
            rm.onclick = () => {
                arr.splice(idx, 1);
                markDirty();
                renderRepeatSimple(container, path, placeholder);
                scheduleRender();
            };
            row.appendChild(input);
            row.appendChild(rm);
            container.appendChild(row);
        });
    }

    // ---------- timeline ----------
    function buildTimelines() {
        form.querySelectorAll('.repeat-timeline').forEach((container) => {
            const path = container.getAttribute('data-list');
            renderTimeline(container, path);
        });
    }

    function renderTimeline(container, path) {
        container.innerHTML = '';
        const arr = getPath(state, path) || [];
        arr.forEach((item, idx) => {
            const card = document.createElement('div');
            card.className = 'timeline-card';

            const head = document.createElement('div');
            head.className = 'timeline-card-head';
            const rm = document.createElement('button');
            rm.type = 'button';
            rm.className = 'remove-btn';
            rm.innerHTML = '<i class="fa-solid fa-trash"></i>';
            rm.onclick = () => {
                arr.splice(idx, 1);
                markDirty();
                renderTimeline(container, path);
                scheduleRender();
            };
            head.appendChild(rm);
            card.appendChild(head);

            const titleLabel = document.createElement('label');
            titleLabel.textContent = 'Intitulé';
            const titleInput = document.createElement('input');
            titleInput.type = 'text';
            titleInput.placeholder = 'ex: Développeur Full-Stack - Novocib';
            titleInput.value = item.title || '';
            titleInput.oninput = () => { item.title = titleInput.value; markDirty(); scheduleRender(); };

            const metaLabel = document.createElement('label');
            metaLabel.textContent = 'Dates / Lieu';
            const metaInput = document.createElement('input');
            metaInput.type = 'text';
            metaInput.placeholder = 'ex: Jul 2025 – Feb 2026';
            metaInput.value = item.meta || '';
            metaInput.oninput = () => { item.meta = metaInput.value; markDirty(); scheduleRender(); };

            const bulletsLabel = document.createElement('label');
            bulletsLabel.textContent = 'Points clés';
            const bulletsList = document.createElement('div');
            bulletsList.className = 'bullets-list';
            if (!item.bullets) item.bullets = [];

            function renderBullets() {
                bulletsList.innerHTML = '';
                item.bullets.forEach((b, bi) => {
                    const row = document.createElement('div');
                    row.className = 'repeat-row';
                    const input = document.createElement('textarea');
                    input.rows = 1;
                    input.value = b || '';
                    input.oninput = () => { item.bullets[bi] = input.value; markDirty(); scheduleRender(); };
                    const rmB = document.createElement('button');
                    rmB.type = 'button';
                    rmB.className = 'remove-btn';
                    rmB.innerHTML = '<i class="fa-solid fa-xmark"></i>';
                    rmB.onclick = () => { item.bullets.splice(bi, 1); markDirty(); renderBullets(); scheduleRender(); };
                    row.appendChild(input);
                    row.appendChild(rmB);
                    bulletsList.appendChild(row);
                });
            }
            renderBullets();

            const addBulletBtn = document.createElement('button');
            addBulletBtn.type = 'button';
            addBulletBtn.className = 'add-btn';
            addBulletBtn.textContent = '+ Ajouter un point';
            addBulletBtn.onclick = () => { item.bullets.push(''); markDirty(); renderBullets(); scheduleRender(); };

            card.appendChild(titleLabel);
            card.appendChild(titleInput);
            card.appendChild(metaLabel);
            card.appendChild(metaInput);
            card.appendChild(bulletsLabel);
            card.appendChild(bulletsList);
            card.appendChild(addBulletBtn);

            container.appendChild(card);
        });
    }

    // ---------- add buttons ----------
    function bindAddButtons() {
        form.querySelectorAll('[data-add]').forEach((btn) => {
            btn.onclick = () => {
                const path = btn.getAttribute('data-add');
                const arr = getPath(state, path) || [];
                const container = form.querySelector(`.repeat-list[data-list="${path}"], .repeat-simple[data-list="${path}"]`);
                if (container.classList.contains('repeat-list')) {
                    const fields = container.getAttribute('data-fields').split(',');
                    const empty = {};
                    fields.forEach((f) => (empty[f] = ''));
                    arr.push(empty);
                } else {
                    arr.push('');
                }
                setPath(state, path, arr);
                markDirty();
                rebuildDynamicSections();
                scheduleRender();
            };
        });

        form.querySelectorAll('[data-add-timeline]').forEach((btn) => {
            btn.onclick = () => {
                const path = btn.getAttribute('data-add-timeline');
                const arr = getPath(state, path) || [];
                arr.push({ title: '', meta: '', bullets: [] });
                setPath(state, path, arr);
                markDirty();
                rebuildDynamicSections();
                scheduleRender();
            };
        });
    }

    function rebuildDynamicSections() {
        buildRepeatLists();
        buildRepeatSimples();
        buildTimelines();
    }

    // ---------- photo ----------
    function updatePhotoPreview() {
        const photo = (state.header && state.header.photo) || '';
        if (photo) {
            photoPreview.src = photo;
            photoPreview.classList.add('has-photo');
        } else {
            photoPreview.src = '';
            photoPreview.classList.remove('has-photo');
        }
    }

    photoFileInput.addEventListener('change', async () => {
        const file = photoFileInput.files[0];
        if (!file) return;

        if (file.size > MAX_PHOTO_BYTES) {
            photoUploadStatus.textContent = 'Trop lourd (1 Mo max)';
            photoUploadStatus.style.color = '#dc2626';
            photoFileInput.value = '';
            return;
        }
        if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
            photoUploadStatus.textContent = 'Format non supporté';
            photoUploadStatus.style.color = '#dc2626';
            photoFileInput.value = '';
            return;
        }

        photoUploadStatus.textContent = 'Envoi...';
        photoUploadStatus.style.color = '#6b7280';

        const fd = new FormData();
        fd.append('variant', '200');
        fd.append('photo', file);

        const res = await fetch(cfg.endpoints.uploadPhoto, {
            method: 'POST',
            headers: { 'X-CSRFToken': cfg.csrfToken },
            body: fd,
        });
        const result = await res.json();

        if (result.ok) {
            setPath(state, 'header.photo', result.url);
            updatePhotoPreview();
            markDirty();
            scheduleRender();
            photoUploadStatus.textContent = 'Photo ajoutée — pensez à Enregistrer';
            photoUploadStatus.style.color = '#16a34a';
            setTimeout(() => (photoUploadStatus.textContent = ''), 3000);
        } else {
            photoUploadStatus.textContent = result.error || 'Erreur';
            photoUploadStatus.style.color = '#dc2626';
        }
        photoFileInput.value = '';
    });

    photoRemoveBtn.addEventListener('click', () => {
        if (!(state.header && state.header.photo)) return;
        setPath(state, 'header.photo', '');
        updatePhotoPreview();
        markDirty();
        scheduleRender();
    });

    // ---------- save / preview ----------
    saveBtn.addEventListener('click', async () => {
        saveStatus.textContent = 'Enregistrement...';
        saveStatus.style.color = '#9ca3af';
        const result = await apiPostJson(cfg.endpoints.save, { data: state });
        if (result.ok) {
            markSaved();
        } else {
            saveStatus.textContent = 'Erreur';
            saveStatus.style.color = '#f87171';
        }
    });

    previewBtn.addEventListener('click', async () => {
        previewBtn.disabled = true;
        const original = previewBtn.innerHTML;
        previewBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Préparation...';
        const result = await apiPostJson(cfg.endpoints.save, { data: state });
        previewBtn.disabled = false;
        previewBtn.innerHTML = original;
        if (result.ok) {
            markSaved();
            window.open(cfg.endpoints.previewView, '_blank');
        } else {
            alert("Impossible d'enregistrer avant l'aperçu.");
        }
    });

    // ---------- init ----------
    bindStaticFields();
    rebuildDynamicSections();
    bindAddButtons();
    updatePhotoPreview();
    renderPreview();
})();
