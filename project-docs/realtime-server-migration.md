# 新仓实时服务迁移操作清单

服务器版本已于2026-10-02 20:01:45（Asia/Shanghai）切换到新仓PR195合并SHA d6a9d3f29ef93c138842342c973b3049fb7bc252，三个现货分片live，备份与配置保留验证通过。旧Bot在只读群中为普通成员，当时自然消息被拒绝；21:03又按运营者明确授权换为原群管理员@xiyunewsbot，原群与话题3/5/7保持，新Bot自然回执仍待验证，旧资源继续保留。版本迁移见 [原部署记录](../realtime/docs/releases/deploy-20261002-xiyunews-repository.md)，后续凭据切换见 [新Bot记录](../realtime/docs/releases/deploy-20261002-xiyunews-bot.md)。旧实时 main 是新仓 origin/main 的祖先，私钥和验证码不发送到聊天、仓库或服务器。下面是复用的操作清单，不代表其每个验收条件已经完成。

## 已恢复的专用连接（2026-10-02）

运营者在操作时确认生成专用密钥并追加公钥后，本机连接配置为 `/Users/minutesdr/.ssh/xiyunews_tokyo_config`，主机别名为 `xiyunews-tokyo`，兼容 `fomobtc-tokyo`。通过已登录阿里云控制台读取主机 ED25519 指纹，再与本机扫描比对一致：`SHA256:XIxHR56+d7J8ntuK03ICzWZf7d2pEJQOFRl231KXE9Y`。独立 known_hosts 与 StrictHostKeyChecking=yes 固定此身份，不修改全局 SSH 配置；私钥只在运营者电脑，公钥禁用 agent、X11 和端口转发。

实际验证已通过 admin 登录和免交互 sudo，保留原两把公钥，并在服务器保存追加前备份。systemd 仍 active/running，MainPID=219051、NRestarts=0，未重启服务。公网 health 仍是旧版本 SHA、三个现货分片 live；连接恢复不是服务器版本迁移完成。详见 [连接验证记录](../realtime/docs/releases/ssh-access-20261002.md)。

## 现有东京服务迁移清单（阶段 4）

仅在阶段 3 使用 merge commit 合并、确认旧历史凭据已撤销后执行。以下迁移不重装 systemd、nginx、证书或看门狗，不改阈值、地址簿、群组、数据库位置与密钥；没有 SSH 配置或既有主机指纹时停止，不使用 StrictHostKeyChecking=no。所有标为“服务器”的命令在同一次 SSH 会话中执行，保留变量；命令不是本轮已执行的部署证据。

### 1. 运营者电脑：核对实际合并 SHA 与专用连接

```bash
set -euo pipefail
XIYU_SSH_CONFIG='/Users/minutesdr/.ssh/xiyunews_tokyo_config'
SOURCE_SHA='填写阶段3实际合并的40位SHA'
test -f "$XIYU_SSH_CONFIG"
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]
git fetch origin
git merge-base --is-ancestor "$SOURCE_SHA" origin/main
git merge-base --is-ancestor 7807126d8c7cdb51e18f0b91ba27f500271f9f08 "$SOURCE_SHA"
git cat-file -e "$SOURCE_SHA:realtime/requirements.lock"
ssh -F "$XIYU_SSH_CONFIG" -o StrictHostKeyChecking=yes fomobtc-tokyo \
  'systemctl is-active fomobtc; readlink -f /opt/fomobtc/current'
```

记录当前 release 路径和健康接口的 source_commit。SOURCE_SHA 必须是新仓中包含 realtime/ 与旧历史的实际合并提交；本次服务器已使用PR195合并SHA d6a9d3f29ef93c138842342c973b3049fb7bc252，旧b226b625release作为上一版保留。未来重复执行时使用当时已审核的新合并SHA，不能覆盖本次已存在目录，实际部署证据以本文件开头链接的记录为准。

### 2. 运营者电脑：传送独立模块

