/* =====================================================================
 *  软木板 · 投影仪
 *  ---------------------------------------------------------------------
 *  学的是「可走的世界」主角房间那台投影仪（town/src/main.js 的 projector / source / deck）：
 *    1. 幕布平时卷着，挂在软木板上方。点软木板（或卷轴） → 幕布拉下来，弹出「选片台」。
 *    2. 选片台 = 同一份片单按类型分组 + 一排筛子；点一行 → 那份摆上幕布，处于「待讲」：
 *       幕布上亮着第一页，面板不弹，桌上照样能点别的。
 *    3. 幕布亮着时点它 → 「开讲」：大屏翻页、字幕逐字打、用登记过的音色念（只放 tools/bake-voice.mjs 烤好的；没烤的页不出声）；房间灯压暗，
 *       幕布和投影光束是亮的。幕布上同步显示正在讲的那一页。
 *    4. 放下 / 收起只走搁板上那台小投影机（点一下切换）。收起时软木板就是软木板：点它打开面板（钉着武器库）。
 *       摆着的那一份记在本机，下次放下来还是它。
 *  片单在 js/projector-library.js（library.json 同一种格式）。
 *  深链：?projector=1 拉下幕布并打开选片台；?projector=<id> 直接摆上那一份；再加 &present=1 直接开讲。
 * ===================================================================== */
