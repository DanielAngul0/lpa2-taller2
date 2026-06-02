/* ═══════════════════════════════════════════════════════
   FACTURA PDF — app.js
   Gestión de formulario, historial de sesión y preview
═══════════════════════════════════════════════════════ */

// ── Estado ────────────────────────────────────────────
let activeEntryId = null;

// ── Elementos DOM ─────────────────────────────────────
const form          = document.getElementById('invoice-form');
const input         = document.getElementById('id_factura');
const submitBtn     = document.getElementById('submit-btn');
const statusBar     = document.getElementById('status-message');
const historyList   = document.getElementById('history-list');
const historyCount  = document.getElementById('history-count');
const emptyState    = document.getElementById('empty-state');
const previewPanel  = document.getElementById('preview-panel');
const previewHolder = document.getElementById('preview-placeholder');
const btnClearAll   = document.getElementById('btn-clear-all');
const navHistory    = document.getElementById('nav-history');

// ── Toasts ────────────────────────────────────────────
const toastContainer = (() => {
    const el = document.createElement('div');
    el.className = 'toast-container';
    document.body.appendChild(el);
    return el;
})();

function showToast(msg, type = '') {
    const t = document.createElement('div');
    t.className = `toast${type ? ' ' + type : ''}`;
    t.textContent = msg;
    toastContainer.appendChild(t);
    setTimeout(() => {
        t.style.opacity = '0';
        t.style.transform = 'translateY(6px)';
        t.style.transition = 'all 0.25s ease';
        setTimeout(() => t.remove(), 280);
    }, 2800);
}

// ── Status ────────────────────────────────────────────
function setStatus(msg, type = '') {
    statusBar.textContent = msg;
    statusBar.className = 'status-bar';
    if (type) statusBar.classList.add(type);
}

// ── Navegación entre vistas ───────────────────────────
function switchView(name) {
    document.querySelectorAll('.view').forEach(v => v.classList.add('view--hidden'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('nav-item--active'));

    document.getElementById(`view-${name}`).classList.remove('view--hidden');
    document.querySelector(`[data-view="${name}"]`).classList.add('nav-item--active');

    if (name === 'history') refreshHistory();
}

document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => switchView(btn.dataset.view));
});

