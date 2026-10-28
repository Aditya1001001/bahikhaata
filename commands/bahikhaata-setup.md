---
description: Set up Bahikhaata (or continue setup) — Splitwise, payment sources, house rules, your private review page, daily run
argument-hint: "[dry-run | update]"
---
Load the `bahikhaata` skill and follow `references/onboarding.md` from the skill folder, step by step.

- If `~/Bahikhaata/bahikhaata.config.json` (or `$BAHIKHAATA_CONFIG`) exists, read its `setup` block and resume at the first unfinished step. Say where you're picking up.
- Otherwise start at step 0. The plugin's files are in `${CLAUDE_PLUGIN_ROOT}`.
- Argument `dry-run`: run `python3 -I ${CLAUDE_PLUGIN_ROOT}/scripts/dry_run.py` and walk the user through what each step did, using fake data. Touch no real account or page.
- Argument `update`: run `setup_workspace.py update-engine` to refresh the scripts in the user's workspace after a plugin update, then `doctor.py`.

Ask one question at a time. Never ask for keys or passwords in chat. Nothing goes to Splitwise without an explicit yes.

$ARGUMENTS
