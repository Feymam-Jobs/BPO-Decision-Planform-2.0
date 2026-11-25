function clientApp(DATA, META) {
  const css = getComputedStyle(document.documentElement);
  const cv = n => css.getPropertyValue(n).trim();
  const PRI = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
  const PRI_ES = { CRITICAL: 'Crítica', HIGH: 'Alta', MEDIUM: 'Media', LOW: 'Baja' };
  const COL = { CRITICAL: cv('--crit'), HIGH: cv('--high'), MEDIUM: cv('--med'), LOW: cv('--low') };
  const PALETTE = ['#3b82f6', '#8b5cf6', '#14b8a6', '#f59e0b', '#ec4899', '#64748b', '#22c55e', '#ef4444'];
  const el = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const num = x => {
    if (x === '' || x === null || x === undefined) return null;
    const n = Number(x);
    return Number.isFinite(n) ? n : null;
  };
  const avg = a => {
    const x = a.filter(n => n !== null);
    return x.length ? x.reduce((s, n) => s + n, 0) / x.length : null;
  };
  const f1 = n => (n === null ? 'N/A' : n.toFixed(1));
  const pct = (a, b) => (b ? Math.round((a / b) * 100) + '%' : '0%');
  const tally = (arr, fn) => {
    const m = new Map();
    arr.forEach(r => { const k = fn(r); m.set(k, (m.get(k) || 0) + 1); });
    return m;
  };
  const text = (x, d) => {
    const s = x === undefined || x === null ? '' : String(x).trim();
    return s === '' ? d : s;
  };
  let agentView = 'tmo-bar';
  function renderAgentPerformance() {
    const agents = META.agents || [];
    const percentage = agentView.startsWith('percentage-');
    const chartType = agentView.endsWith('-line') ? 'line' : 'bar';
    el('agentView').value = agentView;
    el('agentTitle').textContent = percentage ? 'Rendimiento por porcentaje' : 'Rendimiento TMO';
    el('agentDescription').textContent = percentage
      ? 'Porcentaje de mediciones dentro de la meta de TMO'
      : (agents.length ? 'Promedio por agente frente a la meta (' + agents[0].target + ' ' + agents[0].unit_label + ')' : 'Promedio por agente frente a la meta');
    if (chartType === 'line' && agents.length) {
      const visible = agents.slice(0, 12);
      const scale = percentage ? 100 : Math.max(1, ...visible.map(a => a.avg_tmo || 0), ...visible.map(a => a.target));
      const left = 62, right = 710, top = 18, bottom = 188;
      const x = i => visible.length === 1 ? (left + right) / 2 : left + i * (right - left) / (visible.length - 1);
      const y = value => bottom - value / scale * (bottom - top);
      const ticks = percentage ? [0, 25, 50, 75, 100] : [0, scale / 4, scale / 2, scale * 3 / 4, scale];
      const grid = ticks.map(value => '<g><line x1="' + left + '" y1="' + y(value) + '" x2="' + right + '" y2="' + y(value) + '" stroke="var(--grid)"/><text x="' + (left - 8) + '" y="' + (y(value) + 4) + '" text-anchor="end" fill="var(--muted)" font-size="10">' + Math.round(value) + (percentage ? '%' : '') + '</text></g>').join('');
      let segment = [], paths = [];
      visible.forEach((a, i) => {
        const value = percentage ? a.within_pct : a.avg_tmo;
        if (value === null) {
          if (segment.length > 1) paths.push('<path d="' + segment.join(' ') + '" fill="none" stroke="' + (percentage ? 'var(--low)' : 'var(--accent)') + '" stroke-width="3"/>');
          segment = [];
        } else segment.push((segment.length ? 'L' : 'M') + ' ' + x(i) + ' ' + y(value));
      });
      if (segment.length > 1) paths.push('<path d="' + segment.join(' ') + '" fill="none" stroke="' + (percentage ? 'var(--low)' : 'var(--accent)') + '" stroke-width="3"/>');
      const points = visible.map((a, i) => {
        const value = percentage ? a.within_pct : a.avg_tmo;
        if (value === null) return '';
        const label = Number(value).toFixed(percentage ? 0 : 1) + (percentage ? '%' : ' ' + a.unit_label);
        return '<g><circle cx="' + x(i) + '" cy="' + y(value) + '" r="4" fill="' + (percentage ? 'var(--low)' : 'var(--accent)') + '"><title>' + esc(a.agent) + ': ' + label + '</title></circle><text x="' + x(i) + '" y="214" text-anchor="middle" fill="var(--muted)" font-size="10">' + esc(a.agent.slice(0, 12)) + '</text></g>';
      }).join('');
      el('agentPerformance').innerHTML = '<svg viewBox="0 0 730 230" role="img" aria-label="' + (percentage ? 'Porcentaje de cumplimiento' : 'TMO promedio') + ' por agente" style="width:100%;height:auto">' + grid + paths.join('') + points + '</svg>';
      return;
    }
    el('agentPerformance').innerHTML = agents.length ? agents.map(a => {
      const value = percentage ? a.within_pct : a.avg_tmo;
      const width = percentage ? (value === null ? 0 : value) : (value === null ? 0 : Math.min(100, value / Math.max(a.target, value, 1) * 100));
      const label = value === null ? '—' : Number(value).toFixed(percentage ? 0 : 1) + (percentage ? '%' : ' ' + a.unit_label);
      return '<div class="agent-row"><b>' + esc(a.agent) + '</b><div class="agent-track"><div class="agent-fill" style="width:' + width + '%"></div></div><strong>' + label + '</strong></div>';
    }).join('') : '<div class="agent-empty">No hay mediciones de agentes.</div>';
  }
  el('agentView').addEventListener('change', event => {
    agentView = event.currentTarget.value;
    renderAgentPerformance();
  });
  renderAgentPerformance();

  // ---- Columnas de la tabla: las conocidas + cualquier columna extra del archivo
  const KNOWN = ['priority', 'priority_score', 'request_id', 'customer', 'issue', 'category', 'customer_tier', 'urgency', 'sla_hours', 'status'];
  const LABEL = {
    priority: 'Prioridad', priority_score: 'Puntaje', request_id: 'ID', customer: 'Cliente', issue: 'Asunto',
    category: 'Categoría', customer_tier: 'Nivel', urgency: 'Urgencia', sla_hours: 'SLA (h)', status: 'Estado'
  };
  const extra = [];
  DATA.forEach(r => Object.keys(r).forEach(k => { if (!KNOWN.includes(k) && !extra.includes(k)) extra.push(k); }));
  const COLS = KNOWN.concat(extra).filter(k => DATA.some(r => r[k] !== undefined && r[k] !== null && r[k] !== ''));

  const rows = DATA.map(r => Object.assign({}, r, {
    priority: String(r.priority || '').toUpperCase(),
    _u: num(r.urgency), _s: num(r.sla_hours), _p: num(r.priority_score) || 0,
    _cat: text(r.category, 'Sin categoría'), _tier: text(r.customer_tier, 'N/A'),
    _st: text(r.status, 'N/A'), _cu: text(r.customer, 'N/A')
  }));

  // ---- Encabezado y filtros
  el('gen').textContent = 'Generado: ' + META.generated + ' · ' + META.total + ' solicitudes analizadas';
  const fill = (id, values) => {
    el(id).innerHTML = '<option value="">Todos</option>' +
      values.map(x => '<option value="' + esc(x) + '">' + esc(x) + '</option>').join('');
  };
  fill('fCat', [...new Set(rows.map(r => r._cat))].sort());
  fill('fTier', [...new Set(rows.map(r => r._tier))].sort());
  fill('fSt', [...new Set(rows.map(r => r._st))].sort());

  function filtered() {
    const q = el('fQ').value.trim().toLowerCase();
    return rows.filter(r =>
      (!el('fPri').value || r.priority === el('fPri').value) &&
      (!el('fCat').value || r._cat === el('fCat').value) &&
      (!el('fTier').value || r._tier === el('fTier').value) &&
      (!el('fSt').value || r._st === el('fSt').value) &&
      (!q || COLS.some(k => String(r[k] === undefined || r[k] === null ? '' : r[k]).toLowerCase().includes(q))));
  }

  // ---- KPIs
  function renderKpis(f) {
    const n = f.length;
    const c = k => f.filter(r => r.priority === k).length;
    const attention = c('CRITICAL') + c('HIGH');
    const prem = f.filter(r => r._tier.toLowerCase() === 'premium').length;
    const risk = f.filter(r => r._s !== null && r._s <= 4).length;
    const tiles = [
      ['Solicitudes', n, '', 'en la vista actual'],
      ['Críticas', c('CRITICAL'), 'crit', pct(c('CRITICAL'), n) + ' del total'],
      ['Altas', c('HIGH'), 'high', pct(c('HIGH'), n) + ' del total'],
      ['Medias', c('MEDIUM'), 'med', pct(c('MEDIUM'), n) + ' del total'],
      ['Bajas', c('LOW'), 'low', pct(c('LOW'), n) + ' del total'],
      ['Requieren atención', attention, 'crit', 'críticas + altas (' + pct(attention, n) + ')'],
      ['Urgencia promedio', f1(avg(f.map(r => r._u))), '', 'escala de 1 a 10'],
      ['SLA promedio (h)', f1(avg(f.map(r => r._s))), '', 'horas comprometidas'],
      ['SLA de 4 h o menos', risk, 'high', pct(risk, n) + ' de las solicitudes'],
      ['Clientes premium', prem, '', pct(prem, n) + ' de las solicitudes']
    ];
    el('kpis').innerHTML = tiles.map(t =>
      '<div class="kpi ' + t[2] + '"><div class="kl">' + t[0] + '</div><div class="kv">' + t[1] +
      '</div><div class="ks">' + t[3] + '</div></div>').join('');
  }

  // ---- Gráficos
  const hasChart = typeof Chart !== 'undefined';
  const charts = {};
  if (hasChart) {
    Chart.defaults.color = cv('--muted');
    Chart.defaults.borderColor = cv('--grid');
    Chart.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
  } else {
    el('chartNote').style.display = 'block';
  }
  const setChart = (id, type, data, options) => {
    if (!hasChart) return;
    if (charts[id]) { charts[id].data = data; charts[id].update(); return; }
    charts[id] = new Chart(el(id), { type, data, options });
  };
  const legendBottom = () => ({ position: 'bottom', labels: { boxWidth: 12 } });
  const doughnutOpts = () => ({ responsive: true, maintainAspectRatio: false, cutout: '58%', plugins: { legend: legendBottom() } });
  const stackedOpts = () => ({
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: legendBottom() },
    scales: {
      x: { stacked: true, grid: { display: false } },
      y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } }
    }
  });
  const barOpts = horizontal => ({
    responsive: true, maintainAspectRatio: false, indexAxis: horizontal ? 'y' : 'x',
    plugins: { legend: { display: false } },
    scales: horizontal
      ? { x: { beginAtZero: true, ticks: { precision: 0 } }, y: { grid: { display: false } } }
      : { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { precision: 0 } } }
  });

  function renderCharts(f) {
    // 1. Distribución por prioridad
    setChart('cPri', 'doughnut', {
      labels: PRI.map(k => PRI_ES[k]),
      datasets: [{ data: PRI.map(k => f.filter(r => r.priority === k).length), backgroundColor: PRI.map(k => COL[k]), borderWidth: 0 }]
    }, doughnutOpts());

    // 2. Categoría x prioridad
    const cats = [...tally(f, r => r._cat).entries()].sort((a, b) => b[1] - a[1]).slice(0, 10).map(e => e[0]);
    setChart('cCat', 'bar', {
      labels: cats,
      datasets: PRI.map(k => ({
        label: PRI_ES[k], backgroundColor: COL[k],
        data: cats.map(cn => f.filter(r => r._cat === cn && r.priority === k).length)
      }))
    }, stackedOpts());

    // 3. Urgencia (1-10), coloreada según los umbrales del puntaje
    const uh = Array(10).fill(0);
    f.forEach(r => { if (r._u !== null) uh[Math.min(10, Math.max(1, Math.round(r._u))) - 1]++; });
    setChart('cUrg', 'bar', {
      labels: uh.map((_, i) => String(i + 1)),
      datasets: [{ label: 'Solicitudes', data: uh, backgroundColor: uh.map((_, i) => (i >= 8 ? COL.CRITICAL : i >= 6 ? COL.HIGH : i >= 3 ? COL.MEDIUM : COL.LOW)) }]
    }, barOpts(false));

    // 4. SLA por rangos
    const sb = [0, 0, 0, 0];
    f.forEach(r => { if (r._s !== null) sb[r._s <= 2 ? 0 : r._s <= 4 ? 1 : r._s <= 8 ? 2 : 3]++; });
    setChart('cSla', 'bar', {
      labels: ['2 h o menos', 'Hasta 4 h', 'Hasta 8 h', 'Más de 8 h'],
      datasets: [{ label: 'Solicitudes', data: sb, backgroundColor: [COL.CRITICAL, COL.HIGH, COL.MEDIUM, COL.LOW] }]
    }, barOpts(false));

    // 5. Clientes con mayor puntaje acumulado
    const sums = new Map();
    f.forEach(r => sums.set(r._cu, (sums.get(r._cu) || 0) + r._p));
    const top = [...sums.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
    setChart('cCus', 'bar', {
      labels: top.map(e => e[0]),
      datasets: [{ label: 'Puntaje acumulado', data: top.map(e => e[1]), backgroundColor: cv('--accent') }]
    }, barOpts(true));

    // 6. Estado
    const st = [...tally(f, r => r._st).entries()].sort((a, b) => b[1] - a[1]);
    setChart('cSt', 'doughnut', {
      labels: st.map(e => e[0]),
      datasets: [{ data: st.map(e => e[1]), backgroundColor: st.map((_, i) => PALETTE[i % PALETTE.length]), borderWidth: 0 }]
    }, doughnutOpts());
  }

  // ---- Tabla ordenable
  let sort = { k: 'priority_score', dir: -1 };
  const cmp = (a, b) => {
    const key = sort.k === 'priority' ? '_p' : sort.k;
    const x = a[key], y = b[key];
    const nx = num(x), ny = num(y);
    if (nx !== null && ny !== null) return (nx - ny) * sort.dir;
    return String(x === undefined || x === null ? '' : x).localeCompare(String(y === undefined || y === null ? '' : y), 'es') * sort.dir;
  };
  function renderTable(f) {
    const LIMIT = 500;
    const sorted = f.slice().sort(cmp);
    el('thead').innerHTML = '<tr>' + COLS.map(k =>
      '<th data-k="' + esc(k) + '">' + esc(LABEL[k] || k) +
      (sort.k === k ? (sort.dir > 0 ? ' ▲' : ' ▼') : '') + '</th>').join('') + '</tr>';
    el('tbody').innerHTML = sorted.slice(0, LIMIT).map(r => '<tr>' + COLS.map(k => {
      if (k === 'priority') {
        return '<td><span class="badge b-' + esc(r.priority) + '">' + esc(PRI_ES[r.priority] || r.priority || 'N/A') + '</span></td>';
      }
      const v = r[k];
      return '<td>' + esc(v === undefined || v === null ? '' : v) + '</td>';
    }).join('') + '</tr>').join('');
    el('count').textContent = 'Mostrando ' + Math.min(LIMIT, sorted.length) + ' de ' + sorted.length + ' solicitudes' +
      (sorted.length > LIMIT ? ' (afina los filtros para ver el resto)' : '');
    el('empty').style.display = sorted.length ? 'none' : 'block';
  }

  function update() {
    const f = filtered();
    renderKpis(f);
    renderCharts(f);
    renderTable(f);
  }

  el('thead').addEventListener('click', e => {
    const th = e.target.closest('th');
    if (!th) return;
    const k = th.getAttribute('data-k');
    sort = sort.k === k ? { k, dir: -sort.dir } : { k, dir: -1 };
    renderTable(filtered());
  });
  ['fPri', 'fCat', 'fTier', 'fSt'].forEach(id => el(id).addEventListener('change', update));
  el('fQ').addEventListener('input', update);
  el('reset').addEventListener('click', () => {
    ['fPri', 'fCat', 'fTier', 'fSt', 'fQ'].forEach(id => { el(id).value = ''; });
    update();
  });
  update();
}
