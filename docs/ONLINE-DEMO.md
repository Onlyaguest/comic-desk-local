# 在线样例版

不用安装、点开就能逛：<https://raw.githack.com/Onlyaguest/comic-desk-local/main/demo/index.html>

- 内容是 `samples/` 里的虚构数据，和本机「离线样例模式」看到的一样；第一次打开会自动「带我逛一圈」（6 站），顶栏也有按钮随时再逛。
- **只能看**：勾选待办、写便签、改稿等会改数据的操作，在线版只弹一句「要下载到本机才能用」。不联网到别处、不统计、不花 token。
- 想用自己的 Claude Code / Codex 会话：下载仓库，在 Mac 上双击 `start.command`（见 README）。

## 怎么做出来的

`python3 tools/build_online_demo.py` 会复制一份干净源码，在空 HOME、样例模式下起本机服务，把前端会调的接口各请求一次存进 `demo/_rec/`，把页面里的根路径改成相对路径，并在每页最前面加载 `demo/_demo/shim.js`：它把 `fetch` 和图片地址对到录好的文件上。生成物是纯静态文件，任何能按路径发文件的地方都能放。

现在的托管方式是 [githack](https://raw.githack.com/) 直接转发 GitHub 上 `main` 分支的 `demo/` 文件：不需要 GitHub Actions 或 Pages，推送到 main 几分钟后生效。以后开了 GitHub Pages 或其他静态托管，把 `demo/` 原样放上去即可，不用改代码。

## 什么时候重新生成

改了 `app/`、`lib/` 里影响页面的代码，或改了 `samples/` 后：

```sh
python3 tools/build_online_demo.py
python3 -m unittest tests.test_online_demo
python3 tools/audit_release.py --history
```

再连同 `demo/` 一起提交。`demo/` 是生成物，不要手改。
