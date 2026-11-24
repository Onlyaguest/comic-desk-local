/* Rule-based catalog. No model calls or source polling. */
window.DeskWorks = (() => {
  const esc = s => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const date = s => { const d=new Date(s); return isNaN(d)?'时间未知':d.toLocaleDateString('zh-CN'); };
  async function mount(root) {
    let items=[],limit=48;
    root.innerHTML=`<div class="wg"><p class="wg-intro">找到作品，直接打开。置顶、改名和默认版本会保存在本机。</p><div class="wg-controls"><input type="search" aria-label="搜索作品" placeholder="搜索作品名称…"><select aria-label="作品来源"><option value="">所有来源</option><option value="cohub">Cohub</option><option value="local">本地</option></select><select aria-label="作品类型"><option value="">所有类型</option>${['工具','报告','演示','其他'].map(x=>`<option>${x}</option>`).join('')}</select><select aria-label="作品视图"><option value="active">作品</option><option value="pending">待整理</option><option value="hidden">已隐藏</option></select><button type="button" data-reload>更新列表</button></div><p class="wg-status" role="status">正在读取本地作品目录…</p><div class="wg-body"></div></div>`;
    const $=s=>root.querySelector(s), input=$('input'), selects=root.querySelectorAll('select');
    function card(x) {
      const title=esc(x.title), href=esc(x.href), fallback=`<span class="wg-fallback">${title}</span>`;
      return `<article class="wg-card" data-work="${esc(x.id)}"><div class="wg-cover" style="--tone:${parseInt(x.id.slice(-4),16)%360||35}">${x.href?`<a href="${href}" target="_blank" rel="noopener" aria-label="打开作品：${title}">${fallback}${x.cover?`<img loading="lazy" src="${esc(x.cover)}" alt="">`:''}</a>`:fallback}</div><div class="wg-card-body"><div class="wg-title">${x.href?`<a href="${href}" target="_blank" rel="noopener">${title}</a>`:`<strong>${title}</strong>`}<button type="button" data-pin aria-label="${x.pinned?'取消置顶':'置顶'}：${title}" aria-pressed="${x.pinned}">${x.pinned?'★':'☆'}</button></div><p class="wg-meta"><span>${x.source==='cohub'?'Cohub':'本地'}</span><span>${esc(x.category)}</span><time>${date(x.updated)}</time></p>${x.pending?`<p class="wg-reason">${esc(x.reason)}</p>`:''}<details><summary aria-label="管理作品：${title}">⋯ 管理</summary><label>名称<input data-title value="${title}" maxlength="180"></label><label>类型<select data-category>${['工具','报告','演示','其他'].map(k=>`<option ${k===x.category?'selected':''}>${k}</option>`).join('')}</select></label>${x.versions.length>1?`<label>默认版本<select data-version>${x.versions.map(v=>`<option value="${esc(v.id)}" ${v.id===x.preferred?'selected':''}>${esc(v.target.split('/').pop())} · ${date(v.updated)}</option>`).join('')}</select></label>`:''}<button type="button" data-save>保存设置</button><button type="button" data-hide>${x.hidden?'恢复展示':'隐藏作品'}</button>${x.pending&&x.href?'<button type="button" data-approve>确认是作品</button>':''}${x.project_url?`<p><a href="${esc(x.project_url)}" target="_blank" rel="noopener">进入源空间 ↗</a></p>`:''}<p class="wg-path">${esc(x.versions.find(v=>v.id===x.preferred)?.target||'暂无发布地址')}</p>${x.sessions.map(s=>`<a class="wg-session" href="./library.html?session=${encodeURIComponent(s.id)}">${esc(s.title)}</a>`).join('')}</details></div></article>`;
    }
    function paint() {
      if(!root.isConnected)return;
      const q=input.value.trim().toLowerCase(),source=selects[0].value,category=selects[1].value,view=selects[2].value;
      const filtered=items.filter(x=>(!source||x.source===source)&&(!category||x.category===category)&&(!q||x.title.toLowerCase().includes(q))&&(view==='hidden'?x.hidden:view==='pending'?!x.hidden&&x.pending:!x.hidden&&!x.pending));
      const section=(name,list)=>list.length?`<section><h3>${name} <small>${list.length}</small></h3><div class="wg-grid">${list.map(card).join('')}</div></section>`:'';
      let content='';
      if(view==='active'&&!q&&!source&&!category){
        const pinned=filtered.filter(x=>x.pinned).sort((a,b)=>(a.pin_order||a.id).localeCompare(b.pin_order||b.id)),others=filtered.filter(x=>!x.pinned);
        content=section('常用',pinned)+(pinned.length?'':'<p class="wg-empty">点作品上的 ☆，把常用入口留在这里。</p>')+section('最近更新',others.slice(0,12));
      }
      content+=section(view==='pending'?'待整理':view==='hidden'?'已隐藏':'全部作品',filtered.slice(0,limit));
      if(!filtered.length)content='<p class="wg-empty">这里还没有作品。可调整搜索或筛选条件。</p>';
      if(filtered.length>limit)content+='<button type="button" data-more>再显示 48 个</button>';
      $('.wg-body').innerHTML=content;
      $('.wg-status').textContent=`${filtered.length} 个作品 · Cohub ${items.filter(x=>x.source==='cohub').length} · 本地 ${items.filter(x=>x.source==='local').length} · 待整理 ${items.filter(x=>x.pending&&!x.hidden).length}`;
      root.querySelectorAll('.wg-cover img').forEach(img=>img.onerror=()=>img.remove());
    }
    async function load(){try{const r=await fetch('./api/index/works');const d=await r.json();if(!r.ok)throw Error(d.error||'读取失败');items=d.items;paint();}catch(e){$('.wg-status').textContent='读取失败：'+e.message+'。点击更新列表重试。';}}
    input.oninput=()=>{limit=48;paint();};selects.forEach(s=>s.onchange=()=>{limit=48;paint();});
    root.addEventListener('click',async e=>{
      const b=e.target.closest('button');if(!b)return;
      if(b.hasAttribute('data-reload')){await load();return;}
      if(b.hasAttribute('data-more')){limit+=48;paint();return;}
      const cardEl=b.closest('[data-work]');if(!cardEl)return;
      const item=items.find(x=>x.id===cardEl.dataset.work),payload={id:item.id};
      if(b.hasAttribute('data-pin'))payload.pinned=!item.pinned;
      else if(b.hasAttribute('data-hide'))payload.hidden=!item.hidden;
      else if(b.hasAttribute('data-approve'))payload.approved=true;
      else if(b.hasAttribute('data-save')){payload.title=cardEl.querySelector('[data-title]').value;payload.category=cardEl.querySelector('[data-category]').value;const v=cardEl.querySelector('[data-version]');if(v)payload.preferred=v.value;}
      else return;
      b.disabled=true;
      try{const r=await fetch('./api/index/works',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const d=await r.json();if(!r.ok||!d.ok)throw Error(d.error||'保存失败');await load();$('.wg-status').textContent+=' · 已保存';}
      catch(error){$('.wg-status').textContent='未保存：'+error.message;b.disabled=false;}
    });
    await load();
  }
  return {mount};
})();
