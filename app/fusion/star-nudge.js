// 点星提示：用满几次后在右下角温和问一句，给一个 GitHub 链接。
// 只在这个浏览器的 localStorage 里计数；不联网、不上报、不统计，点不点都不影响任何功能。
(() => {
  'use strict';
  const KEY = 'comicDesk.starNudge.v1';
  const REPO = 'https://github.com/Onlyaguest/comic-desk-local';
  const USES = 5, DAYS = 2, GAP = 30 * 60e3, SNOOZE = 14 * 864e5;
  let s;
  try { s = JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return; }
  if (typeof s !== 'object' || s.off) return;
  const now = Date.now(), today = new Date().toISOString().slice(0, 10);
  // 半小时内反复刷新只算一次「用」
  if (!s.last || now - s.last > GAP) { s.uses = (s.uses || 0) + 1; s.last = now; }
  s.days = Array.from(new Set([...(Array.isArray(s.days) ? s.days : []), today])).slice(-10);
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch {} };
  save();
  if (s.uses < USES || s.days.length < DAYS || (s.snooze && now < s.snooze)) return;

  const box = document.createElement('aside');
  box.className = 'star-nudge';
  box.setAttribute('role', 'note');
  box.innerHTML = '<p><b>用得还顺手？</b>去 GitHub 给它点个星 ⭐，能让同样被一堆 AI 会话淹没的人找到它。</p>'
    + '<div><a href="' + REPO + '" target="_blank" rel="noopener">去点星</a>'
    + '<button type="button" data-k="later">以后再说</button>'
    + '<button type="button" data-k="off">别再提示</button></div>';
  const close = patch => { Object.assign(s, patch); save(); box.remove(); };
  box.querySelector('a').addEventListener('click', () => close({off: true, starredAt: now}));
  box.querySelector('[data-k=later]').onclick = () => close({snooze: now + SNOOZE});
  box.querySelector('[data-k=off]').onclick = () => close({off: true});
  setTimeout(() => document.body.append(box), 4000);
})();
