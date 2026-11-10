/* =====================================================================
 *  主机 · 「在跑什么」里的三条活指标：专注 / 心情 / 茶温
 *  ---------------------------------------------------------------------
 *  不再随机乱跳。每条都是「时间 + 你在桌上做过的事」算出来的连续曲线，
 *  所以过去一小时的走势也能当场画出来：
 *    茶温：牛顿冷却。点茶盏「再续一盏」= 倒回 88°C，之后按室温 24°C 慢慢凉（约 18 分钟降一大截）。
 *    专注：一天的精力曲线（上午高、午后低、15–17 点小高峰、17:30 熔断后往下走）
 *          + 番茄钟节奏（25 分钟慢慢爬升，5 分钟休息时回落）
 *          + 戴上耳机（专注模式）期间 +12。
 *    心情：今天 agent 回复的比例定底色，叠两条慢波；续茶、晒太阳、动一动、攒摩拉会让它鼓起来再慢慢回落。
 *    （茶盏面板的「光糖动茶」每点一次都会记一笔；「动」还会让专注回升一点。）
 *  事件只存在你的浏览器（localStorage），不回写任何地方。
 * ===================================================================== */
(function () {
  'use strict';
  const KEY = 'yz_desk_vibe_events_v1';
  const MIN = 60e3, ROOM = 24, HOT = 88, TAU = 18 * MIN;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const load = () => { try { const v = JSON.parse(localStorage.getItem(KEY) || '[]'); return Array.isArray(v) ? v : []; } catch (e) { return []; } };
  let events = load();
  function record(kind) {
    events.push({ k: kind, t: Date.now() });
    events = events.filter((e) => Date.now() - e.t < 36 * 3600e3).slice(-200);
    try { localStorage.setItem(KEY, JSON.stringify(events)); } catch (e) {}
  }
  const last = (kind, t) => { let r = null; for (const e of events) if (e.k === kind && e.t <= t && (!r || e.t > r.t)) r = e; return r; };
  const hourOf = (t) => { const d = new Date(t); return d.getHours() + d.getMinutes() / 60 + d.getSeconds() / 3600; };

  /* ---- 茶温 ---- */
  function tea(t) {
    const r = last('tea', t);
    if (!r) return { v: ROOM, unit: '°C', pct: ROOM, text: '还没泡茶。点桌上的茶盏「再续一盏」', cause: 'none' };
    const v = ROOM + (HOT - ROOM) * Math.exp(-(t - r.t) / TAU);
    const mins = Math.round((t - r.t) / MIN);
    const text = v > 70 ? `刚续上，烫，先晾一晾（${mins} 分钟前）`
      : v > 52 ? '正好入口 🍵'
      : v > 36 ? '温了，趁现在喝'
      : '凉透了，再续一盏？';
    return { v, unit: '°C', pct: v, text, cause: v <= 36 ? 'cold' : 'ok' };
  }

  /* ---- 专注 ---- */
  const DAY = [[0, 18], [7, 32], [9.5, 76], [11.5, 84], [12.5, 62], [13.5, 52], [15, 70], [16.5, 80], [17.5, 58], [18.5, 36], [22, 30], [24, 18]];
  const dayCurve = (h) => { for (let i = 1; i < DAY.length; i++) if (h <= DAY[i][0]) { const [h0, v0] = DAY[i - 1], [h1, v1] = DAY[i]; const k = (h - h0) / (h1 - h0); return v0 + (v1 - v0) * (0.5 - Math.cos(k * Math.PI) / 2); } return 18; };
  function headphonesOn(t) { const on = last('focus-on', t), off = last('focus-off', t); return !!on && (!off || off.t < on.t); }
  function focus(t) {
    const h = hourOf(t);
    const phase = ((t / MIN) % 30 + 30) % 30;               // 半小时一个番茄：0–25 专注，25–30 休息
    const pomo = phase < 25 ? -4 + 12 * (phase / 25) : 8 - 12 * Math.sin((phase - 25) / 5 * Math.PI / 2);
    const hp = headphonesOn(t) ? 12 : 0;
    const mv = last('move', t); const moved = mv ? 8 * Math.exp(-(t - mv.t) / (20 * MIN)) : 0;   // 起来动一动，回来更专注
    const v = clamp(dayCurve(h) + pomo + hp + moved + 2 * Math.sin(t / (3.7 * MIN)), 5, 98);
    const text = hp ? '戴着耳机 · 专注模式'
      : h >= 17.5 && h < 19 ? '17:30 熔断了，只收口不开新坑'
      : phase >= 25 ? `番茄钟休息中，还剩 ${Math.ceil(30 - phase)} 分钟`
      : h >= 12.5 && h < 14 ? '午后犯困时段'
      : v > 75 ? '进入状态' : v > 50 ? '慢慢热起来' : '电量偏低';
    return { v, unit: '%', pct: v, text };
  }

  /* ---- 心情 ---- */
  function mood(t) {
    const T = window.DESK_TODAY && window.DESK_TODAY.stats;
    const base = 62 + (T && T.items ? 18 * (T.replied || 0) / T.items : 8);
    let bump = 0, why = '';
    for (const e of events) {
      if (e.t > t) continue;
      const dt = t - e.t;
      if (e.k === 'tea') { const b = 9 * Math.exp(-dt / (25 * MIN)); bump += b; if (b > 3 && !why) why = '刚续了茶'; }
      if (e.k === 'mora') { const b = 4 * Math.exp(-dt / (12 * MIN)); bump += b; if (b > 1.5) why = '摩拉又多了一枚'; }
      if (e.k === 'light') { const b = 6 * Math.exp(-dt / (40 * MIN)); bump += b; if (b > 2 && !why) why = '晒过太阳了'; }
      if (e.k === 'move') { const b = 4 * Math.exp(-dt / (30 * MIN)); bump += b; if (b > 1.5 && !why) why = '刚动了动'; }
      if (e.k === 'sugar') { const b = 3 * Math.exp(-dt / (40 * MIN)); bump += b; }
    }
    const h = hourOf(t);
    const v = clamp(base + Math.min(bump, 22) + 6 * Math.sin(t / (47 * MIN) * 2 * Math.PI) + 3 * Math.sin(t / (13 * MIN) * 2 * Math.PI + 1.3) - (h >= 23 || h < 6 ? 8 : 0), 10, 99);
    const text = why ? `${why} ☺` : v > 82 ? '挺开心' : v > 66 ? '平静' : v > 50 ? '有点闷' : '需要摸摸头';
    return { v, unit: '%', pct: v, text };
  }

  const KINDS = { focus, mood, tea };
  function series(kind, t, mins = 60, step = 1) {
    const f = KINDS[kind], out = [];
    for (let m = mins; m >= 0; m -= step) out.push(f(t - m * MIN).v);
    return out;
  }

  // 主机里的风扇转速跟着专注走：越专注转得越快
  function fan() {
    const v = focus(Date.now()).v;
    document.documentElement.style.setProperty('--fan-s', (4.2 - v / 30).toFixed(2) + 's');
  }
  fan(); setInterval(fan, 15000);

  window.DESK_VIBE = { record, value: (k, t) => KINDS[k](t || Date.now()), series };
})();
