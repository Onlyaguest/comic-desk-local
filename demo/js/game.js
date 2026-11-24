/* =====================================================================
 *  平板里的两个小游戏（纯 Canvas，无依赖）
 *  用法：window.DESK_GAMES.whack(el) / .catchbean(el) → 返回 { destroy() }
 * ===================================================================== */
(function () {
  'use strict';

  function makeCanvas(el, w, h) {
    el.innerHTML = '';
    const c = document.createElement('canvas');
    c.className = 'game';
    c.width = w; c.height = h;
    el.appendChild(c);
    const ctx = c.getContext('2d');
    ctx.lineJoin = 'round';
    ctx.font = '700 16px "Comic Neue", sans-serif';
    return { c, ctx };
  }

  const ink = '#171310';
  function pop(ctx, x, y, text, color) {
    ctx.save();
    ctx.font = '700 14px "Comic Neue", sans-serif';
    ctx.fillStyle = color; ctx.strokeStyle = ink; ctx.lineWidth = 3;
    ctx.strokeText(text, x, y); ctx.fillText(text, x, y);
    ctx.restore();
  }
  function sfx(t) { if (window.playSfx) window.playSfx(t); }

  /* ---------------- 打地鼠 · Whack ---------------- */
  function whack(el) {
    const W = 400, H = 320;
    const { ctx } = makeCanvas(el, W, H);
    const cols = 3, rows = 3, gw = 108, gh = 88, ox = (W - cols * gw) / 2 + 10, oy = 62;
    const holes = [];
    for (let r = 0; r < rows; r++) for (let k = 0; k < cols; k++)
      holes.push({ x: ox + k * gw, y: oy + r * gh, up: false, t: 0, kind: 0 });

    const S = { score: 0, time: 20, best: +(localStorage.getItem('yz_desk_whack_best') || 0), over: false, active: -1, nextIn: 0 };
    let raf = 0, last = performance.now();

    function spawn() {
      S.active = (Math.random() * holes.length) | 0;
      const h = holes[S.active];
      h.up = true; h.t = 0;
      h.kind = Math.random() < 0.22 ? 1 : 0; // 1 = 金色，双倍
      S.life = h.kind ? 0.75 : 1.05;
    }

    function click(e) {
      if (S.over) { reset(); return; }
      const r = e.currentTarget.getBoundingClientRect();
      const x = (e.clientX - r.left) * W / r.width, y = (e.clientY - r.top) * H / r.height;
      for (const h of holes) {
        if (h.up && Math.hypot(x - (h.x + 18), y - (h.y + 14)) < 46) {
          h.up = false;
          const pts = h.kind ? 2 : 1;
          S.score += pts;
          sfx(h.kind ? 'coin' : 'hit');
          if (h.kind) pop(ctx, h.x + 6, h.y, '+2', '#ffb020');
        }
      }
    }
    el.addEventListener('click', click);

    function reset() {
      S.score = 0; S.time = 20; S.over = false; S.active = -1; S.nextIn = 0;
      holes.forEach((h) => (h.up = false));
    }

    function draw() {
      ctx.fillStyle = '#fff6e0'; ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = '#ffd23f'; ctx.fillRect(0, 0, W, 46);
      ctx.strokeStyle = ink; ctx.lineWidth = 4; ctx.strokeRect(2, 2, W - 4, H - 4);
      ctx.beginPath(); ctx.moveTo(0, 46); ctx.lineTo(W, 46); ctx.stroke();
      ctx.fillStyle = ink; ctx.font = '400 26px "Bangers", cursive';
      ctx.fillText('WHACK! 打地鼠', 14, 34);
      ctx.font = '700 16px "Comic Neue", sans-serif';
      ctx.fillText('★ ' + S.score, W - 150, 32);
      ctx.fillText('⏱ ' + Math.max(0, S.time).toFixed(1), W - 74, 32);

      for (const h of holes) {
        ctx.save();
        // hole
        ctx.fillStyle = '#c98c45'; ctx.strokeStyle = ink; ctx.lineWidth = 4;
        ctx.beginPath(); ctx.ellipse(h.x + 18, h.y + 30, 40, 20, 0, 0, 7); ctx.fill(); ctx.stroke();
        if (h.up) {
          const k = Math.min(1, h.t * 8);
          const yy = h.y + 30 - 46 * k;
          ctx.fillStyle = h.kind ? '#ffb020' : '#8fd14f';
          ctx.beginPath(); ctx.arc(h.x + 18, yy, 26, 0, 7); ctx.fill(); ctx.stroke();
          // ears
          ctx.beginPath(); ctx.arc(h.x - 2, yy - 18, 9, 0, 7); ctx.fill(); ctx.stroke();
          ctx.beginPath(); ctx.arc(h.x + 38, yy - 18, 9, 0, 7); ctx.fill(); ctx.stroke();
          // eyes
          ctx.fillStyle = ink;
          ctx.beginPath(); ctx.arc(h.x + 9, yy - 4, 3.4, 0, 7); ctx.fill();
          ctx.beginPath(); ctx.arc(h.x + 27, yy - 4, 3.4, 0, 7); ctx.fill();
          if (h.kind) pop(ctx, h.x - 2, yy - 26, '★', '#fff');
        }
        ctx.restore();
      }

      if (S.over) {
        ctx.fillStyle = 'rgba(23,19,16,.82)'; ctx.fillRect(0, 0, W, H);
        ctx.fillStyle = '#fff'; ctx.font = '400 40px "Bangers", cursive';
        ctx.fillText('TIME UP!', 130, 150);
        ctx.font = '700 22px "Comic Neue", sans-serif';
        ctx.fillText('得分 ' + S.score, 158, 186);
        ctx.font = '700 16px "Comic Neue", sans-serif';
        ctx.fillText('最高分 ' + S.best + ' · 点一下再来', 110, 220);
      }
    }

    function loop(t) {
      const dt = Math.min(0.05, (t - last) / 1000); last = t;
      if (!S.over) {
        S.time -= dt;
        if (S.time <= 0) { S.over = true; S.time = 0; if (S.score > S.best) { S.best = S.score; localStorage.setItem('yz_desk_whack_best', S.best); } sfx('over'); }
        if (S.active >= 0 && holes[S.active].up) {
          const h = holes[S.active]; h.t += dt;
          if (h.t > S.life) { h.up = false; S.active = -1; }
        } else {
          S.nextIn -= dt;
          if (S.nextIn <= 0) { spawn(); S.nextIn = 0.45 + Math.random() * 0.45; }
        }
      }
      draw();
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);
    return { destroy() { cancelAnimationFrame(raf); el.removeEventListener('click', click); } };
  }

  /* ---------------- 接咖啡豆 · Catch ---------------- */
  function catchbean(el) {
    const W = 400, H = 320;
    const { ctx } = makeCanvas(el, W, H);
    const S = { score: 0, time: 20, over: false, best: +(localStorage.getItem('yz_desk_catch_best') || 0) };
    const basket = { x: W / 2, y: H - 34, w: 78, h: 26 };
    const beans = [];
    let spawnT = 0, raf = 0, last = performance.now(), keyL = false, keyR = false;

    function move(clientX) {
      const r = el.getBoundingClientRect();
      basket.x = (clientX - r.left) * W / r.width;
    }
    function pmove(e) { move(e.clientX); }
    function touch(e) { if (e.touches[0]) move(e.touches[0].clientX); }
    function kd(e) { if (e.key === 'ArrowLeft') keyL = true; if (e.key === 'ArrowRight') keyR = true; }
    function ku(e) { if (e.key === 'ArrowLeft') keyL = false; if (e.key === 'ArrowRight') keyR = false; }
    function click() { if (S.over) reset(); }
    el.addEventListener('pointermove', pmove);
    el.addEventListener('touchmove', touch, { passive: true });
    el.addEventListener('click', click);
    window.addEventListener('keydown', kd); window.addEventListener('keyup', ku);

    function reset() { S.score = 0; S.time = 20; S.over = false; beans.length = 0; }
    function spawn() {
      beans.push({ x: 30 + Math.random() * (W - 60), y: -20, v: 70 + Math.random() * 70, gold: Math.random() < 0.18, rot: 0 });
    }

    function draw() {
      // bg
      const g = ctx.createLinearGradient(0, 0, 0, H);
      g.addColorStop(0, '#bfe3ff'); g.addColorStop(0.55, '#eaf6ff'); g.addColorStop(1, '#c98c45');
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      ctx.strokeStyle = ink; ctx.lineWidth = 4; ctx.strokeRect(2, 2, W - 4, H - 4);
      ctx.fillStyle = 'rgba(23,19,16,.9)';
      ctx.font = '400 24px "Bangers", cursive'; ctx.fillText('CATCH! 接摩拉', 14, 30);
      ctx.font = '700 16px "Comic Neue", sans-serif';
      ctx.fillText('★ ' + S.score, W - 110, 26); ctx.fillText('⏱ ' + Math.max(0, S.time).toFixed(1), W - 60, 26);

      for (const b of beans) {
        ctx.save(); ctx.translate(b.x, b.y); ctx.rotate(Math.sin(b.rot) * 0.5);
        ctx.strokeStyle = ink; ctx.lineWidth = 3;
        if (b.gold) {
          // 原石：蓝白菱形，双倍分
          ctx.fillStyle = '#7fd6ff';
          ctx.beginPath(); ctx.moveTo(0, -16); ctx.lineTo(12, 0); ctx.lineTo(0, 16); ctx.lineTo(-12, 0); ctx.closePath(); ctx.fill(); ctx.stroke();
          ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.moveTo(0, -9); ctx.lineTo(5, 0); ctx.lineTo(0, 9); ctx.lineTo(-5, 0); ctx.closePath(); ctx.fill();
        } else {
          // 摩拉：金币 + 岩纹菱孔
          ctx.fillStyle = '#e8b64c';
          ctx.beginPath(); ctx.ellipse(0, 0, 14 * Math.max(.35, Math.abs(Math.cos(b.rot))), 14, 0, 0, 7); ctx.fill(); ctx.stroke();
          ctx.fillStyle = '#8a5a1c'; ctx.beginPath(); ctx.moveTo(0, -5); ctx.lineTo(4, 0); ctx.lineTo(0, 5); ctx.lineTo(-4, 0); ctx.closePath(); ctx.fill();
        }
        ctx.restore();
      }
      // basket
      ctx.fillStyle = '#e5484d'; ctx.strokeStyle = ink; ctx.lineWidth = 4;
      ctx.beginPath(); ctx.roundRect(basket.x - basket.w / 2, basket.y, basket.w, basket.h, 8); ctx.fill(); ctx.stroke();
      ctx.fillStyle = '#ffd23f';
      ctx.beginPath(); ctx.roundRect(basket.x - basket.w / 2 + 6, basket.y + 5, basket.w - 12, 8, 4); ctx.fill();

      if (S.over) {
        ctx.fillStyle = 'rgba(23,19,16,.82)'; ctx.fillRect(0, 0, W, H);
        ctx.fillStyle = '#fff'; ctx.font = '400 38px "Bangers", cursive'; ctx.fillText('TIME UP!', 132, 148);
        ctx.font = '700 22px "Comic Neue", sans-serif'; ctx.fillText('攒到 ' + S.score + ' 摩拉', 140, 184);
        ctx.font = '700 16px "Comic Neue", sans-serif'; ctx.fillText('最高分 ' + S.best + ' · 点一下再来', 110, 218);
      }
    }

    function loop(t) {
      const dt = Math.min(0.05, (t - last) / 1000); last = t;
      if (!S.over) {
        S.time -= dt;
        if (S.time <= 0) { S.over = true; S.time = 0; if (S.score > S.best) { S.best = S.score; localStorage.setItem('yz_desk_catch_best', S.best); } sfx('over'); }
        if (keyL) basket.x -= 340 * dt; if (keyR) basket.x += 340 * dt;
        basket.x = Math.max(basket.w / 2, Math.min(W - basket.w / 2, basket.x));
        spawnT -= dt; if (spawnT <= 0) { spawn(); spawnT = 0.42 + Math.random() * 0.5; }
        for (let i = beans.length - 1; i >= 0; i--) {
          const b = beans[i];
          b.y += b.v * dt; b.rot += dt * 6;
          if (b.y > basket.y - 6 && b.y < basket.y + basket.h + 8 && Math.abs(b.x - basket.x) < basket.w / 2 + 8) {
            S.score += b.gold ? 2 : 1; beans.splice(i, 1); sfx(b.gold ? 'coin' : 'hit'); continue;
          }
          if (b.y > H + 20) beans.splice(i, 1);
        }
      }
      draw();
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);
    return {
      destroy() {
        cancelAnimationFrame(raf);
        el.removeEventListener('pointermove', pmove);
        el.removeEventListener('touchmove', touch);
        el.removeEventListener('click', click);
        window.removeEventListener('keydown', kd); window.removeEventListener('keyup', ku);
      },
    };
  }

  window.DESK_GAMES = { whack, catchbean };
})();
