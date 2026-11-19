/* 可选浏览器回归：需自行提供 playwright 与浏览器；默认全程离线。 */
const {chromium}=require('playwright');
const assert=require('node:assert/strict'), fs=require('node:fs'),path=require('node:path');
(async()=>{
 const out=process.env.DESK_QA_DIR||'/tmp/comic-desk-browser-qa';fs.mkdirSync(out,{recursive:true});
 const base=process.env.DESK_QA_URL||'http://127.0.0.1:17998';
 const browser=await chromium.launch({headless:true,...(process.env.DESK_CHROME?{executablePath:process.env.DESK_CHROME}:{})});
 const context=await browser.newContext({viewport:{width:1600,height:1100}});const page=await context.newPage();
 const checks=[],errors=[],posts=[],external=[],bad=[];const ok=s=>{checks.push(s);console.log('通过',s)};
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST')posts.push(r.url())});
 page.on('response',r=>{if(r.status()>=400)bad.push([r.status(),r.url()])});
 await page.route('**/*',route=>{const u=new URL(route.request().url());if(['http:','https:'].includes(u.protocol)&&!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.origin);return route.abort();}return route.continue();});
 await page.goto(base,{waitUntil:'networkidle'});await page.locator('.mini-paper').first().waitFor();
 assert.equal(posts.filter(u=>/\/(?:sync-index|refresh|image-fetch)$/.test(u)).length,0);assert.deepEqual(external,[]);ok('首页无自动刷新、取云图或外部请求');
 assert((await page.locator('body').innerText()).includes('离线样例'));ok('页面明确标注离线虚构数据');
 assert.equal(await page.locator('.tray,.board-tray').count(),0);assert((await page.locator('#noteCards>.note').count())>=3);ok('关注复用便签墙，原便签保留');
 await page.locator('#nearBoard').click();assert.equal(await page.locator('.board-column').count(),6);assert.equal(await page.locator('.freshness-slip').count(),4);ok('四路时效与六种状态可见');
 for(const source of ['codex','claude','cohub','mirasim']){await page.locator('#sourceFilter').selectOption(source);assert(await page.locator('.focus-board .paper-card').count()>0);}
 ok('四个来源均可单独筛选');
 await page.locator('#sourceFilter').selectOption('');await page.locator('#boardSearch').fill('不存在的样例关键字');assert.equal(await page.locator('.focus-board .paper-card').count(),0);await page.locator('#boardSearch').fill('');ok('纸卡搜索可用');
 await page.locator('.focus-board [data-card="sample:review"]').click();await page.locator('[data-turn-sheet]').click();await page.getByText('回写内容已核对',{exact:true}).waitFor();
 assert((await page.locator('.collaboration-body').innerText()).includes('动作证据已核对'));ok('背面显示角色、已核对回写与反馈动作');
 await page.screenshot({path:path.join(out,'纸卡背面.png'),animations:'disabled'});
 await page.locator('.paper-sheet [data-pin]').click();await page.locator('.sheet-close').click();await page.locator('#leaveBoard').click();assert.equal(await page.locator('.wall-pin').count(),1);
 await page.reload({waitUntil:'networkidle'});await page.locator('.wall-pin').waitFor();assert.equal(await page.locator('.wall-pin').count(),1);ok('夹到便签墙并在刷新后保留');
 await page.screenshot({path:path.join(out,'脱敏桌面.png'),animations:'disabled'});
 await page.locator('#arrangeDesk').click();assert.equal(await page.locator('#arrangeDesk').getAttribute('aria-pressed'),'true');await page.locator('#resetDesk').click();await page.locator('#arrangeDesk').click();ok('摆放模式和归位可用');
 await page.locator('.poster').click();await page.locator('.album-tile').first().waitFor();assert.equal(await page.locator('.album-tile').count(),2);ok('图像册包含离线成品与过程图');
 await page.locator('#imageQuery').fill('成品');await page.waitForFunction(()=>document.querySelectorAll('.album-tile').length===1);await page.locator('#imageQuery').fill('');await page.waitForFunction(()=>document.querySelectorAll('.album-tile').length===2);ok('图片搜索与目录过滤可用');
 await page.locator('.album-photo').first().click();await page.locator('[data-zoom]').click();await page.locator('.pswp--open').waitFor();await page.keyboard.press('Escape');await page.locator('.pswp--open').waitFor({state:'hidden'});ok('PhotoSwipe本地加载并可关闭返回');
 await page.locator('[data-back]').click();await page.locator('#albumClose').click();
 await page.locator('#nearBoard').click();await page.locator('#refreshIndex').click();await page.waitForFunction(()=>document.querySelector('#refreshIndex')?.disabled===false);ok('样例手动更新仍可用');await page.locator('#leaveBoard').click();
 await page.locator('.fusion-live').waitFor({state:'hidden'});await page.setViewportSize({width:390,height:844});await page.locator('#nearBoard').click();assert((await page.evaluate(()=>document.documentElement.scrollWidth))<=390);await page.screenshot({path:path.join(out,'手机事项板.png'),animations:'disabled'});ok('390px手机事项板无整页横向溢出');
 await page.locator('#leaveBoard').click();await page.locator('.poster').click();await page.locator('.album-tile').first().waitFor();assert((await page.evaluate(()=>document.documentElement.scrollWidth))<=390);await page.screenshot({path:path.join(out,'手机图像册.png'),animations:'disabled'});ok('390px手机图像册无整页横向溢出');
 assert.equal(posts.filter(u=>/image-fetch/.test(u)).length,0);assert.deepEqual(external,[]);assert.deepEqual(errors,[]);assert.deepEqual(bad,[]);ok('全流程无JS异常、资源缺失或远端取图');
 fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify({checks,errors,posts,external,bad},null,2));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
