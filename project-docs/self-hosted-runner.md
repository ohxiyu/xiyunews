# 自托管执行器：保留工作流，迁移计算位置

## 决定与成本边界

2026-11-15：仓库当前为公开。普通 CI 和 CodeQL 在公开仓库使用 GitHub 免费标准 ubuntu-latest，避免与生产任务争用单个受限执行器；私有仓库仍沿用 XIYUNEWS_RUNNER_LABELS，CodeQL 还需原有显式许可开关。只调整代码检查位置，不修改仓库可见性、生产任务、预算或凭据。采集、每天一期的日报及正常生产发布仍使用东京专用 runner；Cloudflare 继续调度和托管网站。

最初迁移发生于 2026-10-13，当时仓库为私有。机器、AI、Actions artifact/cache 等成本与限额仍需单独核对，不能称整个系统免费。不开付费预算、不升套餐、不增加服务器；下面的资源与安装记录保留为既有执行器说明，不要求重新注册。

官方依据：[自托管运行器](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners)、[Actions计费](https://docs.github.com/en/billing/concepts/product-billing/github-actions)、[注册方式](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners)、[Ruby环境要求](https://github.com/ruby/setup-ruby#using-self-hosted-runners)。

生产执行位置由仓库非秘密变量 XIYUNEWS_RUNNER_LABELS 控制，值为 JSON 数组。缺省是 ubuntu-latest；现役服务器标签为 ["self-hosted","Linux","X64","xiyunews-tokyo"]。公开仓库的普通 CI / CodeQL 采用上面的托管例外；不得为页面发布而扩大服务器资源、关闭检查或暂停正常采集。

## 共机保护

2026-11-16 磁盘治理：`ops/maintenance/` 提供默认只预览的 root 维护脚本。用户已授权清理确认闲置的缓存、旧镜像、旧运行器版本和过期日志，保留日报、业务数据库、备份与运行服务。系统 journal 上限 256 MiB / 14 天（运行时 64 MiB，保留 2 GiB 空闲）；运行器诊断日志 128 MiB / 14 天；冷 CI 缓存 512 MiB / 7 天（最近 24 小时及进程/挂载引用受保护）；Docker BuildKit LRU 缓存目标 512 MB、保底 256 MB。只清超过 7 天且无任何容器引用的 dangling 镜像，保留所有带标签镜像、容器和卷。

旧运行器仅处理非当前符号链接指向且超过 7 天的版本；更新暂存需与已安装文件指纹相同并已完成更新。旧 CodeQL 下载缓存超过 48 小时且无引用时可回收，生产所需 Python / Ruby / Node / uv 不处理。CI 目录同时持有原 `run.lock`，跳过进程工作路径及全部容器挂载，源代码、构建产物和发布目录不作为清理目标。每天上海 03:45 加最多 10 分钟抖动执行，应用服务不重启。受保护资源即使超过目标也保留；这些是可清理资源上限，不是会阻止数据库写入的文件系统硬配额。

部署与验收：从已合并提交传输 `ops/maintenance/` 至独立暂存目录，先 `sudo python3 disk_maintenance.py` 预览，再运行 `sudo bash install.sh`，最后 `sudo systemctl start xiyunews-disk-maintenance.service`。仅日志守护进程为加载其配置执行受支持的重启；不重启应用。检查 `systemctl show xiyunews-disk-maintenance.service -p Result -p ExecMainStatus`、timer 下次时间、`df -h /`、原容器 ID/启动时间/健康状态和数据库只读完整性。清掉的包与镜像缓存可重新下载/构建，旧日志不额外备份。

2026-10-13安装前只读测量：Ubuntu24.04/x86_64、2核、1613MiB内存、available846MiB、34GB磁盘可用。现有实时进程约300MiB、NRestarts=0。实际最终配置：单个 runner 串行执行所有 job，物理内存硬上限768MiB、软线704MiB、CPU最多1核、交换上限512MiB，降低CPU/I/O优先级并优先终止执行器而非实时服务。Node堆256MiB、原生解压单线程、npm连接2，Vitest每文件独立进程串行；全量测试与安全审计保留。不是容量保证，持续以真实峰值验收；原640MiB/0.75核仅为首次试验，已由调优值替代。

专用锁定登录的系统用户 xiyunews-runner，无sudo、无SSH密钥。服务使用NoNewPrivileges、只允许自己目录写入、临时目录隔离，并隐藏实时凭据、数据库、源码和admin/root家目录。没有Docker socket、没有公开端口；不重启fomobtc、不读取其env或复制数据库。拒绝fork PR在自托管机器上运行；公开仓库的代码检查已迁往标准托管执行器，自托管生产任务仍只接受受信 main。

首次实际验证发现640MiB软线引发大量内存回收、Vitest同进程累积导致超时；调整后硬上限仍768MiB，软线704MiB、CPU最多1核、Node堆256MiB。受限模式每个测试文件用独立进程串行，全部测试保留，每组结束释放Workerd/Vite内存，不把超时测试跳过。维护timer每周日04:10上海时间加最多20分钟抖动，只清专用诊断目录中14天以上的Runner/Worker日志，并用uv自带prune清无用软件包缓存；不清AI缓存、业务状态、发布归档、凭据或实时目录。timer首次只读预览0项，实际维护Result=success，无业务删除。

单机、单runner没有高可用保证；服务器断网/重启仍可能延迟。systemd自动启动，原Cloudflare共享锁、冷却及恢复继续有效，排队时不启动第二个发送者。资源超限失败时先看runner日志/MemoryPeak和实时健康，不买升级、不增加并行、更不取消实时服务。

## 安装及注册

运维者核对 [SSH身份](../realtime/docs/releases/ssh-access-20261002.md) 和待部署 PR 的准确 SHA；不得因连接错误关闭严格指纹校验。安装脚本只准备新执行器，遇到已注册或其他用户占有的目录会停止；SHA256来自GitHub当前下载接口，依赖使用Ubuntu官方包，不在配置中放业务秘密。

以下步骤在运营者确认部署/注册授权后，由唯一整合负责人执行。专用暂存目录必须此前不存在，只存无秘密的已审核脚本；下载归档另用mktemp创建新目录。不从不可信输入拼命令：

```bash
ssh -F /Users/minutesdr/.ssh/xiyunews_tokyo_config -o BatchMode=yes \
  -o StrictHostKeyChecking=yes xiyunews-tokyo \
  'test ! -e /home/admin/xiyunews-runner-install && mkdir /home/admin/xiyunews-runner-install'
scp -F /Users/minutesdr/.ssh/xiyunews_tokyo_config ops/runner/provision.sh \
  ops/runner/xiyunews-runner.service ops/runner/register.py ops/runner/maintenance.sh \
  ops/runner/xiyunews-runner-maintenance.service ops/runner/xiyunews-runner-maintenance.timer \
  ops/runner/xiyunews-runner-swap.service ops/runner/99-xiyunews-runner.conf \
  xiyunews-tokyo:/home/admin/xiyunews-runner-install/
ssh -F /Users/minutesdr/.ssh/xiyunews_tokyo_config -o BatchMode=yes \
  -o StrictHostKeyChecking=yes xiyunews-tokyo \
  'sudo bash /home/admin/xiyunews-runner-install/provision.sh'
ssh -F /Users/minutesdr/.ssh/xiyunews_tokyo_config -o BatchMode=yes \
  -o StrictHostKeyChecking=yes xiyunews-tokyo \
  'sudo install -m 0755 /home/admin/xiyunews-runner-install/register.py /opt/xiyunews-runner-register.py'
gh api --method POST repos/ohxiyu/xiyunews/actions/runners/registration-token --jq .token | \
  ssh -F /Users/minutesdr/.ssh/xiyunews_tokyo_config -o BatchMode=yes \
    -o StrictHostKeyChecking=yes xiyunews-tokyo \
    'sudo -u xiyunews-runner python3 /opt/xiyunews-runner-register.py'
ssh -F /Users/minutesdr/.ssh/xiyunews_tokyo_config -o BatchMode=yes \
  -o StrictHostKeyChecking=yes xiyunews-tokyo \
  'sudo systemctl enable --now xiyunews-runner-swap xiyunews-runner xiyunews-runner-maintenance.timer; systemctl is-active fomobtc'
gh api repos/ohxiyu/xiyunews/actions/runners \
  --jq '.runners[]|{name,status,busy,labels:[.labels[].name]}'
gh variable set XIYUNEWS_RUNNER_LABELS --repo ohxiyu/xiyunews \
  --body '["self-hosted","Linux","X64","xiyunews-tokyo"]'
```

注册Token仅通过管道stdin传送，register.py设置runner的ACTIONS_RUNNER_INPUT_TOKEN环境输入，命令参数/文件/报告不包含它。Token一小时失效；注册后的runner机器凭据为专用用户持有，不能读取或打印到聊天。现有GitHub业务Secrets继续在原工作流步骤短时注入，不迁移到服务器业务env，安装目录只存无秘密的审查脚本。

服务器无swap时创建一个专用512MiB、root0600交换文件，按独立服务开机启用；执行器MemorySwapMax限制512MiB，物理内存硬上限仍768MiB。不是新增磁盘/套餐，不停止原服务、不改fstab，也不自动删除/交换停用。必要时经批准退役前先确认缓冲已释放。Node原生解压线程单线程、npm下载最多2连接，自托管构建固定npm11.11.1，与已验证环境一致，安全审计仍运行；从Ubuntu仓安装gh以支持来源管理和正常调度脚本。

原服务器vm.swappiness=0导致磁盘缓冲虽启用但不换页，2026-10-13按服务器优化授权改为20，优先保留活跃页面于内存，在压力下允许不活跃页面进入缓冲。配置仅维护在ops/runner/99-xiyunews-runner.conf并安装到同名sysctl.d文件；旧值0记在记录中，不自动回滚。实际峰值、swap和原实时PID/连接均核对，不能将新增swap当无限内存或高可用承诺。

## 验收与交接

### 部署副本与脚本维护

完整 CI 先读取运行目录，再用 scripts/hydrate_checkout.py 分批恢复全部 project-docs Git blob，最终关闭 sparse-checkout，还原同一 HEAD 的完整工作树后执行原测试。每批四个对象、三次重试、单次 180 秒；专用 home 的 .cache/xiyunews-doc-blobs 最多缓存 128 MiB，使用 Git 对象摘要逐个验证，命中对象重新写入当前任务的 Git 对象库，不复用上次工作区、Git 配置或运行凭据。缓存错误不能跳过文档或治理检查。HTTP/1.1 仅为工作流进程环境配置，不修改服务器全局 Git；它不能保证网络永不中断，因此仍需小批次重试。

整站构建和正式发布在 self-hosted 上使用 ops/runner/setup-ruby-cache.sh：工具依赖位于专用 home 的 .cache/xiyunews-bundle，按 ci/producer、Ruby 3.3 和 Gemfile.lock SHA 分路径，先检查已有安装，再以冻结锁文件从本地 gem 归档安装，缺少归档才正常联网安装。缓存只存锁定依赖，不能当作生产渲染结果或省略安全审计；不修改依赖锁或从 PR 路径读取生产依赖缓存。首次可通过原锁文件下载 gem 归档预热对应路径，仍须由 Bundler 进行锁文件校验；不复制密钥或业务数据。新锁会产生新路径，工具缓存磁盘占用随版本维护定期核对，不能承诺永不增长。

每个合法任务的开始/结束 hooks 和既有维护 timer 回收专用 home 下超过 24 小时的 actions-gh-pages Git 临时副本；只处理匹配时间戳、所属者正确、非软链接/挂载点且未被进程 cwd/fd 引用的副本。数据库、AI 缓存、工具缓存、凭据和实时业务目录不在回收范围。遇到损坏业务快照，保留工作区并继续有界临时副本维护；无法安全检查本账号进程时跳过删除。

首次安装 hooks 仍需执行器空闲。已安装环境仅刷新受审脚本时，从准确合并 SHA 导出 ops/runner 后执行 `sudo bash ops/runner/install-job-hooks.sh --refresh-scripts`：先核对已安装 drop-in 完全一致，再原子替换 helper/hooks/维护脚本，不重启执行器、不改环境或资源限制。用专用用户执行 `python3 /opt/xiyunews-job-hooks/deploy_temp_cleanup.py --dry-run` 可只读查看符合条件的数量；实际自动清理以 job hooks 的 deployment_temp_cleanup 事件和维护 timer 日志验收。详见磁盘与发推恢复。

2026-10-13 已注册 repo runner21、xiyunews-tokyo-1，变量选择已生效。实际CI与部署均显示该 runner；PR251、PR249与PR254分别在当前head检查通过后合并。缓存工具环境复用，维护timer已启用；无需重新执行首次注册安装，不读取机器凭据。完整证据见运行记录和持久状态修复。

持久执行器和一次性托管机器不同：浅层Git引用跨任务保留，读取出版状态须使用明确的本地tracking ref更新（`git fetch --depth=1 origin +gh-pages:refs/remotes/origin/gh-pages`），这不是远端强推。初始化前的stdlib门控/恢复/报告用Ubuntu自带python3；其余应用经setup-python/uv固定环境运行。不要靠清空状态历史或重设已发送任务解决环境问题。

1. 当前PR每个实际CI job必须显示self-hosted/xiyunews-tokyo，测试/治理/安全审计/整站构建全部通过，fork保护及单任务串行可核对；原小内存实时服务继续active、NRestarts不增、三个分片live。若GitHub仍因账户状态拒绝自托管任务，保留PR并报告实际annotation，不能认定安装即解决限制。
2. 合并后先走已有无AI Deploy Docs/统一Worker链路验证网站、RSS、公开API、实际source/artifact/version。手动启动正常workflow是既有工作流执行，不能本机手工写gh-pages或绕过发送检查点。
3. 再按任务需要运行正常Feed Collection，确认持久缓存、新事件与出版检查成功；不force_publish、不重刊当日日报、不补发历史、不发测试消息。今天采集验证不能冒充明日07:26自然出刊，后者单独记录。
4. 看systemd MemoryPeak、CPUUsageNSec、OOM及磁盘，记录真实峰值/任务时长与实时health。不把HTTP200当所有来源ready或实际手机收件。

回退不是自动操作。经运营者批准才把变量恢复为 ["ubuntu-latest"] 或停用新runner；账户免费额度已耗尽且预算0时，这会再次暂停业务，不能把它叫可用备用执行器。保留原实时服务、Worker与所有状态，不删除runner凭据/资源以进行“修复”。未来生产和CI若需分离机器或增加容量，先测量并另行确认成本和权限。
