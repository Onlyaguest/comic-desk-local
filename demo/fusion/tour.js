// 「带我逛一圈」：6 站高亮桌上的物件，每站一句话。只在样例模式出现入口；在线样例版首次打开自动开始。
// 纯前端，不联网、不写服务器；看没看过只记在浏览器 localStorage。
(() => {
  'use strict';
  const KEY = 'comicDesk.tour.v1';
  const REPO = 'https://github.com/Onlyaguest/comic-desk-local';
  const online = !!window.__COMIC_DESK_ONLINE__;
  const STEPS = [
    {sel: '[data-obj=board]', title: '事项板 · 四家 AI 收在一块板上',
      text: 'Claude Code、Codex、Cohub 的会话和空间事项，按「助手在做 / 等你拍板 / 看你的 / 卡住」排好。点板子能走近看，纸卡翻过来是协作证据。'},
    {sel: '[data-obj=notes]', title: '便签墙 · 今天盯哪几张',
      text: '把要盯的纸卡夹到这里（最多 12 张），只是关注，不改原事项的状态。'},
    {sel: '[data-obj=monitor]', title: '显示器 · 今天的会话待办',
      text: '每天的 AI 会话变成能勾的待办；勾掉以后那个会话又有新对话，它会自己回来。'},
    {sel: '[data-obj=poster]', title: '作品展台 · AI 做出来的东西',
      text: '图片和小页面都摆在桌上：点开看大图、翻图像册、同名作品比版本。'},
    {sel: '.tools a[href*="publish"]', title: '发稿台 · 从写好到发出去',
      text: '一篇稿排成 7 步：写稿 → 验收 → 我来改 → 外部改 → 挑这版 → 发出去 → 归档，两版能并排对比。'},
    {sel: null, title: online ? '这是在线样例' : '逛完了',
      text: online
        ? '桌上都是虚构数据，能点能看，勾选、写便签、接自己的会话要下载到本机：Mac 上装好 Python 3.11，双击 start.command。不联网、不花 token。'
        : '现在看到的是离线样例。想接自己的 Claude Code / Codex 会话，见 README 的「可选：接真实会话」。',
      last: true},
  ];
  const seen = () => { try { return !!localStorage.getItem(KEY); } catch { return true; } };
  const mark = () => { try { localStorage.setItem(KEY, String(Date.now())); } catch {} };
  let i = 0, ring, card;
  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

  function place() {
    const s = STEPS[i], el = s.sel && document.querySelector(s.sel);
    const r = el && el.getBoundingClientRect();
    const vis = r && r.width > 0 && r.height > 0;
    ring.hidden = !vis;
    if (vis) Object.assign(ring.style, {left: r.left - 8 + 'px', top: r.top - 8 + 'px', width: r.width + 16 + 'px', height: r.height + 16 + 'px'});
    // 卡片放在物件旁边：放得下就在下方，否则上方；没有物件就居中
    const W = Math.min(340, innerWidth - 32), H = card.offsetHeight || 180;
    let x = (innerWidth - W) / 2, y = (innerHeight - H) / 2;
    if (vis) {
      x = Math.max(16, Math.min(innerWidth - W - 16, r.left + r.width / 2 - W / 2));
      y = r.bottom + 18 + H < innerHeight ? r.bottom + 18 : Math.max(16, r.top - H - 18);
    }
    Object.assign(card.style, {left: x + 'px', top: y + 'px', width: W + 'px'});
  }
  function paint() {
    const s = STEPS[i];
    card.innerHTML = `<small>${i + 1} / ${STEPS.length}</small><h3>${esc(s.title)}</h3><p>${esc(s.text)}</p><div>`
      + (i ? '<button type="button" data-t="prev">上一站</button>' : '')
      + (s.last
        ? `<a href="${REPO}" target="_blank" rel="noopener">${online ? '去 GitHub 下载 · 点星' : '去 GitHub 看看'}</a><button type="button" data-t="end">自己逛</button>`
        : '<button type="button" data-t="next" class="go">下一站</button><button type="button" data-t="end">跳过</button>')
      + '</div>';
    place();
    card.querySelector('.go, [data-t=end]')?.focus();
  }
  function end() { mark(); ring?.remove(); card?.remove(); ring = card = null; removeEventListener('resize', place); document.removeEventListener('keydown', key); }
  function key(e) { if (e.key === 'Escape') end(); else if (e.key === 'ArrowRight' && !STEPS[i].last) { i++; paint(); } else if (e.key === 'ArrowLeft' && i) { i--; paint(); } }
  function start() {
    if (card) return;
    i = 0;
    ring = document.createElement('div'); ring.className = 'tour-ring';
    card = document.createElement('aside'); card.className = 'tour-card'; card.setAttribute('role', 'dialog'); card.setAttribute('aria-label', '带我逛一圈');
    card.addEventListener('click', e => {
      const t = e.target.closest('[data-t]')?.dataset.t;
      if (t === 'next') { i++; paint(); } else if (t === 'prev') { i--; paint(); } else if (t === 'end') end();
      if (e.target.closest('a')) end();
    });
    document.body.append(ring, card);
    addEventListener('resize', place); document.addEventListener('keydown', key);
    paint();
  }
  window.startDeskTour = start;
  // 入口：顶栏一个「带我逛一圈」按钮，只在样例模式出现
  async function isDemo() {
    if (online) return true;
    try { return !!(await (await fetch('./api/index/status')).json()).demo; } catch { return false; }
  }
  isDemo().then(demo => {
    if (!demo) return;
    const tools = document.querySelector('.fusion-tools');
    if (tools) {
      const b = document.createElement('button'); b.type = 'button'; b.id = 'deskTour'; b.textContent = '带我逛一圈';
      b.onclick = start; tools.append(b);
    }
    if (online && !seen()) setTimeout(start, 1200);
  });
})();
