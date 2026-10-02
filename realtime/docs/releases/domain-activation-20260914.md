# fomobtc.com domain configuration validation

- Wrangler custom_domain route validated against the installed config schema.
- Frontend build and Wrangler dry run passed; PR #8 initial CI passed all four
  checks (Python 3.11/3.12, frontend, repository).
- Dynadot displayed success after saving ignat.ns.cloudflare.com and
  shaz.ns.cloudflare.com. Cloudflare subsequently displayed active protection.
- User explicitly confirmed deletion of three parking A records (@, www, *);
  Cloudflare displayed deletion success and one remaining API record before
  Wrangler created the root-domain Worker binding.
- Actual release, certificate and browser evidence is recorded separately in
  [domain deployment](deploy-20260914-domain.md).
