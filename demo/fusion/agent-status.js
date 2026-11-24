// AI 自己报状态：顶栏小标。开页和点「更新会话索引」时各读一次本机账本；不轮询、不弹通知、不出声。
(() => {
  'use strict';
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const who = {claude: 'Claude Code', codex: 'Codex'};
  const ago = at => { const m = Math.max(0, Math.round((Date.now() - at) / 60000)); return m < 1 ? '刚刚' : m < 60 ? m + ' 分钟前' : Math.round(m / 60) + ' 小时前'; };
  const tools = document.querySelector('.fusion-tools');
  if (!tools) return;
  const wrap = document.createElement('div'); wrap.className = 'agent-status'; wrap.hidden = true;
  wrap.innerHTML = '<button type="button" aria-expanded="false" aria-controls="agentStatusList"></button><ul id="agentStatusList" hidden></ul>';
  tools.prepend(wrap);
  const btn = wrap.querySelector('button'), list = wrap.querySelector('ul');
  const close = () => { list.hidden = true; btn.setAttribute('aria-expanded', 'false'); };
  btn.onclick = () => { const open = list.hidden; list.hidden = !open; btn.setAttribute('aria-expanded', String(open)); };
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
  async function load() {
    let d;
    try { const r = await fetch('./api/desk/agent-status', {cache: 'no-store'}); d = await r.json(); } catch { return; }
    const shown = (d.items || []).filter(x => x.state === 'waiting' || x.state === 'error');
    wrap.hidden = !shown.length;
    if (!shown.length) { close(); return; }
    const c = d.counts || {};
    btn.textContent = [c.waiting ? '等你 ' + c.waiting : '', c.error ? '出错 ' + c.error : ''].filter(Boolean).join(' · ');
    btn.title = 'Claude Code / Codex 自己报的状态（开页时读取）';
    btn.classList.toggle('has-error', !!c.error);
    list.innerHTML = shown.map(x => `<li class="${esc(x.state)}"><b>${esc(x.label)}</b> ${esc(who[x.agent] || x.agent)} · ${esc(x.project)}<small>${esc(x.detail)}${x.detail ? ' · ' : ''}${esc(ago(x.at))}</small></li>`).join('')
      + '<li class="go"><button type="button">走近看板看全部 →</button></li>';
    list.querySelector('.go button').onclick = () => { close(); document.getElementById('nearBoard')?.click(); };
  }
  document.addEventListener('click', e => { if (e.target.closest('#refreshIndex')) setTimeout(load, 1500); });
  load();
})();