(function () {
  'use strict';
  const stage = document.getElementById('stage');
  if (!stage) return;
  const $ = (s, r = document) => r.querySelector(s);
  const esc = (v) => String(v == null ? '' : v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const KEY = 'yz_desk_projector_v1';
  const KIND = { deck: '幻灯', text: '文档', image: '图', video: '影像', music: '唱片', html: '网页', embed: '网页', pdf: 'PDF' };
  const ORDER = ['deck', 'text', 'image', 'video', 'music', 'html', 'embed', 'pdf'];
  const toast = (m) => { const box = $('#toast'); if (!box) return; const el = document.createElement('div'); el.className = 'tst'; el.textContent = m; box.appendChild(el); setTimeout(() => el.remove(), 2200); };
  const sfx = (t) => window.playSfx && window.playSfx(t);
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { return {}; } };
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify({ down: S.down, itemId: S.item && S.item.id, page: S.page })); } catch (e) {} };

  const S = { down: false, item: null, deck: null, page: 0, presenting: false, auto: false, voice: true, filter: '' };
  let items = [];
  const library = () => { const L = window.DESK_PROJECTOR_LIBRARY; items = L ? (typeof L.items === 'function' ? L.items() : L.items) : []; return items; };

  /* ---------------- 场景里的东西：卷轴 + 幕布 + 桌上的小投影机 + 光束 + 压暗层 ---------------- */
  stage.insertAdjacentHTML('beforeend', `
    <div class="proj-case" aria-hidden="true"><i></i></div>
    <div class="proj-screen" tabindex="0" role="button" aria-label="投影幕布">
      <div class="proj-cloth">
        <div class="proj-face"><div class="proj-scale" id="projFace"></div><div class="proj-empty">幕布拉下来了 · 点我选一份投上去</div></div>
        <div class="proj-ctrl">
          <button data-pc="prev" title="上一页">‹</button><span id="projPage">—</span><button data-pc="next" title="下一页">›</button>
          <button data-pc="talk" class="hot">▶ 开讲</button><button data-pc="pick">📽 换片</button>
        </div>
        <div class="proj-weight"></div>
      </div>
    </div>
    <div class="proj-rig" tabindex="0" role="button" aria-label="投影仪：放下 / 收起幕布" title="投影仪：点一下放下 / 收起幕布"><i class="lens"></i><b>PROJ</b></div>
    <svg class="proj-beam" viewBox="0 0 1600 1000" preserveAspectRatio="none" aria-hidden="true">
      <defs><linearGradient id="projBeamG" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#fff6c8" stop-opacity=".55"/><stop offset="1" stop-color="#fff6c8" stop-opacity=".06"/></linearGradient></defs>
      <polygon id="projBeamP" fill="url(#projBeamG)"/></svg>
    <div class="proj-dim" aria-hidden="true"></div>`);
  document.body.insertAdjacentHTML('beforeend', `
    <div id="projPicker" class="proj-overlay" hidden><div class="proj-bg" data-close="1"></div>
      <div class="panel proj-panel"><button class="panel-close" data-close="1" aria-label="关闭">✕</button>
        <span class="kicker">PROJECTOR · 选片台</span><h2>幕布 · 选片</h2>
        <div class="proj-power"><button id="projPower"></button><span id="projNow" class="muted"></span></div>
        <div id="projList"></div></div></div>
    <div id="projTalk" class="proj-overlay talk" hidden><div class="proj-bg"></div>
      <div class="proj-talkbox">
        <div class="proj-talkhead"><span class="kicker">PROJECTOR · 开讲</span><b id="projTitle"></b><span id="projCount" class="muted"></span>
          <button class="panel-close" data-tk="close" aria-label="关闭">✕</button></div>
        <div class="proj-big"><div class="proj-scale" id="projBig"></div></div>
        <div class="proj-sub"><span id="projSub"></span></div>
        <div class="proj-vhint" id="projVoiceHint"></div>
        <div class="proj-bar">
          <button class="btn ghost" data-tk="prev">‹ 上一页</button>
          <button class="btn" data-tk="auto" id="projAuto">▶ 一页页讲</button>
          <button class="btn ghost" data-tk="next">下一页 ›</button>
          <button class="btn ghost" data-tk="voice" id="projVoice"></button>
          <span class="proj-gap"></span>
          <button class="btn ghost" data-tk="pick">📽 换一份</button>
          <button class="btn ghost" data-tk="stop">⏏ 讲完了</button>
        </div></div></div>`);

  const screen = $('.proj-screen'), face = $('#projFace'), big = $('#projBig');
  const picker = $('#projPicker'), talk = $('#projTalk');

  /* ---------------- 片源 → 一份幻灯（照 main.js deckDataForItem） ---------------- */
  function textDeck(item, text) {
    const pages = []; let buf = [];
    const flush = () => { if (!buf.length) return; pages.push({ title: item.title, note: '', html: `<div class="kicker">${esc(item.title)}</div><pre class="ps-doc">${esc(buf.join('\n'))}</pre>` }); buf = []; };
    String(text).split('\n').forEach((line) => { if ((/^##\s/.test(line) && buf.length > 4) || buf.length >= 16) flush(); buf.push(line); });
    flush();
    pages.forEach((p, i) => { const h = /##\s+(.+)/.exec(p.html); p.note = h ? h[1] : `${item.title} · 第 ${i + 1} 页`; });
    return { title: item.title, mode: 'slides', slides: pages };
  }
  async function deckFor(item) {
    if (item.build) return item.build();
    if (item.kind === 'deck') { const r = await fetch(item.src, { cache: 'no-cache' }); if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); }
    if (item.kind === 'text') { const r = await fetch(item.src, { cache: 'no-cache' }); if (!r.ok) throw new Error('HTTP ' + r.status); return textDeck(item, await r.text()); }
    const slide = { title: item.title, note: item.note || item.title, kind: item.kind === 'html' ? 'embed' : item.kind, src: item.src, cover: item.cover };
    return { title: item.title, mode: 'cards', slides: [slide] };
  }

  /* ---------------- 一页 → 1280×720 的画面 ---------------- */
  function slideHTML(s, where) {
    const k = s.kind || 'html';
    if (S.deck && S.deck.theme === 'chalk' && window.DESK_CHALK && k === 'html' && s.blocks) {
      return window.DESK_CHALK.html(s, { i: S.deck.slides.indexOf(s), n: S.deck.slides.length, where });
    }
    if (k === 'image') return `<div class="pslide ps-media"><img src="${esc(s.src)}" alt=""></div>`;
    if (k === 'video') return `<div class="pslide ps-media"><video src="${esc(s.src)}" ${where === 'big' ? 'controls autoplay' : 'muted autoplay loop'} playsinline></video></div>`;
    if (k === 'music') return `<div class="pslide ps-music">${s.cover ? `<img src="${esc(s.cover)}" alt="">` : '<div class="ps-disc">♪</div>'}
      <div><div class="kicker">唱片</div><h2>${esc(s.title)}</h2><p>${esc(s.note || '')}</p>${where === 'big' ? `<audio src="${esc(s.src)}" controls autoplay></audio>` : '<p class="foot">点幕布开讲就放</p>'}</div></div>`;
    if (k === 'embed' || k === 'pdf') return `<div class="pslide ps-embed"><iframe src="${esc(s.src)}" loading="lazy" ${where === 'big' ? '' : 'tabindex="-1"'} referrerpolicy="strict-origin-when-cross-origin" allow="autoplay; fullscreen"></iframe></div>`;
    return `<div class="pslide ps-html">${s.html || `<h1>${esc(s.title || '')}</h1>`}</div>`;
  }
  // 等比放进框里（宽高都不超），多出来的一边居中——整页永远完整可见
  const fit = (box, el) => {
    const w = box.clientWidth, h = box.clientHeight; if (!w) return;
    const k = h ? Math.min(w / 1280, h / 720) : w / 1280;
    el.style.transform = `translate(${((w - 1280 * k) / 2).toFixed(1)}px,${h ? ((h - 720 * k) / 2).toFixed(1) : 0}px) scale(${k})`;
  };

  /* ---------------- 幕布上的这一页（待讲 / 讲着都同步） ---------------- */
  function paintScreen() {
    const has = !!(S.deck && S.deck.slides && S.deck.slides.length);
    screen.classList.toggle('has', has);
    stage.classList.toggle('proj-lit', S.down && has);
    const n = has ? S.deck.slides.length : 0;
    $('#projPage').textContent = has ? `${S.page + 1}/${n}` : '—';
    if (has) {
      const s = S.deck.slides[S.page];
      // 大屏在讲有声音的东西时，幕布只放画面（不重复出声）
      face.innerHTML = slideHTML(s, 'screen');
      if (window.DESK_CHALK) { window.DESK_CHALK.fit(face); document.fonts && document.fonts.ready.then(() => window.DESK_CHALK.fit(face)); }
      face.querySelectorAll('video').forEach((v) => { v.muted = true; });
    } else face.innerHTML = '';
    requestAnimationFrame(() => fit(face.parentElement, face));
    aimBeam();
    label();
  }
  function label() {
    const L = window.DESK_LABELS; if (!L || !L.board) return;
    L.board.zh = !S.down ? '软木板 · 拉下幕布投影' : (S.deck ? `幕布 · 《${S.deck.title || S.item.title}》· 点它开讲` : '幕布 · 选一份投上去');
  }
  function aimBeam() {
    const p = $('#projBeamP'), lens = $('.proj-rig .lens'), f = $('.proj-face');
    if (!p || !lens || !f || !S.down) return;
    const sr = stage.getBoundingClientRect(), sc = sr.width / 1600 || 1;
    const L = lens.getBoundingClientRect(), F = f.getBoundingClientRect();
    const x = (v) => ((v - sr.left) / sc).toFixed(1), y = (v) => ((v - sr.top) / sc).toFixed(1);
    const lx = x(L.left + L.width / 2), ly = y(L.top + L.height / 2);
    p.setAttribute('points', `${lx},${ly} ${x(F.left)},${y(F.bottom)} ${x(F.left)},${y(F.top)} ${x(F.right)},${y(F.top)} ${x(F.right)},${y(F.bottom)}`);
  }

  /* ---------------- 拉下 / 收起 ---------------- */
  function drop(instant) {
    if (S.down) return;
    S.down = true;
    stage.classList.add('proj-down');
    if (instant) stage.classList.add('proj-instant');
    setTimeout(() => { stage.classList.remove('proj-instant'); aimBeam(); }, 650);
    sfx('open'); save(); paintScreen();
  }
  function rollUp() {
    if (!S.down) return;
    closeTalk(); closePicker();
    S.down = false;
    stage.classList.remove('proj-down', 'proj-lit');
    sfx('close'); save(); label();
    toast('幕布收起 · 软木板回来了（点它看武器库）');
  }

  /* ---------------- 选片台 ---------------- */
  function renderPicker() {
    library();
    const groups = ORDER.map((k) => [k, items.filter((i) => (i.kind || 'deck') === k)]).filter(([, l]) => l.length);
    const shown = groups.filter(([k]) => !S.filter || k === S.filter);
    $('#projPower').textContent = S.down ? '幕布：放下 · 点一下收起' : '幕布：收起 · 点一下拉下';
    $('#projPower').classList.toggle('on', S.down);
    $('#projNow').textContent = S.deck ? `幕布上摆着《${S.deck.title || S.item.title}》，换一份就点它。` : '还没摆东西。点一行就摆上幕布，等你点幕布开讲。';
    $('#projList').innerHTML = `
      <div class="proj-chips"><button class="${S.filter ? '' : 'on'}" data-k="">全部 <b>${items.length}</b></button>
        ${groups.map(([k, l]) => `<button class="${S.filter === k ? 'on' : ''}" data-k="${k}">${KIND[k] || k} <b>${l.length}</b></button>`).join('')}</div>
      ${shown.map(([k, l]) => `${S.filter ? '' : `<div class="proj-group">${KIND[k] || k}</div>`}
        <div class="proj-rows">${l.map((it) => `<div class="proj-row ${S.item && S.item.id === it.id ? 'on' : ''}" data-id="${esc(it.id)}">
          <span class="pr-t"><b>${esc(it.title)}${it.badge ? `<span class="chalk-badge">${esc(it.badge)}</span>` : ''}</b><small>${esc(it.note || '')}</small></span>
          <span class="pr-k">${S.item && S.item.id === it.id ? '在放' : (KIND[it.kind] || it.kind)}</span>
          <button class="pr-go" data-go="${esc(it.id)}" title="摆上去并直接开讲">▶ 直接讲</button></div>`).join('')}</div>`).join('')}
      <p class="muted proj-fine">${esc((window.DESK_PROJECTOR_LIBRARY || {}).note || '')}</p>`;
  }
  function openPicker() { renderPicker(); picker.hidden = false; }
  function closePicker() { picker.hidden = true; }
  picker.addEventListener('click', (e) => {
    if (e.target.closest('[data-close]')) { closePicker(); return; }
    if (e.target.id === 'projPower') { S.down ? rollUp() : drop(); renderPicker(); return; }
    const chip = e.target.closest('[data-k]'); if (chip) { S.filter = chip.dataset.k; renderPicker(); return; }
    const go = e.target.closest('[data-go]'); if (go) { choose(go.dataset.go, true); return; }
    const row = e.target.closest('.proj-row'); if (row) choose(row.dataset.id, false);
  });

  async function choose(id, present, page, quiet) {
    library();
    const it = items.find((x) => x.id === id); if (!it) return;
    try {
      const d = await deckFor(it);
      if (!d || !d.slides || !d.slides.length) throw new Error('这份是空的');
      S.item = it; S.deck = d; S.page = Math.min(page || 0, d.slides.length - 1);
      drop(quiet); save(); paintScreen(); closePicker(); if (!quiet) sfx('coin');
      if (present) openTalk(); else if (!quiet) toast(`《${d.title || it.title}》放上幕布了 · 点幕布开讲`);
    } catch (err) { toast('放不上去：' + (err.message || err)); }
  }

  /* ---------------- 开讲（大屏） ---------------- */
  // 念出来只用「登记过的音色」烤好的音频（tools/voices.json → js/voice-manifest.js，默认音色）。
  // 没烤过的页：只打字幕、不出声。绝不用浏览器自带的通用语音顶替。
  let typer = 0, timer = 0, vo = null;
  const VOICE = () => window.DESK_VOICE || { default: 'yuanzi', voices: {}, lines: {} };
  const voiceKey = () => (S.deck && S.deck.voice) || VOICE().default || 'yuanzi';
  const voiceName = () => ((VOICE().voices || {})[voiceKey()] || {}).name || '默认音色';
  function voiceFor(s, note) {
    if (s.voice) return s.voice;                                   // 幻灯里自带的（可走的世界那种）
    return ((VOICE().lines || {})[voiceKey()] || {})[note] || null;  // 这张桌子烤过的
  }
  function stopTalkTimers() { clearInterval(typer); clearTimeout(timer); if (vo) { vo.pause(); vo.removeAttribute('src'); vo = null; } }
  function showBig() {
    const s = S.deck.slides[S.page];
    $('#projTitle').textContent = S.deck.title || S.item.title;
    $('#projCount').textContent = `${S.page + 1} / ${S.deck.slides.length}${S.deck.speaker ? ' · ' + S.deck.speaker : ''}`;
    big.innerHTML = slideHTML(s, 'big');
    if (window.DESK_CHALK) { window.DESK_CHALK.fit(big); window.DESK_CHALK.write(big); document.fonts && document.fonts.ready.then(() => window.DESK_CHALK.fit(big)); }
    requestAnimationFrame(() => fit(big.parentElement, big));
    // 字幕：逐字打（照可走的世界讲台）
    stopTalkTimers();
    const note = s.note || s.title || '';
    const sub = $('#projSub'); let i = 0; sub.textContent = '';
    typer = setInterval(() => { i += 1; sub.textContent = note.slice(0, i); if (i >= note.length) clearInterval(typer); }, 45);
    const src = voiceFor(s, note);
    $('#projVoiceHint').textContent = S.voice && note && !src && s.kind !== 'music' && s.kind !== 'video' ? `这一页还没烤${voiceName()}的声音，只打字幕` : '';
    if (S.voice && src) { vo = new Audio(src); vo.play().catch(() => {}); }
    if (S.auto) runAuto(s, note, vo);
    paintScreen();
  }
  function runAuto(s, note, audio) {
    const next = () => { if (!S.auto) return; if (S.page < S.deck.slides.length - 1) { S.page += 1; save(); showBig(); } else { S.auto = false; paintAuto(); toast('讲完了 👏'); } };
    const media = big.querySelector('audio,video');
    if (media && (s.kind === 'music' || s.kind === 'video')) { media.addEventListener('ended', () => setTimeout(next, 600), { once: true }); return; }
    const wait = s.duration || Math.max(2600, Math.min(12000, note.length * 230));
    if (audio) {
      let done = false; const end = () => { if (done) return; done = true; timer = setTimeout(next, 650); };
      audio.addEventListener('ended', end, { once: true });
      audio.addEventListener('error', () => { timer = setTimeout(next, wait); }, { once: true });
      timer = setTimeout(end, wait + 15000);   // 兜底：音频没回 ended 也会翻页
    } else timer = setTimeout(next, wait);
  }
  function paintAuto() {
    $('#projAuto').textContent = S.auto ? '⏸ 停一下' : '▶ 一页页讲';
    $('#projVoice').textContent = S.voice ? `🔈 ${voiceName()}念：开` : `🔇 ${voiceName()}念：关`;
    stage.classList.toggle('proj-cinema', !talk.hidden);
  }
  function openTalk() {
    if (!S.deck) { openPicker(); return; }
    closePicker(); talk.hidden = false; showBig(); paintAuto(); sfx('open');
  }
  function closeTalk() { if (talk.hidden) return; S.auto = false; stopTalkTimers(); big.innerHTML = ''; talk.hidden = true; paintAuto(); paintScreen(); }
  function turn(d) { if (!S.deck) return; const n = S.deck.slides.length; S.page = Math.max(0, Math.min(n - 1, S.page + d)); save(); if (!talk.hidden) showBig(); else paintScreen(); }
  talk.addEventListener('click', (e) => {
    const b = e.target.closest('[data-tk]'); if (!b) return;
    const a = b.dataset.tk;
    if (a === 'close') closeTalk();
    else if (a === 'prev') turn(-1);
    else if (a === 'next') turn(1);
    else if (a === 'auto') { S.auto = !S.auto; paintAuto(); if (S.auto) showBig(); else stopTalkTimers(); }
    else if (a === 'voice') { S.voice = !S.voice; if (!S.voice && vo) vo.pause(); else if (S.voice) showBig(); paintAuto(); }
    else if (a === 'pick') { closeTalk(); openPicker(); }
    else if (a === 'stop') { closeTalk(); S.page = 0; save(); paintScreen(); toast('讲完了，幕布还摆着这一份'); }
  });
  // 讲的时候：←/→/空格翻页，Esc 收面板（不让桌面快捷键抢走这些键）
  window.addEventListener('keydown', (e) => {
    if (talk.hidden && picker.hidden) return;
    if (e.target && (e.target.tagName === 'INPUT' || e.target.isContentEditable)) return;
    if (e.key === 'Escape') { closePicker(); closeTalk(); e.stopImmediatePropagation(); return; }
    if (talk.hidden) return;
    if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') { turn(1); e.preventDefault(); e.stopImmediatePropagation(); }
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { turn(-1); e.preventDefault(); e.stopImmediatePropagation(); }
    else e.stopImmediatePropagation();
  }, true);

  /* ---------------- 场景里的点击 ---------------- */
  // 幕布下面那排小按钮、拉绳：自己处理，不冒泡到「点物件」
  screen.addEventListener('click', (e) => {
    const b = e.target.closest('[data-pc]'); if (!b) return;
    e.stopPropagation();
    const a = b.dataset.pc;
    if (a === 'up') rollUp();
    else if (a === 'prev') turn(-1);
    else if (a === 'next') turn(1);
    else if (a === 'talk') openTalk();
    else if (a === 'pick') openPicker();
  }, true);
  // 幕布本身：拉下来时盖住软木板，点它 = 点软木板
  screen.addEventListener('click', (e) => { if (e.target.closest('[data-pc]')) return; e.stopPropagation(); click(); });
  screen.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); click(); } });
  // 搁板上的小投影机：放下 / 收起幕布的唯一开关
  const rig = $('.proj-rig');
  const toggle = () => { if (S.down) rollUp(); else { drop(); setTimeout(() => (S.deck ? toast(`幕布放下了 · 还摆着《${S.deck.title || S.item.title}》`) : openPicker()), 520); } };
  rig.addEventListener('click', (e) => { e.stopPropagation(); toggle(); });
  rig.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });

  // 点幕布（幕布放下时）：没摆东西就选片，摆着就开讲。幕布收起时不走这里，软木板自己开面板
  function click() {
    if (!S.down) { toggle(); return; }
    if (!S.deck) { openPicker(); return; }
    openTalk();
  }

  window.addEventListener('resize', () => { fit(face.parentElement, face); if (!talk.hidden) fit(big.parentElement, big); aimBeam(); });

  /* ---------------- 进门：恢复上次的幕布；深链 ---------------- */
  const saved = load();
  const q = new URLSearchParams(location.search);
  const want = q.get('projector');
  (async () => {
    if (want && want !== '1') await choose(want, false);
    else if (saved.down || want === '1') {
      drop(true);
      if (saved.itemId) await choose(saved.itemId, false, saved.page || 0, true).catch(() => {});
      if (want === '1') openPicker();
    }
    if (q.get('present') === '1' && S.deck) openTalk();
    label();
  })();

  window.DESK_PROJECTOR = { click, toggle, drop, rollUp, openPicker, openTalk, choose, state: S };
})();