// ── Formateo ──────────────────────────────────────────
const fmt = n => `$${Number(n).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

// ── Historial: render lista ───────────────────────────
function renderHistoryList(items) {
    // Limpiar items existentes (mantener empty-state)
    [...historyList.children].forEach(c => {
        if (c.id !== 'empty-state') c.remove();
    });

    if (!items.length) {
        emptyState.style.display = 'flex';
        historyCount.style.display = 'none';
        return;
    }

    emptyState.style.display = 'none';
    historyCount.textContent = items.length;
    historyCount.style.display = 'inline-flex';

    items.forEach(item => {
        const el = document.createElement('div');
        el.className = 'history-item' + (item.id === activeEntryId ? ' history-item--active' : '');
        el.dataset.id = item.id;
        el.innerHTML = `
            <div class="history-item__icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                </svg>
            </div>
            <div class="history-item__info">
                <div class="history-item__id">${escHtml(item.numero_factura)}</div>
                <div class="history-item__meta">${escHtml(item.fecha_generacion)}</div>
            </div>
            <span class="history-item__total">${fmt(item.total)}</span>
            <div class="history-item__actions">
                <button class="btn-icon accent" title="Descargar PDF" data-action="download" data-id="${item.id}" data-num="${escHtml(item.numero_factura)}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                </button>
                <button class="btn-icon danger" title="Eliminar" data-action="delete" data-id="${item.id}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/>
                    </svg>
                </button>
            </div>
        `;

        // Click en la fila → preview
        el.addEventListener('click', e => {
            if (e.target.closest('[data-action]')) return; // dejar que manejen los botones
            selectEntry(item.id, el);
        });

        historyList.appendChild(el);
    });

    // Delegación de acciones
    historyList.querySelectorAll('[data-action="download"]').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            downloadEntry(btn.dataset.id, btn.dataset.num);
        });
    });

    historyList.querySelectorAll('[data-action="delete"]').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            deleteEntry(btn.dataset.id);
        });
    });
}

// ── Historial: fetch ──────────────────────────────────
async function refreshHistory() {
    try {
        const res = await fetch('/historial');
        const items = await res.json();
        renderHistoryList(items);
    } catch {
        showToast('No se pudo cargar el historial', 'error');
    }
}

// ── Historial: seleccionar y previsualizar ────────────
async function selectEntry(id, rowEl) {
    // Marcar activo
    document.querySelectorAll('.history-item').forEach(i => i.classList.remove('history-item--active'));
    rowEl.classList.add('history-item--active');
    activeEntryId = id;

    // Mostrar panel
    previewHolder.style.display = 'none';
    previewPanel.style.display = 'block';
    previewPanel.innerHTML = `
        <div class="preview-panel__header">
            <div>
                <div class="preview-number">Cargando…</div>
            </div>
        </div>
        <div style="padding:40px;text-align:center;color:var(--text-4);">
            <div class="spinner" style="width:24px;height:24px;border-color:var(--border-strong);border-top-color:var(--accent);margin:0 auto 12px;"></div>
            Obteniendo datos…
        </div>
    `;

    try {
        const res = await fetch(`/historial/${id}`);
        if (!res.ok) throw new Error();
        const f = await res.json();
        renderPreview(f, id);
    } catch {
        previewPanel.innerHTML = `<div style="padding:32px;text-align:center;color:var(--danger);">Error al cargar la factura.</div>`;
    }
}

// ── Preview: render HTML ──────────────────────────────
function renderPreview(f, id) {
    const rows = f.detalle.map((item, i) => `
        <tr>
            <td>${item.cantidad}</td>
            <td>${escHtml(item.descripcion)}</td>
            <td style="text-align:right">${fmt(item.precio_unitario)}</td>
            <td style="text-align:right;font-weight:600">${fmt(item.total)}</td>
        </tr>
    `).join('');

    previewPanel.innerHTML = `
        <div class="preview-panel__header">
            <div>
                <div class="preview-number">Factura</div>
                <h2>${escHtml(f.numero_factura)}</h2>
                <div class="preview-date">Emitida el ${escHtml(f.fecha_emision)}</div>
            </div>
            <div class="preview-actions">
                <button class="btn-ghost btn-sm" id="prev-download">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    Descargar PDF
                </button>
                <button class="btn-ghost btn-sm danger" id="prev-delete">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/>
                    </svg>
                    Eliminar
                </button>
            </div>
        </div>
        <div class="preview-body">
            <div class="preview-parties">
                <div class="preview-party">
                    <div class="preview-party__label">Emisor</div>
                    <div class="preview-party__name">${escHtml(f.empresa.nombre)}</div>
                    <div class="preview-party__detail">
                        ${escHtml(f.empresa.direccion).replace(/\n/g, '<br>')}<br>
                        Tel: ${escHtml(f.empresa.telefono)}<br>
                        ${escHtml(f.empresa.email)}
                    </div>
                </div>
                <div class="preview-party">
                    <div class="preview-party__label">Facturado a</div>
                    <div class="preview-party__name">${escHtml(f.cliente.nombre)}</div>
                    <div class="preview-party__detail">
                        ${escHtml(f.cliente.direccion).replace(/\n/g, '<br>')}<br>
                        Tel: ${escHtml(f.cliente.telefono)}
                    </div>
                </div>
            </div>

            <div>
                <div class="preview-items-label">Detalle</div>
                <table class="preview-table">
                    <thead>
                        <tr>
                            <th>Cant.</th>
                            <th>Descripción</th>
                            <th style="text-align:right">P. Unit.</th>
                            <th style="text-align:right">Total</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>

            <div class="preview-totals">
                <div class="preview-total-row">
                    <span>Subtotal</span>
                    <span>${fmt(f.subtotal)}</span>
                </div>
                <div class="preview-total-row">
                    <span>IVA (21%)</span>
                    <span>${fmt(f.impuesto)}</span>
                </div>
                <div class="preview-total-row preview-total-row--main">
                    <span>Total</span>
                    <span>${fmt(f.total)}</span>
                </div>
            </div>
        </div>
    `;

    document.getElementById('prev-download').addEventListener('click', () => downloadEntry(id, f.numero_factura));
    document.getElementById('prev-delete').addEventListener('click', () => deleteEntry(id));
}

// ── Historial: descargar ──────────────────────────────
function downloadEntry(id, numero) {
    const link = document.createElement('a');
    link.href = `/historial/${id}/pdf`;
    link.download = `factura_${numero}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    showToast(`Descargando factura ${numero}…`, 'success');
}

