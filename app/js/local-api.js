/* =====================================================================
 *  本地版 · 动作桥
 *  ---------------------------------------------------------------------
 *  Cohub 版靠 App Action + SDK 跑 notes / todos / refresh / digest。
 *  本地版没有平台，一律走本机 `desk serve` 的 /api/action。
 *  这样 app.js 里只换三行，引擎本身不用知道数据从哪来。
 * ===================================================================== */
(function () {
  window.localAction = async function (action, input) {
    const r = await fetch('/api/action', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ action: String(action), input: input || {} }),
    });
    let j;
    try { j = await r.json(); } catch (e) { throw new Error('本地服务返回的不是 JSON（端口对吗？）'); }
    if (!j || !j.ok) throw new Error((j && j.error) || '本地操作失败');
    return j;
  };
})();
