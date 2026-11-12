/* =====================================================================
 *  本地工作台 · 交互逻辑
 *  基于「彩色漫画工作台 · Violet」反编译重构：
 *   - 所有内容从 js/data.js 读取（DESK_DATA / DESK_LABELS）
 *   - localStorage 全部加 yz_desk_ 前缀（Cohub app 同源，避免和原作互相覆盖）
 *   - 用户输入一律转义后再进 innerHTML
 * ===================================================================== */
(function () {
  'use strict';
  const D = window.DESK_DATA;
  const LBL = window.DESK_LABELS;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (v) => String(v == null ? '' : v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
    del(k) { try { localStorage.removeItem(k); } catch (e) {} },
  };
  const K = {
    theme: 'yz_desk_theme_v1',
    todos: (D.work && D.work.storageKey) || 'yz_desk_todos_v1',
    notes: D.notesKey || 'yz_desk_notes_v1',
    quick: 'yz_desk_quick_v1',
    tea: (D.mug && D.mug.storageKey) || 'yz_desk_tea_v1',
    mora: 'yz_desk_mora_v1',
  };

  /* ---------------- Session 绑定（js/sessions.js） ---------------- */
  const SS = window.DESK_SESSIONS || { bind: {} };
  // 'daily'：按今天（Asia/Shanghai）取飞书每日 Daily Discussion；没有今天的就取最近一天
  function dailySession() {
    const list = window.DESK_DAILY_SESSIONS || [];
    if (!list.length) return null;
    const today = new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 10);
    const hit = list.find((e) => e.date === today);
    const e = hit || [...list].filter((x) => x.date <= today).pop() || list[list.length - 1];
    return { id: e.id, title: e.title + (hit ? '' : '（今天的还没同步，先开最近一天）'), isToday: !!hit };
  }
  function binding(id) {
    const b = SS.bind && SS.bind[id];
    if (!b || !b.id) return null;
    if (b.id === 'daily') {
      const d = dailySession(); if (!d) return null;
      const url = (SS.url || '').replace('{space}', SS.space || '').replace('{id}', d.id);
      return { id: d.id, url, title: b.title || d.title, open: b.open === 'direct' ? 'direct' : 'panel', daily: true };
    }
    const m = /sessions\/([A-Za-z0-9-]+)/.exec(b.id);          // 允许直接粘整条链接
    const sid = m ? m[1] : String(b.id).trim();
    if (!/^[A-Za-z0-9-]{8,}$/.test(sid)) return null;
    const url = (SS.url || '').replace('{space}', SS.space || '').replace('{id}', sid);
    return { id: sid, url, title: b.title || '已绑定 Session', open: b.open === 'direct' ? 'direct' : 'panel' };
  }
  function openSession(id) {
    const b = binding(id); if (!b) return false;
    window.open(b.url, '_blank', 'noopener');
    toast('↗ 打开 Session · ' + b.title);
    return true;
  }
  function sessionFooter(id) {
    const b = binding(id); if (!b) return '';
    if (id === 'monitor' && b.daily) return '';   // 显示器面板顶部已经有今天的 daily 按钮
    return `<div class="sess-foot"><a class="btn sess-btn" href="${esc(b.url)}" target="_blank" rel="noopener">↗ 打开绑定的 Session · ${esc(b.title)}</a></div>`;
  }

  const stage = $('#stage');
  const label = $('#label');
  const modal = $('#modal');
  const panelBody = $('#panelBody');
  const toastBox = $('#toast');
  const CAPTURE = /[?&]capture=([a-z]+)/.exec(location.search);

  const state = { night: true, sound: false, filter: false, lamp: false, theme: 'liyue' };
  let panelCleanup = [];

  /* ---------------- 舞台缩放：1600×1000 固定画布，等比缩放居中 ---------------- */
  function fit() {
    if (CAPTURE) { stage.style.transform = 'none'; return; }
    const availH = Math.max(420, window.innerHeight - 70);
    const s = Math.min(window.innerWidth / 1600, availH / 1000) * 0.97;
    stage.style.transform = `translate(-50%,-50%) scale(${s})`;
  }
  window.addEventListener('resize', fit);

  /* ---------------- 白天 / 黑夜 ---------------- */
  function setNight(n) {
    state.night = n;
    stage.classList.toggle('night', n);
    stage.classList.toggle('day', !n);
    const t = $('[data-tool="dn"] .ico');
    if (t) t.textContent = n ? '☾' : '☀';
  }
  function initTime() {
    const m = D.window.mode;
    let night;
    if (m === 'day') night = false;
    else if (m === 'night') night = true;
    else { const h = new Date().getHours(); night = h < 6 || h >= 18; }
    setNight(night);
  }

  /* ---------------- 配色主题 ---------------- */
  const THEMES = ['liyue', 'sun', 'dusk', 'mint', 'grape', 'night'];
  const THEME_NAMES = { liyue: '璃月', sun: '暖阳', dusk: '黄昏', mint: '薄荷', grape: '葡萄', night: '夜灰' };
  function initTheme() {
    let t = store.get(K.theme, null);
    if (!THEMES.includes(t)) t = (D.meta && D.meta.theme) || 'liyue';
    state.theme = t;
    stage.dataset.theme = t;
  }
  function setTheme(t) {
    state.theme = t;
    stage.dataset.theme = t;
    store.set(K.theme, t);
    toast('🎨 配色 · ' + (THEME_NAMES[t] || t));
  }
  function cycleTheme() {
    setTheme(THEMES[(THEMES.indexOf(state.theme) + 1) % THEMES.length]);
    window.playSfx('click');
  }

  /* ---------------- 音效：WebAudio 实时合成，无音频文件 ---------------- */
  let AC = null;
  function actx() {
    if (!AC) AC = new (window.AudioContext || window.webkitAudioContext)();
    if (AC.state === 'suspended') AC.resume();
    return AC;
  }
  function beep(freq, dur, type = 'square', vol = 0.06, when = 0) {
    if (!state.sound) return;
    const ctx = actx();
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = type; o.frequency.value = freq;
    o.connect(g); g.connect(ctx.destination);
    const t = ctx.currentTime + when;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.start(t); o.stop(t + dur + 0.02);
  }
  window.playSfx = function (type) {
    switch (type) {
      case 'hover': beep(660, 0.05, 'sine', 0.025); break;
      case 'click': beep(440, 0.09, 'square', 0.06); beep(660, 0.08, 'square', 0.04, 0.04); break;
      case 'hit': beep(300, 0.07, 'square', 0.07); break;
      case 'coin': beep(880, 0.07, 'square', 0.06); beep(1320, 0.1, 'square', 0.05, 0.06); break;
      case 'over': beep(400, 0.15, 'sawtooth', 0.06); beep(240, 0.25, 'sawtooth', 0.05, 0.12); break;
      case 'open': beep(520, 0.07, 'sine', 0.05); beep(780, 0.09, 'sine', 0.045, 0.05); break;
      case 'close': beep(600, 0.08, 'sine', 0.045); beep(380, 0.1, 'sine', 0.04, 0.05); break;
    }
  };

  /* ---------------- toast ---------------- */
  function toast(msg) {
    const el = document.createElement('div');
    el.className = 'tst'; el.textContent = msg;
    toastBox.appendChild(el);
    setTimeout(() => el.remove(), 2000);
  }

  /* ============================================================
   *  场景装配：把 data.js 的内容画到桌面上
   * ============================================================ */
  function buildChrome() {
    document.title = D.meta.title;
    const b = $('.brand');
    if (b) b.innerHTML = `<b>${esc(D.meta.owner)}</b><span>${esc(D.meta.brandSub)}</span>`;
    const tk = $('#ticker .tick-in');
    if (tk && D.meta.ticker) tk.textContent = D.meta.ticker;
    const wn = $('.wname');
    if (wn) wn.textContent = D.window.sign || D.window.city;
  }

  function buildBoard() {
    const a = D.about;
    const t = $('.board-title');
    if (t && a.boardTitle) t.innerHTML = `${esc(a.boardTitle[0])}<br><em>${esc(a.boardTitle[1])}</em>`;
    (a.polaroids || []).forEach((p, i) => {
      const pol = $('.polaroid.p' + (i + 1)); if (!pol) return;
      const ph = $('.ph', pol);
      ph.style.backgroundImage = `url('${p.file}')`;
      ph.style.backgroundSize = 'cover';
      ph.style.backgroundPosition = p.pos || 'center';
      $('span', pol).textContent = p.cap;
    });
    const chips = $$('.tag-chip');
    (a.chips || []).forEach((c, i) => { if (chips[i]) chips[i].textContent = c; });
  }

  function buildKbd() {
    const kbd = $('#kbd'); if (!kbd) return;
    let html = '';
    for (let i = 0; i < 70; i++) html += `<i${[12, 25, 40, 55, 63].includes(i) ? ' class="glow"' : ''}></i>`;
    kbd.innerHTML = html;
  }

  /* =====================================================================
   *  便签墙：照「可走的世界」的逻辑 —— 真相是 notes/便签.log.jsonl（只追加）
   *  页面 → App Action「notes」（拥有者在平台沙箱里写 log）→ 回放出当前板上 + 留档
   *  首屏用 js/notes-board.js 快照；长期管理 Session 见 js/sessions.js 的 notes 绑定
   * ===================================================================== */
  const K_NB = 'yz_desk_notes_board_v2';
  const NOTE_COLORS = ['#ffd23f', '#ff8fb1', '#8ee6c8', '#9ec5ff', '#ffb020', '#c9b6ff', '#b8e986'];
  const NB = {
    data: (() => { const c = store.get(K_NB, null), s = window.DESK_NOTES_BOARD; if (c && s && String(s.at) > String(c.at)) return s; return c || s || { board: (D.notes || []).map((n, i) => ({ id: 'local-' + i, text: n.text, color: n.color, rot: n.rot })), archive: [] }; })(),
    status: 'snapshot',     // snapshot | syncing | live | offline | error
    pending: 0,
    listeners: new Set(),
  };
  NB.base = NB.data;   // 最近一次确认过的板子：写失败时退回这里
  function nbSet(d) { if (d && Array.isArray(d.board)) { NB.data = d; NB.base = d; store.set(K_NB, d); } NB.listeners.forEach((fn) => fn()); paintNotesOnDesk(); }
  async function notesAction(input) {
    return window.localAction('notes', input);
  }

  async function notesDo(input, okMsg) {
    NB.pending++; NB.status = 'syncing'; nbSet();
    try {
      const j = await notesAction(input);
      NB.status = 'live'; NB.pending--; nbSet(j);
      if (okMsg) toast(okMsg);
      return true;
    } catch (e) {
      NB.pending--; NB.status = e.offline ? 'offline' : 'error'; NB.data = NB.base; nbSet();
      toast(e.offline ? '本地服务没连上：便签只能看' : '便签没写进去：' + e.message);
      return false;
    }
  }
  function loadNotes() { return (NB.data.board || []).slice(0, 5); }   // 墙上最多挂 5 张（最新的）
  function paintNotesOnDesk() {
    const box = $('#noteCards'); if (!box) return;
    const all = NB.data.board || [];
    box.innerHTML = loadNotes().map((n, i) =>
      `<div class="note" data-i="${i}" data-id="${esc(n.id)}" style="background:${esc(n.color)};transform:rotate(${+n.rot || 0}deg)" title="点一下改这句话"><span class="clip"></span><span class="note-tx">${esc(n.text).replace(/\n/g, '<br>')}</span></div>`
    ).join('') + (all.length > 5 ? `<div class="note-more">+${all.length - 5}</div>` : '');
  }
  function buildNotes() {
    const box = $('#noteCards'); if (!box) return;
    box.addEventListener('click', (e) => {
      if (e.target.closest('.note-more')) { e.stopPropagation(); openObject('notes'); return; }
      const card = e.target.closest('.note'); if (!card) return;
      e.stopPropagation();
      const tx = card.querySelector('.note-tx');
      if (tx.isContentEditable) return;
      tx.contentEditable = 'true';
      tx.classList.add('editing');
      tx.focus();
      const sel = window.getSelection(); const range = document.createRange();
      range.selectNodeContents(tx); sel.removeAllRanges(); sel.addRange(range);
    });
    box.addEventListener('keydown', (e) => {
      const tx = e.target.closest('.note-tx'); if (!tx) return;
      e.stopPropagation();
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); tx.blur(); }
      if (e.key === 'Escape') tx.blur();
    });
    box.addEventListener('blur', (e) => {
      const tx = e.target.closest && e.target.closest('.note-tx'); if (!tx) return;
      const id = tx.closest('.note').dataset.id;
      const n = (NB.data.board || []).find((x) => x.id === id);
      const text = tx.innerText.replace(/\u00a0/g, ' ').replace(/\n{3,}/g, '\n\n').trim();
      tx.contentEditable = 'false'; tx.classList.remove('editing');
      if (!n || !text || text === n.text) { paintNotesOnDesk(); return; }
      n.text = text; paintNotesOnDesk();                 // 先在墙上显示，再写进 log
      notesDo({ op: 'edit', id, text }, '便签已保存 ✎');
    }, true);
    paintNotesOnDesk();
    // 打开页面就去拉一次最新（本地服务没起来就安静地用快照）
    notesAction({ op: 'list' }).then((j) => { NB.status = 'live'; nbSet(j); }).catch((e) => { NB.status = e.offline ? 'offline' : 'snapshot'; nbSet(); });
  }

  function buildFigures() {
    const put = (sel, f) => {
      const el = $(sel); if (!el || !f) return;
      el.innerHTML = f.photo ? `<img src="${esc(f.photo)}" alt="${esc(f.name)}" draggable="false">` : '';
    };
    put('#deskFigure', D.figures[0]);
    put('#deskFigure2', D.figures[1] || D.figures[0]);
    ['figure', 'figure2'].forEach((id, i) => { const el = $('[data-obj="' + id + '"]'), f = D.figures[i] || D.figures[0]; if (el && f) el.setAttribute('aria-label', f.name); });
  }

  /* 展台封面：只读本地索引最新图片，不触发源同步或模型调用。 */
  async function buildPoster() {
    const img = $('#posterImg'), poster = $('.poster'), stamp = $('#posterStamp');
    if (!img || !poster) return;
    try {
      const response = await fetch('/api/index/cover');
      if (!response.ok) throw Error('图片索引不可用');
      const data = await response.json(), latest = data.item;
      if (!latest) {
        img.hidden = true; img.removeAttribute('src'); poster.classList.remove('has-img');
        if (stamp) stamp.hidden = false;
        poster.setAttribute('aria-label', '作品展台');
        return;
      }
      const url = '/api/index/image?id=' + encodeURIComponent(latest.id) + '&v=' + encodeURIComponent(latest.updated || '');
      if (img.getAttribute('src') === url) return;
      img.onload = () => {
        img.hidden = false; poster.classList.add('has-img');
        if (stamp) stamp.hidden = true;
        poster.setAttribute('aria-label', '作品展台：' + latest.title);
      };
      img.onerror = () => {
        img.hidden = true; poster.classList.remove('has-img');
        if (stamp) stamp.hidden = false;
        poster.setAttribute('aria-label', '作品展台');
      };
      img.alt = latest.title; img.src = url;
    } catch (_) { /* 保留现有封面或默认展台，不打断桌面。 */ }
  }

  function buildMonitorChip() {
    const b = binding('monitor'), chip = $('.scr-chip');
    if (b && b.daily && chip) chip.textContent = '▶ ' + b.title.replace(/（.*$/, '');
  }
  function buildMusicFace() {
    const c = D.music.album && D.music.album.cover;
    // 变量在 css/style.css 里被引用，相对路径会按样式表目录解析，所以先转成绝对地址
    if (c) document.documentElement.style.setProperty('--album-cover', `url('${new URL(c, location.href).href}')`);
  }

  function initClock() {
    const paint = () => {
      const d = new Date();
      const hh = String(d.getHours()).padStart(2, '0');
      const mm = String(d.getMinutes()).padStart(2, '0');
      $$('.iph-time').forEach((e) => { e.textContent = hh + ':' + mm; });
    };
    paint();
    setInterval(paint, 15000);
  }

  function initCalendar() {
    const d = new Date();
    const m = $('.cal-month'), dd = $('.cal-day'), wk = $('.cal-week');
    if (m) m.textContent = d.toLocaleString('en-US', { month: 'short' }).toUpperCase();
    if (dd) dd.textContent = d.getDate();
    if (wk) wk.textContent = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'][d.getDay()];
  }

  /* 台灯暖光：光源中心跟着台灯走（原版写死在 82% 62%，和台灯位置对不上） */
  function aimLamp() {
    const lamp = $('.lamp .lamp-shade'), w = $('#warm'); if (!lamp || !w) return;
    const r = lamp.getBoundingClientRect(), sr = stage.getBoundingClientRect();
    const sc = sr.width / 1600 || 1;
    const x = (r.left + r.width / 2 - sr.left) / sc, y = (r.bottom - sr.top) / sc;
    // 变量挂在 #stage 上：暖光层和夜色层（::before）都要读
    stage.style.setProperty('--lx', (x / 16).toFixed(2) + '%');
    stage.style.setProperty('--ly', (y / 10).toFixed(2) + '%');
  }

  /* ---------------- 悬停标签 + 点击分发 ---------------- */
  function bindLabels() {
    $$('.obj').forEach((obj) => {
      const id = obj.dataset.obj;
      const figure = id === 'figure' ? D.figures[0] : id === 'figure2' ? (D.figures[1] || D.figures[0]) : null;
      const lb = figure ? { ...LBL[id], zh: figure.name } : LBL[id];
      obj.addEventListener('mouseenter', () => {
        if (!lb) return;
        label.textContent = lb.zh + (binding(id) ? ' · 🔗' : '');
        const r = obj.getBoundingClientRect();
        const sr = stage.getBoundingClientRect();
        const sc = sr.width / 1600;
        label.style.left = (r.left + r.width / 2 - sr.left) / sc + 'px';
        label.style.top = (r.top - sr.top) / sc + 'px';
        label.classList.add('show');
        window.playSfx('hover');
      });
      obj.addEventListener('mouseleave', () => label.classList.remove('show'));
      obj.addEventListener('click', (e) => { e.stopPropagation(); if (e.shiftKey && openSession(id)) return; openObject(id); });
      obj.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openObject(id); }
      });
    });
  }

  /* ============================================================
   *  面板
   * ============================================================ */
  let panelReturnFocus = null;
  function openModal() {
    if (modal.hidden) panelReturnFocus = document.activeElement;
    modal.hidden = false;
    const heading = panelBody.querySelector('h2');
    $('.panel').setAttribute('aria-label', heading ? heading.textContent : '桌面面板');
    $('.panel-close').focus({ preventScroll: true });
  }
  function runCleanup() {
    panelCleanup.forEach((fn) => { try { fn(); } catch (e) {} });
    panelCleanup = [];
  }
  function closePanel() {
    if (modal.hidden) return;
    modal.hidden = true;
    runCleanup();
    if (panelReturnFocus && panelReturnFocus.isConnected) panelReturnFocus.focus({ preventScroll: true });
    stage.classList.toggle('playing', !!(window.DESK_CD && window.DESK_CD.isPlaying()));   // CD 机常驻：关面板不停歌
    window.playSfx('close');
  }
  modal.addEventListener('click', (e) => { if (e.target.classList.contains('modal-bg')) closePanel(); });
  $('.panel-close').addEventListener('click', closePanel);
  window.addEventListener('keydown', (e) => {
    const command = $('#cmd');
    const active = !command.hidden ? command : !modal.hidden ? modal : null;
    if (!active) return;
    if (e.key === 'Escape') {
      e.preventDefault();
      if (active === command) closeCmd(); else closePanel();
    }
    if (e.key === 'Tab') {
      const controls = [...active.querySelectorAll('button:not([disabled]), a[href], input:not([disabled]), textarea:not([disabled]), select:not([disabled]), iframe, [tabindex="0"]')].filter(el => el.getClientRects().length);
      const first = controls[0], last = controls[controls.length - 1];
      if (!first) { e.preventDefault(); return; }
      if (!active.contains(document.activeElement) || (e.shiftKey && document.activeElement === first) || (!e.shiftKey && document.activeElement === last)) {
        e.preventDefault(); (e.shiftKey ? last : first).focus();
      }
    }
  });

  function wiggle(id) {
    const el = $(`.obj[data-obj="${id}"]`); if (!el) return;
    el.classList.remove('wiggle'); void el.offsetWidth; el.classList.add('wiggle');
    setTimeout(() => el.classList.remove('wiggle'), 520);
  }

  function openObject(id) {
    const bd = binding(id);
    if (bd && bd.open === 'direct') { openSession(id); return; }
    // CD 转盘 / 音响律动跟随常驻播放器的真实状态（原版是只跟随“点没点 CD 机”）
    stage.classList.toggle('playing', !!(window.DESK_CD && window.DESK_CD.isPlaying()));
    // 特殊动作（不弹面板）
    // 幕布放下时，软木板被幕布盖着：点它 = 点幕布（选片 / 开讲）。幕布收起时软木板照常开面板（钉着武器库）
    if (id === 'board' && window.DESK_PROJECTOR && window.DESK_PROJECTOR.state.down) { window.DESK_PROJECTOR.click(); return; }
    if (id === 'glasses') { toggleFilter(true); return; }
    if (id === 'lamp') { toggleLamp(); return; }
    if (id === 'headphones') { toggleSound(); return; }
    if (id === 'keyboard') { openCmd(); return; }
    if (id === 'mouse') { toast('🖱 咔哒'); window.playSfx('click'); return; }
    if (id === 'mora') { addMora(); return; }
    const builder = PANELS[id];
    if (!builder) return;
    // 切换面板前先把上一个面板的音频 / 动画 / 计时器收干净
    runCleanup();
    stage.classList.toggle('playing', !!(window.DESK_CD && window.DESK_CD.isPlaying()));
    const r = builder();
    $('.panel').classList.toggle('wide', !!r.wide);
    panelBody.innerHTML = r.html + sessionFooter(id);
    panelBody.scrollTop = 0;
    openModal();
    window.playSfx('open');
    if (r.wire) r.wire();
  }

  /* ---------- 摩拉：桌上的小金币，点一下 +1 ---------- */
  function addMora() {
    const n = (+store.get(K.mora, 0) || 0) + 1;
    store.set(K.mora, n);
    if (window.DESK_VIBE) window.DESK_VIBE.record('mora');
    wiggle('mora');
    window.playSfx('coin');
    toast(`🪙 今日份的摩拉 +1（攒了 ${n} 枚）`);
  }

  /* ---------- 面板：显示器 · 今日待办 ---------- */
  /* ---------- 面板：显示器 · 待办 TODAY + 进度（账号层：今天我在所有空间发起的事，见 js/today.js） ---------- */
  const K_SEEN = 'yz_desk_today_seen_v1', K_TDONE = 'yz_desk_today_done_v1';
  const ST_ZH = { indexed: '已收录 · 状态见详情', running: '进行中', replied: '已回复 · 待你确认', cancelled: '已取消', error: '出错' };
  async function cohubClient() { throw new Error('本版本不使用 Cohub 客户端，改用本地 /api'); }

  // 按钮：运行 App Action「refresh-today」（拥有者在平台沙箱里跑，访客无需授权），拿回最新 JSON
  async function refreshToday(onStep) {
    if (onStep) onStep('正在扫描本地 agent 记录…');
    const j = await window.localAction('refresh-today', {});
    if (onStep) onStep('已刷新');
    return j;
  }

  /* ---------- 面板：显示器 · 待办（账本：todos/待办.log.jsonl，只追加；管理 Session 见 todos/binding.json） ----------
   * 今天发起的事（候选）+ 我加的 → 勾掉 / 放下 都写进账本；往日没收口单列，不自动变成今天的待办。 */
  const K_TODOS_SNAP = 'yz_desk_todos_board_v1', K_TODOS_MIGRATED = 'yz_desk_todos_migrated_v1';
  async function todosAction(input, onStep) {
    if (onStep) onStep(0);
    return window.localAction('todos', input);
  }

  function panelWork() {
    const snap = store.get(K_TODOS_SNAP, null), base = window.DESK_TODOS;
    let B = (snap && base && String(snap.at) > String(base.at)) ? snap : (base || snap || { today: '', today_open: [], carry: [], done_today: [], dropped: [], counts: {} });
    let active = true;
    panelCleanup.push(() => { active = false; });
    let writing = false;
    let status = 'snapshot', busy = '', openCarry = true, openDrop = false, openDone = false;   // 三个折叠区默认都收起
    let T = window.DESK_TODAY || {items:[],counts:{}};
    const S = T.stats || {};
    const sourceNames = {codex:'Codex',claude:'Claude',mirasim:'Mirasim',cohub:'Cohub',workbuddy:'WorkBuddy'};

    const setB = (b) => { B = b; store.set(K_TODOS_SNAP, b); };

    const row = (t, mode) => {
      const isS = t.kind === 'session';
      if (t.session_id) return `<div class="task td ${mode === 'done' ? 'done' : ''}" data-id="${esc(t.id)}">
        <button type="button" class="box" data-act="${mode === 'done' ? 'reopen' : 'done'}" aria-label="${mode === 'done' ? '重新打开：' : '确认完成：'}${esc(t.session)}" aria-pressed="${mode === 'done'}">${mode === 'done' ? '✓' : ''}</button>
        <div class="tx"><button type="button" class="today-session-open" data-open-session="${esc(t.session_id)}"><b>${esc(t.session)}</b></button></div>
        <span class="tag">${esc([...new Set(t.sources && t.sources.length ? t.sources : [t.session_id.split(':')[0]])].map(s => sourceNames[s] || s).join(' / '))}</span>
        ${mode === 'done' ? '' : '<button class="td-drop" data-act="drop">放下</button>'}
      </div>`;
      const st = isS ? `<span class="tag st-${esc(t.status)}">${esc(ST_ZH[t.status] || t.status)}</span>` : '<span class="tag">我加的</span>';
      return `<div class="task td ${mode === 'done' ? 'done' : ''}" data-id="${esc(t.id)}">
        <button type="button" class="box" data-act="${mode === 'done' ? 'reopen' : 'done'}" aria-label="${mode === 'done' ? '重新打开：' : '确认完成：'}${esc(t.session || t.text)}" aria-pressed="${mode === 'done'}" title="${mode === 'done' ? '重新打开' : '勾掉（我确认做完了）'}">${mode === 'done' ? '✓' : ''}</button>
        <span class="tx">${isS ? `<b>${esc(t.session)}</b><small>${esc(t.text)}</small>
          <small class="td-meta">${esc(t.space)} · ${esc(t.first || '')}${t.last && t.last !== t.first ? '–' + esc(t.last) : ''} · ${t.asks || 1} 次 · <a href="${esc(t.url)}" target="_blank" rel="noopener">打开 ↗</a></small>` : esc(t.text)}</span>
        ${st}
        ${mode === 'done' ? '' : '<button class="td-drop" data-act="drop" title="放下（不做了，留在账本里，可重开）">放下</button>'}
      </div>`;
    };
    function render() {
      const c = B.counts || {};
      const days = {}; (B.carry || []).forEach((t) => { (days[t.day] = days[t.day] || []).push(t); });
      const sess = B.session;
      const statusTxt = { snapshot: '这是快照，正在拉最新账本…', live: '已同步账本', offline: '本地服务没连上：只能看', error: '刚才那次没写进去，可以再试' }[status] || '';
      return `
        <span class="kicker">MONITOR · 今日会话与待办</span>
        <h2>${esc(B.today || '今天')} · 我在忙的事</h2>
        <p class="muted">${esc(statusTxt)} · 开着 ${c.open || 0}（往日没收口 ${c.carry || 0}）· 从 2026-11-11 起按会话收录；未勾选就保留，agent 回复不算完成。</p>
        <div class="td-bar">
          <a class="btn" href="/library.html" style="text-decoration:none">多端会话与产物 ↗</a>
          <button class="btn" id="tdRefresh" ${busy ? 'disabled' : ''}>${busy ? '⏳ ' + esc(busy) : '↻ 刷新会话'}</button>
          ${sess && sess.url && sess.url.trim() ? `<a class="btn sess-btn" href="${esc(sess.url)}" target="_blank" rel="noopener">📋 ${esc(sess.title)} ↗</a>` : ''}
          ${(() => { const b = binding('monitor'); return b && b.daily ? `<a class="btn ghost" href="${esc(b.url)}" target="_blank" rel="noopener" style="text-decoration:none">💬 ${esc(b.title)} ↗</a>` : ''; })()}
        </div>
        
        <div class="section-t">我的待办 <small class="muted">开着 ${(B.today_open || []).length} · 勾掉 ${(B.done_today || []).length}</small></div>
        <div class="td-list">${(B.today_open || []).map((t) => row(t, 'open')).join('') || '<p class="muted">今天还没有开着的事。</p>'}</div>
        <div class="addrow">
          <input id="newTask" aria-label="添加待办" placeholder="加一件要做的事，回车保存到本机账本" maxlength="160">
          <button class="btn" id="addTask">加上</button>
        </div>
        ${(B.done_today || []).length ? `<div class="section-t td-fold" data-fold="done">${openDone ? '▾' : '▸'} 今天勾掉的 <small class="muted">${B.done_today.length} 条 · 点 ✓ 可以重新打开</small></div>
        ${openDone ? `<div class="td-list">${B.done_today.map((t) => row(t, 'done')).join('')}</div>` : ''}` : ''}
        <div class="section-t td-fold" data-fold="carry">${openCarry ? '▾' : '▸'} 往日没收口 <small class="muted">${(B.carry || []).length} 条 · 从 2026-11-11 起，未勾选持续保留</small></div>
        ${openCarry ? Object.keys(days).sort().reverse().map((d) => `
          <div class="td-space">${esc(d)} <small>${days[d].length}</small> <button class="btn ghost td-dayall" data-day="${esc(d)}">确认这天全部完成</button></div>
          <div class="td-list">${days[d].map((t) => row(t, 'open')).join('')}</div>`).join('') || '<p class="muted">没有往日欠着的事。</p>' : ''}
        <div class="section-t td-fold" data-fold="drop">${openDrop ? '▾' : '▸'} 放下的 <small class="muted">${c.dropped || 0} 条 · 正文都还在账本里</small></div>
        ${openDrop ? (B.dropped || []).map((t) => `<div class="nb-arcrow" data-id="${esc(t.id)}"><s>${esc(t.kind === 'session' ? t.session + '：' + t.text : t.text)}</s><small>${esc(t.day)}${t.reason ? ' · ' + esc(t.reason) : ''}</small><button class="btn ghost" data-act="reopen">↺ 重开</button></div>`).join('') || '<p class="muted">还没有放下过。</p>' : ''}
        `;
    }

    const wire = () => {
      const paint = () => {
        if (!active || modal.hidden || !$('#tdRefresh')) return;
        const input = $('#newTask'), draft = input ? input.value : '';
        const focused = document.activeElement;
        const focusId = focused && focused.id, fold = focused && focused.dataset.fold;
        panelBody.innerHTML = render() + sessionFooter('monitor'); wire();
        if ($('#newTask')) $('#newTask').value = draft;
        const restore = focusId ? document.getElementById(focusId) : fold ? panelBody.querySelector('[data-fold="' + fold + '"]') : null;
        if (restore) restore.focus({ preventScroll: true });
      };
      panelBody.querySelectorAll('[data-open-session]').forEach(button=>button.addEventListener('click',async()=>{
        if(button.dataset.openSession.startsWith('workbuddy:')){location.href='/library.html?session='+encodeURIComponent(button.dataset.openSession);return;}
        button.disabled=true;
        try {
          const response=await fetch('/api/index/open',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:'session',id:button.dataset.openSession})});
          const result=await response.json();
          if(!response.ok||result.ok===false) throw Error(result.error||'未能打开原会话');
          if(result.url){location.href=result.url;return;}
          toast(result.opened_in?'已在 '+result.opened_in+' 打开':'已交给原应用打开');
        } catch(e) { toast('打开失败：'+e.message+'；仍可查看本地索引'); }
        finally { button.disabled=false; }
      }));
      const act = async (input, msg) => {
        if (writing) return;
        writing = true;
        panelBody.querySelectorAll('[data-act], #addTask, .td-dayall').forEach(el => el.disabled = true);
        try {
          const j = await todosAction(input); status = 'live'; setB(j);
          if (input.op === 'add' && $('#newTask')) $('#newTask').value = '';
          if (msg) toast(msg);
        } catch (e) { status = e.offline ? 'offline' : 'error'; toast(e.offline ? e.message : '没写进去：' + e.message); }
        finally { writing = false; paint(); }
      };
      // 只有账本确认成功才改变任务状态，失败保留原状态。
      panelBody.querySelectorAll('[data-act]').forEach((el) => el.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = el.closest('[data-id]').dataset.id, a = el.dataset.act;
        if (writing) return;
        window.playSfx('click');
        act(a === 'drop' ? { op: 'drop', id, reason: '在电脑面板放下' } : { op: a, id }, { done: '✓ 勾掉了', drop: '放下了（在「放下的」里能重开）', reopen: '↺ 重新打开' }[a]);
      }));
      panelBody.querySelectorAll('.td-fold').forEach((el) => {
        el.setAttribute('role', 'button'); el.tabIndex = 0;
        el.setAttribute('aria-expanded', String(el.dataset.fold === 'carry' ? openCarry : el.dataset.fold === 'done' ? openDone : openDrop));
        el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); el.click(); } });
        el.addEventListener('click', () => {
        const f = el.dataset.fold;
        if (f === 'carry') openCarry = !openCarry; else if (f === 'done') openDone = !openDone; else openDrop = !openDrop;
        paint();
      }); });
      panelBody.querySelectorAll('.td-dayall').forEach((el) => el.addEventListener('click', async (e) => {
        e.stopPropagation();
        const ids = (B.carry || []).filter((t) => t.day === el.dataset.day).map((t) => t.id);
        if (!ids.length || !confirm(`把 ${el.dataset.day} 的 ${ids.length} 条都勾掉？（你确认全部完成）`)) return;
        if (writing) return;
        writing = true;
        panelBody.querySelectorAll('[data-act], #addTask, .td-dayall').forEach(button => button.disabled = true);
        let completed = 0, failure = '';
        for (const id of ids) {
          try { setB(await todosAction({ op: 'done', id })); completed++; }
          catch (er) { failure = er.message; break; }
        }
        writing = false; status = failure ? 'error' : 'live'; paint();
        toast(failure ? `已保存 ${completed}/${ids.length} 条，其余未完成：${failure}` : `✓ 已勾掉 ${completed} 条`);
      }));
      const add = () => {
        const v = $('#newTask').value.trim(); if (!v) return;
        if (writing) return;
        act({ op: 'add', text: v }, '加进账本了');
      };
      $('#addTask').addEventListener('click', add);
      $('#newTask').addEventListener('keydown', (e) => { e.stopPropagation(); if (e.key === 'Enter' && !e.isComposing) add(); });
      $('#tdRefresh').addEventListener('click', async () => {
        if (busy) return;
        busy = '正在读取新增与变化…'; paint();
        try {
          const response=await fetch('/api/index/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
          if(!response.ok) throw Error('无法启动同步');
          let job=await response.json();
          while(job.running) {
            await new Promise(resolve=>setTimeout(resolve,2000));
            T=await fetch('/api/index/today').then(r=>r.json()); setB(await todosAction({op:'list'}));
            const state=await fetch('/api/index/status').then(r=>r.json());
            job=state.job; busy=job.message||'正在同步';
            if(!active||modal.hidden||!$('#tdRefresh')) return;
            paint();
          }
          if(job.error) throw Error(job.error);
          T=await fetch('/api/index/today').then(r=>r.json()); setB(await todosAction({op:'list'}));
          buildPoster();
          toast('今天的多端会话已刷新');
        } catch (e) { toast('刷新未完成：'+e.message); }
        busy = ''; if(active&&!modal.hidden&&$('#tdRefresh')) paint();
      });
    };

    // 打开就拉最新账本；第一次顺手把浏览器里旧的「我自己加的」搬进账本
    const pull = async () => {
      try {
        const response=await fetch('/api/index/today');
        if(response.ok) T=await response.json();
        const old = store.get(K.todos, null);
        let j;
        if (Array.isArray(old) && old.length && !store.get(K_TODOS_MIGRATED, false)) {
          j = await todosAction({ op: 'import', items: old.map((t) => ({ text: t.text, done: !!t.done })) });
          store.set(K_TODOS_MIGRATED, true);
          toast(`把浏览器里 ${old.length} 条旧待办搬进了账本`);
        } else j = await todosAction({ op: 'list' });
        status = 'live'; setB(j);
      } catch (e) { status = e.offline ? 'offline' : 'error'; }
      if (active && !writing && !modal.hidden && $('#tdRefresh')) {
        const input = $('#newTask'), draft = input ? input.value : '', focused = document.activeElement;
        const focusId = focused && focused.id;
        panelBody.innerHTML = render() + sessionFooter('monitor'); wireNow();
        $('#newTask').value = draft;
        if (focusId) { const restore = document.getElementById(focusId); if (restore) restore.focus({ preventScroll: true }); }
      }
    };
    let wireNow = wire;
    setTimeout(pull, 0);
    return { html: render(), wire };
  }
  function minutesSince(hhmm) {
    const [h, m] = String(hhmm).split(':').map(Number); const n = new Date();
    return (n.getHours() * 60 + n.getMinutes()) - (h * 60 + m);
  }

  /* ---------- 面板：窗户 · 本机索引页 ---------- */
  function panelDashboard() {
    const w = D.window.dashboard || {};
    return {
      wide: true,
      html: `
        <span class="kicker">WINDOW · ${esc(w.title)}</span>
        <h2>${esc(w.title)}</h2>
        <p class="muted">${esc(w.sub)}　<a href="${esc(w.url)}" target="_blank" rel="noopener">在新标签页打开 ↗</a></p>
        <div class="dash-frame"><div class="dash-loading">正在打开看板…</div>
          <iframe id="dashFrame" src="${esc(w.url)}" title="${esc(w.title)}" loading="eager" referrerpolicy="strict-origin-when-cross-origin"></iframe></div>`,
      wire: () => {
        const f = $('#dashFrame');
        f.addEventListener('load', () => f.classList.add('ready'));
      },
    };
  }

  /* ---------- 面板：契约卷轴 · 今日契约 ---------- */
  function panelContract() {
    const c = D.contract;
    return {
      html: `
        <span class="kicker">CONTRACT · ${esc(c.title)}</span>
        <div class="scroll-sheet">
          <div class="scroll-seal">契</div>
          <h2>立约两条</h2>
          ${(c.clauses || []).map((x, i) => `<div class="clause"><span class="clause-k">${esc(x.k)}</span><div><b>第${'一二三四五'[i]}条　${esc(x.text)}</b><small>${esc(x.sub || '')}</small></div></div>`).join('')}
        </div>
        <p class="muted">来源：${esc(c.source)}</p>
        <p class="muted">${esc(c.note)}</p>`,
    };
  }

  /* ---------- 面板：CD 机 · 本地歌单（点击直接播放，不跳转） ---------- */
  function panelMusic() {
    const alb = D.music.album || {};
    const songs = D.music.songs || [];
    const html = `
      <span class="kicker">CD PLAYER · ${esc(alb.artist)}</span>
      <h2>${esc(alb.title || '放张唱片')} ♪</h2>
      <p class="muted">${esc(alb.sub)} · ${esc(alb.bpm)}</p>
      <div class="mp3">
        <div class="mp3-cover" style="background-image:url('${esc(alb.cover)}')">
          <div class="mp3-disc" id="mp3Disc"></div>
        </div>
        <div class="mp3-info">
          <div class="mp3-now" id="mp3Now"></div>
          <div class="mp3-sub" id="mp3Sub"></div>
          <div class="mp3-bar" id="mp3Seek" title="点一下跳到这里"><i id="mp3Bar"></i></div>
          <div class="mp3-times"><span id="mp3Cur">0:00</span><span id="mp3Dur">0:00</span></div>
          <div class="mp3-ctrl">
            <button class="mp3btn" id="mp3Prev" aria-label="上一首">⏮</button>
            <button class="mp3btn big" id="mp3Play" aria-label="播放/暂停">▶</button>
            <button class="mp3btn" id="mp3Next" aria-label="下一首">⏭</button>
          </div>
        </div>
      </div>
      <div class="section-t">曲目</div>
      <div class="tracks" id="mp3List">
        ${songs.map((t, i) => `
          <div class="track" data-i="${i}">
            <span class="no">${String(i + 1).padStart(2, '0')}</span>
            <span class="tt">${esc(t.title)}</span>
            <span class="ar">${esc(t.tag)}</span>
          </div>`).join('')}
      </div>
      <a class="btn ghost" id="albumPage" style="text-decoration:none;display:inline-block;margin-top:12px" href="${esc(alb.url || '#')}" ${alb.url ? 'target="_blank" rel="noopener"' : 'data-unbound="1"'}>在独立页面打开 ↗</a>`;

    const wire = () => {
      const au = new Audio();
      au.preload = 'metadata';
      let cur = 0;
      const fmt = (s) => { s = Math.max(0, s | 0); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
      const load = (i, autoplay) => {
        cur = (i + songs.length) % songs.length;
        au.src = songs[cur].file;
        $('#mp3Now').textContent = songs[cur].title;
        $('#mp3Sub').textContent = songs[cur].tag;
        $('#mp3Bar').style.width = '0%'; $('#mp3Cur').textContent = '0:00'; $('#mp3Dur').textContent = '…';
        $$('#mp3List .track').forEach((el, k) => el.classList.toggle('on', k === cur));
        if (autoplay) play();
      };
      const play = () => { au.play().then(() => { $('#mp3Play').textContent = '⏸'; stage.classList.add('playing'); }).catch(() => {}); };
      const pause = () => { au.pause(); $('#mp3Play').textContent = '▶'; stage.classList.remove('playing'); };

      au.addEventListener('timeupdate', () => {
        const d = au.duration || 0;
        const bar = $('#mp3Bar'); if (!bar) return;
        bar.style.width = d ? (au.currentTime / d * 100) + '%' : '0%';
        $('#mp3Cur').textContent = fmt(au.currentTime);
      });
      au.addEventListener('loadedmetadata', () => { const el = $('#mp3Dur'); if (el) el.textContent = fmt(au.duration); });
      au.addEventListener('ended', () => load(cur + 1, true));

      $('#mp3Play').addEventListener('click', () => { if (au.paused) play(); else pause(); });
      $('#mp3Next').addEventListener('click', () => load(cur + 1, true));
      $('#mp3Prev').addEventListener('click', () => load(cur - 1, true));
      $('#mp3Seek').addEventListener('click', (e) => {
        const r = e.currentTarget.getBoundingClientRect();
        if (au.duration) au.currentTime = (e.clientX - r.left) / r.width * au.duration;
      });
      $('#mp3List').addEventListener('click', (e) => {
        const row = e.target.closest('.track'); if (!row) return;
        load(+row.dataset.i, true);
      });
      const ap = $('#albumPage');
      if (ap && ap.dataset.unbound) ap.addEventListener('click', (e) => { e.preventDefault(); toast('独立页面还没绑定（data.js → music.album.url）'); });
      load(0, false);
      play();   // 点击 CD 机属于用户手势，可以直接播
      panelCleanup.push(() => { try { au.pause(); au.removeAttribute('src'); au.load(); } catch (e) {} stage.classList.remove('playing'); });
    };
    return { html, wire };
  }

  /* ---------- 面板：平板 · 视频 & 游戏 ---------- */
  function panelTablet(startTab, head) {
    let tab = startTab || 'video';
    const html = head ? `${head}
      <div class="section-t">桌面小游戏</div>
      <div id="tabBody"></div>` : `
      <span class="kicker">TABLET · 平板</span>
      <h2>平板</h2>
      <div class="tabs">
        <button class="tabbtn ${tab === 'video' ? 'on' : ''}" data-tab="video">▶ 视频</button>
        <button class="tabbtn ${tab === 'game' ? 'on' : ''}" data-tab="game">🎮 游戏</button>
      </div>
      <div id="tabBody"></div>`;

    const videoHTML = () => `
      <div class="sitelist">
        ${D.videos.sites.map((s) => `<a class="site" href="${esc(s.url)}" target="_blank" rel="noopener" style="border-color:${esc(s.color)}">${esc(s.name)}<br><small style="opacity:.6;font-weight:400">${esc(s.desc)}</small></a>`).join('')}
      </div>
      <div class="section-t">${esc(D.videos.recentTitle || '最近在看的')}</div>
      ${D.videos.recent.map((v) => {
        const inner = `<div class="thumb"></div>
          <div><div class="vt">${esc(v.title)}</div><div class="vs">${esc(v.source)}</div></div>
          <div class="vl">${esc(v.len)}</div>`;
        return v.url ? `<a class="vid" href="${esc(v.url)}" target="_blank" rel="noopener">${inner}</a>` : `<div class="vid">${inner}</div>`;
      }).join('')}`;

    const gameHTML = () => `
      <p class="muted">选一个玩（点画布开始，20 秒一局）：</p>
      <div class="tabs">
        <button class="tabbtn on" data-game="whack">🔨 打地鼠</button>
        <button class="tabbtn" data-game="catchbean">🪙 接摩拉</button>
      </div>
      <div class="game-wrap"><div id="gameMount"></div></div>`;

    let gameInst = null;
    const destroyGame = () => { if (gameInst) { gameInst.destroy(); gameInst = null; } };
    const mountGame = (which) => {
      destroyGame();
      const mount = $('#gameMount'); if (!mount || !window.DESK_GAMES[which]) return;
      gameInst = window.DESK_GAMES[which](mount);
    };
    const wire = () => {
      panelCleanup.push(destroyGame);
      const body = $('#tabBody');
      const paint = () => {
        destroyGame();
        body.innerHTML = tab === 'video' ? videoHTML() : gameHTML();
        if (tab === 'game') mountGame('whack');
      };
      $$('.tabbtn[data-tab]').forEach((b) => b.addEventListener('click', () => {
        tab = b.dataset.tab;
        $$('.tabbtn[data-tab]').forEach((x) => x.classList.toggle('on', x === b));
        paint();
      }));
      body.addEventListener('click', (e) => {
        const g = e.target.closest('[data-game]'); if (!g) return;
        $$('.tabbtn[data-game]').forEach((x) => x.classList.toggle('on', x === g));
        mountGame(g.dataset.game);
      });
      paint();
    };
    return { html, wire };
  }
  function gamelibHTML() {
    const G = D.gamelib;
    if (!G || !G.groups) return '';
    const total = G.groups.reduce((n, g) => n + g.items.length, 0);
    return `
      <div class="gl-head"><span class="kicker">GAME LIBRARY · ${esc(G.title)}</span><span class="muted">${esc(G.sub)}</span></div>
      ${G.groups.map((g) => `
        <div class="gl-group" style="--c:${esc(g.color)}">
          <div class="gl-name">${esc(g.name)} <small>${g.items.length}</small></div>
          <div class="gl-grid">
            ${g.items.map((it) => `<a class="gl-card" href="${esc(it.url)}" target="_blank" rel="noopener">
              <span class="gl-ico">${esc(it.icon)}</span>
              <span class="gl-t"><b>${esc(it.title)}</b><small>${esc(it.note)} · ${esc(G.from)} ${esc(it.date)}</small></span></a>`).join('')}
          </div>
        </div>`).join('')}
      <p class="muted">共 ${total} 个，全部在新标签页打开；加入入口和邀请链接只是打开页面，不会替你加入。</p>`;
  }

  /* 手柄：「日常在看」的入口 + 游戏库（公开分享）。桌面小游戏已按要求去掉（平板里还有） */
  function panelGames() {
    const W = D.watchlist;
    if (!W || !W.items || !W.items.length) return panelTablet('game');
    const head = `
      <span class="kicker">CONTROLLER · ${esc(W.title)}</span>
      <h2>${esc(W.title)}</h2>
      <p class="muted">${esc(W.sub)}</p>
      <div class="watchlist">
        ${W.items.map((w) => {
          const inner = `<span class="sc-ico">${esc(w.icon)}</span>
            <span class="wl-t"><b>${esc(w.title)}</b><small>${esc(w.note)}</small></span>
            <span class="sc-tag">${esc(w.tag)}</span>`;
          return w.url
            ? `<a class="showcard wl" href="${esc(w.url)}" target="_blank" rel="noopener" style="--c:${esc(w.color)}">${inner}</a>`
            : `<div class="showcard wl nolink" style="--c:${esc(w.color)}">${inner}</div>`;
        }).join('')}
      </div>
      <div class="wl-gap"></div>
      ${gamelibHTML()}`;
    return { html: head };
  }

  /* ---------- 面板：书 · 在读在学 ---------- */
  function panelBook() {
    const html = `
      <span class="kicker">INDEX · 索引</span>
      <h2>索引</h2>
      <p class="muted">每一条都是一个真实位置：文件夹、文件、网页、App。点开就走。</p>
      ${D.books.map((b) => `
        <div class="prog">
          <div class="prow"><b><a href="${esc(b.link)}" target="_blank" rel="noopener" style="color:inherit">${esc(b.title)} ↗</a></b>${b.progress != null ? `<span>${b.progress}%</span>` : ''}</div>
          ${b.progress != null ? `<div class="bar"><i style="width:${b.progress}%;background:${esc(b.color)}"></i></div>` : `<div class="bar ghostbar"><i style="width:100%;background:${esc(b.color)}"></i></div>`}
          <div class="muted">${esc(b.author)} · ${esc(b.note)}</div>
        </div>`).join('')}
      ${D.booksLink ? `<div style="margin-top:16px"><a class="btn" style="text-decoration:none;display:inline-block" href="${esc(D.booksLink)}" target="_blank" rel="noopener">${esc(D.booksLinkLabel || '打开书架 ↗')}</a>${D.booksLink2 ? `<a class="muted" style="margin-left:14px" href="${esc(D.booksLink2)}" target="_blank" rel="noopener">${esc(D.booksLink2Label)}</a>` : ''}</div>` : ''}`;
    return { html };
  }

  /* ---------- 面板：手办 · 拿起来端详（原版结构：📷 照片 1:1 / 🧊 3D 可拖动 / 下载） ---------- */
  let mvLoading = null;
  function ensureModelViewer() {
    if (window.customElements && customElements.get('model-viewer')) return Promise.resolve();
    if (!mvLoading) mvLoading = new Promise((res) => {
      const sc = document.createElement('script'); sc.type = 'module'; sc.src = 'assets/vendor-model-viewer.js';
      sc.onload = res; sc.onerror = res; document.head.appendChild(sc);
    });
    return mvLoading;
  }
  function panelFigure(idx) {
    const f = D.figures[idx] || D.figures[0];
    const glb = f.model3d && f.model3d.glb;
    const has3d = !!(glb || f.turn);
    const both = !!(has3d && f.photo);
    const dl = glb
      ? `<div class="fig-dl"><a class="btn ghost" href="${esc(glb)}" download>⤓ 下载 3D 模型 (.glb)</a></div>`
      : (f.photo ? `<div class="fig-dl"><a class="btn ghost" href="${esc(f.photo)}" download>⤓ 下载立牌原图</a></div>` : '');
    const acts = (f.actions || []).filter((g) => g.items && g.items.length);
    const nActs = acts.reduce((n, g) => n + g.items.length, 0);
    const tabs = (both || nActs) ? `<div class="tabs" id="figTabs">
        ${f.photo ? '<button class="tabbtn on" data-v="photo">📷 立牌照片 · 1:1</button>' : ''}
        ${nActs ? `<button class="tabbtn" data-v="act">🎬 动作 · ${nActs}</button>` : ''}
        ${has3d ? '<button class="tabbtn" data-v="3d">🧊 3D（可拖动）</button>' : ''}
      </div>` : '';
    const actBar = nActs ? `<div class="fig-acts" id="figActs" hidden>
        ${acts.map((g, gi) => `<div class="fig-act-group"><span class="fig-act-name">${esc(g.group)}</span>
          ${g.items.map((it, ii) => `<button class="fig-act" data-a="${gi}.${ii}">${esc(it.label)}${it.voice ? ' <i>🔈</i>' : ''}</button>`).join('')}</div>`).join('')}
      </div>` : '';
    const html = `
      <span class="kicker">FIGURE · 拿起来端详</span>
      <h2>${esc(f.name)}</h2>
      <p class="muted">${esc(f.series)} · ${esc(f.height)}</p>
      ${tabs}
      <div class="fig-stage" id="figStage"><div class="fig-big" id="figBig"></div><div class="fig-hint" id="figHint"></div></div>
      ${actBar}
      <p style="margin-top:14px">${esc(f.story)}</p>
      <div class="fig-dl">${dl.replace(/^<div class="fig-dl">|<\/div>$/g, '')}${f.link ? `<a class="btn ghost" href="${esc(f.link)}" target="_blank" rel="noopener">${esc(f.linkLabel || '打开 ↗')}</a>` : ''}</div>`;

    const wire = () => {
      const st = $('#figStage'), big = $('#figBig'), hint = $('#figHint');
      let raf = null, offDrag = null, voice = null;
      const actsEl = $('#figActs');
      const stopVoice = () => { if (voice) { try { voice.pause(); } catch (e) {} voice = null; } };
      const stop = () => { if (raf) { cancelAnimationFrame(raf); raf = null; } if (offDrag) { offDrag(); offDrag = null; } st.classList.remove('turnmode', 'grab', 'actmode'); stopVoice(); if (actsEl) actsEl.hidden = true; };

      // 🎬 动作：透明循环动图 / 视频片段 / 静图；带配音的选中时说一句（点按钮属于用户手势，可以直接播）
      function showAct(key, withVoice) {
        stop();
        if (actsEl) actsEl.hidden = false;
        st.classList.add('actmode');
        big.style.marginTop = '';
        const [gi, ii] = String(key || '0.0').split('.').map(Number);
        const it = (acts[gi] || acts[0]).items[ii] || acts[0].items[0];
        $$('.fig-act', actsEl).forEach((b) => b.classList.toggle('on', b.dataset.a === `${gi}.${ii}`));
        big.innerHTML = it.kind === 'video'
          ? `<video class="fig-video" src="${esc(it.src)}" autoplay loop muted playsinline></video>`
          : `<img class="fig-photo fig-anim" src="${esc(it.src)}" alt="${esc(f.name)} · ${esc(it.label)}" draggable="false">`;
        hint.textContent = it.hint || it.label;
        if (withVoice && it.voice) { voice = new Audio(it.voice); voice.play().catch(() => {}); }
      }
      if (actsEl) actsEl.addEventListener('click', (e) => {
        const b = e.target.closest('.fig-act'); if (!b) return;
        showAct(b.dataset.a, true);
      });

      function showPhoto() {
        stop();
        big.style.transform = '';
        big.innerHTML = `<img class="fig-photo" src="${esc(f.photo)}" alt="${esc(f.name)}" draggable="false">`;
        hint.textContent = f.photoHint || '这是立牌照片（1:1）';
        const t0 = performance.now();
        raf = requestAnimationFrame(function loop(t) {
          big.style.marginTop = (Math.sin((t - t0) / 700) * 4) + 'px';
          raf = requestAnimationFrame(loop);
        });
      }

      // 有 GLB：和原版一样用 model-viewer（自动旋转 + 拖动）
      function showGLB() {
        stop();
        big.style.marginTop = '';
        big.innerHTML = '';
        hint.textContent = '正在载入 3D 模型…';
        ensureModelViewer().then(() => {
          big.innerHTML = `<model-viewer class="fig-mv" src="${esc(glb)}" camera-controls auto-rotate auto-rotate-delay="0" rotation-per-second="30deg" shadow-intensity="1" exposure="1.1" interaction-prompt="none" touch-action="pan-y" alt="${esc(f.name)} 3D 模型"></model-viewer>`;
          hint.textContent = '按住拖动可以旋转';
        });
      }

      // 没有 GLB：立牌转身（正面 + 背面剪影），自动慢转，按住左右拖动 = 转动
      function showTurn() {
        stop();
        big.style.marginTop = '';
        st.classList.add('turnmode');
        big.innerHTML = `<div class="fig-turn" id="figTurn">
            <img class="fig-face front" src="${esc(f.turn)}" alt="${esc(f.name)}" draggable="false">
            <img class="fig-face back" src="${esc(f.turn)}" alt="" draggable="false"></div>
          <div class="fig-floor"></div>`;
        hint.textContent = '按住左右拖动可以转动（立牌转身；放进 .glb 后这里会换成真 3D）';
        const turn = $('#figTurn');
        let angle = 0, vel = 0.5, drag = null;   // 与原版 model-viewer 一样默认自动旋转（约 30°/s）
        const loop = () => {
          if (!drag) { vel += (0.5 - vel) * 0.02; angle += vel; }
          turn.style.transform = `rotateY(${angle}deg)`;
          raf = requestAnimationFrame(loop);
        };
        const down = (e) => { drag = { x: e.clientX, a: angle, lx: e.clientX }; st.classList.add('grab'); try { st.setPointerCapture(e.pointerId); } catch (er) {} };
        const move = (e) => { if (!drag) return; angle = drag.a + (e.clientX - drag.x) * 0.8; vel = (e.clientX - drag.lx) * 0.8; drag.lx = e.clientX; };
        const up = () => { drag = null; st.classList.remove('grab'); };
        st.addEventListener('pointerdown', down); st.addEventListener('pointermove', move);
        st.addEventListener('pointerup', up); st.addEventListener('pointercancel', up);
        offDrag = () => { st.removeEventListener('pointerdown', down); st.removeEventListener('pointermove', move); st.removeEventListener('pointerup', up); st.removeEventListener('pointercancel', up); };
        raf = requestAnimationFrame(loop);
      }
      const show3D = () => (glb ? showGLB() : showTurn());

      const tabsEl = $('#figTabs');
      if (tabsEl) tabsEl.addEventListener('click', (e) => {
        const b = e.target.closest('.tabbtn'); if (!b) return;
        $$('.tabbtn', tabsEl).forEach((x) => x.classList.toggle('on', x === b));
        if (b.dataset.v === 'photo') showPhoto(); else if (b.dataset.v === 'act') showAct('0.0', false); else show3D();
      });
      if (f.photo || !has3d) showPhoto(); else show3D();
      panelCleanup.push(stop);
    };
    return { html, wire };
  }

  /* ---------- 面板：软木板 · 关于 ---------- */
  function panelBoard() {
    const a = D.about;
    return {
      html: `
        <span class="kicker">${esc(a.kicker)}</span>
        <h2>${esc(a.name)}</h2>
        <p><b>${esc(a.role)}</b></p>
        ${a.lines.map((l) => `<p>${esc(l)}</p>`).join('')}
        <div class="sitelist">${a.tags.map((t) => `<span class="site">${esc(t)}</span>`).join('')}</div>
        <p class="muted">板上钉着的东西都能单独点：武器库、三张拍立得、三张标签贴。</p>`,
    };
  }

  /* ---------- 软木板上钉着的东西：各点各的（幕布收起时） ---------- */
  function showPanel(r) {
    runCleanup();
    $('.panel').classList.toggle('wide', !!r.wide);
    panelBody.innerHTML = r.html;
    panelBody.scrollTop = 0;
    openModal();
    window.playSfx('open');
    if (r.wire) r.wire();
  }
  function panelEmbed(e) {
    return {
      wide: true,
      html: `
        <span class="kicker">${esc(e.kicker)}</span>
        <h2>${esc(e.title)}</h2>
        <p class="muted">${esc(e.sub)}　<a href="${esc(e.url)}" target="_blank" rel="noopener">整页打开 ↗</a></p>
        <div class="dash-frame"><div class="dash-loading">正在打开…</div>
          <iframe id="pinFrame" src="${esc(e.url)}" title="${esc(e.title)}" loading="eager" referrerpolicy="strict-origin-when-cross-origin"></iframe></div>`,
      wire: () => { const f = $('#pinFrame'); if (f) f.addEventListener('load', () => f.classList.add('ready')); },
    };
  }
  function panelPolaroid(p) {
    return {
      html: `
        <span class="kicker">POLAROID · 软木板</span>
        <h2>${esc(p.title || p.cap)}</h2>
        <img class="shot-big pol-big" src="${esc(p.file)}" alt="">
        ${p.note ? `<p class="muted">${esc(p.note)}</p>` : ''}
        ${!p.url && !p.goto ? '<p class="empty-state" role="status">这个位置还没有设置入口。可以先到书架查看已配置的链接。</p><button class="btn" id="polBrowse">查看已有链接 →</button>' : ''}
        ${p.goto ? `<button class="btn" id="polGo">${esc(p.gotoLabel || '去看看')}</button>` : ''}
        ${p.url ? `<div class="addrow"><a class="btn" style="text-decoration:none" href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.urlLabel || '打开 ↗')}</a>
          ${(p.links || []).map((l) => `<a class="btn ghost" style="text-decoration:none" href="${esc(l.u)}" target="_blank" rel="noopener">${esc(l.t)} ↗</a>`).join('')}</div>` : ''}`,
      wire: () => { const browse = $('#polBrowse'); if (browse) browse.addEventListener('click', () => openObject('book')); const b = $('#polGo'); if (b) b.addEventListener('click', () => openObject(p.goto)); },
    };
  }
  function openPin(el) {
    const a = D.about, w = D.arsenal;
    const k = el.dataset.pin;
    wigglePin(el);
    if (k === 'arsenal' && w) { showPanel(panelEmbed({ kicker: 'ARSENAL · 武器库', title: w.title, sub: w.sub, url: w.url })); return; }
    const pol = /^pol(\d)$/.exec(k);
    if (pol) { const p = (a.polaroids || [])[+pol[1] - 1]; if (p) showPanel(panelPolaroid(p)); return; }
    const chip = /^chip(\d)$/.exec(k);
    if (chip) {
      const act = (a.chipActs || [])[+chip[1] - 1]; if (!act) return;
      if (act.embed) showPanel(panelEmbed(act.embed));
      else if (act.open) { if (act.hint) toast(act.hint); openObject(act.open); }
      return;
    }
    if (k === 'pin') { window.playSfx('click'); toast('📌 图钉按紧了'); }
  }
  function wigglePin(el) { el.classList.remove('pin-hit'); void el.offsetWidth; el.classList.add('pin-hit'); }
  (function wireBoardPins() {
    const board = $('.obj.board'); if (!board) return;
    $$('.polaroid', board).forEach((x, i) => { x.dataset.pin = 'pol' + (i + 1); });
    $$('.tag-chip', board).forEach((x, i) => { x.dataset.pin = 'chip' + (i + 1); });
    $$('.cork > .pin', board).forEach((x) => { x.dataset.pin = 'pin'; });
    const ac = $('.arsenal-card', board); if (ac) ac.dataset.pin = 'arsenal';
    // 捕获阶段先看点的是不是钉着的东西；幕布放下时一律交给幕布
    board.addEventListener('click', (e) => {
      if (window.DESK_PROJECTOR && window.DESK_PROJECTOR.state.down) return;
      const el = e.target.closest('[data-pin]'); if (!el || !board.contains(el)) return;
      e.stopPropagation();
      openPin(el);
    }, true);
  })();

  /* ---------- 面板：便签墙（新增 / 改字 / 撕掉 / 留档恢复，全部追加进 log） ---------- */
  function panelNotes() {
    let color = NOTE_COLORS[0], showArc = false;
    const html = `<div id="nbRoot">
      <span class="kicker">NOTES · 便签墙</span>
      <h2>随手写的</h2>
      <p class="muted" id="nbStatus"></p>
      <div class="nb-add">
        <textarea id="nbText" rows="2" maxlength="140" placeholder="写一张新便签…（回车钉上，Shift+回车换行）"></textarea>
        <div class="nb-tools">
          <span class="nb-colors">${NOTE_COLORS.map((c, i) => `<i data-c="${c}" class="${i ? '' : 'on'}" style="background:${c}"></i>`).join('')}</span>
          <button class="btn" id="nbPin">📌 钉上</button>
        </div>
      </div>
      <div class="notelist" id="nbList"></div>
      <div class="nb-arc"><button class="btn ghost" id="nbArcBtn"></button><div id="nbArc" hidden></div></div></div>`;
    const wire = () => {
      const paint = () => {
        const d = NB.data, board = d.board || [], arc = d.archive || [];
        const st = { snapshot: '这是快照，正在等最新的…', syncing: '正在写进便签 log…', live: `已同步 · 板上 ${board.length} 张`, offline: '本地服务没连上：只能看', error: '刚才那次没写进去，可以再试一次' }[NB.status] || '';
        const el = $('#nbStatus'); if (!el) return;
        el.textContent = st + '　· 撕掉的不会消失，都在下面的留档里';
        $('#nbList').innerHTML = board.map((n) => `
          <div class="notecard nb-card" data-id="${esc(n.id)}" style="background:${esc(n.color)};--r:${+n.rot || 0}deg">
            <div class="nb-tx" contenteditable="true" spellcheck="false">${esc(n.text)}</div>
            <button class="nb-tear" title="撕掉（会进留档，可以恢复）">✕</button>
          </div>`).join('') || '<p class="muted">墙上空了。</p>';
        $('#nbArcBtn').textContent = `${showArc ? '收起' : '看看'}留档 · 撕掉的 ${arc.length} 张`;
        $('#nbArc').hidden = !showArc;
        $('#nbArc').innerHTML = arc.map((n) => `
          <div class="nb-arcrow"><s>${esc(n.text)}</s><small>${esc(String(n.delAt || '').slice(5, 16).replace('T', ' '))}${n.reason ? ' · ' + esc(n.reason) : ''}</small>
            <button class="btn ghost nb-restore" data-id="${esc(n.id)}">↺ 钉回去</button></div>`).join('') || '<p class="muted">还没有撕掉过。</p>';
      };
      NB.listeners.add(paint);
      panelCleanup.push(() => NB.listeners.delete(paint));
      paint();
      const pin = () => {
        const t = $('#nbText'), text = t.value.trim(); if (!text) return;
        t.value = '';
        NB.data = { ...NB.data, board: [{ id: 'pending-' + Date.now(), text, color, rot: Number.isFinite(NB.data.nextRot) ? NB.data.nextRot : -3 }, ...(NB.data.board || [])] };
        nbSet();
        notesDo({ op: 'add', text, color }, '📌 钉上了');
        window.playSfx('coin');
      };
      $('#nbPin').addEventListener('click', pin);
      $('#nbText').addEventListener('keydown', (e) => { e.stopPropagation(); if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); pin(); } });
      $('.nb-colors').addEventListener('click', (e) => {
        const c = e.target.dataset && e.target.dataset.c; if (!c) return;
        color = c; $$('.nb-colors i').forEach((x) => x.classList.toggle('on', x === e.target));
      });
      $('#nbArcBtn').addEventListener('click', () => { showArc = !showArc; paint(); });
      const root = $('#nbRoot');
      root.addEventListener('click', (e) => {
        const tear = e.target.closest('.nb-tear');
        if (tear) {
          const id = tear.closest('.nb-card').dataset.id;
          if (id.startsWith('pending-')) return;
          const n = NB.data.board.find((x) => x.id === id);
          NB.data = { ...NB.data, board: NB.data.board.filter((x) => x.id !== id), archive: [{ ...n, delAt: new Date().toISOString() }, ...(NB.data.archive || [])] };
          nbSet();
          notesDo({ op: 'del', id, reason: '在桌上撕掉' }, '撕掉了（在留档里）');
          window.playSfx('close');
        }
        const rs = e.target.closest('.nb-restore');
        if (rs) notesDo({ op: 'restore', id: rs.dataset.id }, '↺ 钉回去了');
      });
      root.addEventListener('focusout', (e) => {
        const tx = e.target.closest && e.target.closest('.nb-tx'); if (!tx) return;
        const id = tx.closest('.nb-card').dataset.id;
        const n = (NB.data.board || []).find((x) => x.id === id);
        const text = tx.innerText.replace(/\u00a0/g, ' ').trim();
        if (!n || id.startsWith('pending-') || !text || text === n.text) return;
        n.text = text; paintNotesOnDesk();
        notesDo({ op: 'edit', id, text }, '便签已保存 ✎');
      });
      root.addEventListener('keydown', (e) => { if (e.target.closest && e.target.closest('.nb-tx')) { e.stopPropagation(); if (e.key === 'Escape') e.target.blur(); } });
      if (NB.status === 'snapshot' || NB.status === 'error') notesAction({ op: 'list' }).then((j) => { NB.status = 'live'; nbSet(j); }).catch((er) => { NB.status = er.offline ? 'offline' : 'error'; nbSet(); });
    };
    return { html, wire };
  }

  /* ---------- 面板：海报 · 作品展台 —— 全部图片产物（新 → 旧），另附 Works 橱窗 ---------- */
  function panelPoster() {
    const S = D.showcase, G = [...(window.DESK_GALLERY || [])];
    const PAGE = 48;
    const fmt = (iso) => { if (!iso) return ''; const d = new Date(iso); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
    const html = `
      <span class="kicker">POSTER · ${esc(S.title)}</span>
      <h2>${esc(S.title)}</h2>
      <p class="muted">多端索引里的图片，点缩略图看大图。这里展示最近 100 张。</p>
      <p><a class="btn" href="/library.html?view=images">查看全部图片与搜索 ↗</a></p>
      <div class="tabs">
        <button class="tabbtn on" data-ptab="all">🖼 全部图片 · ${G.length}</button>
        <button class="tabbtn" data-ptab="works">应用与页面</button>
      </div>
      <div id="posterBody"></div>`;



    const wire = () => {
      const body = $('#posterBody');
      let shown = 0, tab = 'all';
      const tile = (g, i) => `<figure class="gshot" data-i="${i}" role="button" tabindex="0" aria-label="查看图片：${esc(g.title)}"><img src="${esc(g.url)}" alt="${esc(g.title)}" loading="lazy" decoding="async"><figcaption>${esc(fmt(g.created))}</figcaption></figure>`;
      const more = () => {
        const grid = $('#gGrid'); if (!grid) return;
        grid.insertAdjacentHTML('beforeend', G.slice(shown, shown + PAGE).map((g, k) => tile(g, shown + k)).join(''));
        shown = Math.min(G.length, shown + PAGE);
        const btn = $('#gMore'); if (btn) btn.hidden = shown >= G.length;
        const cnt = $('#gCount'); if (cnt) cnt.textContent = `${shown} / ${G.length}`;
      };
      const paintAll = () => {
        shown = 0;
        body.innerHTML = G.length
          ? `<div class="ggrid" id="gGrid"></div>
             <div class="gfoot"><span class="muted" id="gCount"></span><button class="btn ghost" id="gMore">再看 ${PAGE} 张</button></div>`
          : `<div class="emptybox">🖼</div><p class="muted">还没有同步到图片。</p>`;
        if (!G.length) return;
        more();
        $('#gMore').addEventListener('click', more);
      };
      const view = (i) => {
        i = (i + G.length) % G.length;
        const g = G[i];
        body.innerHTML = `
          <div class="gview">
            <img class="shot-big" src="${esc(g.url)}" alt="${esc(g.title)}">
            <div class="gview-bar">
              <button class="btn ghost" id="gBack">← 全部</button>
              <button class="btn ghost" id="gPrev">‹ 上一张</button>
              <span class="muted">${i + 1} / ${G.length} · ${esc(g.title)} · ${esc(g.src || '')} · ${esc(fmt(g.created))}</span>
              <button class="btn ghost" id="gNext">下一张 ›</button>
              <a class="btn" href="${esc(g.url)}" target="_blank" rel="noopener" style="text-decoration:none">打开原图 ↗</a>
            </div>
          </div>`;
        $('#gBack').addEventListener('click', () => { paintAll(); const tile = body.querySelector('.gshot'); if (tile) tile.focus(); });
        $('#gPrev').addEventListener('click', () => view(i - 1));
        $('#gNext').addEventListener('click', () => view(i + 1));
      };
      body.addEventListener('click', (e) => { const f = e.target.closest('.gshot'); if (f) { view(+f.dataset.i); $('#gBack').focus(); } });
      body.addEventListener('keydown', e => { const f = e.target.closest('.gshot'); if (f && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); f.click(); } });
      $$('.tabbtn[data-ptab]').forEach((b) => b.addEventListener('click', () => {
        tab = b.dataset.ptab;
        $$('.tabbtn[data-ptab]').forEach((x) => x.classList.toggle('on', x === b));
        if (tab === 'all') paintAll(); else {
          body.innerHTML = '<p><a href="/works.html">独立打开应用与页面 ↗</a></p><div id="worksMount"></div>';
          window.DeskWorks.mount($('#worksMount'));
        }
      }));
      paintAll();
      fetch('/api/index/artifacts?images=1&limit=100').then(r=>r.json()).then(data=>{
        if(!body.isConnected||!data.items) return;
        G.splice(0,G.length,...data.items.map(a=>({title:a.title,url:'/api/index/image?id='+encodeURIComponent(a.id),created:a.updated,src:a.source})));
        const button=panelBody.querySelector('[data-ptab="all"]');
        if(button) button.textContent='🖼 图片 · '+data.total;
        if(tab==='all') paintAll();
      }).catch(()=>toast('图片索引暂时不可用'));
    };
    return { html, wire, wide: true };
  }

  /* ---------- 面板：主机 ---------- */
  function panelPC() {
    const p = D.pc, V = window.DESK_VIBE;
    const EMO = { focus: '🎯', mood: '🌤', tea: '🍵' };
    const live = p.stats.map((st, i) => ({ ...st, i })).filter((st) => st.live && V);
    const fixed = p.stats.filter((st) => !st.live);
    const html = `
      <span class="kicker">PC TOWER · ${esc(p.name)}</span>
      <h2>桌面状态</h2>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin:6px 0">
        ${p.parts.map((x) => `<span class="site">${esc(x)}</span>`).join('')}
      </div>
      ${live.map((st) => `<div class="vibe" data-k="${esc(st.live)}">
          <div class="vibe-head"><span class="vibe-emo">${EMO[st.live] || '•'}</span><b>${esc(st.label)}</b>
            <span class="vibe-val"><em>—</em><small></small><i class="vibe-trend"></i></span></div>
          <div class="bar vibe-bar"><i></i></div>
          <div class="vibe-foot"><span class="vibe-text"></span>${st.live === 'tea' ? '<button class="btn ghost vibe-btn" data-act="tea">🍵 续一盏</button>' : ''}${st.live === 'focus' ? '<button class="btn ghost vibe-btn" data-act="focus">🎧 专注模式</button>' : ''}</div>
          <canvas class="vibe-spark" width="640" height="70"></canvas>
        </div>`).join('')}
      ${live.length ? '<p class="muted vibe-note">以下为桌面互动模拟，不代表真实健康或系统测量。曲线是过去 60 分钟，跟着时间和你在桌上做的事走：续茶会把茶温倒回 88°C 再慢慢凉，也会让心情鼓一下；戴耳机专注 +12；番茄钟每半小时一轮；17:30 之后专注往下走。主机风扇转速也跟着专注变。</p>' : ''}
      ${fixed.length ? '<p class="muted">尚未接入系统状态监测；这里不显示存储、索引或同步完成率。</p>' : ''}
      <div class="section-t">配置说明</div>
      ${p.running.map((r) => `<div class="run">▸ ${esc(r)}</div>`).join('')}`;
    const COLOR = { focus: '#7c4dff', mood: '#ff5fa2', tea: '#14b8a6' };
    const wire = () => {
      if (!live.length) return;
      const draw = (el, k, now) => {
        const pts = V.series(k, now, 60, 1), c = el.querySelector('canvas'), x = c.getContext('2d');
        const W = c.width, H = c.height, lo = k === 'tea' ? 20 : 0, hi = 100;
        const X = (i) => 6 + i * (W - 12) / (pts.length - 1), Y = (v) => H - 6 - (v - lo) / (hi - lo) * (H - 12);
        x.clearRect(0, 0, W, H);
        x.strokeStyle = 'rgba(23,19,16,.12)'; x.lineWidth = 1; x.setLineDash([4, 6]);
        [25, 50, 75].forEach((g) => { x.beginPath(); x.moveTo(0, Y(lo + (hi - lo) * g / 100)); x.lineTo(W, Y(lo + (hi - lo) * g / 100)); x.stroke(); });
        x.setLineDash([]);
        x.beginPath(); pts.forEach((v, i) => (i ? x.lineTo(X(i), Y(v)) : x.moveTo(X(i), Y(v))));
        x.lineTo(X(pts.length - 1), H); x.lineTo(X(0), H); x.closePath();
        x.fillStyle = COLOR[k] + '22'; x.fill();
        x.beginPath(); pts.forEach((v, i) => (i ? x.lineTo(X(i), Y(v)) : x.moveTo(X(i), Y(v))));
        x.strokeStyle = '#171310'; x.lineWidth = 5; x.lineJoin = 'round'; x.stroke();
        x.strokeStyle = COLOR[k]; x.lineWidth = 2.5; x.stroke();
        const lx = X(pts.length - 1), ly = Y(pts[pts.length - 1]);
        x.beginPath(); x.arc(lx, ly, 6, 0, 7); x.fillStyle = COLOR[k]; x.fill(); x.lineWidth = 3; x.strokeStyle = '#171310'; x.stroke();
        return pts;
      };
      const paint = () => {
        const now = Date.now();
        $$('.vibe', panelBody).forEach((el) => {
          const k = el.dataset.k, r = V.value(k, now), pts = draw(el, k, now);
          const prev = pts[pts.length - 6], d = r.v - prev;
          el.querySelector('.vibe-val em').textContent = k === 'tea' ? r.v.toFixed(1) : Math.round(r.v);
          el.querySelector('.vibe-val small').textContent = r.unit;
          el.querySelector('.vibe-trend').textContent = Math.abs(d) < 0.6 ? '→' : d > 0 ? '↗' : '↘';
          el.querySelector('.vibe-bar i').style.width = Math.max(3, Math.min(100, r.pct)) + '%';
          el.querySelector('.vibe-bar i').style.background = COLOR[k];
          el.querySelector('.vibe-text').textContent = r.text;
        });
      };
      paint();
      const id = setInterval(paint, 1000);
      panelCleanup.push(() => clearInterval(id));
      panelBody.addEventListener('click', (e) => {
        const b = e.target.closest('.vibe-btn'); if (!b) return;
        if (b.dataset.act === 'tea') {
          const n = (+store.get(K.tea, 0) || 0) + 1; store.set(K.tea, n);
          V.record('tea'); window.playSfx('coin'); toast('🍵 续上了，第 ' + n + ' 盏');
        } else if (b.dataset.act === 'focus') toggleSound();
        paint();
      });
    };
    return { html, wire };
  }

  /* ---------- 面板：手机 · 微信群聊（多 agent）——实现在 js/wx/（外壳 / 会话模型 / adapter / 角色包），这里只转发 ---------- */
  function panelPhone() {
    if (!window.DESK_WX || !window.DESK_WX.panel) {
      return { html: '<span class="kicker">PHONE · 手机</span><h2>手机功能尚未接入</h2><p class="muted">当前版本暂未提供手机内容，无需反复刷新。会话请从显示器查看。</p>' };
    }
    const p = window.DESK_WX.panel({ toast, sfx: window.playSfx });
    return { html: p.html, wire: () => { p.wire(); panelCleanup.push(p.cleanup); } };
  }

  /* ---------- 面板：笔筒 · 随手记 ---------- */
  function panelPens() {
    let notes = store.get(K.quick, []);
    if (!Array.isArray(notes)) notes = [];
    const listHTML = () => notes.map((n) => `<div class="task nohover"><span class="box">✎</span><span class="tx">${esc(n)}</span></div>`).join('') || '<p class="muted">还空着。</p>';
    const html = `
      <span class="kicker">PENS · 笔筒</span>
      <h2>写点什么</h2>
      <p class="muted">灵感随手记在这里（只存在你自己的浏览器，不进 My Daily 的记忆）。</p>
      <div class="addrow"><input id="qn" placeholder="写一句灵感…" maxlength="200"><button class="btn" id="qadd">记下</button></div>
      <div id="qnlist">${listHTML()}</div>`;
    const wire = () => {
      const add = () => {
        const v = $('#qn').value.trim(); if (!v) return;
        notes.unshift(v); store.set(K.quick, notes);
        $('#qnlist').innerHTML = listHTML();
        $('#qn').value = ''; window.playSfx('coin');
      };
      $('#qadd').addEventListener('click', add);
      $('#qn').addEventListener('keydown', (e) => { if (e.key === 'Enter') add(); });
    };
    return { html, wire };
  }

  /* ---------- 面板：茶盏 · 计数 + 5 分钟歇一歇 ---------- */
  /* 茶盏 → 光 · 糖 · 动 · 茶：一点就算一次，只记今天，不填任何东西 */
  function panelMug() {
    const K_LSM = 'yz_desk_lsm_v1';
    const ITEMS = [
      { k: 'light', icon: '☀', name: '光', did: '晒到太阳了', nudge: '去窗边晒几分钟太阳？', every: 180 },
      { k: 'sugar', icon: '🍬', name: '糖', did: '吃了点东西', nudge: '留意一下血糖，垫点东西？', every: 180 },
      { k: 'move', icon: '🏃', name: '动', did: '起来动了动', nudge: '坐挺久了，起来动一动？', every: 90 },
      { k: 'tea', icon: '🍵', name: '茶', did: '续了一盏', nudge: '茶凉了，续一盏？', every: 60 },
    ];
    const today = new Date().toDateString();
    let log = store.get(K_LSM, null);
    if (!log || log.date !== today) log = { date: today, light: [], sugar: [], move: [], tea: [] };
    const ago = (k) => { const a = log[k]; return a.length ? Math.round((Date.now() - a[a.length - 1]) / 60e3) : null; };
    const hint = () => {
      const h = new Date().getHours();
      const due = ITEMS.filter((it) => (it.k !== 'light' || (h >= 8 && h < 17)) && (ago(it.k) === null ? h >= 10 : ago(it.k) >= it.every));
      if (!due.length) return ITEMS.every((it) => log[it.k].length) ? '光糖动茶都齐了，今天回血到位 ✨' : '现在挺好，不用管。';
      return due[0].nudge;
    };
    const html = () => `
      <span class="kicker">TEA · 回一口血</span>
      <h2>光 · 糖 · 动 · 茶</h2>
      <p class="muted">做了哪样就点一下，不用记别的。只算今天，只存在你的浏览器。</p>
      <div class="lsm">${ITEMS.map((it) => {
        const n = log[it.k].length, a = ago(it.k);
        return `<button class="lsm-btn ${n ? 'on' : ''}" data-k="${it.k}">
          <span class="lsm-ico">${it.icon}</span><b>${it.name}</b>
          <small>${n ? `${n} 次 · ${a < 1 ? '刚刚' : a + ' 分钟前'}` : '今天还没有'}</small></button>`;
      }).join('')}</div>
      <p class="lsm-hint">${esc(hint())}</p>
      <button class="btn ghost lsm-undo" id="lsmUndo" ${Object.keys(log).some((k) => Array.isArray(log[k]) && log[k].length) ? '' : 'hidden'}>撤销上一次</button>`;
    const wire = () => {
      const paint = () => { panelBody.innerHTML = html() + sessionFooter('mug'); wire(); };
      $$('.lsm-btn').forEach((b) => b.addEventListener('click', () => {
        const it = ITEMS.find((x) => x.k === b.dataset.k);
        log[it.k].push(Date.now()); log.last = it.k; store.set(K_LSM, log);
        if (it.k === 'tea') store.set(K.tea, (+store.get(K.tea, 0) || 0) + 1);
        if (window.DESK_VIBE) window.DESK_VIBE.record(it.k);
        window.playSfx('coin'); toast(`${it.icon} ${it.did}`); paint();
      }));
      const u = $('#lsmUndo');
      if (u) u.addEventListener('click', () => {
        const k = log.last; if (!k || !log[k] || !log[k].length) return;
        log[k].pop(); if (k === 'tea') store.set(K.tea, Math.max(0, (+store.get(K.tea, 0) || 0) - 1));
        log.last = null; store.set(K_LSM, log); toast('撤销了'); paint();
      });
    };
    return { html: html(), wire };
  }

  /* ---------- 面板：音响 ---------- */
  function panelSpeaker() {
    return {
      html: `<span class="kicker">SPEAKER · 律动</span><h2>音响</h2>
      <p>它跟着音乐一起跳。想听歌的话，去点桌上的 CD 机——里面是本地歌单。</p>
      <div class="eq" style="position:static;height:70px;justify-content:flex-start;gap:8px">${'<i style="width:16px"></i>'.repeat(9)}</div>
      <p class="muted">提示：戴上耳机（或点右上角 ♪）打开环境音。</p>`,
    };
  }

  /* ---------- 面板：相机 · 相册 ---------- */
  /* 相机 → 相册：最近我上传的图片（js/uploads.js，tools/sync-uploads.py 生成；不含截屏、单据、敏感信息） */
  function panelCamera() {
    const K_HIDE = 'yz_desk_album_hidden_v1';
    const hidden = new Set(store.get(K_HIDE, []) || []);
    const all = (window.DESK_UPLOADS || []).map((u) => ({ file: u.url, title: u.name.replace(/\.(webp|jpe?g|png|heic)$/i, ''), cat: u.at, loc: u.session, id: u.url }));
    const mine = () => all.filter((p) => !hidden.has(p.id));
    let list = mine(), src = 'mine';
    if (!list.length && D.photos && D.photos.length) { list = D.photos; src = 'desk'; }
    // 顶部两个 tab：相册 / 每日总结（每日总结的实现在 js/digest-panel.js）
    const tabs = (on) => `<span class="kicker">CAMERA · ${on === 'digest' ? '每日总结' : '相册'}</span>
      <div class="cam-tabs"><button class="cam-tab ${on === 'album' ? 'on' : ''}" data-tab="album">📷 相册</button><button class="cam-tab ${on === 'digest' ? 'on' : ''}" data-tab="digest">📝 每日总结</button></div>`;
    const wireTabs = () => $$('.cam-tab').forEach((b) => b.addEventListener('click', () => {
      if (b.dataset.tab === 'album') { panelBody.innerHTML = grid() + sessionFooter('camera'); wire(); }
      else if (window.DeskDigest) window.DeskDigest.open(panelBody, { tabs, wireTabs, footer: sessionFooter('camera'), toast, cleanup: panelCleanup });
    }));
    const grid = () => `
      ${tabs('album')}
      <h2>相册</h2>
      <p class="muted">${src === 'mine'
        ? `最近你上传的 ${list.length} 张，新的在前（已自动挡掉截屏、单据和含敏感信息的图）。点开可以看大图，也可以从相册拿掉。`
        : '还没有找到你上传的照片，先放桌上的相册。'}${hidden.size ? `　<a href="#" id="albumRestore">恢复拿掉的 ${hidden.size} 张</a>` : ''}</p>
      <div class="photogrid">
        ${list.map((p, i) => `
          <figure class="shot" data-i="${i}">
            <img src="${esc(p.file)}" alt="${esc(p.title)}" loading="lazy">
            <figcaption><b>${esc(p.cat)}</b><small>${esc(p.loc || '')}</small></figcaption>
          </figure>`).join('')}
      </div>`;
    const wire = () => {
      wireTabs();
      const r = $('#albumRestore');
      if (r) r.addEventListener('click', (e) => { e.preventDefault(); hidden.clear(); store.set(K_HIDE, []); list = mine(); src = 'mine'; panelBody.innerHTML = grid() + sessionFooter('camera'); wire(); });
      $$('.shot').forEach((el) => el.addEventListener('click', () => {
        const p = list[+el.dataset.i];
        panelBody.innerHTML = `<span class="kicker">PHOTO · ${esc(p.cat)}</span><h2>${esc(src === 'mine' ? p.cat : p.title)}</h2>
          <img class="shot-big" src="${esc(p.file)}" alt="">
          <p class="muted">${esc(src === 'mine' ? '上传于「' + (p.loc || '') + '」' : p.cat + (p.loc && p.loc !== '—' ? ' · ' + p.loc : ''))}</p>
          ${src === 'mine' ? '<button class="btn ghost" id="albumHide">从相册拿掉这张</button>' : ''}` + sessionFooter('camera');
        const h = $('#albumHide');
        if (h) h.addEventListener('click', () => { hidden.add(p.id); store.set(K_HIDE, [...hidden]); list = mine(); toast('已从相册拿掉（只在你的浏览器）'); panelBody.innerHTML = grid() + sessionFooter('camera'); wire(); });
      }));
    };
    return { html: grid(), wire };
  }

  /* ---------- 面板：台历 · 绑定 Space 手账 ---------- */
  function panelCalendar() {
    const d = new Date();
    const date = `${d.getMonth() + 1} 月 ${d.getDate()} 日 · 周${'日一二三四五六'[d.getDay()]}`;
    return {
      html: `<span class="kicker">CALENDAR · 台历</span>
        <h2>${date}</h2>
        <p>手账尚未接入。</p>
        <p class="muted">这里目前只显示日期。今天的会话与待办，可以从显示器查看。</p>
        <button class="btn" id="calendarToday">查看今天的会话与待办 →</button>`,
      wire: () => $('#calendarToday').addEventListener('click', () => openObject('monitor')),
    };
  }

  /* ---------- 面板：桂花 ---------- */
  function panelPlant() {
    const m = D.plant.moods[Math.floor(Math.random() * D.plant.moods.length)];
    return {
      html: `<span class="kicker">OSMANTHUS · 心情</span><h2>${esc(D.plant.name)}</h2>
        <p>${esc(D.plant.line)}</p><p class="muted">再点一次，换一句。</p>
        <div class="run" style="font-size:15px">🌼 ${esc(m)}</div>`,
    };
  }

  /* ---------- 面板：更新说明 ---------- */
  function panelUpdate() {
    const u = D.update;
    const list = Object.keys(LBL).map((k) => esc(LBL[k].zh)).join(' · ');
    return {
      html: `<span class="kicker">HOW TO UPDATE</span><h2>${esc(u.title)}</h2>
      <p>待办与便签通过本地服务写入本机账本，刷新页面仍会保留；目前不代表自动跨设备同步。</p>
      <p>配色、音效、笔筒随手记和生活打卡保存在当前浏览器，换浏览器不会自动带过去。</p>
      <p>内容配置优先读取 data/content.local.json，未配置时使用 data/content.json；修改配置后需重新生成页面数据。</p>
      <div class="section-t">可交互清单（${Object.keys(LBL).length} 件）</div>
      <p class="muted">${list}</p>
      <div class="section-t">Session 绑定（js/sessions.js）</div>
      <p class="muted">${Object.keys(LBL).map((k) => { const b = binding(k); return `${esc(LBL[k].zh)}：${b ? `<a href="${esc(b.url)}" target="_blank" rel="noopener">${esc(b.title)}</a>${b.open === 'direct' ? '（直开）' : ''}` : '—'}`; }).join(' · ')}</p>
      <p class="muted">已绑定 ${Object.keys(LBL).filter((k) => binding(k)).length} / ${Object.keys(LBL).length}。Shift + 点击已绑定的物件可直接打开 Session。</p>
      <div class="section-t">快捷键</div>
      <p class="muted"><b>/</b> 命令面板 · <b>t</b> 配色 · <b>d</b> 白天黑夜 · <b>l</b> 台灯 · <b>f</b> 滤镜 · <b>m</b> 环境音 · <b>Esc</b> 关闭</p>`,
    };
  }

  const PANELS = {
    window: panelDashboard, monitor: panelWork, pc: panelPC, book: panelBook, contract: panelContract,
    mug: panelMug, pens: panelPens, figure: () => panelFigure(0), figure2: () => panelFigure(1),
    speaker: panelSpeaker, cd: () => (window.DESK_CD ? window.DESK_CD.panel({ $, $$, esc, toast, stage, D, cleanup: { push: (fn) => panelCleanup.push(fn) } }) : panelMusic()), tablet: () => panelTablet('video'), phone: panelPhone,
    controller: panelGames, board: panelBoard, notes: panelNotes, poster: panelPoster,
    camera: panelCamera, calendar: panelCalendar, plant: panelPlant, update: panelUpdate,
  };

  /* ============================================================
   *  工具：滤镜 · 台灯 · 环境音
   * ============================================================ */
  function toggleFilter(showToast) {
    state.filter = !state.filter;
    stage.classList.toggle('filter', state.filter);
    $('[data-tool="filter"]').classList.toggle('on', state.filter);
    if (showToast) toast(state.filter ? '😎 世界变成漫画了' : '摘掉眼镜');
    window.playSfx('click');
  }

  function toggleLamp() {
    state.lamp = !state.lamp;
    aimLamp();
    stage.classList.toggle('lamp-on', state.lamp);
    toast(state.lamp ? '💡 台灯开了' : '关灯');
    window.playSfx('click');
  }

  /* 环境音：WebAudio 生成的棕噪声，无外部文件 */
  let noise = null;
  function toggleSound() {
    state.sound = !state.sound;
    $('[data-tool="sound"]').classList.toggle('on', state.sound);
    stage.classList.toggle('focus', state.sound);
    if (window.DESK_VIBE) window.DESK_VIBE.record(state.sound ? 'focus-on' : 'focus-off');
    if (state.sound) {
      const ctx = actx();
      const buf = ctx.createBuffer(1, ctx.sampleRate * 3, ctx.sampleRate);
      const d = buf.getChannelData(0);
      let last = 0;
      for (let i = 0; i < d.length; i++) { const w = Math.random() * 2 - 1; last = (last + 0.02 * w) / 1.02; d[i] = last * 3.2; }
      const src = ctx.createBufferSource(); src.buffer = buf; src.loop = true;
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 520;
      const g = ctx.createGain(); g.gain.value = 0.07;
      src.connect(lp); lp.connect(g); g.connect(ctx.destination); src.start();
      noise = { src, g };
      toast('🎧 专注模式 · 环境音已开');
    } else {
      if (noise) { try { noise.g.gain.value = 0; noise.src.stop(); } catch (e) {} noise = null; }
      toast('环境音已关');
    }
    window.playSfx('click');
  }

  /* ============================================================
   *  命令面板（键盘）—— 条目直接由 DESK_LABELS 生成，不再手写一份
   * ============================================================ */
  const CMD_ITEMS = [
    ...Object.keys(LBL).filter((k) => PANELS[k] || ['mora'].includes(k)).map((k) => ({ k, t: LBL[k].zh })),
    { action: 'theme', t: '切换配色 🎨' }, { action: 'dn', t: '切换白天 / 黑夜' },
    { action: 'lamp', t: '开关台灯 💡' }, { action: 'sound', t: '开关环境音 🎧' },
    { action: 'filter', t: '漫画滤镜 😎' }, { k: 'update', t: '这张桌子怎么更新' },
    { href: '/catalog.html', t: '打开索引页 📇' },
    ...Object.keys((SS && SS.bind) || {}).filter((k) => binding(k)).map((k) => ({ session: k, t: '🔗 ' + ((LBL[k] && LBL[k].zh) || k) + ' → ' + binding(k).title })),
  ];
  let cmdSel = 0, cmdItems = [], cmdReturnFocus = null;
  function openCmd() {
    cmdReturnFocus = document.activeElement;
    $('#cmd').hidden = false; $('#cmdInput').value = ''; cmdSel = 0;
    renderCmd(''); $('#cmdInput').focus();
    window.playSfx('open');
  }
  function closeCmd() { $('#cmd').hidden = true; if (cmdReturnFocus && cmdReturnFocus.isConnected) cmdReturnFocus.focus({ preventScroll: true }); }
  function renderCmd(q) {
    q = q.toLowerCase();
    cmdItems = CMD_ITEMS.filter((i) => i.t.toLowerCase().includes(q) || (i.k || i.session || '').includes(q));
    $('#cmdList').innerHTML = cmdItems.map((i, idx) => `<div class="cmditem ${idx === cmdSel ? 'on' : ''}" data-i="${idx}">${esc(i.t)}</div>`).join('') || '<div class="cmditem">没有找到…</div>';
  }
  function runAction(a) {
    if (a === 'dn') { setNight(!state.night); toast(state.night ? '🏮 入夜' : '☀ 天亮'); }
    if (a === 'sound') toggleSound();
    if (a === 'filter') toggleFilter(true);
    if (a === 'theme') cycleTheme();
    if (a === 'lamp') toggleLamp();
  }
  function runCmd() {
    const i = cmdItems[cmdSel]; if (!i) return;
    closeCmd();
    if (i.session) openSession(i.session);
    else if (i.href) { if (/^https?:/.test(i.href)) window.open(i.href, '_blank', 'noopener'); else location.href = i.href; }
    else if (i.action) runAction(i.action);
    else openObject(i.k);
  }
  $('#cmd').addEventListener('click', (e) => { if (e.target.id === 'cmd') closeCmd(); });
  $('#cmdList').addEventListener('click', (e) => {
    const it = e.target.closest('.cmditem'); if (!it || it.dataset.i === undefined) return;
    cmdSel = +it.dataset.i; runCmd();
  });
  $('#cmdInput').addEventListener('input', (e) => { cmdSel = 0; renderCmd(e.target.value); });
  $('#cmdInput').addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); cmdSel = Math.min(cmdItems.length - 1, cmdSel + 1); renderCmd($('#cmdInput').value); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); cmdSel = Math.max(0, cmdSel - 1); renderCmd($('#cmdInput').value); }
    else if (e.key === 'Enter') { e.preventDefault(); runCmd(); }
    else if (e.key === 'Escape') { e.stopPropagation(); closeCmd(); }
  });

  /* ---------------- 工具按钮 ---------------- */
  $$('.tool[data-tool]').forEach((b) => b.addEventListener('click', () => {
    const t = b.dataset.tool;
    if (t === 'update') openObject('update'); else runAction(t);
  }));

  /* 快捷键：在输入框 / 可编辑便签里打字时不触发（原版在面板便签里打 t/d/f 会误触） */
  window.addEventListener('keydown', (e) => {
    const tg = e.target;
    if (tg && (tg.tagName === 'INPUT' || tg.tagName === 'TEXTAREA' || tg.isContentEditable)) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (!$('#cmd').hidden) return;
    if (e.key === '/') { e.preventDefault(); openCmd(); }
    else if (e.key === 'd') runAction('dn');
    else if (e.key === 'f') toggleFilter(true);
    else if (e.key === 'm') toggleSound();
    else if (e.key === 't') cycleTheme();
    else if (e.key === 'l') toggleLamp();
  });

  /* ---------------- 启动 ---------------- */
  initTheme();
  buildChrome();
  buildBoard();
  buildKbd();
  buildNotes();
  buildFigures();
  buildMusicFace();
  buildMonitorChip();
  buildPoster();
  initClock();
  initCalendar();
  bindLabels();
  fit();
  initTime();
  requestAnimationFrame(aimLamp);
  window.addEventListener('resize', aimLamp);

  /* 3D 贴图采集模式：?capture=wall|shelf，只留指定区域的物件，透明背景截图用 */
  if (CAPTURE) {
    document.body.classList.add('capture', 'capture-' + CAPTURE[1]);
    const only = /[?&]id=([a-z0-9]+)/.exec(location.search);
    if (only) { document.body.classList.add('capture-only'); const t = $(`.obj[data-obj="${only[1]}"]`); if (t) t.classList.add('cap-target'); }
    setNight(/[?&]night=1/.test(location.search));
    return;
  }
  setTimeout(() => toast('👋 点一点桌上的东西，它们都是活的'), 700);

  const hash = location.hash.replace('#', '');
  if (hash) { setTimeout(() => openObject(hash), 350); }

  /* 调试/验收钩子：不影响用户 */
  window.__desk = { openObject, setTheme, setNight, toggleLamp, state };
})();
