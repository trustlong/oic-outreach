'use strict';
// Shared code for OIC Outreach pages (index.html + nearme.html)

// ── Constants ─────────────────────────────────────────────────────────────────
const ETH_COLOR = {
  "Asian/PI":"#1a73e8","Hispanic":"#e67e22","Black":"#8e44ad",
  "White":"#7f8c8d","Unknown":"#95a5a6","Am.Indian":"#27ae60","Multiracial":"#c0392b",
};

const ENTITY_RE = /\b(LLC|INC|CORP|LTD|LP|LLP|TRUST|TRS|PROPERTIES|HOLDINGS|REALTY|GROUP|FUND|FOUNDATION|SERIES|CONSERVE|BUILDWELL|ENTERPRISES|PARTNERS|VENTURES|CAPITAL|INVESTMENTS|ESTATE|MORTGAGE|TITLE|ABSTRACT)\b/i;

const MONTH_NAMES = ['January','February','March','April','May','June','July','August','September','October','November','December'];

// ── Shared state (set by each page) ──────────────────────────────────────────
let currentCards   = [];  // [{r, score, dist}] currently displayed
let followUpSource = [];  // all records eligible for Follow Up

// ── Utilities ─────────────────────────────────────────────────────────────────
function isEntity(owner) { return ENTITY_RE.test(owner || ''); }

function parseCSV(text) {
  const lines = text.trim().split('\n');
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
  return lines.slice(1).map(line => {
    const vals = [];
    let cur = '', inQuote = false;
    for (const ch of line) {
      if (ch === '"') { inQuote = !inQuote; }
      else if (ch === ',' && !inQuote) { vals.push(cur.trim()); cur = ''; }
      else { cur += ch; }
    }
    vals.push(cur.trim());
    const obj = {};
    headers.forEach((h, i) => obj[h] = vals[i] || '');
    return obj;
  });
}

function parseDate(s) {
  if (!s) return null;
  for (const re of [/(\d{2})\/(\d{2})\/(\d{4})/, /(\d{4})-(\d{2})-(\d{2})/]) {
    const m = s.match(re);
    if (m) return re.source.startsWith('(\\d{2})') ? new Date(m[3],m[1]-1,m[2]) : new Date(m[1],m[2]-1,m[3]);
  }
  return null;
}

function fmtOrigin(o) {
  o = String(o || '');
  if (o.startsWith('Out-of-state')) return '✈ Moved from ' + o.replace('Out-of-state (','').replace(')','');
  if (o.startsWith('In-state')) return '↔ Moved within VA';
  return '? Origin unknown';
}

function fmtName(n) {
  return String(n || '').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
}

