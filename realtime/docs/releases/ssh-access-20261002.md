# 2026-10-02 专用 SSH 连接恢复验证

任务：https://github.com/ohxiyu/xiyunews/issues/196；同一编辑负责人、agent/xiyunews-cloudflare 分支、Draft PR197。此记录只证明运维连接恢复，不是新仓服务器部署记录，应用版本没有变化。

## 授权与处理范围

运营者操作时明确确认：在本机生成 xiyunews 专用密钥，只追加公钥到已核对东京服务器 admin 账号，保留已有公钥和服务。本机配置 `/Users/minutesdr/.ssh/xiyunews_tokyo_config`，别名 `xiyunews-tokyo`，兼容 `fomobtc-tokyo`；私钥不离开运营者电脑、不进入仓库。独立 known_hosts 固定主机身份，StrictHostKeyChecking=yes、IdentitiesOnly=yes，公钥禁用 agent/X11/端口转发，不重置登录密码。

通过已登录阿里云命令助手读取主机 ED25519 指纹，再与本机扫描核对一致：`SHA256:XIxHR56+d7J8ntuK03ICzWZf7d2pEJQOFRl231KXE9Y`。命令助手执行 ID 为 `t-jpn6ytnli78r280`；追加前备份 `/home/admin/.ssh/authorized_keys.before-xiyunews-20261002T115457Z`，未覆盖已有密钥。没有把未经验证的扫描结果直接当可信身份，没有关闭主机校验。

## 验证结果

2026-10-02 19:55（Asia/Shanghai）专用 SSH 实际登录成功，hostname=iZ6wef42ecn2o4yvvow70gZ、用户 admin，sudo -n true 成功。原 ECDSA 与 ED25519 公钥仍在，新专用公钥指纹为 `SHA256:LKa9c4mYTTo8ftk++HBWYHsr0XRbIr7RMowl1AY1RU4`；目录 admin/0700，authorized_keys 为 admin/0600。

systemd fomobtc 仍 active/running，MainPID=219051、NRestarts=0，current 仍指向 `/opt/fomobtc/releases/b226b625cf3875b6693e0768d75d88d50b33c08d`。公网 health 回读版本2.6.0、source_commit等于该旧SHA、Telegram启用、三个spot分片live。没有重启服务、切换release、修改SQLite/业务环境、发送测试消息或改变阈值和信源。

## 未完成与下一步

本连接检查在19:55结束时尚未执行服务器版本切换，连接恢复本身不作为迁移完成证据。随后按此前服务器部署授权于20:01:45完成新仓SHA切换，详见 [独立部署记录](deploy-20261002-xiyunews-repository.md)；自然Telegram送达仍被群权限阻断，Cloudflare安全配置和边缘切换也未完成，不从本次SSH授权扩大权限。
