# xiyu.news collaboration

These rules apply to people and coding agents. The user-approved 2026-11-09 daily-edition refactor supersedes older product/process instructions.

## Product and boundaries

- The public product is one Chinese crypto/AI daily edition: 07:00 cutoff, 07:26 start, Asia/Shanghai. Background collection only scores and caches; it does not publish or send messages.
- `realtime/` is an independent application. Do not edit it, import its package, combine its dependencies/databases, or alter its destinations for the daily refactor.
- Preserve already published editions and delivery receipts. Do not regenerate or resend history. Keep redirects for retired public addresses.
- Keep copyright, licenses, source attribution and third-party notices.
- Never commit credentials, `.env`, private endpoints or generated runtime state. Secrets belong in Actions/Worker configuration.
- Do not change models, concurrency, candidate caps, paid plans or quotas without the user's approval. No automatic paid-provider switch or top-up.

## One task, one PR

1. Read `agent.md` and `project-docs/handoff.md`; inspect current remote main, open work and the task Issue.
2. Claim one bounded Issue with one owner, `agent/*` branch and isolated checkout from current main. Work serially when changes depend on the same modules.
3. Keep the diff focused. Do not overwrite another person's work or force-push. `main` is the code source of truth; never merge generated branches into it.
4. Run checks appropriate to the change. Before merge, reconcile current main and confirm all required CI is green.
5. Standing owner authorization permits merging green, synchronized PRs and their normal automatic deployments without asking again. Never write generated branches manually, change secrets, roll back, or deploy a Worker manually without authorization for that action.
6. State the change, validation and remaining limitations in the PR. Keep the one-page handoff current. Five-stage release records, screenshot commits and follow-up evidence PRs are not required.
7. Verify ancestry before deleting a merged task branch; preserve unfinished work in a draft PR. Do not delete unrelated work.

## Validation and delivery

- Python 3.11+ and uv; use the lockfile. Update dependency locks only for dependency changes.
- Preserve application VERSION/pyproject/uv.lock consistency and independent Worker package/lock consistency. Do not require a new release-note file for each change.
- Use meaningful behavior tests, plus build/visual checks when presentation changes. A screenshot is optional; production claims require actual observations.
- CI/governance must validate versions, relevant links and a small current task pointer, without requiring historical release archives or ceremonial evidence.
- Follow the refactor stages in handoff. Report multi-day acceptance as pending until observed; never invent elapsed time, successful delivery, balances, analytics or source facts.
- On 2026-11-09 the owner explicitly waived the X preview trial and authorized direct main-account operation after quality gates and API availability checks. Keep the daily two-post limit, do not purchase/upgrade a plan, and never automatically retry an unknown delivery. Balance checking/alerts are disabled at the owner's request; retain token cost accounting.

- Operational alerts use the owner-designated 日报运维 forum topic. Create only the explicitly requested topic; never alter realtime destinations or fall back to the general group/reader channel.