function distMiles(lat1, lon1, lat2, lon2) {
  const R = 3958.8, dLat = (lat2-lat1)*Math.PI/180, dLon = (lon2-lon1)*Math.PI/180;
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

// ── Period helpers ────────────────────────────────────────────────────────────
function lastMonthRange() {
  const now = new Date();
  const end   = new Date(now.getFullYear(), now.getMonth(), 1);
  const start = new Date(end.getFullYear(), end.getMonth()-1, 1);
  return { start, end, label: `${MONTH_NAMES[start.getMonth()]} ${start.getFullYear()}` };
}

function lastYearRange() {
  const start = new Date(); start.setFullYear(start.getFullYear()-1);
  return { start, end: null, label: 'Past 12 Months' };
}

function inRange(dateStr, range) {
  const d = parseDate(dateStr);
  return d && d >= range.start && (range.end === null || d < range.end);
}

// ── localStorage ──────────────────────────────────────────────────────────────
function cardKey(r) {
  const name = (r.Owner1||'').replace(/[^a-z0-9]/gi,'').toLowerCase().slice(0,12);
  const date = (r.Sale1D||'').replace(/[^0-9]/g,'');
  return `oic-${name}-${date}-${parseFloat(r.LAT||0).toFixed(3)}-${parseFloat(r.LON||0).toFixed(3)}`;
}
function getState(r)        { return JSON.parse(localStorage.getItem(cardKey(r)) || '{}'); }
function setState(r, patch) { const s=getState(r); localStorage.setItem(cardKey(r), JSON.stringify({...s,...patch})); }

// ── Filtering & ranking ───────────────────────────────────────────────────────
function top10(records, range, scoreFn) {
  return records
    .filter(r => !isEntity(r.Owner1) && r.MOVE_ORIGIN !== 'Local' && inRange(r.Sale1D, range))
    .map(r => { const s = scoreFn(r); return s ? {r, ...s} : null; })
    .filter(Boolean)
    .sort((a, b) => b.score - a.score || a.dist - b.dist)
    .slice(0, 10);
}

// ── CSV loading ───────────────────────────────────────────────────────────────
async function loadCSV(url) {
  const res = await fetch(url);
  return parseCSV(await res.text());
}

// ── Card HTML ─────────────────────────────────────────────────────────────────
function cardHTML(r, i, score, distLabel) {
  const eth   = r.ESTIMATED_ETHNICITY || 'Unknown';
  const color = ETH_COLOR[eth] || '#95a5a6';
  const nav   = (r.LAT && r.LON) ? `https://maps.google.com/?q=${parseFloat(r.LAT)},${parseFloat(r.LON)}` : '';
  const addr  = (r.LocAddr||'').replace(/^\d+\.0\s*/,'').trim() || 'Address on file';
  const st    = getState(r);
  return `
  <div class="card" id="card-${i}" style="border-left-color:${color};opacity:${st.visited?'0.45':'1'}">
    <div class="card-header" onclick="toggleCard(${i})">
      <span class="rank">${i+1}</span>
      <div class="card-main">
        <div class="card-name">${fmtName(r.Owner1||'')}</div>
        <div class="card-meta">
          <span>${distLabel} · ${r.SOURCE||''}</span>
          <span style="color:#aaa">·</span>
          <span>${r.Sale1D||''}</span>
        </div>
      </div>
      <span class="eth-badge" style="background:${color}">${eth}</span>
      <span class="chevron">▼</span>
    </div>
    <div class="card-detail">
      <div class="detail-row"><span class="detail-label">Address</span><span class="detail-value">${addr}, ${r.SOURCE||''}</span></div>
      <div class="detail-row"><span class="detail-label">Origin</span><span class="detail-value">${fmtOrigin(r.MOVE_ORIGIN||'')}</span></div>
      <div class="detail-row"><span class="detail-label">Household</span><span class="detail-value">Est. ${r.EST_HOUSEHOLD_SIZE||'?'} people</span></div>
      <div class="score-dots">
        ${Array.from({length:7},(_,j)=>`<div class="dot ${j<score?'filled':''}"></div>`).join('')}
        <span class="score-label">Score ${score}/7</span>
      </div>
      ${nav?`<a class="nav-btn" href="${nav}" target="_blank" rel="noopener"
        onclick="gtag('event','navigate_address',{ethnicity:'${eth}',county:'${r.SOURCE||''}'})">📍 Navigate to address</a>`:''}
      <div class="actions">
        <button class="action-btn ${st.visited?'visited':''}" id="visited-${i}" onclick="toggleVisited(${i},event)">${st.visited?'✅ Visited':'❓ Visited'}</button>
        <button class="action-btn ${st.interested?'interested':''}" id="interested-${i}" onclick="toggleInterested(${i},event)">${st.interested?'📌 Following Up':'❓ Follow Up?'}</button>
        <button class="action-btn" onclick="toggleNote(${i},event)">📝 Note</button>
      </div>
      <textarea class="note-area ${st.note?'visible':''}" id="note-${i}" placeholder="Add a note..."
        oninput="saveNote(${i})" onchange="saveNote(${i})">${st.note||''}</textarea>
      <button class="note-save ${st.note?'visible':''}" id="note-save-${i}" onclick="saveNote(${i})">Save note</button>
      <div class="note-saved-text" id="note-saved-${i}">✓ Saved</div>
    </div>
  </div>`;
}

function renderCards(items, containerId) {
  const el = document.getElementById(containerId);
  if (!items.length) { el.innerHTML = '<div class="empty">No records for this period.</div>'; return; }
  el.innerHTML = items.map((item, i) => cardHTML(item.r, i, item.score, `${item.dist.toFixed(1)} mi`)).join('');
}

// ── Card interactions ─────────────────────────────────────────────────────────
function toggleCard(i) {
  const card = document.getElementById('card-'+i);
  card.classList.toggle('open');
  const isOpen = card.classList.contains('open');
  card.style.opacity = (!isOpen && document.getElementById('visited-'+i)?.classList.contains('visited')) ? '0.45' : '1';
}

function toggleVisited(i, e) {
  e.stopPropagation();
  const btn = document.getElementById('visited-'+i);
  const active = btn.classList.toggle('visited');
  btn.textContent = active ? '✅ Visited' : '❓ Visited';
  setState(currentCards[i].r, {visited: active});
  gtag('event','mark_visited',{status:active?'visited':'unvisited',ethnicity:currentCards[i].r.ESTIMATED_ETHNICITY||'Unknown',county:currentCards[i].r.SOURCE||''});
  const card = document.getElementById('card-'+i);
  card.style.opacity = (active && !card.classList.contains('open')) ? '0.45' : '1';
}

function toggleInterested(i, e) {
  e.stopPropagation();
  const btn = document.getElementById('interested-'+i);
  const active = btn.classList.toggle('interested');
  btn.textContent = active ? '📌 Following Up' : '❓ Follow Up?';
  setState(currentCards[i].r, {interested: active});
  gtag('event','mark_follow_up',{status:active?'following':'unfollowing',ethnicity:currentCards[i].r.ESTIMATED_ETHNICITY||'Unknown',county:currentCards[i].r.SOURCE||''});
  renderFollowUp();
}

function toggleNote(i, e) {
  e.stopPropagation();
  document.getElementById('note-'+i).classList.toggle('visible');
  document.getElementById('note-save-'+i).classList.toggle('visible');
  document.getElementById('note-'+i).focus();
}

function saveNote(i) {
  const val = document.getElementById('note-'+i).value;
  setState(currentCards[i].r, {note: val});
  gtag('event','save_note');
  const key = cardKey(currentCards[i].r);
  const fpTA = document.getElementById('fp-note-'+key);
  if (fpTA && fpTA.value !== val) fpTA.value = val;
  const saved = document.getElementById('note-saved-'+i);
  saved.style.display = 'block';
  setTimeout(() => saved.style.display='none', 1500);
}

// ── Follow Up ─────────────────────────────────────────────────────────────────
function renderFollowUp() {
  const interested = followUpSource.filter(r => getState(r).interested);
  const wrap  = document.getElementById('followup-wrap');
  const count = document.getElementById('followup-count');
  const cont  = document.getElementById('followup-cards');
  if (!interested.length) { wrap.classList.remove('has-items'); return; }
  wrap.classList.add('has-items');
  count.textContent = `(${interested.length})`;
  cont.innerHTML = interested.map(r => {
    const eth   = r.ESTIMATED_ETHNICITY || 'Unknown';
    const color = ETH_COLOR[eth] || '#95a5a6';
    const key   = cardKey(r);
    const note  = getState(r).note || '';
    const nav   = (r.LAT && r.LON) ? `https://maps.google.com/?q=${parseFloat(r.LAT)},${parseFloat(r.LON)}` : '';
    const addr  = (r.LocAddr||'').replace(/^\d+\.0\s*/,'').trim() || 'Address on file';
    return `
    <div class="card" id="fp-card-${key}" style="border-left-color:${color};margin-bottom:6px">
      <div class="card-header" onclick="toggleFpCard('${key}')">
        <div class="card-main">
          <div class="card-name">${fmtName(r.Owner1||'')}</div>
          <div class="card-meta"><span>${r.SOURCE||''}</span><span style="color:#aaa">·</span><span>${r.Sale1D||''}</span></div>
        </div>
        <span class="eth-badge" style="background:${color}">${eth}</span>
        <span class="chevron">▼</span>
      </div>
      <div class="card-detail">
        <div class="detail-row"><span class="detail-label">Address</span><span class="detail-value">${addr}, ${r.SOURCE||''}</span></div>
        <div class="detail-row"><span class="detail-label">Origin</span><span class="detail-value">${fmtOrigin(r.MOVE_ORIGIN||'')}</span></div>
        <div class="detail-row" style="flex-direction:column;gap:4px">
          <span class="detail-label">Note</span>
          <textarea class="note-area visible" id="fp-note-${key}" style="margin-top:4px" placeholder="Add a note..."
            oninput="saveFpNote('${key}')" onchange="saveFpNote('${key}')">${note}</textarea>
          <button class="note-save visible" onclick="saveFpNote('${key}')">Save note</button>
          <div class="note-saved-text" id="fp-note-saved-${key}">✓ Saved</div>
        </div>
        ${nav?`<a class="nav-btn" href="${nav}" target="_blank" rel="noopener"
          onclick="gtag('event','navigate_address',{ethnicity:'${eth}',county:'${r.SOURCE||''}'})">📍 Navigate to address</a>`:''}
        <div style="margin-top:10px">
          <button style="font-size:.78em;color:#c0392b;background:none;border:1px solid #eaa;border-radius:6px;padding:5px 10px;cursor:pointer"
            onclick="removeFollowUp('${key}',event)">✕ Remove from Following Up</button>
        </div>
      </div>
    </div>`;
  }).join('');
}

function toggleFpCard(key) { document.getElementById('fp-card-'+key)?.classList.toggle('open'); }

function toggleFollowUpSection() {
  const cards   = document.getElementById('followup-cards');
  const chevron = document.getElementById('followup-chevron');
  const collapsed = cards.style.display === 'none';
  cards.style.display = collapsed ? '' : 'none';
  chevron.style.transform = collapsed ? '' : 'rotate(180deg)';
}

function saveFpNote(key) {
  const val = document.getElementById('fp-note-'+key)?.value || '';
  const stored = JSON.parse(localStorage.getItem(key) || '{}');
  localStorage.setItem(key, JSON.stringify({...stored, note: val}));
  currentCards.forEach((item, i) => {
    if (cardKey(item.r) === key) {
      const ta = document.getElementById('note-'+i);
      if (ta && ta.value !== val) ta.value = val;
    }
  });
  const saved = document.getElementById('fp-note-saved-'+key);
  if (saved) { saved.style.display='block'; setTimeout(()=>saved.style.display='none',1500); }
}

function removeFollowUp(key, e) {
  e.stopPropagation();
  const stored = JSON.parse(localStorage.getItem(key) || '{}');
  localStorage.setItem(key, JSON.stringify({...stored, interested: false}));
  gtag('event','remove_follow_up');
  currentCards.forEach((item, i) => {
    if (cardKey(item.r) === key) {
      const btn = document.getElementById('interested-'+i);
      if (btn) { btn.classList.remove('interested'); btn.textContent = '❓ Follow Up?'; }
    }
  });
  renderFollowUp();
}
