/* 本地版 · Session 绑定表
 * 不连任何平台；想给物件挂一个本地入口，就把 path 或 url 填进 bind。
 *   open: 'panel'  先开面板，面板底部多一个「↗ 打开」按钮
 *         'direct' 点击直接打开
 *   path: 本地文件或文件夹（支持 ~）
 *   url:  http(s) 或 obsidian:// 等
 */
window.DESK_SESSIONS = {
  space: '',
  url: '{url}',
  bind: {},
};
