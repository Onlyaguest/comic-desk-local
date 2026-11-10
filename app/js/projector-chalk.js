/* =====================================================================
 *  投影仪 · 黑板主题（deck.theme === 'chalk'）
 *  一页 = 一块黑板：木框 + 石板底 + 彩色粉笔字 + 角落涂鸦 + 粉笔槽。
 *  素材改自 chalkboard-bulletin（No.98 黑板报，作者 ATou / kid space）：
 *    assets/projector/chalk/{slate,doodles,strips,tools}.webp
 *  大屏开讲时一块块「用粉笔写出来」；幕布上的小画面静止。
 *  页面格式见 tools/guide-deck.py。
 * ===================================================================== */
(function () {
  'use strict';
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  // 行内：**重点** → 黄粉笔；`代码` → 粉笔框；==x== → 波浪下划线
  const md = (s) => esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/==([^=]+)==/g, '<u>$1</u>');

  // doodles.webp 的切片坐标（来自原 kit 的 ATLAS）
  const DOODLE = { star: [4, 4, 161, 163], flower: [169, 4, 128, 199], sun: [301, 4, 194, 198], cat: [499, 4, 170, 186], rocket: [673, 4, 178, 182], cloud: [855, 4, 192, 134], arrow: [1051, 4, 198, 82], moon: [1253, 4, 153, 156], trophy: [1410, 4, 166, 170], pencil: [1580, 4, 165, 163], bubble: [1749, 4, 183, 160], heart: [4, 207, 154, 140], tulip: [162, 207, 134, 191], corner: [300, 207, 170, 174], plane: [474, 207, 204, 179], sparkle: [682, 207, 157, 160] };
  const SHEET = { doodles: [1934, 400], strips: [1183, 499], tools: [1639, 122] };
  const STRIP = { ribbon: [4, 4, 1172, 113], lace: [4, 121, 1177, 144], vine: [4, 269, 1173, 106], bunting: [4, 379, 1168, 118] };
  const TOOL = { eraser: [4, 4, 244, 102], white: [252, 4, 226, 42], pink: [482, 4, 224, 42], yellow: [710, 4, 226, 42], blue: [940, 4, 227, 42], green: [1171, 4, 226, 42], stub: [1401, 4, 116, 42] };
  const BASE = 'assets/projector/chalk/';
  function sprite(sheet, f, w, cls, style) {
    const [x, y, fw, fh] = f, [W, H] = SHEET[sheet], k = w / fw;
    return `<i class="${cls}" style="width:${w}px;height:${Math.round(fh * k)}px;background:url(${BASE}${sheet}.webp) ${-x * k}px ${-y * k}px/${W * k}px ${H * k}px no-repeat;${style || ''}"></i>`;
  }

  let fontsAsked = false;
  function ensureFonts() {
    if (fontsAsked) return; fontsAsked = true;
    ['zcool-kuaile@5.2.5/400.css', 'caveat@5.2.5/latin-700.css'].forEach((f) => {
      const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = 'https://cdn.jsdelivr.net/npm/@fontsource/' + f; document.head.appendChild(l);
    });
    // 粉笔边缘：轻微抖动 + 颗粒（一次性挂在页面里）
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '0'); svg.setAttribute('height', '0'); svg.style.position = 'absolute';
    svg.innerHTML = `<filter id="ckRough" x="-5%" y="-5%" width="110%" height="110%">
      <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="2" seed="7" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="1.8" xChannelSelector="R" yChannelSelector="G" result="d"/>
      <feTurbulence type="fractalNoise" baseFrequency="1.6" numOctaves="1" seed="3" result="g"/>
      <feColorMatrix in="g" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -1.4 1.25" result="ga"/>
      <feComposite in="d" in2="ga" operator="in"/></filter>`;
    document.body.appendChild(svg);
  }

  function block(b, i) {
    const c = b.c || 'white';
    let inner = '';
    if (b.h) inner += `<h3 class="ck-h ck-${c}">${md(b.h)}${b.tag ? ` <span class="ck-tag">${md(b.tag)}</span>` : ''}</h3>`;
    if (b.p) inner += `<p class="ck-p">${md(b.p)}</p>`;
    if (b.items) inner += `<ul class="ck-ul ck-dot-${c}"${b.cols ? ` style="column-count:${b.cols};column-gap:40px"` : ''}>${b.items.map((t) => `<li>${md(t)}</li>`).join('')}</ul>`;
    if (b.ol) inner += `<ol class="ck-ol" start="${b.start || 1}">${b.ol.map((t, k) => `<li><span class="ck-n">${(b.start || 1) + k}</span><span>${md(t)}</span></li>`).join('')}</ol>`;
    if (b.tags) inner += `<div class="ck-tags">${b.tags.map((t, k) => `<span class="ck-${['yellow', 'pink', 'blue', 'green'][k % 4]}">${md(t)}</span>`).join('')}</div>`;
    if (b.code) inner += `<pre class="ck-code">${esc(b.code)}</pre>`;
    if (b.table) inner += `<table class="ck-table"><thead><tr>${b.table.head.map((h) => `<th>${md(h)}</th>`).join('')}</tr></thead><tbody>${b.table.rows.map((r) => `<tr>${r.map((x) => `<td>${md(x)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
    return `<section class="ck-b${b.h ? ' boxed' : ''}" style="--i:${i}">${inner}</section>`;
  }

  function html(s, ctx) {
    ensureFonts();
    const n = ctx.n || 1, k = (ctx.i || 0) + 1, cover = s.layout === 'cover';
    const blocks = (s.blocks || []).map((b, i) => block(b, i + 2)).join('');
    const tray = sprite('tools', TOOL.eraser, 92, 'ck-eraser') + sprite('tools', TOOL.white, 96, 'ck-stick', 'transform:rotate(-4deg)') +
      sprite('tools', TOOL.yellow, 84, 'ck-stick') + sprite('tools', TOOL.pink, 70, 'ck-stick', 'transform:rotate(3deg)') + sprite('tools', TOOL.stub, 34, 'ck-stick');
    const dood = s.doodle && DOODLE[s.doodle] ? sprite('doodles', DOODLE[s.doodle], cover ? 150 : 92, 'ck-doodle' + (cover ? ' big' : ''), 'opacity:.8') : '';
    const top = cover ? sprite('strips', STRIP.bunting, 1100, 'ck-bunting') : '';
    return `<div class="pslide ps-chalk${cover ? ' ck-cover' : ''}${s.dense ? ' ck-dense' : ''}" style="--cols:${s.cols || 1}">
      ${top}
      <div class="ck-board">
        <header class="ck-head" style="--i:0">
          ${s.kicker ? `<span class="ck-kick">${md(s.kicker)}</span>` : ''}
          <h2 class="ck-title">${md(s.title || '')}</h2>
          ${cover ? '' : sprite('strips', STRIP.vine, 340, 'ck-vine')}
        </header>
        <div class="ck-body">${blocks}</div>
      </div>
      ${dood}
      <div class="ck-page">${k} / ${n}</div>
      <div class="ck-tray">${tray}</div>
    </div>`;
  }

  // 字稍多就把这一页整体缩一点（最小 0.86）；再多就该拆页（tools/guide-deck.py），不靠缩字
  function fit(root) {
    const sl = root && root.querySelector('.ps-chalk'); if (!sl) return;
    const body = sl.querySelector('.ck-body'); if (!body) return;
    const over = () => body.scrollHeight > body.clientHeight + 2 || body.scrollWidth > body.clientWidth + 2;   // 分栏时溢出往右跑
    let f = 1; sl.style.setProperty('--ckf', f);
    for (let t = 0; t < 10 && over() && f > 0.86; t++) { f -= 0.02; sl.style.setProperty('--ckf', f.toFixed(2)); }
    sl.classList.toggle('ck-over', over());
  }
  function write(root) {   // 大屏：一块块写出来
    const sl = root && root.querySelector('.ps-chalk'); if (!sl) return;
    sl.classList.remove('ck-write'); void sl.offsetWidth; sl.classList.add('ck-write');
  }

  window.DESK_CHALK = { html, fit, write, ensureFonts };
})();
