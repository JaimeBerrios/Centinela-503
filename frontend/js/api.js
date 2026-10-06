(() => {
  const configured = new URLSearchParams(window.location.search).get('api');
  const base = (configured || localStorage.getItem('centinela-api-url') || 'http://127.0.0.1:8000').replace(/\/$/, '');
  const getToken = () => sessionStorage.getItem('centinela-token');

  async function request(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
    if (getToken()) headers.Authorization = `Bearer ${getToken()}`;
    const response = await fetch(`${base}${path}`, { ...options, headers, signal: AbortSignal.timeout(7000) });
    if (response.status === 401 && getToken()) window.dispatchEvent(new CustomEvent('centinela:session-expired'));
    if (!response.ok) {
      let detail = `La API respondió ${response.status}`;
      try {
        const body = await response.json();
        if (body.detail) detail = Array.isArray(body.detail) ? body.detail.map((x) => x.msg || x).join(', ') : body.detail;
      } catch { /* Respuesta sin cuerpo JSON. */ }
      throw new Error(detail);
    }
    return response.status === 204 ? null : response.json();
  }
  const json = (method, payload) => ({ method, body: JSON.stringify(payload) });

  window.CentinelaAPI = {
    base,
    getToken,
    setToken: (token) => token ? sessionStorage.setItem('centinela-token', token) : sessionStorage.removeItem('centinela-token'),
    setupStatus: () => request('/auth/setup-status'),
    setup: (data) => request('/auth/setup', json('POST', data)),
    login: (data) => request('/auth/login', json('POST', data)),
    me: () => request('/auth/me'),
    logout: () => request('/auth/logout', { method: 'POST' }),
    getHealth: () => request('/health/'),
    getOverview: () => request('/overview'),
    getIncidents: () => request('/incidents'),
    getAlerts: () => request('/sensors/'),
    createAlert: (data) => request('/sensors/', json('POST', data)),
    updateIncident: (id, data) => request(`/incidents/${id}`, json('PATCH', data)),
    deleteIncident: (id) => request(`/incidents/${id}`, { method: 'DELETE' }),
    bulkDeleteIncidents: (ids) => request('/incidents/bulk-delete', json('POST', { ids })),
    getRecommendations: (id) => request(`/incidents/${id}/recommendations`),
    getBrigades: () => request('/brigades/'),
    createBrigade: (data) => request('/brigades/', json('POST', data)),
    updateBrigade: (id, data) => request(`/brigades/${id}`, json('PATCH', data)),
    getAssignments: () => request('/assignments'),
    createAssignment: (data) => request('/assignments', json('POST', data)),
    updateAssignment: (id, data) => request(`/assignments/${id}`, json('PATCH', data)),
    getDecisions: () => request('/decisions'),
    createDecision: (data) => request('/decisions', json('POST', data)),
    getUsers: () => request('/users/'),
    createUser: (data) => request('/users/', json('POST', data)),
    updateUser: (id, data) => request(`/users/${id}`, json('PATCH', data)),
    deactivateUser: (id) => request(`/users/${id}`, { method: 'DELETE' }),
    clearHardwareAlert: () => request('/sensors/clear-hardware', { method: 'POST' }),
    getPolicies: () => request('/policies'),
    updatePolicies: (data) => request('/policies', json('PATCH', data)),
    getAudit: () => request('/audit'),
  };
})();
