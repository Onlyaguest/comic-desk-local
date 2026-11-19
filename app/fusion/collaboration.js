/* 纸卡背面只呈现已有证据；不提供自行验收或改写规则的按钮。 */
(() => {
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const date=x=>x?new Date(x).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}):'未记录时间';
 const label=(text,state)=>`<span class="evidence-state ${state==='verified'||state==='referenced'?'verified':'pending'}">${esc(text)}</span>`;
 function render(data){
  if(!data)return '<p class="collab-loading" role="status">正在翻看这张卡的协作记录…</p>';
  if(data.error)return `<p role="status">${esc(data.error)}</p><p class="sheet-note">保留原卡；当前不把缺失记录算作已回写或已验收。</p>`;
  const c=data.collaboration||{},r=c.responsibility||{},w=c.writeback||{};
  return `<section class="collab-section"><h3>谁负责 · 在哪里</h3><p class="collab-actor">${esc(r.actor||'执行者待核实')} <small>${esc(r.machine||'执行节点未知')}</small></p><p>${esc(r.duty||'岗位信息待核实')}</p><p class="sheet-note">${r.identified?'已按来源或派活记录关联执行者；以下岗位按当前正本显示。':'目前只有会话/来源信息，尚未认定任务负责人。'}${r.source?.path?' 依据：'+esc(r.source.path.split('/').pop())+' · '+date(r.source.checkedAt||r.source.modifiedAt):''}</p></section>
  <section class="collab-section"><h3>最近回复 · 回写</h3>${label(w.label||'未见回写说明',w.state)}${w.statement?`<blockquote class="declaration">${esc(w.statement)}</blockquote>`:'<p class="sheet-note">未读到明确的回写行，保持未知。</p>'}<p class="sheet-note">${w.observedAt?'回复记录 '+date(w.observedAt):'没有可核对的交付时间'}${w.sourceRef?' · '+esc(w.sourceRef):''}</p>${(w.evidence||[]).length?'<ul class="evidence-list">'+w.evidence.map((e,i)=>`<li>${e.ok?'✓':'待核对'} ${esc(e.target)}${w.receiptId?` <a href="/api/desk/evidence?receipt=${encodeURIComponent(w.receiptId)}&index=${i}" target="_blank" rel="noopener">查看依据 ↗</a>`:''}</li>`).join('')+'</ul>':''}${(c.writebackHistory||[]).map(h=>`<details class="prior-writeback"><summary>此前交付已核对 · ${esc(h.sourceRef)}</summary><blockquote class="declaration">${esc(h.statement)}</blockquote><ul class="evidence-list">${h.evidence.map((e,i)=>`<li>✓ ${esc(e.target)} <a href="/api/desk/evidence?receipt=${encodeURIComponent(h.receiptId)}&index=${i}" target="_blank" rel="noopener">查看依据 ↗</a></li>`).join('')}</ul><p class="sheet-note">这笔回执对应此前交付，未用来认定本轮已经完成。</p></details>`).join('')}</section>
  <section class="collab-section"><h3>你的评价 · 后续动作</h3>${(c.feedback||[]).length?c.feedback.map(f=>`<article class="feedback-note"><small>原话 ${esc(f.sourceRef)} · ${date(f.at)}</small><blockquote>${esc(f.text)}</blockquote><p>${label(f.action.label,f.action.state)}</p><p>${label(f.principle.id+' · '+f.principle.label,f.principle.state)}</p><p>${label(f.adoption.label,f.adoption.state)}</p><p class="sheet-note">${esc(f.nextDispatch.label)}。评价、落实和新派活分开记。</p></article>`).join(''):'<p>尚未关联到这张卡的验收评价。</p><p class="sheet-note">你仍在原任务里说一句评价；这里显示证据，不让你再填一次表，也不自动当作验收通过。</p>'}</section><p class="sheet-note">协作记录只读本机 · 云端读取 ${data.metrics?.cloudCliCalls??0} 次 · 模型调用 ${data.metrics?.modelCalls??0} 次</p>`;
 }
 window.DeskCollaboration={render};
})();
