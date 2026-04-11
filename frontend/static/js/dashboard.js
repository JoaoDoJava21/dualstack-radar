// ================================================================
// dashboard.js — DualStack Radar
// Navegação, filtros, scan, polling e renderização de leads
// ================================================================


// ================================================================
// 1. NAVEGAÇÃO LATERAL
// ================================================================

const PAGE_TITLES = {
  radar:     ['Lead <span>Radar</span>',          'DualStack Solutions — João Victor & Carlos'],
  historico: ['<span>Histórico</span> de Leads',  'Todos os leads capturados nesta sessão'],
  template:  ['Template de <span>Proposta</span>','System prompt usado para gerar propostas'],
  config:    ['<span>Configurações</span>',        'DualStack Radar — parâmetros do sistema'],
};

/**
 * Navega para a página correspondente ao item clicado na sidebar.
 * @param {HTMLElement} el - Item clicado (.nav-item)
 */
function setPage(el) {
  document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
  el.classList.add('active');

  const page = el.dataset.page || 'radar';

  document.getElementById('page-radar').style.display    = page === 'radar'    ? '' : 'none';
  document.getElementById('page-template').style.display = page === 'template' ? '' : 'none';
  document.getElementById('page-config').style.display   = page === 'config'   ? '' : 'none';

  const showLeads = page === 'radar' || page === 'historico';
  document.getElementById('leads-section').style.display = showLeads ? '' : 'none';

  if (page === 'historico') {
    document.getElementById('leads-section-title').textContent = 'Histórico de leads';
  } else {
    document.getElementById('leads-section-title').textContent = 'Leads capturados';
  }

  const [title, sub] = PAGE_TITLES[page] || PAGE_TITLES.radar;
  document.querySelector('.page-title').innerHTML  = title;
  document.querySelector('.page-sub').textContent  = sub;

  if (page === 'config') verificarConfig();
}

/** Consulta /api/status para exibir se GROQ_API_KEY está configurada. */
async function verificarConfig() {
  try {
    const r = await fetch('/api/status');
    const s = await r.json();
    const el = document.getElementById('cfg-groq-status');
    if (el) el.innerHTML = s.groq_ok
      ? '<span style="color:#10b981">✓ Configurada</span>'
      : '<span style="color:#ff6b6b">✗ Não configurada (.env)</span>';
  } catch { /* silencioso */ }
}


// ================================================================
// 2. FILTRO DE PLATAFORMA
// ================================================================

const platsAtivas = new Set(['todos', 'Workana', '99Freelas', 'Reddit', 'GitHub']);

/**
 * Alterna a visibilidade de uma plataforma e reaplica o filtro.
 * @param {HTMLElement} el   - Pill clicada (.plat-pill)
 * @param {string}      plat - Chave da plataforma ('todos' | 'Workana' | ...)
 */
function togglePlat(el, plat) {
  el.classList.toggle('on');
  if (platsAtivas.has(plat)) platsAtivas.delete(plat);
  else                        platsAtivas.add(plat);
  filtrarLeads();
}

/**
 * Mostra ou esconde cada card de lead conforme as plataformas ativas.
 */
function filtrarLeads() {
  const todos = platsAtivas.has('todos');
  document.querySelectorAll('.lead-card[data-plat]').forEach(card => {
    const visivel = todos || platsAtivas.has(card.dataset.plat);
    card.style.display = visivel ? '' : 'none';
  });
}


// ================================================================
// 3. ESTADO LOCAL
// ================================================================

let scanning   = false;
let totalLeads = 0;
let totalProps = 0;
let leadIds    = new Set();
let pollTimer  = null;

const platClass = {
  'Workana':   'plat-workana',
  '99Freelas': 'plat-99freelas',
  'Reddit':    'plat-reddit',
  'GitHub':    'plat-github',
};

const STEPS = [
  { id: 'st-workana', keyword: 'Workana',   prog: 20 },
  { id: 'st-freelas', keyword: '99Freelas', prog: 45 },
  { id: 'st-reddit',  keyword: 'Reddit',    prog: 65 },
  { id: 'st-github',  keyword: 'GitHub',    prog: 80 },
  { id: 'st-groq',    keyword: 'proposta',  prog: 95, groq: true },
];


// ================================================================
// 4. INICIAR SCAN — POST /api/scan
// ================================================================

async function iniciarScan() {
  if (scanning) return;

  const resp = await fetch('/api/scan', { method: 'POST' });
  const data = await resp.json();
  if (!data.ok) {
    alert(data.msg || 'Erro ao iniciar scan');
    return;
  }

  scanning = true;
  const btn = document.getElementById('btn-scan');
  const lbl = document.getElementById('btn-label');
  btn.classList.add('scanning');
  lbl.textContent = 'Escaneando...';
  document.getElementById('sf-label').textContent   = 'Rodando scan...';
  document.getElementById('scan-bar').style.display = 'block';

  STEPS.forEach(s => {
    const el = document.getElementById(s.id);
    el.classList.remove('active', 'done');
  });

  document.getElementById('empty-state')?.remove();

  pollTimer = setInterval(pollStatus, 1200);
}


// ================================================================
// 5. POLLING DE STATUS — GET /api/status
// ================================================================

