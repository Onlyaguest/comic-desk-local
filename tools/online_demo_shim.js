// 在线样例版垫片（由 tools/build_online_demo.py 写进 demo/_demo/shim.js）。
// 页面原本请求本机服务的接口；这里把请求对到录好的静态文件上。只能看：改动类操作给一句提示。
// 不联网到别处、不上报，只读同目录下的文件。
(() => {
  'use strict';
  const ROUTES = /*@@ROUTES@@*/{};
  const BASE = new URL('../', document.currentScript.src).href;
  const BASE_PATH = new URL(BASE).pathname;
  const READONLY = '在线样例只能看：这一步要下载到本机才能用（不联网、不花 token）。';
  window.__COMIC_DESK_ONLINE__ = true;

  const sortObj = v => Array.isArray(v) ? v.map(sortObj)
    : v && typeof v === 'object' ? Object.keys(v).sort().reduce((o, k) => (o[k] = sortObj(v[k]), o), {}) : v;
  // 把任意地址换成「相对站点根」的接口键；不是接口就返回 null
  function rel(u) {
    let url;
    try { url = new URL(u, location.href); } catch { return null; }
    if (url.origin !== location.origin) return null;
    let p = url.pathname;
    if (p.startsWith(BASE_PATH)) p = p.slice(BASE_PATH.length); else p = p.replace(/^\//, '');
    if (!p.startsWith('api/')) return null;
    const q = [...url.searchParams].sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0);
    return {path: p, q};
  }
  const pyQuote = s => encodeURIComponent(s).replace(/%20/g, '+').replace(/[!'()*]/g, c => '%' + c.charCodeAt(0).toString(16).toUpperCase());
  const keyOf = r => r.path + (r.q.length ? '?' + r.q.map(([k, v]) => pyQuote(k) + '=' + pyQuote(v)).join('&') : '');
  function lookup(method, r, body) {
    if (method === 'POST') return ROUTES['POST ' + r.path + ' ' + body];
    const exact = ROUTES['GET ' + keyOf(r)];
    if (exact) return exact;
    // 只留决定内容的参数再找一次（图片的 v=、分页外的筛选等）
    const keep = r.q.filter(([k]) => ['id', 'mode', 'receipt', 'index', 'p', 'days'].includes(k));
    const slim = ROUTES['GET ' + keyOf({path: r.path, q: keep})];
    if (slim) return slim;
    if (keep.some(([k]) => k === 'id' || k === 'p')) return null;
    const any = Object.keys(ROUTES).find(k => k.startsWith('GET ' + r.path + '?') || k === 'GET ' + r.path);
    return any && ROUTES[any];
  }
  const fileUrl = hit => hit.go ? hit.go.replace('@@BASE@@', BASE) : BASE + hit.f;

  let toastTimer;
  function toast(msg) {
    let t = document.getElementById('demoOnlineToast');
    if (!t) {
      t = document.createElement('div'); t.id = 'demoOnlineToast'; t.setAttribute('role', 'status');
      t.style.cssText = 'position:fixed;left:50%;top:16px;transform:translateX(-50%);z-index:10000;max-width:min(92vw,440px);background:#282015;color:#fff5d9;padding:10px 16px;border-radius:8px;font:14px/1.5 -apple-system,"PingFang SC",sans-serif;box-shadow:3px 4px 0 #a9422d';
      (document.body || document.documentElement).append(t);
    }
    t.textContent = msg; t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 3200);
  }
  const json = (obj, status = 200) => new Response(JSON.stringify(obj), {status, headers: {'content-type': 'application/json'}});

  const realFetch = window.fetch.bind(window);
  window.fetch = async function (input, init = {}) {
    const url = typeof input === 'string' ? input : input && input.url;
    const r = rel(url);
    if (!r) return realFetch(input, init);
    const method = String(init.method || (input && input.method) || 'GET').toUpperCase();
    let body = '';
    if (method === 'POST') {
      try { body = JSON.stringify(sortObj(JSON.parse(init.body || '{}'))); } catch { body = String(init.body || ''); }
    }
    const hit = lookup(method, r, body);
    if (!hit) {
      if (method !== 'GET') toast(READONLY);
      return json({ok: false, error: READONLY, demoOnline: true}, method === 'GET' ? 404 : 409);
    }
    if (hit.go) return json({ok: true, url: fileUrl(hit)});
    const res = await realFetch(fileUrl(hit));
    let data = await res.text();
    if (hit.t === 'application/json') data = data.split('@@BASE@@').join(BASE);
    return new Response(data, {status: hit.s || 200, headers: {'content-type': hit.t}});
  };

  // <img src> / <a href> 直接指向接口的（代码里拼的图片地址），换成录好的文件
  function fix(el) {
    for (const attr of ['src', 'href']) {
      const v = el.getAttribute && el.getAttribute(attr);
      if (!v || v.indexOf('api/') < 0) continue;
      const r = rel(v);
      const hit = r && lookup('GET', r, '');
      if (hit) el.setAttribute(attr, fileUrl(hit));
    }
  }
  const scan = root => { if (root.querySelectorAll) { fix(root); root.querySelectorAll('img[src*="api/"],a[href*="api/"]').forEach(fix); } };
  new MutationObserver(list => {
    for (const m of list) {
      if (m.type === 'attributes') fix(m.target); else m.addedNodes.forEach(scan);
    }
  }).observe(document.documentElement, {subtree: true, childList: true, attributes: true, attributeFilter: ['src', 'href']});
  document.addEventListener('DOMContentLoaded', () => scan(document.body));

  // 在线版的提示条：替换本机版「离线样例」条的那一句
  const hide = document.createElement('style');
  hide.textContent = '.desk-demo-banner{display:none!important}';  // 本机版的「模拟一条新对话」在线上点不了
  document.head ? document.head.append(hide) : document.documentElement.append(hide);
  document.addEventListener('DOMContentLoaded', () => {
    const bar = document.createElement('aside');
    bar.className = 'demo-online-bar';
    bar.style.cssText = 'position:fixed;left:12px;top:auto;bottom:12px;z-index:9997;background:#fff5d9;color:#282015;border:2px solid #282015;border-radius:8px;padding:6px 10px;font:12px/1.4 -apple-system,"PingFang SC",sans-serif;box-shadow:2px 3px 0 #282015;max-width:calc(100vw - 24px)';
    bar.innerHTML = '<b>在线样例</b> · 数据全是虚构的，只能看 · <a href="https://github.com/Onlyaguest/comic-desk-local" target="_blank" rel="noopener" style="color:#a9422d">下载到本机用</a> <button type="button" aria-label="收起提示" style="border:0;background:none;font:inherit;cursor:pointer;padding:0 2px">×</button>';
    bar.querySelector('button').onclick = () => bar.remove();
    document.body.append(bar);
  });
})();
