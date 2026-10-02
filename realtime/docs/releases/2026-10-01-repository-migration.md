# 私有主仓 realtime 并入

Issue: https://github.com/ohxiyu/xiyunews/issues/172

从旧 main 7807126d8c7cdb51e18f0b91ba27f500271f9f08 以不 squash 的 subtree 导入。合并必须使用 merge commit 保留祖先，不能 squash/rebase 本阶段 PR。原 LICENSE、发布记录与提交历史原样保留。运行版本仍为 2.6.0；没有业务或依赖变更，不把代码合并记为服务器部署。

两边规则冲突时根 AGENTS 优先：采用 agent/*、一 Issue 一 PR、根与 realtime 各自交接/发布记录。旧 agent.md 的详细接手说明保留；不为统一入口删除操作手册。check_repository 将 git diff 的路径限定并转换为 realtime 相对路径，git ls-files 限定当前目录；不忽略本模块规则、不扫描主项目依赖。

CI 独立矩阵 3.11/3.12；在 realtime 内运行 ruff、mypy、pytest（TELEGRAM_ENABLED=false）、compileall、check_repository 和看门狗 Node。根 CI 与依赖不合并，工作流原入口 .github/workflows/ci.yml 是唯一路径。

配置阈值、地址簿、systemd、nginx、env 和 SQLite 路径保持字节不变。部署包仅包含新仓 realtime 前缀，解包 strip-components=1 后目录结构与旧 release 相同。

本机没有运营者 SSH 配置，因此服务器切换、新 SHA、自然 message_id、看门狗恢复未验证；旧仓不提前归档。线上只读 health 仍为旧源码 b226b625cf3875b6693e0768d75d88d50b33c08d，三个现货分片 live。
