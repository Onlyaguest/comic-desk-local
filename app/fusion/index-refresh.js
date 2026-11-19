/* 新版取消开页自动同步；原索引同步仅由明确的刷新操作触发。 */
(() => {
 let pending;
 window.refreshDeskIndex=()=>pending||(pending=(async()=>{
  const r=await fetch('/api/desk/sync-index',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
  const j=await r.json();if(!r.ok||!j.ok)throw Error(j.error||'索引更新未成功');
  window.dispatchEvent(new CustomEvent('desk:index-updated',{detail:j}));return j;
 })().finally(()=>pending=null));
})();
