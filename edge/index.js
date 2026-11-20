import {DurableObject} from 'cloudflare:workers';
import watchdog from '../realtime/scripts/deploy/watchdog/worker.js';
import {serve} from './routes.js';

// Keep the existing class and storage so published rolling-feed bookmarks still resolve.
export class RecoveryGate extends DurableObject {
  legacyStory(id) {
    if (!/^[a-f0-9]{32}$/.test(id)) return null;
    return this.ctx.storage.sql.exec(
      'SELECT value FROM gate WHERE key = ?', 'feed:story:' + id,
    ).toArray()[0]?.value ?? null;
  }
}

export default {
  fetch: serve,
  async scheduled(controller, env) {
    if (controller.cron === '*/5 * * * *' && env.ENABLE_REALTIME_WATCHDOG === 'true') {
      await watchdog.scheduled(controller, env);
    }
  },
};
