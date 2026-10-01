# 新仓实时服务迁移操作清单

本文件已准备但尚未执行，不能当作部署证据。完整 realtime 历史尚未上传至远端 main；必须先确认旧历史凭据已撤销、阶段 3 PR 以 merge commit 合并，再使用其实际完整 SHA 执行。SSH 配置和主机指纹必须使用运营者既有可信连接，不发送私钥或验证码。

## 现有东京服务迁移清单（阶段 4）

仅在阶段 3 使用 merge commit 合并、确认旧历史凭据已撤销后执行。以下迁移不重装 systemd、nginx、证书或看门狗，不改阈值、地址簿、群组、数据库位置与密钥；没有 SSH 配置或既有主机指纹时停止，不使用 StrictHostKeyChecking=no。所有标为“服务器”的命令在同一次 SSH 会话中执行，保留变量；命令不是本轮已执行的部署证据。

### 1. 运营者电脑：核对实际合并 SHA 与原连接

```bash
set -euo pipefail
XIYU_SSH_CONFIG='/填写已有SSH配置的绝对路径'
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

记录当前 release 路径和健康接口的 source_commit。SOURCE_SHA 必须来自实际合并的阶段 3 PR；当前仅网站迁移的 main 没有 realtime，不能拿它冒充服务器新版本。

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
