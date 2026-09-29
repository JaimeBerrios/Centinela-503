(() => {
  const minLat = 13.461, maxLat = 13.507, minLon = -88.209, maxLon = -88.151;
  const NS = 'http://www.w3.org/2000/svg';
  const layer = document.getElementById('map-markers');
  let onSelect = null;
  let scale = 1;
  let selecting = false;

  function coords(latitude, longitude) {
    const lat = Number(latitude);
    const lon = Number(longitude);
    return {
      x: 48 + Math.max(0, Math.min(1, (lon - minLon) / (maxLon - minLon))) * 804,
      y: 34 + (1 - Math.max(0, Math.min(1, (lat - minLat) / (maxLat - minLat)))) * 350,
    };
  }

  function draw(clusters = [], selectIncident) {
    onSelect = selectIncident || null;
    layer.replaceChildren();
    clusters.slice(0, 40).forEach((cluster, index) => {
      const x = Number(cluster.center_longitude);
      const y = Number(cluster.center_latitude);
      if (!Number.isFinite(x) || !Number.isFinite(y)) return;
      const p = coords(y, x);
      const alerts = cluster.alerts || [];
      const isHigh = cluster.cluster_priority === 'Alta' || alerts.some((a) => a.priority === 'Alta');
      const group = document.createElementNS(NS, 'g');
      group.setAttribute('class', `map-marker${isHigh ? ' high' : ''}`);
      group.setAttribute('transform', `translate(${p.x} ${p.y})`);
      group.setAttribute('role', 'button');
      group.setAttribute('tabindex', '0');
      group.setAttribute('aria-label', `${alerts.length} alerta(s) ${isHigh ? 'de prioridad alta' : 'en revisión'}`);
      group.innerHTML = `<circle class="marker-wave" r="9"/><circle class="marker-ring" r="10"/><circle class="marker-core" r="3.2"/>${alerts.length > 1 ? `<text class="marker-count" y=".5">${alerts.length}</text>` : ''}`;
      const pick = () => {
        if (alerts[0] && onSelect) onSelect(alerts[0]);
      };
      group.addEventListener('click', pick);
      group.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); pick(); }
      });
      layer.append(group);
    });
  }

  function setSelecting(value) {
    selecting = value;
    const viewport = document.getElementById('map-viewport');
    viewport.classList.toggle('map-selecting', value);
    if (value) viewport.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  const viewport = document.getElementById('map-viewport');
  viewport.addEventListener('click', (event) => {
    if (!selecting || event.target.closest('.map-zoom, .map-marker')) return;
    const rect = viewport.getBoundingClientRect();
    const viewX = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    const viewY = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));
    const longitude = minLon + viewX * (maxLon - minLon);
    const latitude = maxLat - viewY * (maxLat - minLat);
    setSelecting(false);
    if (onLocation) onLocation(latitude, longitude);
  });
  let onLocation = null;
  document.getElementById('zoom-in').addEventListener('click', () => {
    scale = Math.min(1.5, scale + 0.12);
    document.querySelector('.map-art').style.transform = `scale(${scale})`;
  });
  document.getElementById('zoom-out').addEventListener('click', () => {
    scale = Math.max(1, scale - 0.12);
    document.querySelector('.map-art').style.transform = `scale(${scale})`;
  });
  document.getElementById('locate-button').addEventListener('click', () => {
    scale = 1;
    document.querySelector('.map-art').style.transform = 'scale(1)';
  });
  window.CentinelaMap = { draw, setSelecting, onLocation: (handler) => { onLocation = handler; } };
})();
