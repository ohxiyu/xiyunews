const path = require("path");

const root = __dirname;

module.exports = {
  apps: [
    {
      name: "coinsignal",
      namespace: "coinsignal",
      cwd: root,
      script: "run.py",
      interpreter: path.join(root, "venv", "bin", "python"),
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      watch: false,
      min_uptime: "10s",
      restart_delay: 4000,
      max_restarts: 10,
      max_memory_restart: "1G",
      kill_timeout: 10000,
      out_file: path.join(root, "logs", "coinsignal-out.log"),
      error_file: path.join(root, "logs", "coinsignal-error.log"),
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      merge_logs: true,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
  ],
};
