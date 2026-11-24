/* =====================================================================
 *  相机 →「每日总结」tab：跑 session-activity-digest，显示今天的 md
 *  ---------------------------------------------------------------------
 *  按钮 → App Action「daily-digest」{op:'run'}：备候选包 → 投给固定载体对话跑 skill → md 写到
 *         session-notes/reality-sensemaking/reviews/session-activity-digest-YYYY-MM-DD.md（同日覆盖 = Refresh）
 *  进度 → 反复调 {op:'status', wait:60}：Action 在沙箱里最多等 60s，跑完就把 md 带回来。
 *  首屏 → js/digest.js 快照（Action 跑完时写），再用 localStorage 里最近一次拿到的结果兜底。
 *  只按钮触发，不定时、不写手账。
 * ===================================================================== */
(function () {
  'use strict';
  const K = 'yz_desk_digest_v1';
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const today = () => { const d = new Date(Date.now() + 8 * 3600e3); return d.toISOString().slice(0, 10); };   // CST 日期
  const load = () => { try { return JSON.parse(localStorage.getItem(K) || 'null'); } catch (e) { return null; } };
  const keep = (v) => { try { localStorage.setItem(K, JSON.stringify(v)); } catch (e) {} };

  async function action(input, maxMs) {
    return window.localAction('daily-digest', input);
  }

  /* ---- 极简 md → html：标题、按缩进嵌套的列表、粗体、行内代码、链接（空链接按纯文本） ---- */
  function inline(s) {
    let t = esc(s);
    t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
    t = t.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
    t = t.replace(/\[([^\]]+)\]\(([^)\s]*)\)/g, (m, a, u) => (/^https?:\/\//.test(u) ? `<a href="${u}" target="_blank" rel="noopener">${a}</a>` : `<span class="dg-nolink">${a}</span>`));
    t = t.replace(/(^|\s)#([^\s#<]{1,20})/g, '$1<span class="dg-tag">#$2</span>');
    return t;
  }
  function md2html(md) {
    const lines = String(md || '').replace(/\r/g, '').split('\n');
    let html = '', depth = 0;
    // 缩进单位按文中实际最小缩进算：skill 默认 4 空格，审批版（Roam 形状）是 2 空格
    const ind = lines.map((l) => /^(\s+)[-*] /.exec(l)).filter(Boolean).map((m) => m[1].replace(/\t/g, '    ').length);
    const unit = ind.length ? Math.max(1, Math.min(4, Math.min(...ind))) : 4;
    const close = (to) => { while (depth > to) { html += '</li></ul>'; depth--; } };
    for (const raw of lines) {
      const li = /^(\s*)[-*] (.*)$/.exec(raw);
      if (li) {
        const lvl = Math.floor(li[1].replace(/\t/g, '    ').length / unit) + 1;
        if (lvl > depth) { while (depth < lvl) { html += '<ul>'; depth++; if (depth < lvl) html += '<li>'; } }
        else { close(lvl); html += '</li>'; }
        html += '<li>' + inline(li[2]);
        continue;
      }
      close(0);
      const h = /^(#{1,4}) (.*)$/.exec(raw);
      if (h) html += `<h${h[1].length + 2}>${inline(h[2])}</h${h[1].length + 2}>`;
      else if (/^\s*>/.test(raw)) html += '<blockquote>' + inline(raw.replace(/^\s*>\s?/, '')) + '</blockquote>';
      else if (raw.trim()) html += '<p>' + inline(raw) + '</p>';
    }
    close(0);
    return html;
  }

  function open(body, opt) {
    let st = null, alive = true, busy = false;
    opt.cleanup.push(() => { alive = false; });
    const snap = window.DESK_DIGEST, cached = load();
    const pick = [snap, cached].filter((x) => x && x.md && x.date === today()).sort((a, b) => String(b.finishedAt || '').localeCompare(String(a.finishedAt || '')))[0];
    st = pick ? { state: 'done', ...pick } : { state: 'idle', date: today() };
    // 固定版本（js/digest-versions.js，tools/digest-versions.py 生成的脱敏页面副本）：默认看第一份 = 已审批版
    const VERS = window.DESK_DIGEST_VERSIONS || [];
    let view = VERS.length ? VERS[0].id : 'live';

    const badge = () => {
      if (st.state === 'running') return `<span class="dg-st run">生成中 · ${esc((st.startedAt || '').slice(11, 16))} 开始</span>`;
      if (st.state === 'failed') return `<span class="dg-st bad">这次没成：${esc(st.error || '未知原因')}</span>`;
      if (st.state === 'done' && st.md) return `<span class="dg-st ok">今天的总结 · ${esc((st.finishedAt || '').slice(11, 16))} 生成</span>`;
      return '<span class="dg-st">今天还没生成</span>';
    };
    const facts = () => {
      const c = st.check, out = [];
      if (st.codex) out.push(st.codex === 'delivered' ? 'Codex 已送达并合并' : 'Codex 未送达（只含 Cohub，partial）');
      if (c) out.push(`${c.entries} 条活动 · ${c.sorted ? '时间已升序' : '⚠ 时间未升序'} · ${c.entriesMissingFields ? '⚠ ' + c.entriesMissingFields + ' 条缺字段' : '字段齐全'}`);
      if (st.path) out.push(`文件：<code>${esc(st.path)}</code>`);
      return out.length ? `<p class="muted dg-facts">${out.join('　·　')}</p>` : '';
    };
    const ver = () => VERS.find((v) => v.id === view);
    const paint = (note) => {
      body.innerHTML = `
        ${opt.tabs('digest')}
        <h2>每日总结</h2>
        <p class="muted">把今天 00:00 到现在你在各个 Session 里真实跑过的事压成一条时间线（session-activity-digest）。点按钮生成；同一天再点是刷新，覆盖同一个 md。Codex 那边送进收件箱的内容会一起合并。</p>
        <div class="dg-bar">${badge()}<button class="btn" id="dgRun" ${st.state === 'running' || busy ? 'disabled' : ''}>${st.state === 'running' ? '⏳ 生成中…' : st.md ? '↻ 刷新今天的总结' : '✦ 生成今天的总结'}</button></div>
        ${note ? `<p class="dg-note">${esc(note)}</p>` : ''}
        ${VERS.length ? `<div class="dg-vers">${VERS.map((v) => `<button class="dg-ver ${v.kind} ${v.id === view ? 'on' : ''}" data-v="${esc(v.id)}">${v.kind === 'approved' ? '✔ ' : ''}${esc(v.label)} · ${esc(v.date.slice(5))}</button>`).join('')}<button class="dg-ver ${view === 'live' ? 'on' : ''}" data-v="live">今天 · ${st.md ? '按钮生成版' : '还没生成'}</button></div>` : ''}
        ${ver() ? `<p class="dg-vhead">${ver().kind === 'approved' ? '<span class="dg-st ok dg-appr">已审批 · Full</span>' : '<span class="dg-st">partial</span>'} <b>${esc(ver().date)} · ${esc(ver().window)} CST</b> · ${ver().entries} 条活动</p>
          <p class="muted dg-facts">${esc(ver().note)}<br>${esc(ver().diff)}<br>原文：<code>${esc(ver().path)}</code></p>
          <div class="dg-md">${md2html(ver().md)}</div>`
        : `${facts()}
        <div class="dg-md">${st.md ? md2html(st.md) : '<p class="muted">还没有内容。</p>'}</div>`}` + opt.footer;
      opt.wireTabs();
      body.querySelectorAll('.dg-ver').forEach((x) => x.addEventListener('click', () => { view = x.dataset.v; paint(); }));
      const b = body.querySelector('#dgRun');
      if (b) b.addEventListener('click', run);
    };
    const absorb = (r) => {
      if (!r) return;
      st = { ...st, ...r, md: r.md || (r.state === 'running' ? st.md : r.md) || st.md };
      if (st.state === 'done' && st.md) keep({ date: st.date, md: st.md, finishedAt: st.finishedAt, path: st.path, codex: st.codex, check: st.check });
    };
    async function poll() {
      const t0 = Date.now();
      while (alive && st.state === 'running' && Date.now() - t0 < 25 * 60e3) {
        try { absorb(await action({ op: 'status', wait: 60 }, 150e3)); }
        catch (e) { if (alive) paint('查进度出错，稍后自动再查：' + e.message); await new Promise((r) => setTimeout(r, 15e3)); continue; }
        if (!alive) return;
        paint(st.state === 'running' ? `还在跑（已 ${Math.round((Date.now() - t0) / 60e3)} 分钟），一般 3–10 分钟。可以关掉面板，回来再看。` : '');
        if (st.state === 'done') opt.toast('📝 今天的总结好了');
      }
    }
    async function run() {
      busy = true; view = 'live'; paint('已发出，正在备今天的候选 Session…');
      try {
        const r = await action({ op: 'run' }, 240e3);
        busy = false;
        if (!r.ok) { st = { ...st, state: 'failed', error: r.error }; paint(); return; }
        absorb(r); paint('已交给总结对话，正在按 skill 逐条核证据…');
        poll();
      } catch (e) { busy = false; paint(e.offline ? e.message : '没发出去：' + e.message); }
    }
    paint();
    // 打开时悄悄对一下最新状态（离线打开就只看快照）
    action({ op: 'status', wait: 0 }, 60e3).then((r) => { if (!alive) return; if (r && (r.md || r.state === 'running' || r.state === 'failed')) { absorb(r); paint(); } if (st.state === 'running') poll(); }).catch(() => {});
  }

  window.DeskDigest = { open, md2html };
})();
