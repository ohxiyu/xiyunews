# 第7项：任务工作区隔离

Source commit: 合并后记录，前置eeb9a4641c0a6a7333a92adb6855bed26b8998d4
Worker version: 本项不改网站代码，当前a553648b-755f-4c92-aefc-26fa2573cc9b
Deployment: 当前PR通过后在空闲执行器激活受保护job hook；原实时进程不重启
Verification: 基线1099应用测试/4跳过，合并前置6后的5项相关测试与shell语法通过。固定工作区/所有者/根symlink拒绝、嵌套链接不跟随、状态预验证与无env复制、matrix独立记录均覆盖。实际hook任务尚待验收。
Rollback: 不恢复或清空原业务数据库。必要时暂停执行器、撤回本项独立drop-in后空闲重启，另行取得明确回退授权；工具/状态/注册凭据留在独立目录。

按照[GitHub官方hook文档](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/run-scripts)，受保护脚本安装到执行器应用目录之外，start/completed均有90秒上限。只处理/opt/xiyunews-runner/_work/xiyunews/xiyunews的内容，保留工作区目录本身；核对路径、父目录、所有者和symlink。工具缓存、home/state、备份导出、注册凭据、实时服务与数据库均在该范围外。完成hook在checkout等post步骤结束后清理。

main指定生产工作流的5个合法JSON文件先镜像到独立state，CI不能污染业务状态；中断后的有效producer文件在下次清理前保存，坏状态不静默删除。任务账本先用独立publication.sqlite3/job_runs，每次invocation唯一，matrix不覆盖；hook_completed不是GitHub结论success。第9项会在同一独立日报SQLite里接入分析和业务状态，始终不导入实时应用或合并实时DB。

安装：严格SSH从合并SHA导出ops/runner，root运行install-job-hooks.sh。脚本先准备受保护文件、确认无Runner.Worker；忙碌则不激活。空闲短暂暂停guardian、切换执行器配置并立即恢复；不操作fomobtc。此前只读确认实际工作路径与所有者一致。首次新main任务完成后检查hook记录、工作区为空、工具/状态存在，以及原实时PID/NRestarts。

实际：PR273/d910e1a771816ad71db0ff818c7058186668b09e，当前CI38394848262全部适用项成功后合并。空闲安装hooks，main完整CI38400911987全部成功。独立SQLite读取7条hook_completed，工作区0项，tool cache存在；原实时PID235825/NRestarts0。hook只记完成，不伪造GitHub结论；本次GitHub结论分别由实际CI证明。