目标目录已存在时停止，避免覆盖旧 release；失败留下的新空目录也不自动删除。SSH 保持既有账号、主机别名和已知指纹。

```bash
ssh -F "$XIYU_SSH_CONFIG" -o StrictHostKeyChecking=yes fomobtc-tokyo \
  "test ! -e /opt/fomobtc/releases/$SOURCE_SHA && \
   sudo install -d -o fomobtc -g fomobtc /opt/fomobtc/releases/$SOURCE_SHA"
git archive "$SOURCE_SHA" realtime | \
  ssh -F "$XIYU_SSH_CONFIG" -o StrictHostKeyChecking=yes fomobtc-tokyo \
    "sudo -u fomobtc tar -x --strip-components=1 -C /opt/fomobtc/releases/$SOURCE_SHA"
ssh -t -F "$XIYU_SSH_CONFIG" -o StrictHostKeyChecking=yes fomobtc-tokyo
```

### 3. 服务器：安装新 release，停机后备份

下面重新填写同一个 SHA；不从旧仓 tag 或短 SHA 推断。先安装独立 venv，再停服务缩短停机时间，安装失败时旧服务不受影响。

```bash
set -euo pipefail
SOURCE_SHA='填写同一40位合并SHA'
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]
XIYU_RELEASE="/opt/fomobtc/releases/$SOURCE_SHA"
XIYU_BACKUP="/opt/fomobtc/backups/xiyunews-$SOURCE_SHA"
XIYU_PREVIOUS=$(readlink -f /opt/fomobtc/current)
test -L /opt/fomobtc/current
test -x "$XIYU_PREVIOUS/venv/bin/python"
test -f "$XIYU_RELEASE/requirements.lock"
test ! -e "$XIYU_BACKUP"
python3 -c 'import sys; assert sys.version_info[:2] in {(3, 11), (3, 12)}'
sudo -u fomobtc python3 -m venv "$XIYU_RELEASE/venv"
sudo -u fomobtc "$XIYU_RELEASE/venv/bin/pip" install \
  --require-hashes -r "$XIYU_RELEASE/requirements.lock"
sudo install -d -m 0700 "$XIYU_BACKUP"
sudo cp -p /etc/fomobtc.env "$XIYU_BACKUP/runtime.env"
sudo systemctl stop fomobtc
if systemctl is-active --quiet fomobtc; then exit 1; fi
sudo "$XIYU_PREVIOUS/venv/bin/python" - "$XIYU_BACKUP" <<'PY'
import os
import sqlite3
import sys
from pathlib import Path
target = Path(sys.argv[1]) / 'fomobtc.sqlite3'
with sqlite3.connect('file:/var/lib/fomobtc/fomobtc.sqlite3?mode=ro', uri=True) as source:
    with sqlite3.connect(target) as backup:
        source.backup(backup)
        assert backup.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
os.chmod(target, 0o600)
print('SQLite backup verified')
PY
printf 'Previous release: %s\n' "$XIYU_PREVIOUS"
```

环境备份仅在服务器 root-only 目录，不下载、不提交、不展示内容。备份或停机检查失败时不切换；不要盲目执行后续代码块。记录原路径、原 source_commit 和备份路径，保留旧 release。

### 4. 服务器：只更新版本标识并原子切换

用 sudoedit 仅把 SOURCE_COMMIT 改为上面的完整 SHA，保留其余行，尤其 Token、群/话题、数据库和信源设置。不要整份覆盖环境文件，也不安装导入包中的 systemd/nginx 文件。

```bash
sudoedit /etc/fomobtc.env
sudo chmod 0600 /etc/fomobtc.env
test ! -e /opt/fomobtc/current.xiyunews-next
test ! -L /opt/fomobtc/current.xiyunews-next
sudo ln -s "$XIYU_RELEASE" /opt/fomobtc/current.xiyunews-next
sudo mv -T /opt/fomobtc/current.xiyunews-next /opt/fomobtc/current
XIYU_STARTED_AT=$(date +%s)
sudo systemctl start fomobtc
systemctl is-active fomobtc
systemctl show fomobtc --property=MainPID --value
```

