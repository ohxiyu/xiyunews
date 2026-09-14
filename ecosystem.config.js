// Compatibility option for existing PM2 deployments. Prefer systemd on a new VPS.
const path = require("path");
module.exports = { apps: [{
  name: "fomobtc", namespace: "fomobtc", cwd: __dirname,
  script: "run.py", interpreter: path.join(__dirname,"venv/bin/python"),
  instances: 1, exec_mode: "fork", autorestart: true, watch: false,
  restart_delay: 5000, max_restarts: 10, max_memory_restart: "1G", kill_timeout: 15000,
  out_file: path.join(__dirname,"logs/fomobtc-out.log"),
  error_file: path.join(__dirname,"logs/fomobtc-error.log"),
  env: {PYTHONUNBUFFERED:"1"}
}]};
