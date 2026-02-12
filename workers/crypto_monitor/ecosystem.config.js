module.exports = {
    apps: [{
        name: "qsh-crypto-monitor",
        namespace: "qwe-signal-hub",
        script: "./run.py",
        cwd: "/home/deploy/apps/QweSignalHub/workers/crypto_monitor",
        interpreter: "./venv/bin/python",
        instances: 1,
        exec_mode: "fork",
        autorestart: true,
        watch: false,
        max_memory_restart: "1G",
        error_file: "./logs/pm2-error.log",
        out_file: "./logs/pm2-out.log",
        log_date_format: "YYYY-MM-DD HH:mm:ss",
        merge_logs: true,
        env: {
            PYTHONUNBUFFERED: "1"
        },
        // 重启策略
        min_uptime: "10s",
        max_restarts: 10,
        restart_delay: 4000,
        // 优雅关闭
        kill_timeout: 5000,
        listen_timeout: 3000
    }]
};
