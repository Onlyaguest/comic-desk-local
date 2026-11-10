/* =====================================================================
 *  本地版 · 投影仪片单
 *  ---------------------------------------------------------------------
 *  格式沿用 walkable-city.deck.v1：一行 = 一件能放上幕布的东西。
 *  本地版只留四类：关于、契约、索引、照片。
 *  想加片，就在 items 里加一行；带 build 的几份跟 data/content.json 同步。
 * ===================================================================== */
(function () {
  window.DESK_PROJECTOR_LIBRARY = {
    title: '桌面 · 投影片单',
    note: '本地版：关于 / 契约 / 索引 / 照片。加一件就是加一行。',
    items: () => {
      const D = window.DESK_DATA || {};
      const A = D.about || {}, C = D.contract || {};
      const items = [];

      items.push({
        id: 'about', kind: 'deck', title: '关于' + (A.name || '我'),
        note: '点软木板弹出的「关于」也可以投出来讲',
        build: () => ({
          schema: 'walkable-city.deck.v1', title: '关于' + (A.name || '我'), speaker: A.name, mode: 'slides',
          slides: [
            { title: A.name, note: (A.name || '') + '。' + (A.role || ''),
              html: `<div class="kicker">${A.kicker || ''}</div><h1>${A.name || ''}</h1><p class="lead">${A.role || ''}</p>
                <div class="ps-pols">${(A.polaroids || []).map((p) => `<figure><img src="${p.file}" alt=""><figcaption>${p.cap || ''}</figcaption></figure>`).join('')}</div>` },
            ...(A.lines || []).map((l, i) => ({ title: `${A.name} · ${i + 1}`, note: l,
              html: `<div class="kicker">${A.kicker || ''} · ${String(i + 1).padStart(2, '0')}</div><p class="big">${l}</p>` })),
            { title: '标签', note: '关键词：' + (A.tags || []).join('、') + '。',
              html: `<div class="kicker">TAGS</div><h2>我在做的这些事</h2><div class="ps-tags">${(A.tags || []).map((t) => `<span>${t}</span>`).join('')}</div>` },
          ],
        }),
      });

      if (C.clauses && C.clauses.length) items.push({
        id: 'contract', kind: 'deck', title: C.title || '今日契约', note: C.source || '',
        build: () => ({
          schema: 'walkable-city.deck.v1', title: C.title || '今日契约', speaker: A.name, mode: 'slides',
          slides: [
            { title: '立约两条', note: C.clauses.map((x) => x.text).join('；'), html: `<div class="kicker">CONTRACT · ${C.title || ''}</div><h1>立约两条</h1><ul class="ps-list">${C.clauses.map((x) => `<li>${x.k} · ${x.text}</li>`).join('')}</ul>` },
            ...C.clauses.map((x, i) => ({ title: `第${'一二三四五'[i]}条`, note: x.text + '。' + (x.sub || ''), html: `<div class="kicker">第${'一二三四五'[i]}条 · ${x.k}</div><p class="big">${x.text}</p><p class="foot">${x.sub || ''}</p>` })),
          ],
        }),
      });

      items.push({ id: 'readme', kind: 'text', title: '这张桌子怎么用 · README', src: 'README.md', note: '原文按小节分页，查字段时用' });
      items.push({ id: 'index', kind: 'html', title: '索引 · 所有物件与链接', src: 'INDEX.html', note: '本地索引页：每个物件、每条链接、每个数据文件' });

      (D.photos || []).slice(0, 8).forEach((p, i) => items.push({ id: 'photo-' + i, kind: 'image', title: p.title || '照片', src: p.file, note: [p.cat, p.loc].filter(Boolean).join(' · ') }));
      (window.DESK_GALLERY || []).slice(0, 6).forEach((g, i) => items.push({ id: 'gen-' + i, kind: 'image', title: '最新图片 · ' + (i + 1), src: g.url, note: (g.created || '').slice(0, 10) + ' · ' + (g.src || '') }));

      return items;
    },
  };
})();
