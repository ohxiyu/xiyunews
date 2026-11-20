# xiyu.news collaboration

- The public website uses Equation News for current content. Preserve attribution, licenses and already published editions. Keep retired public links usable where an archive or successor exists.
- Keep the independent `realtime/` service, database, rules and destinations isolated. The website Worker also runs its watchdog. Preserve the existing Worker, namespaces and secrets.
- Never commit credentials, private endpoints or runtime state. Preserve active databases and historical delivery receipts.
- Read [agent.md](agent.md) and the [current handoff](project-docs/handoff.md). Inspect remote main, open work and the task Issue. Use one Issue and PR on an `agent/*` branch from current main.
- Run behavior and build checks. Before merge, reconcile current main and verify relevant CI. Standing authorization permits merging green, synchronized PRs and their normal deployments. Generated branches, secrets, manual Worker deployment and rollback require separate authorization.
- Update the handoff and report production observations separately from local results. Preserve unfinished work in a draft PR. Never force-push or delete unrelated work.
