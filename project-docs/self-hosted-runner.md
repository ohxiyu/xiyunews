# 自托管执行器：保留工作流，迁移计算位置

## 决定与成本边界

私人仓库 ohxiyu/xiyunews 继续维护代码、工作流、Secrets 和正常产物分支；Cloudflare 继续调度和托管网站。把任务执行从 GitHub 托管机器改到既有东京服务器的一个专用 runner，不改每日窗口、四小时采集、分发门控或实时提醒。GitHub 官方当前说明自托管运行器不收执行分钟费用；机器、AI、Actions artifact/cache 等各自成本与限额仍需单独核对，不能称整个系统免费。不开付费预算、不升套餐、不增加服务器。

官方依据：[自托管运行器](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners)、[Actions计费](https://docs.github.com/en/billing/concepts/product-billing/github-actions)、[注册方式](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners)、[Ruby环境要求](https://github.com/ruby/setup-ruby#using-self-hosted-runners)。

所有执行位置由仓库非秘密变量 XIYUNEWS_RUNNER_LABELS 控制，值为 JSON 数组。缺省仍是原 ubuntu-latest；迁移后的准确值为 ["self-hosted","Linux","X64","xiyunews-tokyo"]。先注册并验证 runner 在线，再设置变量，当前 PR 的 CI 用新执行器实际验证，通过且同步 main 才合并。旧 main 在合并前仍是原托管位置，不绕过 CI；合并后采集、日报、周报、CI、静态部署、队列分发与恢复全部引用该变量。

## 共机保护

2026-10-13只读测量：Ubuntu24.04/x86_64、2核、1613MiB内存、available846MiB、34GB磁盘可用。现有实时进程约300MiB、NRestarts=0。不是容量保证：新任务必须按实际峰值验收。只创建一个 runner，所有 job 排队串行；整个服务上限768MiB、软线640MiB、CPU0.75核，降低CPU/I/O优先级、优先终止执行器而非实时服务。Vitest在此环境内串行，编译/安装并行受限。

专用锁定登录的系统用户 xiyunews-runner，无sudo、无SSH密钥。服务使用NoNewPrivileges、只允许自己目录写入、临时目录隔离，并隐藏实时凭据、数据库、源码和admin/root家目录。没有Docker socket、没有公开端口；不重启fomobtc、不读取其env或复制数据库。CI拒绝fork PR在自托管机器上运行；只供这个私有仓库及其可信维护分支使用，仓库公开前必须先停用和重新审查此配置。

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
  ops/runner/xiyunews-runner-swap.service \
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

## 验收与交接

1. 当前PR每个实际CI job必须显示self-hosted/xiyunews-tokyo，测试/治理/安全审计/整站构建全部通过，fork保护及单任务串行可核对；原小内存实时服务继续active、NRestarts不增、三个分片live。若GitHub仍因账户状态拒绝自托管任务，保留PR并报告实际annotation，不能认定安装即解决限制。
2. 合并后先走已有无AI Deploy Docs/统一Worker链路验证网站、RSS、公开API、实际source/artifact/version。手动启动正常workflow是既有工作流执行，不能本机手工写gh-pages或绕过发送检查点。
3. 再按任务需要运行正常Feed Collection，确认持久缓存、新事件与出版检查成功；不force_publish、不重刊当日日报、不补发历史、不发测试消息。今天采集验证不能冒充明日07:26自然出刊，后者单独记录。
4. 看systemd MemoryPeak、CPUUsageNSec、OOM及磁盘，记录真实峰值/任务时长与实时health。不把HTTP200当所有来源ready或实际手机收件。

回退不是自动操作。经运营者批准才把变量恢复为 ["ubuntu-latest"] 或停用新runner；账户免费额度已耗尽且预算0时，这会再次暂停业务，不能把它叫可用备用执行器。保留原实时服务、Worker与所有状态，不删除runner凭据/资源以进行“修复”。未来生产和CI若需分离机器或增加容量，先测量并另行确认成本和权限。
