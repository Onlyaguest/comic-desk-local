始终用简体中文。先读 README.md 与 docs/DATA-CONTRACT.md。
不修改 data/ 中已有账本历史。生成的页面快照不提交 Git。默认样例不得扫描用户 HOME、读取全局规则/群聊或调用外部 CLI。
融合源码在 lib/desk/fusion/ 和 app/fusion/；保持现有配色与交互，样例仅放 samples/。真实快照、协作角色、回执及图片缓存均在被忽略的 data/fusion/。
修改代码后运行 bash verify.sh；发布前运行 python3 tools/smoke_release.py 与 python3 tools/audit_release.py --history。审计与空 HOME 自检都包含未暂存候选源码，禁止仅验证旧 HEAD。
当前仓库已公开可见；禁止自动修改可见性、改写远端历史或添加本机主页/自启配置。commit / push 仍须用户确认，先交改动清单、隐私扫描和测试结果。
