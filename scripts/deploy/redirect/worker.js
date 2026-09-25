// fomobtc.com has no web page any more: every request goes to the Telegram group.
// 302 (not 301) so browsers do not cache it if the invite link is ever replaced.
export default {
  fetch(request, env) {
    return Response.redirect(env.TARGET, 302);
  },
};