// ── Historial: eliminar ───────────────────────────────
async function deleteEntry(id) {
    try {
        const res = await fetch(`/historial/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error();

        if (activeEntryId === id) {
            activeEntryId = null;
            previewPanel.style.display = 'none';
            previewHolder.style.display = 'flex';
        }

        showToast('Factura eliminada del historial', 'success');
        await refreshHistory();
    } catch {
        showToast('No se pudo eliminar la factura', 'error');
    }
}

// ── Historial: limpiar todo ───────────────────────────
btnClearAll.addEventListener('click', async () => {
    if (!confirm('¿Eliminar todo el historial de esta sesión?')) return;
    try {
        await fetch('/historial/limpiar', { method: 'POST' });
        activeEntryId = null;
        previewPanel.style.display = 'none';
        previewHolder.style.display = 'flex';
        showToast('Historial limpiado', 'success');
        await refreshHistory();
    } catch {
        showToast('Error al limpiar el historial', 'error');
    }
});

// ── Formulario ────────────────────────────────────────
input.addEventListener('input', () => {
    input.value = input.value.toUpperCase().trimStart();
    setStatus('');
});

form.addEventListener('submit', async e => {
    e.preventDefault();

    const value = input.value.trim();
    if (!value) {
        setStatus('Debes ingresar un número de factura.', 'is-error');
        input.focus();
        return;
    }
    if (value.length < 3) {
        setStatus('El identificador debe tener al menos 3 caracteres.', 'is-error');
        input.focus();
        return;
    }

    const originalHtml = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="spinner"></span> Generando PDF…`;
    setStatus('Consultando el backend y generando el documento…', 'is-success');

    try {
        const formData = new FormData(form);
        const response = await fetch('/generar-pdf', { method: 'POST', body: formData });

        if (!response.ok) {
            const text = await response.text().catch(() => '');
            throw new Error(text || 'Ocurrió un error al generar la factura.');
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `factura_${value}.pdf`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);

        setStatus('PDF generado y descargado correctamente.', 'is-success');
        showToast(`Factura ${value} guardada en el historial`, 'success');

        // Actualizar badge del historial
        await updateHistoryBadge();

    } catch (err) {
        setStatus(err.message || 'No se pudo generar el PDF.', 'is-error');
        showToast(err.message || 'Error al generar el PDF', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHtml;
    }
});

// ── Badge del historial ───────────────────────────────
async function updateHistoryBadge() {
    try {
        const res = await fetch('/historial');
        const items = await res.json();
        if (items.length) {
            historyCount.textContent = items.length;
            historyCount.style.display = 'inline-flex';
        } else {
            historyCount.style.display = 'none';
        }
    } catch { /* ignorar */ }
}

// ── Escape HTML ───────────────────────────────────────
function escHtml(str) {
    return String(str ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ── Init ──────────────────────────────────────────────
updateHistoryBadge();