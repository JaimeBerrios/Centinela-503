(() => {
  const $ = (selector, parent = document) => parent.querySelector(selector);
  const $$ = (selector, parent = document) => [...parent.querySelectorAll(selector)];
  const roles = {
    admin: 'Administrador Institucional',
    coordinator: 'Coordinador de Emergencia',
    brigade_operator: 'Operador de Brigada',
    reporter: 'Reportante',
  };
  const pageInfo = {
    incidents: ['Incidentes', 'Registro, clasificación sugerida y validación humana de alertas.'],
    brigades: ['Brigadas', 'Disponibilidad, zona de operación y capacidades registradas.'],
    assignments: ['Asignaciones', 'Despacho operativo y seguimiento de las tareas asignadas.'],
    decisions: ['Decisiones', 'Historial de criterios y acciones confirmadas por coordinación.'],
    users: ['Usuarios y roles', 'Acceso local con responsabilidades diferenciadas.'],
    policies: ['Políticas locales', 'Parámetros del piloto que solo administra el rol institucional.'],
    audit: ['Bitácora de auditoría', 'Trazabilidad de accesos y cambios administrativos.'],
  };
  let currentUser = null;
  let currentView = 'overview';

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const date = (value) => {
    if (!value) return '—';
    const raw = String(value);
    const d = new Date(raw.includes('T') ? raw : `${raw.replace(' ', 'T')}Z`);
    return Number.isNaN(d.getTime()) ? raw : d.toLocaleString('es-SV', { dateStyle: 'medium', timeStyle: 'short' });
  };
  const button = (label, action, tone = '') => `<button class="table-action ${tone}" data-action="${action}">${label}</button>`;
  function toast(message, error = false) {
    if (window.CentinelaApp?.toast) return window.CentinelaApp.toast(message, error);
    const stack = $('#toast-stack');
    const node = document.createElement('div');
    node.className = `toast${error ? ' error' : ''}`;
    node.innerHTML = `<svg><use href="${error ? '#i-alert' : '#i-check'}"/></svg><span>${esc(message)}</span>`;
    stack.append(node);
    setTimeout(() => node.remove(), 4000);
  }
  function fail(error) { toast(error?.message || 'No se pudo completar la acción.', true); }

  function showAuth(message = '') {
    $('#app-shell').hidden = true;
    $('#auth-screen').hidden = false;
    $('#auth-error').textContent = message;
    $('#setup-error').textContent = message;
  }
  function showApp(user) {
    currentUser = user;
    $('#auth-screen').hidden = true;
    $('#app-shell').hidden = false;
    $('#profile-name').textContent = user.full_name;
    $('#profile-role').textContent = roles[user.role] || user.role;
    $('#profile-initials').textContent = user.full_name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase();
    $('#topbar-logout').textContent = user.full_name.slice(0, 1).toUpperCase();
    window.CentinelaApp?.setCanReport(user.role !== 'brigade_operator');
    $$('.report-action').forEach((item) => { item.hidden = user.role === 'brigade_operator'; });
    $$('[data-roles]').forEach((item) => {
      const allowed = item.dataset.roles.split(',');
      item.hidden = !allowed.includes(user.role);
    });
    // Initial dashboard is kept as a shared view for all four local roles.
    window.CentinelaApp?.sync();
    navigate('overview');
  }

  async function initializeAuth() {
    const token = CentinelaAPI.getToken();
    if (token) {
      try {
        const user = await CentinelaAPI.me();
        showApp(user);
        return;
      } catch { CentinelaAPI.setToken(null); }
    }
    try {
      const status = await CentinelaAPI.setupStatus();
      const setup = !!status.setup_required;
      $('#login-form').hidden = setup;
      $('#setup-form').hidden = !setup;
      $('#auth-title').textContent = setup ? 'Configura el acceso institucional' : 'Centro de coordinación';
      $('#auth-subtitle').textContent = setup
        ? 'Crea la cuenta administradora inicial. Después podrás dar de alta a los otros roles.'
        : 'Inicia sesión para acceder a la plataforma local de respuesta.';
      showAuth();
    } catch (error) {
      $('#login-form').hidden = false;
      $('#setup-form').hidden = true;
      showAuth(`No se pudo conectar con el servidor local. Comprueba que el backend esté activo en ${CentinelaAPI.base}.`);
    }
  }

  $('#login-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const submit = $('#auth-submit');
    submit.disabled = true;
    $('#auth-error').textContent = '';
    try {
      const result = await CentinelaAPI.login({ username: form.get('username'), password: form.get('password') });
      CentinelaAPI.setToken(result.access_token);
      showApp(result.user);
    } catch (error) { $('#auth-error').textContent = error.message; }
    finally { submit.disabled = false; }
  });
  $('#setup-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const submit = $('button[type="submit"]', event.currentTarget);
    submit.disabled = true;
    $('#setup-error').textContent = '';
    try {
      const result = await CentinelaAPI.setup({ full_name: form.get('full_name'), username: form.get('username'), password: form.get('password') });
      CentinelaAPI.setToken(result.access_token);
      showApp(result.user);
    } catch (error) { $('#setup-error').textContent = error.message; }
    finally { submit.disabled = false; }
  });

  async function signOut() {
    try { if (CentinelaAPI.getToken()) await CentinelaAPI.logout(); } catch { /* La sesión puede haber vencido. */ }
    CentinelaAPI.setToken(null);
    currentUser = null;
    currentView = 'overview';
    showAuth('La sesión se cerró. Inicia sesión para continuar.');
    initializeAuth();
  }
  $('#topbar-logout').addEventListener('click', signOut);
  $('#sidebar-logout').addEventListener('click', signOut);
  window.addEventListener('centinela:session-expired', () => {
    CentinelaAPI.setToken(null);
    currentUser = null;
    showAuth('Tu sesión venció. Inicia sesión nuevamente.');
    initializeAuth();
  });

  function navigate(view) {
    if (!currentUser) return;
    if (view !== 'overview' && !pageInfo[view]) return;
    const link = $(`[data-view="${view}"]`);
    if (link?.dataset.roles && !link.dataset.roles.split(',').includes(currentUser.role)) {
      toast('Tu rol no tiene acceso a esa sección.', true);
      return;
    }
    currentView = view;
    $('#overview-view').hidden = view !== 'overview';
    $('#management-view').hidden = view === 'overview';
    $$('.nav-link[data-view]').forEach((item) => item.classList.toggle('active', item.dataset.view === view && (view !== 'overview' || item.getAttribute('href') === '#inicio')));
    if (view === 'overview') {
      $('.breadcrumb strong').textContent = 'Vista general';
      return;
    }
    const [title, subtitle] = pageInfo[view];
    $('.breadcrumb strong').textContent = title;
    $('#management-title').textContent = title;
    $('#management-subtitle').textContent = subtitle;
    const action = $('#management-action');
    const actionViews = { brigades: ['Nueva brigada', 'admin'], users: ['Nuevo usuario', 'admin'], decisions: ['Registrar decisión', 'coordinator,admin'] };
    const actionInfo = actionViews[view];
    const enabled = actionInfo && actionInfo[1].split(',').includes(currentUser.role);
    action.hidden = !enabled;
    if (enabled) action.querySelector('span').textContent = actionInfo[0];
    loadView(view);
  }

  $$('[data-view]').forEach((item) => item.addEventListener('click', (event) => {
    event.preventDefault();
    const view = item.dataset.view;
    if (view === 'overview' && item.getAttribute('href') !== '#inicio') {
      navigate('overview');
      const anchor = item.getAttribute('href');
      setTimeout(() => document.querySelector(anchor)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 50);
    } else navigate(view);
  }));

  async function loadView(view) {
    const host = $('#management-content');
    host.innerHTML = '<div class="management-loading"><span class="loading-pip"></span> Cargando información local…</div>';
    try {
      const pages = {
        incidents: renderIncidentsPage,
        brigades: renderBrigadesPage,
        assignments: renderAssignmentsPage,
        decisions: renderDecisionsPage,
        users: renderUsersPage,
        policies: renderPoliciesPage,
        audit: renderAuditPage,
      };
      await pages[view]();
    } catch (error) {
      host.innerHTML = `<div class="management-empty"><strong>No se pudo cargar esta sección</strong><p>${esc(error.message)}</p><button class="quiet-button" data-action="retry">Reintentar</button></div>`;
    }
    bindManagementActions(view);
  }

  const table = (headers, rows) => `<div class="data-table-wrap"><table class="data-table"><thead><tr>${headers.map((h) => `<th>${h}</th>`).join('')}</tr></thead><tbody>${rows || `<tr><td class="table-empty" colspan="${headers.length}">Todavía no hay registros guardados.</td></tr>`}</tbody></table></div>`;
  const priorityPill = (priority) => `<span class="state-pill ${priority === 'Alta' ? 'danger' : priority === 'Media' ? 'warning' : priority === 'Baja' ? 'success' : ''}">${esc(priority || 'Pendiente')}</span>`;
  const statusPill = (value) => `<span class="state-pill ${value === 'Disponible' || value === 'Validada' || value === 'Resuelta' || value === 'Completada' ? 'success' : value === 'Fuera de servicio' || value === 'Rechazada' || value === 'Cancelada' ? 'danger' : 'warning'}">${esc(value || '—')}</span>`;
  function emptyPanel(title, detail) { return `<div class="management-empty"><span class="empty-icon"><svg><use href="#i-grid"/></svg></span><strong>${title}</strong><p>${detail}</p></div>`; }

  async function renderIncidentsPage() {
    const canValidate = ['admin', 'coordinator'].includes(currentUser.role);
    const incidentsResult = await CentinelaAPI.getIncidents();
    const brigadeResult = canValidate ? await CentinelaAPI.getBrigades() : { data: [] };
    const incidents = incidentsResult.data || [];
    const brigades = brigadeResult.data || [];
    const rows = incidents.map((item) => {
      const actions = canValidate && item.triage_state !== 'Validada'
        ? `<div class="row-control"><select data-priority="${item.id}" aria-label="Prioridad que valida coordinación"><option value="" disabled${['Alta','Media','Baja'].includes(item.suggested_priority) ? '' : ' selected'}>Elegir</option><option${item.suggested_priority === 'Alta' ? ' selected' : ''}>Alta</option><option${item.suggested_priority === 'Media' ? ' selected' : ''}>Media</option><option${item.suggested_priority === 'Baja' ? ' selected' : ''}>Baja</option></select><button class="table-action" data-action="validate" data-id="${item.id}">Validar</button><button class="table-action danger-action" data-action="delete" data-id="${item.id}" style="margin-left:5px">Eliminar</button></div>`
        : (canValidate && item.resolution_status === 'Abierta'
          ? `<button class="table-action" data-action="recommend" data-id="${item.id}">Comparar brigadas disponibles</button><div class="recommendation-slot" id="recommendations-${item.id}"></div>`
          : `<span class="muted-cell">${canValidate ? '—' : 'Coordinación valida'}</span>`);
      return `<tr>${canValidate ? `<td><input type="checkbox" class="incident-checkbox" value="${item.id}" style="cursor:pointer"></td>` : ''}<td><strong>#${item.id}</strong><small>${date(item.timestamp)}</small></td><td class="description-cell"><strong>${esc(item.category || 'Sin clasificar')} · ${esc(item.source || 'local')}</strong><small>${esc(item.incident_text || item.status)}</small></td><td>${priorityPill(item.suggested_priority)}<small class="table-subline">${esc(item.suggested_reason || 'Sin regla local aplicable')} · ${esc(item.triage_state)}</small></td><td>${statusPill(item.resolution_status)}</td><td>${actions}</td></tr>`;
    }).join('');
    $('#management-content').innerHTML = `<div class="management-stats"><div><span>REPORTES</span><strong>${incidents.length}</strong></div><div><span>PENDIENTES DE VALIDAR</span><strong>${incidents.filter((i) => i.triage_state !== 'Validada').length}</strong></div><div><span>PRIORIDAD ALTA SUGERIDA</span><strong>${incidents.filter((i) => i.suggested_priority === 'Alta').length}</strong></div></div>${incidents.length ? (canValidate ? `<div style="margin-bottom:10px"><button class="table-action danger-action" id="bulk-delete-btn" disabled>Eliminar Seleccionadas (0)</button></div>` : '') + table(canValidate ? ['<input type="checkbox" id="select-all-incidents" style="cursor:pointer">','REGISTRO','REPORTE','TRIAJE SUGERIDO','ESTADO','ACCIÓN'] : ['REGISTRO','REPORTE','TRIAJE SUGERIDO','ESTADO','ACCIÓN'], rows) : emptyPanel('Aún no hay incidentes', 'Las alertas recibidas por los nodos y los reportes del dashboard aparecerán aquí.')}`;
  }

  async function renderBrigadesPage() {
    const result = await CentinelaAPI.getBrigades();
    const brigades = result.data || [];
    if (!brigades.length) { $('#management-content').innerHTML = emptyPanel('No hay brigadas registradas', 'El Administrador Institucional puede crear la primera brigada y registrar su zona y capacidades.'); return; }
    $('#management-content').innerHTML = `<div class="brigade-grid">${brigades.map((b) => `<article class="brigade-card"><div class="brigade-card-head"><span class="brigade-emblem"><svg><use href="#i-people"/></svg></span><span class="brigade-id">BRIGADA ${String(b.id).padStart(2, '0')}</span>${statusPill(b.status)}</div><h3>${esc(b.name)}</h3><p class="brigade-zone"><svg><use href="#i-pin"/></svg>${esc(b.zone || 'Zona sin especificar')}</p><div class="skill-list">${(b.skills || []).map((skill) => `<span>${esc(skill)}</span>`).join('') || '<span>Sin capacidades registradas</span>'}</div><div class="brigade-card-foot"><span>${b.active_assignments || 0} asignación(es) activa(s)</span>${b.status !== 'Asignada' && (['admin','coordinator'].includes(currentUser.role) || (currentUser.role === 'brigade_operator' && b.id === currentUser.brigade_id)) ? `<select data-brigade-status="${b.id}"><option${b.status === 'Disponible' ? ' selected' : ''}>Disponible</option><option${b.status === 'Fuera de servicio' ? ' selected' : ''}>Fuera de servicio</option></select>` : `<span class="muted-cell">Actualizado ${date(b.updated_at)}</span>`}</div></article>`).join('')}</div>`;
  }

  async function renderAssignmentsPage() {
    const result = await CentinelaAPI.getAssignments();
    const assignments = result.data || [];
    const rows = assignments.map((a) => {
      const allowed = currentUser.role === 'brigade_operator' || ['admin','coordinator'].includes(currentUser.role);
      const next = {
        'Asignada': ['En camino', 'Atendiendo', 'Completada'],
        'En camino': ['Atendiendo', 'Completada'],
        'Atendiendo': ['Completada'],
      }[a.status] || [];
      if (allowed && currentUser.role !== 'brigade_operator' && next.length) next.push('Cancelada');
      const controls = allowed && next.length
        ? `<div class="row-control"><select data-assignment-status="${a.id}" required><option value="" selected disabled>Siguiente estado</option>${next.map((status) => `<option>${status}</option>`).join('')}</select><button class="table-action" data-action="advance" data-id="${a.id}">Actualizar</button></div>`
        : statusPill(a.status);
      return `<tr><td><strong>#${a.id}</strong><small>${date(a.created_at)}</small></td><td>#${a.incident_id} · ${esc(a.incident_text || a.incident_type)}</td><td><strong>${esc(a.brigade_name)}</strong><small>${esc(a.brigade_zone || '')}</small></td><td>${statusPill(a.status)}</td><td>${controls}</td></tr>`;
    }).join('');
    $('#management-content').innerHTML = assignments.length ? table(['ASIGNACIÓN','ALERTA','BRIGADA','ESTADO','ACTUALIZAR'], rows) : emptyPanel('Sin asignaciones activas', currentUser.role === 'admin' || currentUser.role === 'coordinator' ? 'Valida primero una alerta en Incidentes y asígnala a una brigada disponible.' : 'Cuando coordinación asigne tu brigada, la tarea aparecerá aquí.');
  }

  async function renderDecisionsPage() {
    const result = await CentinelaAPI.getDecisions();
    const decisions = result.data || [];
    const form = ['admin','coordinator'].includes(currentUser.role) ? `<form class="inline-create" id="decision-form"><div class="form-title"><strong>Registrar decisión de coordinación</strong><span>Se añadirá al historial local.</span></div><div class="inline-fields"><input name="action" required maxlength="120" placeholder="Acción o criterio"><input name="incident_id" type="number" min="1" placeholder="N.º de alerta (opcional)"><input name="details" required maxlength="1000" placeholder="Motivo, prioridad validada o indicación"><button class="primary-button" type="submit">Guardar decisión</button></div></form>` : '';
    const rows = decisions.map((d) => `<tr><td>${date(d.created_at)}</td><td><strong>${esc(d.action)}</strong><small>${d.incident_id ? `Alerta #${d.incident_id}` : 'Registro general'}</small></td><td>${esc(d.user_name || 'Sistema local')}</td><td class="description-cell">${esc(d.details)}</td></tr>`).join('');
    $('#management-content').innerHTML = `${form}${decisions.length ? table(['FECHA','DECISIÓN','RESPONSABLE','DETALLE'], rows) : emptyPanel('Aún no hay decisiones registradas', 'La validación de alertas, asignación de recursos y cambios de estado se guardarán automáticamente aquí.')}`;
  }

  async function renderUsersPage() {
    const [usersResult, brigadeResult] = await Promise.all([CentinelaAPI.getUsers(), CentinelaAPI.getBrigades()]);
    const users = usersResult.data || [];
    const brigades = brigadeResult.data || [];
    const brigadeOptions = brigades.map((b) => `<option value="${b.id}">${esc(b.name)}</option>`).join('');
    const rows = users.map((u) => `<tr><td><strong>${esc(u.full_name)}</strong><small>@${esc(u.username)}</small></td><td><select data-user-role="${u.id}"${u.id === currentUser.id ? ' disabled' : ''}><option value="admin"${u.role === 'admin' ? ' selected' : ''}>Administrador</option><option value="coordinator"${u.role === 'coordinator' ? ' selected' : ''}>Coordinador</option><option value="brigade_operator"${u.role === 'brigade_operator' ? ' selected' : ''}>Operador</option><option value="reporter"${u.role === 'reporter' ? ' selected' : ''}>Reportante</option></select></td><td><select data-user-brigade="${u.id}"><option value="">Sin brigada</option>${brigades.map((b) => `<option value="${b.id}"${u.brigade_id === b.id ? ' selected' : ''}>${esc(b.name)}</option>`).join('')}</select></td><td>${statusPill(u.active ? 'Activa' : 'Desactivada')}</td><td><div class="row-control">${u.id === currentUser.id ? '<span class="muted-cell">Tu cuenta</span>' : `<input class="reset-password" type="password" minlength="10" maxlength="128" data-user-password="${u.id}" placeholder="Nueva contraseña"><button class="table-action" data-action="update-user" data-id="${u.id}">Guardar</button>${button(u.active ? 'Desactivar' : 'Activar', 'deactivate-user', 'danger-action')}`}</div></td></tr>`).join('');
    $('#management-content').innerHTML = `<form class="inline-create" id="user-form" hidden><div class="form-title"><strong>Crear acceso local</strong><span>La contraseña se guarda como hash en el servidor.</span></div><div class="inline-fields user-fields"><input name="full_name" required minlength="2" maxlength="120" placeholder="Nombre completo"><input name="username" required minlength="3" maxlength="40" pattern="[A-Za-z0-9._-]+" placeholder="Usuario"><input name="password" required type="password" minlength="10" maxlength="128" placeholder="Contraseña · mínimo 10"><select name="role" required><option value="reporter">Reportante</option><option value="coordinator">Coordinador de Emergencia</option><option value="brigade_operator">Operador de Brigada</option><option value="admin">Administrador Institucional</option></select><select name="brigade_id"><option value="">Sin brigada asociada</option>${brigadeOptions}</select><button class="primary-button" type="submit">Crear usuario</button></div><div class="inline-message" id="user-form-message"></div></form>${table(['PERSONA','ROL','BRIGADA','ESTADO','ACCESO'], rows)}`;
  }

  async function renderPoliciesPage() {
    const result = await CentinelaAPI.getPolicies();
    const p = result.data || {};
    $('#management-content').innerHTML = `<form class="policy-form" id="policy-form"><div class="policy-intro"><span class="readiness-icon"><svg><use href="#i-shield"/></svg></span><div><strong>Configuración del piloto local</strong><p>Estos valores se almacenan en SQLite y el radio de agrupación se aplica al mapa.</p></div></div><label for="cluster-radius">Radio de agrupación espacial</label><div class="policy-input-row"><input type="number" id="cluster-radius" name="cluster_radius_m" min="10" max="500" value="${esc(p.cluster_radius_m || 50)}"><span>metros</span></div><small class="field-help">Distancia máxima entre alertas para mostrarlas como un mismo grupo. Rango permitido: 10–500 m.</small><div class="policy-fixed-note"><svg><use href="#i-shield"/></svg><span><strong>Validación humana siempre activa</strong><small>El servidor exige que coordinación valide la prioridad antes de despachar una brigada.</small></span></div><button class="primary-button" type="submit">Guardar políticas</button><div class="inline-message" id="policy-message"></div></form>`;
  }

  async function renderAuditPage() {
    const result = await CentinelaAPI.getAudit();
    const records = result.data || [];
    const rows = records.map((a) => `<tr><td>${date(a.created_at)}</td><td><strong>${esc(a.full_name || 'Sistema')}</strong><small>@${esc(a.username || 'local')}</small></td><td>${esc(a.action)}</td><td>${esc(a.entity)} ${a.entity_id ? `#${a.entity_id}` : ''}</td><td class="description-cell">${esc(JSON.stringify(a.details || {}))}</td></tr>`).join('');
    $('#management-content').innerHTML = records.length ? table(['FECHA','USUARIO','ACCIÓN','ELEMENTO','DETALLE'], rows) : emptyPanel('Bitácora vacía', 'Los accesos y cambios administrativos aparecerán en este registro.');
  }

  $('#management-action').addEventListener('click', () => {
    if (currentView === 'brigades') {
      const host = $('#management-content');
      let form = $('#brigade-form');
      if (form) { form.remove(); return; }
      form = document.createElement('form'); form.id = 'brigade-form'; form.className = 'inline-create';
      form.innerHTML = '<div class="form-title"><strong>Registrar brigada</strong><span>Define su zona, capacidades y ubicación para comparar distancias.</span></div><div class="inline-fields brigade-fields"><input name="name" required minlength="2" maxlength="100" placeholder="Nombre de brigada"><input name="zone" maxlength="120" placeholder="Zona o sector"><input name="skills" maxlength="250" placeholder="Capacidades separadas por coma"><input name="latitude" type="number" step="any" min="-90" max="90" placeholder="Latitud (opcional)"><input name="longitude" type="number" step="any" min="-180" max="180" placeholder="Longitud (opcional)"><button class="primary-button" type="submit">Guardar brigada</button></div><div class="inline-message"></div>';
      host.prepend(form);
    } else if (currentView === 'users') {
      $('#user-form').hidden = !$('#user-form').hidden;
      $('#user-form').scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else if (currentView === 'decisions') {
      $('#decision-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      $('input[name="action"]')?.focus();
    }
  });

  function bindManagementActions(view) {
    const host = $('#management-content');
    if (host.dataset.eventsBound === 'true') return;
    host.dataset.eventsBound = 'true';
    host.addEventListener('change', (e) => {
      if (e.target.id === 'select-all-incidents') {
        const checkboxes = host.querySelectorAll('.incident-checkbox');
        checkboxes.forEach(cb => cb.checked = e.target.checked);
      }
      if (e.target.classList.contains('incident-checkbox') || e.target.id === 'select-all-incidents') {
        const checked = host.querySelectorAll('.incident-checkbox:checked');
        const btn = $('#bulk-delete-btn', host);
        if (btn) {
          btn.disabled = checked.length === 0;
          btn.textContent = `Eliminar Seleccionadas (${checked.length})`;
        }
      }
    });
    host.addEventListener('click', async (e) => {
      if (e.target.id === 'bulk-delete-btn') {
        const checked = Array.from(host.querySelectorAll('.incident-checkbox:checked')).map(cb => Number(cb.value));
        if (!checked.length) return;
        if (!confirm(`¿Estás seguro de eliminar ${checked.length} alertas seleccionadas?`)) return;
        e.target.disabled = true;
        e.target.textContent = 'Eliminando...';
        try {
          const res = await CentinelaAPI.bulkDeleteIncidents(checked);
          toast(res.message || 'Alertas eliminadas.');
          return loadView(currentView);
        } catch(error) {
          toast(error.message || 'Error eliminando en lote.', true);
          e.target.disabled = false;
        }
        return;
      }
    });
    host.addEventListener('click', async (event) => {
      const action = event.target.closest('[data-action]');
      if (!action) return;
      const id = Number(action.dataset.id);
      try {
        if (action.dataset.action === 'retry') return loadView(currentView);
        if (action.dataset.action === 'validate') {
          const priority = $(`[data-priority="${id}"]`).value;
          if (!priority) return toast('Elige la prioridad que validará coordinación.', true);
          await CentinelaAPI.updateIncident(id, { priority, triage_state: 'Validada', decision_note: `Coordinación validó la prioridad ${priority}.` });
          toast(`Alerta #${id} validada.`);
          return loadView(currentView);
        }
        if (action.dataset.action === 'delete') {
          if (!confirm(`¿Estás seguro de que deseas eliminar permanentemente la alerta #${id}?`)) return;
          await CentinelaAPI.deleteIncident(id);
          toast(`Alerta #${id} eliminada.`);
          return loadView(currentView);
        }
        if (action.dataset.action === 'recommend') {
          const slot = $(`#recommendations-${id}`);
          action.disabled = true;
          action.textContent = 'Comparando brigadas…';
          try {
            const result = await CentinelaAPI.getRecommendations(id);
            slot.innerHTML = result.data.length ? `<div class="recommendation-note">${esc(result.data_note)}</div>${result.data.slice(0, 4).map((r) => `<div class="recommendation-row"><span><strong>${esc(r.name)}</strong><small>${esc(r.zone || 'Zona sin definir')} · ${r.distance_km_straight_line == null ? 'distancia no disponible' : `${r.distance_km_straight_line} km en línea recta`}${r.matched_skills.length ? ` · capacidades: ${esc(r.matched_skills.join(', '))}` : ''}</small></span><button class="table-action" data-action="assign" data-id="${id}" data-brigade-id="${r.brigade_id}">Asignar</button></div>`).join('')}` : '<div class="recommendation-note">No hay brigadas disponibles. Revisa su disponibilidad o registra una brigada.</div>';
            action.remove();
          } catch (error) { action.disabled = false; action.textContent = 'Comparar brigadas disponibles'; throw error; }
          return;
        }
        if (action.dataset.action === 'assign') {
          const brigadeId = Number(action.dataset.brigadeId);
          if (!brigadeId) return toast('Selecciona una brigada disponible.', true);
          await CentinelaAPI.createAssignment({ incident_id: id, brigade_id: brigadeId, note: 'Asignación desde el tablero de operaciones.' });
          toast(`Brigada asignada a la alerta #${id}.`);
        }
        if (action.dataset.action === 'advance') {
          const selector = $(`[data-assignment-status="${id}"]`);
          const status = selector.value;
          if (!status) return toast('Elige el siguiente estado de la atención.', true);
          await CentinelaAPI.updateAssignment(id, { status, details: `Estado actualizado a ${status}.` });
          toast(`Asignación #${id}: ${status.toLowerCase()}.`);
        }
        if (action.dataset.action === 'deactivate-user') {
          const active = action.closest('tr')?.querySelector('.state-pill')?.textContent === 'Activa';
          if (!confirm(active ? '¿Desactivar el acceso de esta persona?' : '¿Reactivar el acceso de esta persona?')) return;
          await CentinelaAPI.updateUser(id, { active: !active });
          toast(active ? 'Acceso desactivado.' : 'Acceso reactivado.');
        }
        if (action.dataset.action === 'update-user') {
          const role = $(`[data-user-role="${id}"]`).value;
          const brigadeValue = $(`[data-user-brigade="${id}"]`).value;
          const password = $(`[data-user-password="${id}"]`).value;
          const payload = { role, brigade_id: brigadeValue ? Number(brigadeValue) : null };
          if (password) payload.password = password;
          await CentinelaAPI.updateUser(id, payload);
          toast('Rol y acceso actualizados.');
        }
        await loadView(currentView);
        if (currentView === 'incidents') window.CentinelaApp?.sync();
      } catch (error) { fail(error); }
    });

    host.addEventListener('change', async (event) => {
      const select = event.target.closest('[data-brigade-status]');
      if (!select) return;
      try { await CentinelaAPI.updateBrigade(Number(select.dataset.brigadeStatus), { status: select.value }); toast('Disponibilidad de brigada actualizada.'); await loadView(currentView); }
      catch (error) { fail(error); }
    });

    host.addEventListener('submit', async (event) => {
      event.preventDefault();
      const form = event.target;
      const data = new FormData(form);
      const message = $('.inline-message', form);
      try {
        if (form.id === 'brigade-form') {
          const latitude = data.get('latitude');
          const longitude = data.get('longitude');
          await CentinelaAPI.createBrigade({ name: data.get('name'), zone: data.get('zone'), skills: String(data.get('skills') || '').split(',').map((x) => x.trim()).filter(Boolean), latitude: latitude ? Number(latitude) : null, longitude: longitude ? Number(longitude) : null });
          toast('Brigada registrada.');
        } else if (form.id === 'user-form') {
          const brigade = data.get('brigade_id');
          await CentinelaAPI.createUser({ full_name: data.get('full_name'), username: data.get('username'), password: data.get('password'), role: data.get('role'), brigade_id: brigade ? Number(brigade) : null });
          toast('Usuario creado.');
        } else if (form.id === 'decision-form') {
          const incident = data.get('incident_id');
          await CentinelaAPI.createDecision({ action: data.get('action'), details: data.get('details'), incident_id: incident ? Number(incident) : null });
          toast('Decisión añadida al registro.');
        } else if (form.id === 'policy-form') {
          await CentinelaAPI.updatePolicies({ cluster_radius_m: Number(data.get('cluster_radius_m')), simulator_enabled: data.has('simulator_enabled') });
          toast('Políticas locales guardadas.');
        } else return;
        await loadView(currentView);
      } catch (error) {
        if (message) message.textContent = error.message;
        else fail(error);
      }
    });
  }

  initializeAuth();
})();