只由既有 systemd 启动一个进程，不再运行 run.py 或第二份发布目录。若启动失败，停止验收并报告，不反复重发通知、清队列或自动回滚。

### 5. 运营者电脑与服务器：健康、自然回执、看门狗

现货连接需要至少 180 秒自然预热，期间 warming 不算完成；不要靠改状态或阈值绕过。运营者电脑检查完整 SHA 和三分片：

```bash
curl --max-time 20 -fsS https://api.fomobtc.com/api/health | \
  jq -e --arg expected "$SOURCE_SHA" \
  '.source_commit == $expected and \
   .sources.spot_stream_0.state == "live" and \
   .sources.spot_stream_1.state == "live" and \
   .sources.spot_stream_2.state == "live"'
curl --max-time 20 -sS -o /dev/null -w 'Readiness HTTP: %{http_code}\n' \
  https://api.fomobtc.com/api/ready
```

额外比较采集进度、队列和所有来源与迁移前基线。既有 Hyperliquid degraded 会导致 ready 503，必须如实记录：满足迁移的 SHA/现货要求不等于全来源 ready，也不因这次改名改变信源或监控规则。

服务器等待下一条自然消息，不发送测试新闻。行情通知的 price_notice 在公共列表中隐藏，因此从 SQLite 只读提取发送后回执，不误把 event 创建时间或 notification_sent 当作 message_id：

```bash
sudo -u fomobtc /opt/fomobtc/current/venv/bin/python - "$XIYU_STARTED_AT" <<'PY'
import json
import sqlite3
import sys
with sqlite3.connect('file:/var/lib/fomobtc/fomobtc.sqlite3?mode=ro', uri=True) as db:
    db.row_factory = sqlite3.Row
    rows = db.execute(
        "SELECT id,kind,source,sent,telegram_id FROM events "
        "WHERE status='sent' AND sent>=? AND telegram_id IS NOT NULL "
        "ORDER BY sent DESC LIMIT 5", (int(sys.argv[1]),),
    ).fetchall()
print(json.dumps([dict(row) for row in rows]))
PY
```

空列表表示还没有自然回执，不能标记交付验收通过；用户手机收件与 API 回执分别记录。既有看门狗至少观察两轮五分钟检查，确认没有新增异常告警，不清空 KV、不重新部署、不更换凭据。全部证据齐备后再由运营者把原 ohxiyu/fomobtc 归档为只读，不删除仓库。

### 6. 仅在确认回滚后：恢复原 release

回滚需要运营者授权；本清单只提供方法，不自动执行。保留当前数据库与已写回执，不把备份数据库覆盖回来，否则可能丢失新发送记录、导致重复。先核对 XIYU_PREVIOUS 是第 3 步记录的确切旧 release，且该目录仍有自身 venv。

```bash
test -x "$XIYU_PREVIOUS/venv/bin/python"
sudo systemctl stop fomobtc
sudoedit /etc/fomobtc.env
# 仅把 SOURCE_COMMIT 恢复为记录的旧完整 SHA，保留其他配置。
test ! -e /opt/fomobtc/current.xiyunews-rollback
test ! -L /opt/fomobtc/current.xiyunews-rollback
sudo ln -s "$XIYU_PREVIOUS" /opt/fomobtc/current.xiyunews-rollback
sudo mv -T /opt/fomobtc/current.xiyunews-rollback /opt/fomobtc/current
sudo systemctl start fomobtc
systemctl is-active fomobtc
```

重新核对旧 SHA、单进程、三个分片、自然消息与看门狗，不删除失败 release 或备份。把真实执行时间、源码 SHA、回执和基线降级写入本模块发布记录；没有执行时只记“操作清单已准备”。
