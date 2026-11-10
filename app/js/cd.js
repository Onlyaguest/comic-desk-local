/* =====================================================================
 *  CD 机 · 多碟播放器（常驻）
 *  碟：每日一首（js/daily-songs.js）· 本地歌单（data.js music）·
 *      角色歌工坊 · Cheng · 歌单（js/music-lib.js）
 *
 *  播放器是全局唯一的：关掉 CD 面板、打开别的面板都不会停。
 *  桌面左下角有一个迷你播放条（暂停 / 下一首 / 停止 / 点歌名回到 CD 面板）。
 *
 *  window.DESK_CD.panel({ $, $$, esc, toast, stage, D, cleanup }) → { html, wire, wide }
 *  window.DESK_CD.isPlaying() → 是否正在播（app.js 用它保持 CD 转盘 / 音响律动）
 *  播放状态（当前碟、当前曲、随机）存在 localStorage：yz_desk_cd_v1
 * ===================================================================== */
(function () {
  'use strict';
  const KEY = 'yz_desk_cd_v1';
  const PAGE = 40;
  const esc = (v) => String(v == null ? '' : v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = (s) => { s = Math.max(0, s | 0); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
  const byId = (id) => document.getElementById(id);

  /* ---------------- 碟片 ---------------- */
  let DISCS = null;
  function discs() {
    if (DISCS) return DISCS;
    const D = window.DESK_DATA || { music: {} };
    const L = window.DESK_MUSIC_LIB || {};
    const daily = (window.DESK_DAILY_SONGS || []).map((s) => ({
      title: s.old ? `${s.title}（旧版）` : s.title, tag: `${s.date.slice(5)}${s.old ? ' · 旧版' : ''} · ${s.mood || ''}`, file: s.file, old: !!s.old,
      dur: s.seconds ? fmt(s.seconds) : '', lyrics: s.lyrics, style: s.style, date: s.date,
    }));
    DISCS = [
      { id: 'daily', icon: '📅', title: '每日一首', sub: '每天根据前一天的日结自动写一首（song2）', tracks: daily, color: '#ff5fa2', empty: '还没有歌。日结出来后会自动生成。' },
      { id: 'mine', icon: '💿', title: (D.music.album || {}).title || '本地歌单', sub: (D.music.album || {}).sub || '', tracks: (D.music.songs || []).map((s) => ({ ...s })), color: '#ffb020' },
    ];
    if (L.studio) DISCS.push({ id: 'studio', icon: '🎤', title: L.studio.title, sub: L.studio.sub, tracks: L.studio.tracks, page: L.studio.page, color: '#7c4dff' });
    if (L.cheng) DISCS.push({ id: 'cheng', icon: '🎧', title: L.cheng.title, sub: L.cheng.sub, tracks: L.cheng.tracks, page: L.cheng.page, color: '#14b8a6', groupBy: 'album' });
    return DISCS;
  }

  /* ---------------- 全局播放器（只建一次） ---------------- */
  const st = (() => { try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { return {}; } })();
  const save = (o) => { Object.assign(st, o); try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {} };
  const P = { au: null, disc: null, cur: -1, shuffle: !!st.shuffle, toast: () => {}, openPanel: null };

  function audio() {
    if (P.au) return P.au;
    const au = P.au = new Audio();
    au.preload = 'metadata';
    au.addEventListener('timeupdate', ui);
    au.addEventListener('loadedmetadata', ui);
    au.addEventListener('play', ui);
    au.addEventListener('pause', ui);
    au.addEventListener('ended', () => next(1));
    au.addEventListener('error', () => {
      if (P.cur >= 0 && au.getAttribute('src')) { P.toast('这首加载失败，跳到下一首'); setTimeout(() => next(1), 600); }
    });
    return au;
  }
  const track = () => (P.disc && P.cur >= 0 ? P.disc.tracks[P.cur] : null);
  // 每日一首：最新那首还没打开听过 → 算新歌（记在 st.heardDaily）
  const newestDaily = () => ((window.DESK_DAILY_SONGS || [])[0] || null);
  const dkey = (n) => (n ? `${n.date}|${n.title}` : '');   // 同一天重做也算新歌
  const hasNewDaily = () => { const n = newestDaily(); return !!(n && dkey(n) !== st.heardDaily); };
  const isPlaying = () => !!(P.au && !P.au.paused && !P.au.ended && P.au.getAttribute('src'));

  function load(disc, i, autoplay) {
    if (!disc || !disc.tracks.length) return;
    const au = audio();
    P.disc = disc;
    P.cur = (i + disc.tracks.length) % disc.tracks.length;
    au.src = track().file || track().src;
    save({ disc: disc.id, track: P.cur });
    if (disc.id === 'daily' && track().date && !track().old && newestDaily() && track().date === newestDaily().date) { save({ heardDaily: dkey(newestDaily()) }); badge(); }
    if (autoplay) play();
    ui(true);
  }
  function play() { if (P.au && P.au.getAttribute('src')) P.au.play().catch(() => {}); }
  function pause() { if (P.au) P.au.pause(); }
  function toggle() { if (!track()) { const d = discs().find((x) => x.tracks.length); load(d, 0, true); } else if (P.au.paused) play(); else pause(); }
  function next(d) {
    if (!P.disc || !P.disc.tracks.length) return;
    load(P.disc, P.shuffle ? Math.floor(Math.random() * P.disc.tracks.length) : P.cur + d, true);
  }
  function stop() {
    if (!P.au) return;
    P.au.pause(); P.au.removeAttribute('src'); P.au.load();
    P.cur = -1;
    ui(true);
  }

  /* ---------------- 迷你播放条（桌面左下，关掉面板也在） ---------------- */
  function mini() {
    let el = byId('cdMini');
    if (el) return el;
    el = document.createElement('div');
    el.id = 'cdMini';
    el.className = 'cd-mini';
    el.hidden = true;
    el.innerHTML = `<span class="cd-mini-disc"></span>
      <button class="cd-mini-title" data-act="open" title="打开 CD 机"><b id="cdMiniTitle"></b><small id="cdMiniSub"></small></button>
      <button data-act="toggle" id="cdMiniPlay" aria-label="播放/暂停">⏸</button>
      <button data-act="next" aria-label="下一首">⏭</button>
      <button data-act="stop" aria-label="停止" title="停止">■</button>
      <i class="cd-mini-bar"><i id="cdMiniBar"></i></i>`;
    el.addEventListener('click', (e) => {
      const b = e.target.closest('[data-act]'); if (!b) return;
      const a = b.dataset.act;
      if (a === 'toggle') toggle();
      else if (a === 'next') next(1);
      else if (a === 'stop') stop();
      else if (a === 'open' && P.openPanel) P.openPanel();
    });
    document.body.appendChild(el);
    return el;
  }

  /* ---------------- 同步所有界面 ---------------- */
  function ui(full) {
    const t = track(), au = P.au, playing = isPlaying();
    const stage = byId('stage');
    if (stage) stage.classList.toggle('playing', playing);

    // 迷你条：有歌就显示；CD 面板开着时藏起来
    const m = mini();
    const panelOpen = !!byId('cdDiscs') && !byId('modal').hidden;
    m.hidden = !t || panelOpen;
    if (t) {
      byId('cdMiniTitle').textContent = t.title;
      byId('cdMiniSub').textContent = (P.disc ? P.disc.title : '') + (au && au.duration ? ' · ' + fmt(au.currentTime) + ' / ' + fmt(au.duration) : '');
      byId('cdMiniPlay').textContent = playing ? '⏸' : '▶';
      byId('cdMiniBar').style.width = au && au.duration ? (au.currentTime / au.duration * 100) + '%' : '0%';
      m.classList.toggle('paused', !playing);
    }

    // CD 面板（开着才更新）
    if (!byId('mp3Now')) return;
    byId('mp3Play').textContent = playing ? '⏸' : '▶';
    byId('mp3Bar').style.width = au && au.duration ? (au.currentTime / au.duration * 100) + '%' : '0%';
    byId('mp3Cur').textContent = fmt(au ? au.currentTime : 0);
    if (au && au.duration) byId('mp3Dur').textContent = fmt(au.duration);
    if (!full) return;
    byId('mp3Now').textContent = t ? t.title : '点一首开始';
    byId('mp3Sub').textContent = t ? (t.tag || '') + (P.disc && P.panelDisc && P.disc.id !== P.panelDisc.id ? ` · 正在播：${P.disc.title}` : '') : '';
    if (!(au && au.duration)) byId('mp3Dur').textContent = t && t.dur ? t.dur : '0:00';
    const sameDisc = P.panelDisc && P.disc && P.panelDisc.id === P.disc.id;
    document.querySelectorAll('#mp3List .track').forEach((el) => el.classList.toggle('on', sameDisc && +el.dataset.i === P.cur));
    byId('mp3Lyr').hidden = !(t && t.lyrics);
    const box = byId('cdLyrics');
    if (t && t.lyrics) box.innerHTML = `<div class="muted">${esc(t.style || '')}</div><pre>${esc(t.lyrics)}</pre>`;
    else box.hidden = true;
  }

  /* ---------------- 面板 ---------------- */
  function panel(ctx) {
    const { $, $$, toast, cleanup } = ctx;
    P.toast = toast;
    P.openPanel = () => { const o = document.querySelector('.obj[data-obj="cd"]'); if (o) o.click(); };
    const list = discs();
    // 面板显示的碟：正在播的那张 → 上次那张 → 第一张有歌的
    const fresh = !P.disc && hasNewDaily();
    let disc = fresh ? list[0] : (P.disc || list.find((d) => d.id === st.disc && d.tracks.length) || list.find((d) => d.tracks.length) || list[0]);
    P.panelDisc = disc;
    const cover = ((window.DESK_DATA || {}).music || {}).album ? window.DESK_DATA.music.album.cover : '';

    const html = `
      <span class="kicker">CD PLAYER · 四张碟 · 关掉面板也会继续放</span>
      <h2 id="cdTitle">${esc(disc.title)} ♪</h2>
      <div class="cd-discs" id="cdDiscs">
        ${list.map((d) => `<button class="cd-disc-btn ${d.id === disc.id ? 'on' : ''}" data-disc="${esc(d.id)}" style="--c:${esc(d.color)}">
          <span>${esc(d.icon)}</span><b>${esc(d.title)}</b><small>${d.tracks.length} 首${d.id === 'daily' && d.tracks[0] ? ' · 最新 ' + esc(d.tracks[0].date.slice(5)) : ''}</small>${d.id === 'daily' && hasNewDaily() ? '<i class="cd-new">NEW</i>' : ''}</button>`).join('')}
      </div>
      <p class="muted" id="cdSub"></p>
      <div class="mp3">
        <div class="mp3-cover" style="background-image:url('${esc(cover)}')"><div class="mp3-disc"></div></div>
        <div class="mp3-info">
          <div class="mp3-now" id="mp3Now">点一首开始</div>
          <div class="mp3-sub" id="mp3Sub"></div>
          <div class="mp3-bar" id="mp3Seek" title="点一下跳到这里"><i id="mp3Bar"></i></div>
          <div class="mp3-times"><span id="mp3Cur">0:00</span><span id="mp3Dur">0:00</span></div>
          <div class="mp3-ctrl">
            <button class="mp3btn" id="mp3Prev" aria-label="上一首">⏮</button>
            <button class="mp3btn big" id="mp3Play" aria-label="播放/暂停">▶</button>
            <button class="mp3btn" id="mp3Next" aria-label="下一首">⏭</button>
            <button class="mp3btn" id="mp3Shuf" aria-label="随机" title="随机播放">🔀</button>
            <button class="mp3btn" id="mp3Stop" aria-label="停止" title="停止">■</button>
            <button class="mp3btn" id="mp3Lyr" aria-label="歌词" title="歌词" hidden>📝</button>
          </div>
        </div>
      </div>
      <div class="cd-lyrics" id="cdLyrics" hidden></div>
      <div class="cd-tools"><input id="cdFind" placeholder="搜曲名 / 角色 / 风格…" maxlength="40"><span class="muted" id="cdCount"></span></div>
      <div class="tracks" id="mp3List"></div>
      <div class="cd-foot" id="cdFoot"></div>`;

    const wire = () => {
      let view = [], shown = 0;
      function filter() {
        const q = ($('#cdFind').value || '').trim().toLowerCase();
        view = disc.tracks.map((t, i) => ({ t, i })).filter(({ t }) => !q || [t.title, t.tag, t.who, t.album, t.style].join(' ').toLowerCase().includes(q));
        shown = 0; $('#mp3List').innerHTML = ''; more();
        $('#cdCount').textContent = q ? `${view.length} / ${disc.tracks.length}` : `${disc.tracks.length} 首`;
        if (!disc.tracks.length) $('#mp3List').innerHTML = `<p class="muted">${esc(disc.empty || '这张碟还是空的。')}</p>`;
      }
      function row({ t, i }) {
        const on = P.disc && P.disc.id === disc.id && i === P.cur;
        const ext = t.suno ? `<a class="trk-ext" href="${esc(t.suno)}" target="_blank" rel="noopener" title="在 Suno 打开">↗</a>` : '';
        return `<div class="track ${on ? 'on' : ''}" data-i="${i}">
          <span class="no">${String(i + 1).padStart(2, '0')}</span><span class="tt">${esc(t.title)}</span>
          <span class="ar">${esc(t.tag || '')}${t.dur ? ' · ' + esc(t.dur) : ''}</span>${ext}</div>`;
      }
      function more() {
        const box = $('#mp3List'); let h = '', lastGroup = shown ? view[shown - 1].t[disc.groupBy] : null;
        view.slice(shown, shown + PAGE).forEach((v) => {
          if (disc.groupBy && v.t[disc.groupBy] !== lastGroup) { lastGroup = v.t[disc.groupBy]; h += `<div class="trk-group">${esc(lastGroup)}</div>`; }
          h += row(v);
        });
        box.insertAdjacentHTML('beforeend', h);
        shown = Math.min(view.length, shown + PAGE);
        $('#cdFoot').innerHTML = (shown < view.length ? `<button class="btn ghost" id="cdMore">再显示 ${Math.min(PAGE, view.length - shown)} 首（共 ${view.length}）</button>` : '')
          + (disc.page ? `<a class="btn ghost" style="text-decoration:none" href="${esc(disc.page)}" target="_blank" rel="noopener">打开原页面 ↗</a>` : '');
        const mb = $('#cdMore'); if (mb) mb.addEventListener('click', more);
      }
      function showDisc(id) {
        disc = list.find((d) => d.id === id) || disc;
        P.panelDisc = disc;
        $$('.cd-disc-btn').forEach((b) => b.classList.toggle('on', b.dataset.disc === disc.id));
        $('#cdTitle').textContent = disc.title + ' ♪';
        $('#cdSub').textContent = disc.sub || '';
        $('#cdFind').value = '';
        filter();
        ui(true);
      }

      $('#mp3Play').addEventListener('click', () => { if (!track()) load(disc, 0, true); else toggle(); });
      $('#mp3Next').addEventListener('click', () => next(1));
      $('#mp3Prev').addEventListener('click', () => next(-1));
      $('#mp3Stop').addEventListener('click', stop);
      $('#mp3Shuf').classList.toggle('on', P.shuffle);
      $('#mp3Shuf').addEventListener('click', (e) => { P.shuffle = !P.shuffle; e.currentTarget.classList.toggle('on', P.shuffle); save({ shuffle: P.shuffle }); toast(P.shuffle ? '🔀 随机播放' : '顺序播放'); });
      $('#mp3Lyr').addEventListener('click', () => { const b = $('#cdLyrics'); b.hidden = !b.hidden; });
      $('#mp3Seek').addEventListener('click', (e) => { const r = e.currentTarget.getBoundingClientRect(); if (P.au && P.au.duration) P.au.currentTime = (e.clientX - r.left) / r.width * P.au.duration; });
      $('#mp3List').addEventListener('click', (e) => { if (e.target.closest('a')) return; const r = e.target.closest('.track'); if (r) load(disc, +r.dataset.i, true); });
      $('#cdDiscs').addEventListener('click', (e) => { const b = e.target.closest('[data-disc]'); if (b && b.dataset.disc !== disc.id) showDisc(b.dataset.disc); });
      $('#cdFind').addEventListener('input', filter);
      $('#cdFind').addEventListener('keydown', (e) => e.stopPropagation());

      showDisc(disc.id);
      // 第一次点 CD 机：直接开始放（点击本身就是用户手势）；已经在放就只同步界面，不重头放
      if (!track() && disc.tracks.length) {
        const start = !fresh && disc.id === st.disc && Number.isInteger(st.track) && st.track < disc.tracks.length ? st.track : 0;
        if (fresh) toast(`🎵 新的一首：${disc.tracks[0].title}（${disc.tracks[0].tag.split(' · ')[0]}）`);
        load(disc, start, true);
      }
      ui(true);
      // 关面板：不停歌，只把迷你播放条亮出来
      cleanup.push(() => { P.panelDisc = null; setTimeout(() => ui(true), 0); });
    };
    return { html, wire, wide: true };
  }

  function badge() {
    const o = document.querySelector('.obj[data-obj="cd"]'); if (!o) return;
    let b = o.querySelector('.cd-new-badge');
    if (hasNewDaily()) {
      if (!b) { b = document.createElement('i'); b.className = 'cd-new-badge'; o.appendChild(b); }
      b.textContent = '新歌 ' + newestDaily().date.slice(5);
    } else if (b) b.remove();
    document.querySelectorAll('.cd-disc-btn[data-disc="daily"] .cd-new').forEach((e) => { if (!hasNewDaily()) e.remove(); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', badge); else setTimeout(badge, 0);

  window.DESK_CD = { panel, isPlaying, toggle, next, stop };
})();
