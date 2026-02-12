module.exports = {
    apps: [
        // Unified Service: Bot + Scheduler + API
        {
            name: "qsh-truth-machine",
            namespace: "qwe-signal-hub",
            script: "./run.py",
            interpreter: "./venv/bin/python3",
            cwd: "/home/deploy/apps/QweSignalHub/workers/truth_machine",
            env: {
                "NODE_ENV": "production",
                "API_PORT": "8081",
                "REPORTS_DB_PATH": "/home/deploy/apps/QweSignalHub/workers/truth_machine/db/reports.db"
            },
            max_memory_restart: "300M",
            restart_delay: 5000,
            autorestart: true,
            max_restarts: 10,
            min_uptime: "10s",
            error_file: "./logs/api-error.log",
            out_file: "./logs/api-out.log",
            log_date_format: "YYYY-MM-DD HH:mm:ss Z",
            merge_logs: true
        }
    ]
}
