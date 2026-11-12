始终用简体中文。先读 README.md 与 docs/DATA-CONTRACT.md。
不修改 data/ 中已有账本历史。生成的页面快照不提交 Git。默认样例不得扫描用户 HOME 或调用外部 CLI。
修改代码后运行 bash verify.sh；发布前运行 python3 tools/audit_release.py。
仓库保持私有，禁止自动改成公开或改写远端历史。
