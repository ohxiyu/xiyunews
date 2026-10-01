# 阶段 3：保留历史并入实时服务

Issue: https://github.com/ohxiyu/xiyunews/issues/172

基线为 PR171 合并 d5360740bb571c6bf95d3fcb631a54ac00634e9f；旧项目 main 为 7807126d8c7cdb51e18f0b91ba27f500271f9f08。使用 git subtree add --prefix=realtime，不加 squash，导入提交 2e4577db3dfafd6252882efc03e9fb751ceaca21；合并 PR 必须 merge commit，之后再次以 merge-base --is-ancestor 验证。

两个应用完全隔离依赖、src、数据库与 Telegram 目的地；主站版式未变。根 AGENTS 优先，独立 CI 采用路径门控的 Python 3.11/3.12，执行 ruff/mypy/pytest/compileall/子仓契约/看门狗 Node；根治理也要求 realtime 改动提供根交接与证据。历史发布记录、许可证、配置阈值、地址簿、systemd、nginx 原样保留。

部署包从新仓完整 SHA archive realtime，解包 strip-components=1；不改服务路径与运行方式。私有历史导入前，两仓已核对 private=true；扫描覆盖 654 个历史 blob 的常见高置信凭据模式，不等于全面安全审计。两份已删除的旧 README（workers/polymarket/README.md、workers/truth_machine/README.md）第 346 行含同一疑似 Telegram Token，非明显占位符；不能确认已撤销，未调用该凭据、未输出其内容。两个仓库的协作者目前均只有 ohxiyu，但私有不替代密钥撤销；本阶段历史仍仅在本地，未推送。需要运营者确认旧凭据已撤销后才能保留完整历史继续，不能擅自改写历史来规避原要求。

Python 3.11/3.12 本地各 61 项 realtime 测试、ruff、mypy、compileall、仓库契约和 3 项看门狗 Node 通过；主项目 929 项隔离测试与治理通过。远端 CI 尚未验证；PR 不在历史密钥状态未明确时建立或合并。

## 前阶段真实部署回写

PR169、PR171 已合并。Deploy Docs 36823514928 成功，产物 7fe7ed4c15610534c3d1609552616cf6dfc9cd4a 的 Cloudflare check 成功，生产部署 c8c57131-fafc-4db1-bcb7-efea8feb0317；xiyu.news HTTPS 首页现为 200，title/canonical 为新域。旧域开关仍 false，因此 200 是过渡状态，不称 301 验收通过。

Source commit: d5360740bb571c6bf95d3fcb631a54ac00634e9f（阶段 2 调度器）。
Worker version: ac52cef1-d767-4d0e-903b-bfe1886b3b1f。
Deployment: wrangler deploy --keep-vars，显式新仓、临时旧公共检查地址，原 Secrets 保留。
Verification: health 仓库 ohxiyu/xiyunews，public_site_url 仍为过渡 bmt.news；ready 返回 actions:write 和 contents:read；自然采集派发尚未出现。阶段 3 服务器仍是旧版本 2.6.0/b226b625cf3875b6693e0768d75d88d50b33c08d，三个分片 live；本机缺少 SSH 配置，未切换。
Rollback: 没有执行回滚；调度器保留 Durable Object 和重试记录，实时旧 release 保留，切换需要持有 SSH 的运营者电脑。
