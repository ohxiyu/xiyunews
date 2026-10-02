# xiyunews 完整历史整合恢复

Issue: https://github.com/ohxiyu/xiyunews/issues/172

运营者确认原Bot Token已撤销，解除完整旧仓历史的上传门槛。不读取、输出或调用旧凭据，不修改原提交历史；subtree不squash，合并PR必须merge commit，并验证原main完整SHA为新main祖先。项目管理名称统一为xiyunews，README和模块规则标题同步；服务路径、systemd、Python内部名称、SQLite、阈值、地址簿、目的地与依赖保持不变。

本次根项目已同步2026-10-02的main修复，修复交接与Telegram文档冲突时保留最新运营者决策、旧域清理事实和安全条件。Python3.11/3.12及根测试正在重新执行；真实结果记录在根发布证据和PR，不复用昨天测试当成本次验收。

仓库整合不是服务器发布。现役服务器仍是原2.6.0与旧source_commit；原可信SSH连接缺失，新合并SHA、自然回执、看门狗状态尚未验收，不提前退役旧仓或删除现役资源。