async function pollStatus() {
  let status;
  try {
    const r = await fetch('/api/status');
    status   = await r.json();
  } catch {
    return;
  }

  const log = status.log || [];
  if (log.length) {
    document.getElementById('scan-msg').textContent = log[log.length - 1];
  }

  STEPS.forEach(s => {
    const el = document.getElementById(s.id);
    let jaFeito, emCurso;
    if (s.groq) {
      jaFeito = log.some(l => l.includes('concluído'));
      emCurso = !jaFeito && log.some(l => l.includes('Gerando proposta') || l.includes('Total:'));
    } else {
      jaFeito = log.some(l => l.includes(s.keyword) && l.includes('leads encontrados'));
      emCurso = log.some(l => l.includes('Rastreando ' + s.keyword));
    }

    if (jaFeito) {
      el.classList.remove('active');
      el.classList.add('done');
      document.getElementById('prog-fill').style.width = s.prog + '%';
    } else if (emCurso) {
      el.classList.add('active');
      el.classList.remove('done');
    }
  });

  await buscarLeads();

  if (!status.rodando) {
    clearInterval(pollTimer);
    await buscarLeads();

    document.getElementById('prog-fill').style.width = '100%';
    document.getElementById('scan-msg').textContent  = '✓ Scan completo!';

    await sleep(800);

    document.getElementById('scan-bar').style.display = 'none';

    const ultimo = status.ultimo_scan || '--:--';
    document.getElementById('sf-time').textContent  = 'Último scan: ' + ultimo;
    document.getElementById('sf-label').textContent = 'Online';

    const btn = document.getElementById('btn-scan');
    btn.classList.remove('scanning');
    document.getElementById('btn-label').textContent = 'Novo Scan';
    scanning = false;
  }
}


// ================================================================
// 6. BUSCAR LEADS — GET /api/leads
// ================================================================

async function buscarLeads() {
  let leads;
  try {
    const r = await fetch('/api/leads');
    leads    = await r.json();
  } catch {
    return;
  }

  leads.forEach((lead, idx) => {
    if (leadIds.has(lead.id)) return;
    leadIds.add(lead.id);
    addLeadCard(lead, idx);
    totalLeads++;
    if (lead.proposta) totalProps++;

    document.getElementById('st-total').textContent    = totalLeads;
    document.getElementById('st-prop').textContent     = totalProps;
    document.getElementById('live-count').textContent  = totalLeads;
    document.getElementById('hist-count').textContent  = totalLeads;
    document.getElementById('leads-badge').textContent =
      totalLeads + ' resultado' + (totalLeads !== 1 ? 's' : '');
  });
}


// ================================================================
// 7. RENDERIZAR CARD DE LEAD
// ================================================================

function addLeadCard(lead, idx) {
  const grid = document.getElementById('leads-grid');
  const pc   = platClass[lead.plataforma] || 'plat-github';

  const card = document.createElement('div');
  card.className             = 'lead-card';
  card.dataset.plat          = lead.plataforma;
  card.style.animationDelay  = (idx * 0.1) + 's';

  const linkShort = (lead.link || '').replace('https://', '').substring(0, 55);
  const proposta  = (lead.proposta || '').replace(/\n/g, '<br>');

  card.innerHTML = `
    <div class="lead-top">
      <span class="lead-plat ${pc}">${lead.plataforma}</span>
      <span class="lead-time">Capturado · ${lead.hora || '--:--'}</span>
    </div>
    <div class="lead-title">${lead.pedido}</div>
    <a class="lead-link" href="${lead.link}" target="_blank" rel="noopener noreferrer">
      <svg viewBox="0 0 24 24">
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
        <polyline points="15 3 21 3 21 9"/>
        <line x1="10" y1="14" x2="21" y2="3"/>
      </svg>
      ${linkShort}...
    </a>
    <div class="proposal-box">
      <div class="proposal-label">Proposta gerada pela IA</div>
      <div class="proposal-text">${proposta}</div>
    </div>
    <div class="lead-actions">
      <button class="btn-act btn-open" onclick="window.open('${lead.link}','_blank')">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
          <polyline points="15 3 21 3 21 9"/>
          <line x1="10" y1="14" x2="21" y2="3"/>
        </svg>
        Ver projeto
      </button>
      <button class="btn-act btn-copy"
              onclick="copiarProposta(this, '${encodeURIComponent(lead.proposta || '')}')">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
        </svg>
        Copiar proposta
      </button>
    </div>
  `;

  grid.insertBefore(card, grid.firstChild);
}


// ================================================================
// 8. COPIAR PROPOSTA PARA CLIPBOARD
// ================================================================

function copiarProposta(btn, encoded) {
  const text = decodeURIComponent(encoded);
  navigator.clipboard.writeText(text).then(() => {
    btn.classList.add('copied');
    btn.innerHTML = `
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"/>
      </svg> Copiado!`;

    setTimeout(() => {
      btn.classList.remove('copied');
      btn.innerHTML = `
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
        </svg> Copiar proposta`;
    }, 2000);
  });
}


// ================================================================
// 9. LIMPAR LEADS — POST /api/clear
// ================================================================

async function limparLeads() {
  if (scanning) return;
  await fetch('/api/clear', { method: 'POST' });

  document.getElementById('leads-grid').innerHTML = `
    <div class="empty" id="empty-state">
      <div class="empty-icon">⚡</div>
      <div class="empty-title">Nenhum lead ainda</div>
      <div class="empty-sub">Clique em "Iniciar Scan" para começar</div>
    </div>`;

  totalLeads = 0; totalProps = 0; leadIds.clear();
  document.getElementById('st-total').textContent    = '0';
  document.getElementById('st-prop').textContent     = '0';
  document.getElementById('live-count').textContent  = '0';
  document.getElementById('hist-count').textContent  = '0';
  document.getElementById('leads-badge').textContent = '0 resultados';
  document.getElementById('btn-label').textContent   = 'Iniciar Scan';
  document.getElementById('sf-label').textContent    = 'Pronto';
  document.getElementById('sf-time').textContent     = 'Último scan: —';
}


// ================================================================
// 10. UTILITÁRIOS
// ================================================================

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
