// 在线样例版垫片（由 tools/build_online_demo.py 写进 demo/_demo/shim.js）。
// 页面原本请求本机服务的接口；这里把请求对到录好的静态文件上。只能看：改动类操作给一句提示。
// 不联网到别处、不上报，只读同目录下的文件。
(() => {
  'use strict';
  const ROUTES = {"GET api/desk/agent-status": {"f": "_rec/35e69c69d0cba185.json", "s": 200, "t": "application/json"}, "GET api/desk/board?days=30": {"f": "_rec/2434d8c40e262c09.json", "s": 200, "t": "application/json"}, "GET api/desk/board?days=7": {"f": "_rec/92f100754adb3dd6.json", "s": 200, "t": "application/json"}, "GET api/desk/board?days=all": {"f": "_rec/d5f30381d112d5eb.json", "s": 200, "t": "application/json"}, "GET api/desk/card?id=sample%3Aitem-1": {"f": "_rec/6b82016307330968.json", "s": 200, "t": "application/json"}, "GET api/desk/card?id=sample%3Aitem-2": {"f": "_rec/1411a22f650b6396.json", "s": 200, "t": "application/json"}, "GET api/desk/card?id=sample%3Aitem-4": {"f": "_rec/5d1bf4e116b87161.json", "s": 200, "t": "application/json"}, "GET api/desk/card?id=sample%3Aitem-5": {"f": "_rec/f10d16f14aab4f5f.json", "s": 200, "t": "application/json"}, "GET api/desk/card?id=sample%3Aitem-6": {"f": "_rec/f9ca2992c3eb6a82.json", "s": 200, "t": "application/json"}, "GET api/desk/card?id=sample%3Areview": {"f": "_rec/b114a87b6f625aaf.json", "s": 200, "t": "application/json"}, "GET api/desk/card?id=session%3Ademo%3Aclaude": {"f": "_rec/3017ccb6422bd0ab.json", "s": 200, "t": "application/json"}, "GET api/desk/card?id=session%3Ademo%3Acodex": {"f": "_rec/6a41ef3735f2c2fa.json", "s": 200, "t": "application/json"}, "GET api/desk/card?id=session%3Ademo%3Acohub": {"f": "_rec/a65df3fda659de97.json", "s": 200, "t": "application/json"}, "GET api/desk/evidence?index=0&receipt=sample-writeback": {"f": "_rec/f586174927daa357.html", "s": 200, "t": "text/html"}, "GET api/desk/image?id=8bec7a7913cb108f10e01c54&mode=full": {"f": "_rec/5e968f8ffc00e3e6.svg", "s": 200, "t": "image/svg+xml"}, "GET api/desk/image?id=8bec7a7913cb108f10e01c54&mode=thumb": {"f": "_rec/5e968f8ffc00e3e6.svg", "s": 200, "t": "image/svg+xml"}, "GET api/desk/image?id=e2f0ea354232d1c98d0c0581&mode=full": {"f": "_rec/7c7ec8d76f579a44.svg", "s": 200, "t": "image/svg+xml"}, "GET api/desk/image?id=e2f0ea354232d1c98d0c0581&mode=thumb": {"f": "_rec/7c7ec8d76f579a44.svg", "s": 200, "t": "image/svg+xml"}, "GET api/desk/images?limit=24&offset=0&q=&source=&status=": {"f": "_rec/1441517382701055.json", "s": 200, "t": "application/json"}, "GET api/desk/space": {"f": "_rec/6ae4901940bcf6b1.json", "s": 200, "t": "application/json"}, "GET api/index/artifacts?from=&images=1&limit=30&offset=0&q=&source=&to=": {"f": "_rec/f432adac6beb9541.json", "s": 200, "t": "application/json"}, "GET api/index/artifacts?from=&limit=30&offset=0&q=&source=&to=": {"f": "_rec/9cc38920b1069608.json", "s": 200, "t": "application/json"}, "GET api/index/artifacts?images=1&limit=100": {"f": "_rec/602dab5668410982.json", "s": 200, "t": "application/json"}, "GET api/index/cover": {"f": "_rec/168a192f123e3c58.json", "s": 200, "t": "application/json"}, "GET api/index/detail?id=demo%3Aclaude": {"f": "_rec/1aed3004c46e0dce.json", "s": 200, "t": "application/json"}, "GET api/index/detail?id=demo%3Acodex": {"f": "_rec/2f0cacd2e8eff975.json", "s": 200, "t": "application/json"}, "GET api/index/detail?id=demo%3Acohub": {"f": "_rec/83092e4900dcd21c.json", "s": 200, "t": "application/json"}, "GET api/index/detail?id=demo%3Amirasim": {"f": "_rec/a728305ed8adb4f8.json", "s": 200, "t": "application/json"}, "GET api/index/detail?id=demo%3Aworkbuddy": {"f": "_rec/234513c13ba05212.json", "s": 200, "t": "application/json"}, "GET api/index/image?id=8bec7a7913cb108f10e01c54": {"f": "_rec/5e968f8ffc00e3e6.svg", "s": 200, "t": "image/svg+xml"}, "GET api/index/image?id=e2f0ea354232d1c98d0c0581": {"f": "_rec/7c7ec8d76f579a44.svg", "s": 200, "t": "image/svg+xml"}, "GET api/index/sessions?from=&limit=30&offset=0&q=&source=&to=": {"f": "_rec/0a239450d217fc15.json", "s": 200, "t": "application/json"}, "GET api/index/status": {"f": "_rec/510921beae2932a2.json", "s": 200, "t": "application/json"}, "GET api/index/today": {"f": "_rec/41247e6965c287b6.json", "s": 200, "t": "application/json"}, "GET api/index/work-view?id=local%3A36bb885a9c17c1e854bbd688": {"go": "@@BASE@@samples/report-v2.html"}, "GET api/index/work-view?id=local%3A41eedeb4ba903d7f55929bc5": {"go": "@@BASE@@samples/timer.html"}, "GET api/index/works": {"f": "_rec/a84f542feb4e5969.json", "s": 200, "t": "application/json"}, "GET api/publish/diff?id=sample-desk-intro": {"f": "_rec/ab1fb46d3025d9d2.json", "s": 200, "t": "application/json"}, "GET api/publish/diff?id=sample-desk-intro-v2": {"f": "_rec/8d15d8655f67c13b.json", "s": 200, "t": "application/json"}, "GET api/publish/diff?id=sample-idea": {"f": "_rec/8d15d8655f67c13b.json", "s": 200, "t": "application/json"}, "GET api/publish/diff?id=sample-tea-timer": {"f": "_rec/8d15d8655f67c13b.json", "s": 200, "t": "application/json"}, "GET api/publish/file?id=sample-desk-intro&p=packs%2F2026-11-01_desk-intro%2Fimgs%2Fflow.svg": {"f": "_rec/6453e81b13eecf98.svg", "s": 200, "t": "image/svg+xml"}, "GET api/publish/post?id=sample-desk-intro": {"f": "_rec/4c6948a09c98d079.json", "s": 200, "t": "application/json"}, "GET api/publish/post?id=sample-desk-intro-v2": {"f": "_rec/dbadad183fcaa72b.json", "s": 200, "t": "application/json"}, "GET api/publish/post?id=sample-idea": {"f": "_rec/83ec3b0cf283038e.json", "s": 200, "t": "application/json"}, "GET api/publish/post?id=sample-tea-timer": {"f": "_rec/32e4ec76df640fde.json", "s": 200, "t": "application/json"}, "GET api/publish/state": {"f": "_rec/efd0fb6299b66481.json", "s": 200, "t": "application/json"}, "POST api/action {\"action\":\"notes\",\"input\":{\"op\":\"list\"}}": {"f": "_rec/ac6939c2fbd1caa4.json", "s": 200, "t": "application/json"}, "POST api/action {\"action\":\"todos\",\"input\":{\"op\":\"list\"}}": {"f": "_rec/45c2a9cfc4985ec2.json", "s": 200, "t": "application/json"}, "POST api/desk/sync-index {}": {"f": "_rec/e9a0a2f499832343.json", "s": 200, "t": "application/json"}};
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
