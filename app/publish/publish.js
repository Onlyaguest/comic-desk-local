// 发稿台页面：#/ 列表 · #/p/<id> 一篇 · #/diff/<id> 外改对比 · #/cmp/<a>/<b> 两版并排。只调本机 /api/publish/*。
(function () {
  'use strict';
  const view = document.getElementById('view');
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const toast = (s) => { const t = document.getElementById('toast'); t.textContent = s; t.classList.add('on'); setTimeout(() => t.classList.remove('on'), 1800); };
  const get = (u) => fetch(u, { cache: 'no-store' }).then((r) => r.json());
  async function act(body) {
    try {
      const r = await fetch('/api/publish/action', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
      const j = await r.json();
      if (!j.ok) throw new Error(j.error || '没成功');
      return j;
    } catch (e) { toast('没成功：' + e.message); return null; }
  }
  async function copy(s) {
    try { await navigator.clipboard.writeText(s); toast('已复制'); }
    catch (e) { const a = document.createElement('textarea'); a.value = s; document.body.appendChild(a); a.select(); try { document.execCommand('copy'); toast('已复制'); } catch (_) { toast('复制不了，长按手动选'); } a.remove(); }
  }

  // ---- 极简 markdown：先转义再加格式，不接受原始 HTML，链接只认 http(s) ----
  function inline(s, img) {
    s = esc(s);
    s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)[^)]*\)/g, (_, alt, src) => `<img alt="${alt}" src="${esc(img(src.replace(/&amp;/g, '&')))}" loading="lazy">`);
    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<i>$2</i>');
    return s.replace(/\n/g, '<br>');
  }
  function md(src, img) {
    src = String(src || '').replace(/\r/g, '').replace(/^---\n[\s\S]*?\n---\n/, '');
    return src.split(/\n\s*\n/).map((b) => {
      b = b.replace(/^\n+|\s+$/g, '');
      if (!b) return '';
      let m;
      if ((m = b.match(/^(#{1,4})\s+(.*)$/)) && !b.includes('\n')) return `<h${m[1].length + 1}>${inline(m[2], img)}</h${m[1].length + 1}>`;
      if (/^(-{3,}|\*{3,})$/.test(b)) return '<hr>';
      if (b.split('\n').every((l) => /^>\s?/.test(l))) return `<blockquote>${inline(b.replace(/^>\s?/gm, ''), img)}</blockquote>`;
      if (b.split('\n').every((l) => /^\s*[-*]\s+/.test(l))) return `<ul>${b.split('\n').map((l) => `<li>${inline(l.replace(/^\s*[-*]\s+/, ''), img)}</li>`).join('')}</ul>`;
      if (b.split('\n').every((l) => /^\s*\d+\.\s+/.test(l))) return `<ol>${b.split('\n').map((l) => `<li>${inline(l.replace(/^\s*\d+\.\s+/, ''), img)}</li>`).join('')}</ol>`;
      return `<p>${inline(b, img)}</p>`;
    }).join('');
  }
  const imgFor = (id, dir) => (src) => {
    if (/^(https?:|data:)/.test(src)) return src;
    const parts = (dir ? dir + '/' + src : src).split('/'); const out = [];
    for (const p of parts) { if (p === '..') out.pop(); else if (p && p !== '.') out.push(p); }
    return '/api/publish/file?id=' + encodeURIComponent(id) + '&p=' + encodeURIComponent(out.join('/'));
  };
  const tag = (x) => `<span class="tag s-${esc(x.status)}">${esc(x.status)}</span>${x.account ? `<span class="tag">${esc(x.platform || '')} · ${esc(x.account)}</span>` : ''}${x.date ? `<span>${esc(x.date)}</span>` : ''}`;

  // ---- 列表 ----
  let filter = '';
  try { filter = localStorage.getItem('publish-filter') || ''; } catch (e) {}
  async function list() {
    const s = await get('/api/publish/state');
    document.getElementById('mode').textContent = s.mode === 'demo' ? '离线样例' : '个人模式';
    const accs = [...new Set(s.posts.map((x) => x.account).filter(Boolean))];
    const card = (x) => `<a class="it${x.picked ? ' picked' : ''}" href="#/p/${encodeURIComponent(x.id)}" data-acc="${esc(x.account || '')}"><b>${x.picked ? '⭐ ' : ''}${esc(x.status === '灵感' ? (x.idea || x.title) : x.title)}</b><div class="meta">${tag(x)}</div>${x.note ? `<div class="note">${esc(x.note)}</div>` : ''}</a>`;
    const show = (x) => !filter || x.account === filter;
    const picked = s.posts.filter((x) => x.picked && !['已发出', '已归档'].includes(x.status) && show(x));
    let html = `<h1>我的稿子</h1><div class="sub">${s.mode === 'demo' ? '现在是离线样例，稿子都是编的；接自己的稿子见 docs/PUBLISH.md。' : '读的是你在 config.local.json 里指定的登记表。'}</div>`;
    html += `<div class="chips"><button class="chip${filter ? '' : ' on'}" data-f="">全部</button>${accs.map((a) => `<button class="chip${a === filter ? ' on' : ''}" data-f="${esc(a)}">${esc(a)}</button>`).join('')}</div>`;
    if (picked.length) html += `<h2>⭐ 挑了要发的 · ${picked.length}</h2>` + picked.map(card).join('');
    for (const st of s.statuses) {
      const xs = s.posts.filter((x) => x.status === st && show(x));
      if (!xs.length) continue;
      html += `<h2>${esc(st)} · ${xs.length}</h2>` + xs.map(card).join('');
    }
    view.innerHTML = html;
    view.querySelectorAll('.chip').forEach((c) => c.onclick = () => { filter = c.dataset.f; try { localStorage.setItem('publish-filter', filter); } catch (e) {} list(); });
  }

  // ---- 一篇 ----
  const ICON = { done: '✅', doing: '⏳', todo: '⬜', fail: '❗' };
  async function one(id) {
    const d = await get('/api/publish/post?id=' + encodeURIComponent(id));
    if (!d.ok) { view.innerHTML = `<p class="empty">${esc(d.error || '没有这篇')}</p><a class="btn" href="#/">← 回列表</a>`; return; }
    document.getElementById('mode').textContent = d.mode === 'demo' ? '离线样例' : '个人模式';
    const x = d.post;
    const B = (label, attrs, cls) => `<button class="btn ${cls || ''}" ${attrs}>${label}</button>`;
    const rows = {
      write: () => d.siblings.map((s) => `<a class="btn" href="#/cmp/${encodeURIComponent(x.id)}/${encodeURIComponent(s.id)}">和「${esc((s.title || s.id).slice(0, 14))}」并排比</a>`).join(''),
      qa: () => B('标记验收过', 'data-qa="过"') + B('标记要改', 'data-qa="要改"') + (d.commands.includes('check') ? B('跑检查', 'data-run="check"') : ''),
      mine: () => `<textarea id="mytext" rows="4" placeholder="把你改好的段落贴进来，或者写一句要怎么改"></textarea>
        <div class="row" style="margin:6px 0 0;grid-column:auto">${B('按我这段重写整篇', 'data-note="rewrite"', 'p')}${B('只改这一处', 'data-note="patch"')}${B('以后都这样', 'data-note="rule"')}</div>
        <div class="copybox" id="copybox" hidden><div class="sub">记下了。下面这段复制给你的 AI 助手（Claude、Codex、豆包都行），它就知道怎么改：</div><textarea rows="6" readonly></textarea><div class="btns">${B('复制这段', 'id="copyprompt"', 'p')}</div></div>
        ${d.notes.length ? `<div class="hist">最近：${d.notes.slice(0, 5).map((n) => `<div>${esc(String(n.at || '').slice(0, 16).replace('T', ' '))} · ${esc(n.label || n.kind)}${n.text ? '：' + esc(n.text.slice(0, 80)) : ''}</div>`).join('')}</div>` : ''}`,
      outside: () => B(d.outside ? '重新导出一份' : '导出去改', 'data-export="1"')
        + (d.commands.includes('fetch') ? B('拉回改动', 'data-run="fetch"') : '')
        + (d.outside && d.outside.changed ? `<a class="btn p" href="#/diff/${encodeURIComponent(x.id)}">看改了哪 · ${d.outside.changed} 处</a>` : '')
        + (d.outsideFile ? `<div class="path">外改文件：${esc(d.outsideFile)}（用任何编辑器打开改，存盘后刷新这页）</div>` : ''),
      pick: () => (['已发出', '已归档'].includes(x.status) ? '' : x.picked ? B('取消「要发」', 'data-pick="0"') : B('⭐ 挑这篇要发', 'data-pick="1"', 'p')),
      send: () => B('复制标题', 'id="ct"') + (d.body ? B('复制正文', 'id="cb"') : '') + (d.commands.includes('preview') ? B('跑预览', 'data-run="preview"') : '') + (x.status !== '已发出' ? B('我发出去了', 'data-sent="1"') : ''),
      archive: () => B(x.url ? '改链接' : '填链接', 'data-url="1"') + (x.url ? `<a class="btn" href="${esc(x.url)}" target="_blank" rel="noopener">看原文</a>` : '') + (x.status !== '已归档' ? B('归档', 'data-status="已归档"') : B('放回草稿', 'data-status="草稿"')),
    };
    const flow = d.steps.map((s) => `<div class="st ${s.state}"><div class="ic">${ICON[s.state] || ''}</div><div><b>${esc(s.label)}</b><div class="d">${esc(s.detail)}</div></div>${rows[s.k] ? `<div class="row">${rows[s.k]()}</div>` : ''}<div class="out" hidden></div></div>`).join('');
    view.innerHTML = `<a class="btn" href="#/">← 列表</a><h1>${x.picked ? '⭐ ' : ''}${esc(x.title)}</h1><div class="meta">${tag(x)}</div>${x.note ? `<div class="note">${esc(x.note)}</div>` : ''}
      <h2>走到哪了</h2><div class="flow">${flow}</div>
      ${x.status === '灵感' && x.idea ? `<div class="body"><p>${esc(x.idea)}</p></div>` : ''}
      ${d.body ? `<h2>正文</h2><div class="body" id="body">${md(d.body, imgFor(x.id, d.bodyDir))}</div>` : ''}`;
    wire(x, d);
  }
  function wire(x, d) {
    const reload = () => one(x.id);
    const $ = (q) => view.querySelector(q);
    view.querySelectorAll('[data-pick]').forEach((b) => b.onclick = async () => { if (await act({ op: 'pick', id: x.id, on: b.dataset.pick === '1' })) { toast('改好了'); reload(); } });
    view.querySelectorAll('[data-status]').forEach((b) => b.onclick = async () => { if (await act({ op: 'status', id: x.id, status: b.dataset.status })) { toast('改好了'); reload(); } });
    view.querySelectorAll('[data-qa]').forEach((b) => b.onclick = async () => { const why = b.dataset.qa === '过' ? '' : (prompt('哪里要改？一句话', '') || ''); if (await act({ op: 'qa', id: x.id, qa: b.dataset.qa + (why ? ' · ' + why : '') })) { toast('记下了'); reload(); } });
    const sent = $('[data-sent]'); if (sent) sent.onclick = async () => { const u = prompt('有链接就贴上（没有也行）', ''); if (u === null) return; if (await act({ op: 'status', id: x.id, status: '已发出', url: u.trim() })) { toast('改好了'); reload(); } };
    const url = $('[data-url]'); if (url) url.onclick = async () => { const u = prompt('原文链接', x.url || ''); if (u === null) return; if (await act({ op: 'url', id: x.id, url: u.trim() })) { toast('改好了'); reload(); } };
    view.querySelectorAll('[data-note]').forEach((b) => b.onclick = async () => {
      const ta = $('#mytext'); const text = ta.value.trim(); if (!text) { toast('先在框里写你要怎么改'); ta.focus(); return; }
      const j = await act({ op: 'note', id: x.id, kind: b.dataset.note, text }); if (!j) return;
      ta.value = ''; const box = $('#copybox'); box.hidden = false; box.querySelector('textarea').value = j.note.prompt;
      $('#copyprompt').onclick = () => copy(j.note.prompt); toast('记下了');
    });
    const ex = $('[data-export]'); if (ex) ex.onclick = async () => { if (d.outside && d.outside.changed && !confirm('外改文件里还有 ' + d.outside.changed + ' 处没采用的改动，重新导出会盖掉它们。确定吗？')) return; const j = await act({ op: 'export', id: x.id }); if (j) { toast('导出了'); reload(); } };
    view.querySelectorAll('[data-run]').forEach((b) => b.onclick = async () => {
      const out = b.closest('.st').querySelector('.out'); out.hidden = false; out.textContent = '在跑…'; b.disabled = true;
      const j = await act({ op: 'run', id: x.id, key: b.dataset.run }); b.disabled = false;
      if (!j) { out.textContent = '没成功'; return; }
      out.textContent = (j.result.ok ? '做好了\n' : '没成功\n') + (j.result.out || ''); if (j.result.ok && b.dataset.run === 'fetch') setTimeout(reload, 900);
    });
    const ct = $('#ct'); if (ct) ct.onclick = () => copy(x.title || '');
    const cb = $('#cb'); if (cb) cb.onclick = () => copy($('#body').innerText.trim());
  }

  // ---- 外改对比 ----
  async function diff(id) {
    const r = await get('/api/publish/diff?id=' + encodeURIComponent(id));
    const back = `<a class="btn" href="#/p/${encodeURIComponent(id)}">← 回这篇</a>`;
    if (!r.ok) { view.innerHTML = back + '<p class="empty">还没有外改的版本。</p>'; return; }
    const c = r.diff;
    const out = c.blocks.map((b) => {
      if (b.t === 'same') return `<p class="same">…… ${b.n} 段没动 ……</p>`;
      if (b.t === 'edit') return `<p class="add">${b.parts.map(([t, v]) => t === 'add' ? `<ins>${esc(v)}</ins>` : t === 'del' ? `<del>${esc(v)}</del>` : esc(v)).join('')}</p>`;
      return b.v.map((v) => `<p class="${b.t}">${esc(v)}</p>`).join('');
    }).join('');
    const warn = [];
    if (!c.hasBase) warn.push('没有导出时的底稿，下面是「外改版」对「现在的定稿」：定稿后来又改过的话，差异不全是你改的。');
    if (c.localMoved) warn.push('导出以后定稿又被改过。采用外改版会盖掉那次改动（旧稿会先存进 历史/）。');
    if (c.imgs.edited > c.imgs.base) warn.push(`外改版多了 ${c.imgs.edited - c.imgs.base} 张图，新图对不上本机文件，采用后要自己放进稿件目录。`);
    if (c.title.edited && c.title.edited !== c.title.local) warn.push(`标题会从「${c.title.local}」改成「${c.title.edited}」。`);
    view.innerHTML = `${back}<h1>外部改了哪</h1><div class="sub">${c.changed} 处不一样 · 绿色是外改版新加的，划线是原来有、外改版删掉的</div>
      ${warn.map((w) => `<div class="warn">${esc(w)}</div>`).join('')}
      <div class="btns"><button class="btn p" id="adopt">采用外改版当定稿</button></div><div class="body dif">${out}</div>`;
    document.getElementById('adopt').onclick = async () => {
      if (!confirm('用外改版替换定稿？旧稿会先存进稿件目录的 历史/。')) return;
      const j = await act({ op: 'adopt', id }); if (j) { toast('采用了' + (j.lost && j.lost.length ? '，有新图要自己放' : '')); location.hash = '#/p/' + encodeURIComponent(id); }
    };
  }

  // ---- 两版并排 ----
  async function cmp(a, b) {
    const ds = await Promise.all([a, b].map((id) => get('/api/publish/post?id=' + encodeURIComponent(id))));
    if (ds.some((d) => !d.ok)) { view.innerHTML = '<p class="empty">有一篇找不到了。</p>'; return; }
    view.innerHTML = `<a class="btn" href="#/p/${encodeURIComponent(a)}">← 回去</a><h1>两版并排</h1><div class="sub">挑中哪版，就去那版点「⭐ 挑这篇要发」；另一版可以归档。</div>
      <div class="cmp">${ds.map((d) => `<div><h2>${esc(d.post.title)}</h2><div class="meta">${tag(d.post)}</div><div class="btns"><a class="btn" href="#/p/${encodeURIComponent(d.post.id)}">去这版</a></div><div class="body">${md(d.body, imgFor(d.post.id, d.bodyDir))}</div></div>`).join('')}</div>`;
  }

  function route() {
    const h = decodeURIComponent(location.hash.replace(/^#\/?/, ''));
    const [kind, p1, p2] = h.split('/');
    window.scrollTo(0, 0);
    if (kind === 'p' && p1) return one(p1);
    if (kind === 'diff' && p1) return diff(p1);
    if (kind === 'cmp' && p1 && p2) return cmp(p1, p2);
    return list();
  }
  window.addEventListener('hashchange', route);
  route();
})();
