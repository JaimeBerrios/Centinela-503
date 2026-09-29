(() => {
  const $ = (selector, parent = document) => parent.querySelector(selector);
  const $$ = (selector, parent = document) => [...parent.querySelectorAll(selector)];
  const state = { connected: false, demo: true, clusters: [], alerts: [], filter: 'all', expanded: false, picked: null, lastSync: null };
  let canReport = true;
  const sampleAlerts = [
    { id: 'demo-1', node_id: 2, status: 'Emergencia', priority: 'Alta', latitude: 13.4862, longitude: -88.1814, incident_text: 'Inundación reportada cerca del mercado municipal', timestamp: new Date(Date.now() - 3 * 60000).toISOString(), demo: true },
    { id: 'demo-2', node_id: 1, status: 'Emergencia', priority: 'Pendiente', latitude: 13.4792, longitude: -88.1738, incident_text: 'Caída de árbol obstruye parcialmente la vía', timestamp: new Date(Date.now() - 11 * 60000).toISOString(), demo: true },
    { id: 'demo-3', node_id: 2, status: 'Emergencia', priority: 'Alta', latitude: 13.4911, longitude: -88.1896, incident_text: 'Se percibió movimiento sísmico; verificar daños', timestamp: new Date(Date.now() - 19 * 60000).toISOString(), demo: true },
    { id: 'demo-4', node_id: 1, status: 'Normal', priority: 'Pendiente', latitude: 13.4743, longitude: -88.1645, incident_text: 'Reporte de grieta en pared de vivienda', timestamp: new Date(Date.now() - 31 * 60000).toISOString(), demo: true },
  ];

  const escapeHTML = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
  function parseDate(raw) {
    if (!raw) return null;
    const value = String(raw).includes('T') ? String(raw) : `${String(raw).replace(' ', 'T')}Z`;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  function relativeTime(raw) {
    const date = parseDate(raw);
    if (!date) return 'sin hora';
    const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
    if (seconds < 60) return 'hace instantes';
    if (seconds < 3600) return `hace ${Math.floor(seconds / 60)} min`;
    if (seconds < 86400) return `hace ${Math.floor(seconds / 3600)} h`;
    return date.toLocaleDateString('es-SV', { day: '2-digit', month: 'short' });
  }
  function titleFor(alert) {
    const text = (alert.incident_text || '').trim();
    if (text) return text.length > 58 ? `${text.slice(0, 57)}…` : text;
    return alert.status === 'Normal' ? 'Reporte informativo de nodo' : `Alerta del nodo ${alert.node_id ?? 'local'}`;
  }
  function allAlerts(clusters) {
    return (clusters || []).flatMap((cluster) => cluster.alerts || []).sort((a, b) => (parseDate(b.timestamp)?.getTime() || 0) - (parseDate(a.timestamp)?.getTime() || 0));
  }
  function clustersFromAlerts(alerts) {
    return alerts.map((alert, index) => ({ cluster_id: alert.id ?? index, cluster_priority: alert.priority, center_latitude: alert.latitude, center_longitude: alert.longitude, alerts: [alert] }));
  }

  function renderMetrics() {
    const alerts = state.alerts;
    const high = alerts.filter((a) => (a.priority === 'Pendiente' ? a.suggested_priority : a.priority) === 'Alta').length;
    const clusters = state.clusters.length;
    const twoMin = Date.now() - 120000;
    const nodes = new Set(alerts.filter((a) => {
      const date = parseDate(a.timestamp);
      return Number(a.node_id) > 0 && date && date.getTime() >= twoMin;
    }).map((a) => Number(a.node_id)));
    $('#metric-alerts').textContent = alerts.length;
    $('#metric-high').textContent = high;
    $('#metric-clusters').textContent = clusters;
    $('#metric-nodes').innerHTML = `${nodes.size}<small> / 2</small>`;
    $('#nav-alert-count').textContent = alerts.length;
    $('#recent-count').textContent = alerts.length;
    $('#filter-all-count').textContent = alerts.length;
    $('#filter-high-count').textContent = high;
    $('#filter-pending-count').textContent = alerts.filter((a) => a.triage_state !== 'Validada').length;
    $('#map-count').textContent = state.demo ? 'VISTA PREVIA · DATOS ILUSTRATIVOS' : `${alerts.length} reportes · sincronizado ${state.lastSync ? state.lastSync.toLocaleTimeString('es-SV', { hour: '2-digit', minute: '2-digit' }) : '—'}`;
    const suggestionReady = alerts.some((a) => a.suggested_priority && a.suggested_priority !== 'Pendiente');
    $('#ml-readiness').innerHTML = suggestionReady ? '<i class="ready-pending">!</i> REGLAS LOCALES · VALIDAR' : '<i class="ready-pending">!</i> SIN SUGERENCIA';
  }

  function renderIncidents() {
    const filtered = state.alerts.filter((alert) => state.filter === 'all' || (state.filter === 'Alta' ? (alert.priority === 'Alta' || (alert.priority === 'Pendiente' && alert.suggested_priority === 'Alta')) : (state.filter === 'Pendiente' ? alert.triage_state !== 'Validada' : alert.priority === state.filter)));
    const shown = state.expanded ? filtered : filtered.slice(0, 5);
    const list = $('#incident-list');
    if (!shown.length) {
      list.innerHTML = `<div class="incident-empty"><div class="empty-icon"><svg><use href="#i-check"/></svg></div><strong>${state.alerts.length ? 'Sin alertas en este filtro' : (state.demo ? 'Vista previa del piloto' : 'Sin alertas registradas')}</strong><span>${state.alerts.length ? 'Prueba con otro filtro para ver reportes.' : (state.demo ? 'Conecta el servidor para mostrar datos reales.' : 'Las nuevas alertas aparecerán aquí.')}</span></div>`;
      $('#show-all-button').hidden = true;
      return;
    }
    list.innerHTML = shown.map((alert) => {
      const pending = !alert.priority || alert.priority === 'Pendiente';
      const normal = alert.status === 'Normal';
      const kind = normal ? 'normal' : (pending ? 'pending' : '');
      const label = normal ? 'INFORMATIVA' : (pending ? `SUG. ${String(alert.suggested_priority || 'Pendiente').toUpperCase()}` : `PRIORIDAD ${String(alert.priority).toUpperCase()}`);
      return `<article class="incident-row" data-id="${escapeHTML(alert.id)}" tabindex="0" role="button" aria-label="Ver ${escapeHTML(titleFor(alert))}">
        <div class="incident-symbol ${kind}"><svg><use href="${normal ? '#i-radio' : '#i-alert'}"/></svg></div>
        <div class="incident-main"><div class="incident-title">${escapeHTML(titleFor(alert))}</div><div class="incident-desc">${escapeHTML(alert.incident_text || `Reporte ${normal ? 'informativo' : 'de emergencia'} · Nodo ${alert.node_id ?? 'local'}`)}</div><div class="incident-meta"><span class="severity-tag ${kind}">${label}</span><i class="incident-meta-sep"></i><span class="incident-meta-text">${escapeHTML(alert.category || 'Sin clasificar')}</span><i class="incident-meta-sep"></i><span class="incident-meta-text">${alert.node_id ? `NODO ${String(alert.node_id).padStart(2, '0')}` : 'DASHBOARD'}</span></div></div>
        <time class="incident-time">${relativeTime(alert.timestamp)}</time>
      </article>`;
    }).join('');
    $('#show-all-button').hidden = filtered.length <= 5;
    $('#show-all-button').innerHTML = state.expanded ? 'Mostrar menos <svg><use href="#i-chevron"/></svg>' : `Explorar registro completo <svg><use href="#i-arrow"/></svg>`;
    $$('.incident-row', list).forEach((row) => {
      const open = () => {
        const alert = state.alerts.find((item) => String(item.id) === row.dataset.id);
        if (alert) showToast(`${titleFor(alert)} · ${relativeTime(alert.timestamp)}`, false, 3800);
      };
      row.addEventListener('click', open);
      row.addEventListener('keydown', (event) => { if (event.key === 'Enter') open(); });
    });
  }

  function renderNodes() {
    const nodes = [1, 2].map((nodeId) => {
      const item = state.alerts.find((a) => Number(a.node_id) === nodeId);
      const date = item ? parseDate(item.timestamp) : null;
      const age = date ? Math.max(0, Date.now() - date.getTime()) : Infinity;
      const recent = age < 120000;
      const stale = item && !recent;
      const status = recent ? 'REPORTE RECIENTE' : (stale ? 'SIN REPORTE RECIENTE' : (state.demo ? 'NODO SIMULADO' : 'ESPERANDO REPORTE'));
      const when = item ? relativeTime(item.timestamp) : 'sin telemetría';
      const origin = nodeId === 1 ? 'Nodo base · servidor' : 'Estación de campo';
      return `<div class="node-card"><div class="node-card-top"><div class="node-card-title"><svg><use href="#i-radio"/></svg> Nodo ${String(nodeId).padStart(2, '0')}</div><span class="node-status-dot ${recent ? 'online' : (stale ? 'stale' : '')}" title="Estado derivado del último reporte"></span></div><div class="node-card-data"><span>${origin}</span><strong>${when}</strong></div><div class="node-card-data"><span>Último estado</span><strong class="node-card-state">${status}</strong></div></div>`;
    });
    $('#node-list').innerHTML = nodes.join('');
  }

  function renderActivity() {
    const recent = state.alerts.slice(0, 4);
    if (!recent.length) {
      $('#activity-list').innerHTML = `<div class="activity-empty">${state.demo ? 'Los eventos ilustrativos no se guardan en el registro.' : 'El registro aparecerá cuando se reciban alertas.'}</div>`;
      return;
    }
    $('#activity-list').innerHTML = recent.map((alert) => {
      const pending = !alert.priority || alert.priority === 'Pendiente';
      return `<div class="activity-item"><span class="activity-icon ${alert.priority === 'Alta' ? 'high' : (pending ? 'pending' : '')}"><svg><use href="${alert.status === 'Normal' ? '#i-radio' : '#i-alert'}"/></svg></span><span class="activity-copy"><strong>${alert.status === 'Normal' ? 'Reporte recibido' : (pending ? 'Alerta por validar' : 'Alerta registrada')}</strong> · Nodo ${alert.node_id ?? 'local'}</span><time class="activity-ago">${relativeTime(alert.timestamp)}</time></div>`;
    }).join('');
  }

  function renderConnection() {
    const pill = $('#connection-pill');
    pill.classList.toggle('offline', !state.connected);
    $('#connection-label').textContent = state.connected ? 'API LOCAL EN LÍNEA' : 'API SIN CONEXIÓN';
    $('#map-hint').innerHTML = state.demo ? 'MODO <span>DEMO · DATOS ILUSTRATIVOS</span>' : 'MAPA <span>LOCAL · SAN MIGUEL</span>';
  }

  function render() {
    renderConnection();
    renderMetrics();
    renderIncidents();
    renderNodes();
    renderActivity();
    CentinelaMap.draw(state.clusters, (alert) => {
      const row = $(`.incident-row[data-id="${CSS.escape(String(alert.id))}"]`);
      row?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      row?.focus({ preventScroll: true });
      if (!row) showToast(titleFor(alert));
    });
  }

  async function sync() {
    if (!CentinelaAPI.getToken()) return;
    try {
      const [health, payload] = await Promise.all([CentinelaAPI.getHealth(), CentinelaAPI.getAlerts()]);
      if (!health || health.status !== 'ok') throw new Error('El servidor local no confirmó su estado.');
      state.connected = true;
      state.demo = false;
      state.clusters = Array.isArray(payload.data) ? payload.data : [];
      state.alerts = allAlerts(state.clusters);
      state.lastSync = new Date();
    } catch (error) {
      state.connected = false;
      state.demo = true;
      state.alerts = sampleAlerts;
      state.clusters = clustersFromAlerts(sampleAlerts);
      if (error?.name !== 'AbortError' && error?.name !== 'TimeoutError') console.info('Usando vista previa; API local no disponible.');
    }
    render();
  }

  function showToast(message, error = false, duration = 3600) {
    const toast = document.createElement('div');
    toast.className = `toast${error ? ' error' : ''}`;
    toast.innerHTML = `<svg><use href="${error ? '#i-alert' : '#i-check'}"/></svg><span>${escapeHTML(message)}</span>`;
    $('#toast-stack').append(toast);
    window.setTimeout(() => toast.remove(), duration);
  }
  function openReport() {
    if (!canReport) return;
    $('#form-error').textContent = '';
    $('#report-modal').classList.add('open');
    $('#report-modal').setAttribute('aria-hidden', 'false');
    window.setTimeout(() => $('#incident-text').focus(), 120);
  }
  function closeReport() {
    $('#report-modal').classList.remove('open');
    $('#report-modal').setAttribute('aria-hidden', 'true');
    CentinelaMap.setSelecting(false);
  }
  function updateLocation(latitude, longitude) {
    state.picked = { latitude, longitude };
    $('#incident-lat').value = latitude.toFixed(6);
    $('#incident-lon').value = longitude.toFixed(6);
    $('#selected-coordinates').textContent = `${latitude.toFixed(4)}° N · ${Math.abs(longitude).toFixed(4)}° O`;
    $('#map-hint').innerHTML = 'MAPA <span>LOCAL · SAN MIGUEL</span>';
    $('#map-toast').classList.add('visible');
    window.setTimeout(() => $('#map-toast').classList.remove('visible'), 2100);
    openReport();
  }
  function startLocationPick() {
    closeReport();
    CentinelaMap.setSelecting(true);
    $('#map-hint').innerHTML = 'HAZ CLIC EN EL MAPA <span>PARA FIJAR LA UBICACIÓN</span>';
    showToast('Selecciona el punto del incidente en el mapa.');
  }

  $('#open-report').addEventListener('click', openReport);
  $('#open-map-report').addEventListener('click', openReport);
  $('#close-report').addEventListener('click', closeReport);
  $('#report-modal').addEventListener('click', (event) => { if (event.target === $('#report-modal')) closeReport(); });
  $('#choose-location').addEventListener('click', startLocationPick);
  $('#map-pick').addEventListener('click', startLocationPick);
  CentinelaMap.onLocation(updateLocation);
  $('#refresh-button').addEventListener('click', sync);
  $('#activity-refresh').addEventListener('click', sync);
  $('#view-all').addEventListener('click', () => { state.expanded = true; $('#alertas').scrollIntoView({ behavior: 'smooth', block: 'start' }); renderIncidents(); });
  $('#show-all-button').addEventListener('click', () => { state.expanded = !state.expanded; renderIncidents(); });
  $$('.filter-chip').forEach((button) => button.addEventListener('click', () => {
    state.filter = button.dataset.filter;
    $$('.filter-chip').forEach((item) => item.classList.toggle('selected', item === button));
    state.expanded = false;
    renderIncidents();
  }));
  $('#incident-text').addEventListener('input', (event) => { $('#char-count').textContent = `${event.target.value.length} / 500`; });
  $('#report-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const errorBox = $('#form-error');
    const button = $('#submit-report');
    errorBox.textContent = '';
    if (!state.connected) {
      errorBox.textContent = 'No hay conexión con la API local. Inicia el backend y vuelve a intentar.';
      return;
    }
    const payload = {
      node_id: Number($('#node-id').value),
      status: $('#incident-type').value,
      incident_text: $('#incident-text').value.trim(),
      latitude: Number($('#incident-lat').value),
      longitude: Number($('#incident-lon').value),
    };
    button.disabled = true;
    button.innerHTML = '<svg><use href="#i-refresh"/></svg> Guardando en el servidor local…';
    try {
      const result = await CentinelaAPI.createAlert(payload);
      closeReport();
      $('#report-form').reset();
      $('#char-count').textContent = '0 / 500';
      $('#incident-lat').value = '13.4833';
      $('#incident-lon').value = '-88.1833';
      $('#selected-coordinates').textContent = 'San Miguel · ubicación aproximada del piloto';
      showToast(`Alerta ${result.id} guardada en el servidor local.`);
      await sync();
    } catch (error) {
      errorBox.textContent = `No se pudo guardar: ${error.message}. Revisa la API y vuelve a intentar.`;
    } finally {
      button.disabled = false;
      button.innerHTML = '<svg><use href="#i-send"/></svg> Enviar alerta al servidor local <span class="submit-arrow"><svg><use href="#i-arrow"/></svg></span>';
    }
  });
  window.addEventListener('keydown', (event) => {
    if ((event.key === 'n' || event.key === 'N') && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) openReport();
    if (event.key === 'Escape') closeReport();
  });

  function updateClock() {
    const now = new Date();
    $('#clock-time').textContent = new Intl.DateTimeFormat('es-SV', { timeZone: 'America/El_Salvador', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(now);
    $('#clock-date').textContent = new Intl.DateTimeFormat('es-SV', { timeZone: 'America/El_Salvador', weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' }).format(now).toUpperCase();
    $('#header-date').textContent = new Intl.DateTimeFormat('es-SV', { timeZone: 'America/El_Salvador', day: '2-digit', month: 'short', year: 'numeric' }).format(now).toUpperCase();
  }
  window.CentinelaApp = { openReport, sync, setCanReport: (value) => { canReport = !!value; } };
  updateClock();
  window.setInterval(updateClock, 1000);
  sync();
  window.setInterval(sync, 12000);
})();
