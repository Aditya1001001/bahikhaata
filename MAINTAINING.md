# Maintaining the package

```
.claude-plugin/        plugin.json, marketplace.json (this folder is its own one-plugin marketplace)
commands/              /bahikhaata-setup, /bahikhaata-run, /bahikhaata-review
skills/bahikhaata/     SKILL.md (trigger + safety rules) and references/ (onboarding, runbook, sources, rules, troubleshooting)
pipeline/              config-driven scripts: bk.py (config), build, add, sw, sw_all, publish_review, ingest_review, publish_months, fake_splitwise
templates/             review.html, CLAUDE.md.tmpl, settings.allowlist.tmpl.json, scheduled-task.md.tmpl
scripts/               install_splitwise_mcp.sh, setup_workspace.py, doctor.py, dry_run.py, refresh_template.py
sample/                fictional data (Kabir and Zoya, Flat 4B) for the dry run
```

- **Before every share:** run `python3 -I scripts/dry_run.py`, which must print `ALL CHECKS PASSED`. Step 9 scans the package for paths, Gmail addresses, artifact URLs, connector UUIDs and 8-digit IDs. It also checks your own denylist at `~/.bahikhaata-denylist.json`, which is kept outside the package on purpose.
- **Bump the version** in `.claude-plugin/plugin.json` when you change anything. Friends then run `/plugin marketplace update bahikhaata` and `/bahikhaata-setup update`.
- **Changed your page's design?** Run `python3 -I scripts/refresh_template.py ~/Splitwise/splitwise-mcp/pipeline/review.html`, then the dry run.
- Build a zip without caches: `cd .. && zip -r bahikhaata.zip bahikhaata-skill -x '*/__pycache__/*' '*.DS_Store'`
- **Refresh the README screenshots** after changing the page: `python3 -I scripts/dry_run.py --keep --workspace /tmp/bk-ws`, run `engine/pipeline/publish_months.py` in that workspace (with `BAHIKHAATA_CONFIG` and `BAHIKHAATA_DRY_RUN=1` set), then `python3 -I scripts/screenshots_preview.py /tmp/bk-ws templates/review.html /tmp/preview.html`, and capture each tab with headless Chrome: `--headless=new --window-size=1000,1250 --screenshot=out.png "file:///tmp/preview.html?tab=hisaab"` (also `cal`, `darj`). Save the images in `docs/screenshots/`.
