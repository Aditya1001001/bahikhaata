# Onboarding (`/bahikhaata-setup`)

Goal: a non-technical user finishes in about 15 minutes, mostly by answering questions. Rules for the whole flow:
- **One question at a time**, in plain words, with a suggested answer they can accept. Use AskUserQuestion when there are clear options.
- **Do the technical work yourself.** Run the scripts and explain the result in one line. Don't show stack traces; fix or explain them.
- **Resume, don't restart.** Read `setup` in the config first and skip finished steps. Say where you're picking up ("Splitwise is connected; next, your payment sources").
- **Never ask for keys or passwords in chat.**
- After each step: `setup_workspace.py done <step>`, then one line of progress ("3 of 8 done").

Paths below: `$E` = `<workspace>/engine`, `$PY` = `<workspace>/splitwise-mcp/venv/bin/python`. Before the engine exists, run the setup script from the plugin folder (`${CLAUDE_PLUGIN_ROOT}/scripts/`) with `python3 -I`.

## 0. Welcome (30 s)
Say what's going to happen in three lines: you connect Splitwise and your payment sources, tell me your house rules, and get your own private review page. Then nothing is added to Splitwise until you say so. Ask one question: **where to keep files** (default `~/Bahikhaata`). Then:
```
python3 -I ${CLAUDE_PLUGIN_ROOT}/scripts/setup_workspace.py init ~/Bahikhaata
```
For the rest of setup, work with `~/Bahikhaata` as the working directory (or set `BAHIKHAATA_CONFIG`). A demo or test uses `"dry_run": true`; see step 9.

## 1. Splitwise (5 min) → step `splitwise`
1. `bash $E/scripts/install_splitwise_mcp.sh <workspace>/splitwise-mcp`. It clones the server, makes the venv, applies the `server.run()` fix, and creates an empty private `.env`. If it prints `NEED_PYTHON` or `NEED_GIT`, give the user the one command it names and wait.
2. Walk them through the keys (they do this in their browser):
   - Open **secure.splitwise.com/apps** and click *Register your application*. Any name works; Homepage `http://localhost`; Callback `http://localhost:8000/callback`.
   - Copy the Consumer Key, Consumer Secret and API key.
   - Open the file for them (`open -t <workspace>/splitwise-mcp/.env`, or reveal it in Finder), paste after the `=` signs, and save.
   - Say plainly: "Don't paste these here. They stay in that file on your Mac."
3. `$PY -I $E/scripts/doctor.py --groups`. On `TODO .env`, wait for them. On `FAIL`, use the hint and troubleshooting.md.
4. From the group list, ask **which group you share with your flatmate**. Then, if the group has more than one other member, ask **who the flatmate is**. Ask what they call the flatmate day to day, and whether the flatmate shows up under another name on GPay or the bank (aliases).
5. `setup_workspace.py set me.name=… me.full_name=… me.splitwise_id=… flatmate.name=… flatmate.splitwise_id=… 'flatmate.aliases=["…"]' splitwise.group_id=… splitwise.group_name="…"`
6. Optionally add the server to the workspace `.mcp.json` (command `$PY`, args `["-m","splitwise_mcp_server"]`) so they can ask for Splitwise things in chat. The pipeline itself doesn't need it.

## 2. Payment sources (3 min) → step `sources`
Explain: "I need to see your payments. A bank feed shows every payment; receipts show what it was for."
1. Call `mcp__mcp-registry__suggest_connectors` with keywords like `["Fold", "Gmail", "Swiggy", "Instamart"]` so they can connect with one click. Check what's already connected with `list_connectors` or by looking at the loaded tools.
2. **Bank feed (one of):**
   - **Fold** (`mcp.fold.money/mcp`, needs Fold Plus). It sees all linked bank and card debits.
   - **No Fold:** a monthly bank or card statement CSV saved as `expense-log/raw/<period>/bank.csv`, in the format in sources.md. Ask which bank; you'll convert their export.
3. **Gmail** (recommended): receipts from Swiggy, Instamart, Zomato, Amazon and others, plus card alerts. Ask which address gets those receipts. **Zomato needs no connector**: its order emails are enough.
4. **Swiggy / Instamart** connectors (optional): Instamart gives delivery addresses for the last ~15 days; Swiggy gives recent food orders.
5. Test each connected source with one small read-only call (e.g. Fold `list_transactions` for the last 3 days, Gmail `search_threads` for `from:swiggy newer_than:7d`). Report only counts, not contents.
6. Record the **exact tool names** you used (they include a per-user server id) and which sources are on:
   `set sources.fold=true 'sources.gmail={"enabled":true,"address":"…"}' connector_tools.fold_list_transactions=mcp__…__list_transactions connector_tools.gmail_search_threads=… connector_tools.gmail_get_thread=… …`
   Record read tools only.
   - Watch out: Fold also has `list_groups`, which isn't Splitwise. Splitwise's tool is `get_groups`.

## 3. Household rules (3 min) → step `rules`
Ask these one at a time, offering the default each time:
1. **Home address** as saved in delivery apps. You need distinctive words: building, area, city. → `home.keywords`, `home.city`.
2. **Default split** (50/50).
3. **Rent:** Is rent tracked in this group? If so, who pays the landlord: you pay all of it (`i_pay_all`), or you each pay your own half (`each_pays_own_half`)? What name shows on the bank transfer to the landlord (`rent.landlord_pattern`)? Does a payment in a month cover that month or the one before?
4. **Always shared:** start from rent, utilities, broadband, house help, and groceries and household items delivered home. Ask what they'd add or remove, e.g. "creatine is shared" or "gym gear is always personal". Things they always share become `learned` rules with `tag: "likely shared"`. Things that are never shared become `never_add` entries.
5. **Never add:** anything that is already covered some other way, e.g. lump furniture-rental prepayments when the monthly entries are logged separately. → `never_add: [{"match": "furlenco", "why": "…"}]`.
Write the answers with `set` (for rules.json, edit the file directly). Then run `setup_workspace.py render` and read the generated household rules back to the user for a yes.

## 4. Their own review page (1 min) → step `page`
1. `render` has already written `<workspace>/review.html` from the template.
2. Publish it as a **new private artifact** (never update anyone else's page) with the `db` and `user` capabilities. Load the artifact-capabilities skill first. Title: "Bahikhaata".
3. Seed `summary/main` with `ArtifactData set` from `out/summary_main.json` (it holds their names, group and the setup checklist).
4. `set review_page=<url>`, then `render` again so CLAUDE.md and the schedule pick up the URL.
5. Tell them: "This page is private to you. Bookmark it. It's where you'll stamp entries each week."

## 5. Auto-add (1 min) → step `auto_add`
Explain: "Some things are almost always shared. I can add those straight to Splitwise and show them on the page with an Undo. It's off unless you turn it on."
Offer each category in `rules.json` `auto_categories` (instamart_home, rent if a rent mode is set, licious, firstclub, plus any `learned` shared rule they mentioned) as a multi-select. For each one picked, confirm the cap (default ₹3,000; rent is the rent total). Write `auto_add` and `caps`. Choosing none is fine.

## 6. First run (4 min) → step `first_run`
1. Period: the last 7 days, or 14 if they want. Set `history_start` to that start date.
2. Follow runbook.md steps 1, 2 and 4 for that period. **No auto-add on this first run**, so they see everything first: in step 3 use `add.py --decided-only`.
3. Show a short summary: N payments found, M likely shared, K need a call. Link the page and ask them to stamp a few entries there now (Saanjha/Apna), then come back.
4. Read their decisions (runbook step 0). Show `add.py --preview` and ask: "Add these N to Splitwise?" Add only on an explicit yes, then show the new balance.
5. If they opted into auto-add, tell them what would have been auto-added this time.

## 7. Schedule and permissions (1 min) → step `schedule`
1. Explain the daily run in one sentence: "Every morning at 10 I'll fetch yesterday's payments, add your auto categories, and queue the rest. You review once a week."
2. Ask the time (default 10:00). Create the scheduled task with `mcp__scheduled-tasks__create_scheduled_task`, named `bahikhaata-run`, with the prompt from `out/scheduled-task.md` and that time. If there's already a task with that name, pick another name and don't touch the existing one.
3. Permissions: `render` wrote `<workspace>/.claude/settings.local.json`. Before finishing, show this plain list, using their real tool names:
   - Read files in your Bahikhaata folder, and write only to `expense-log/`, `out/` and `state.json`.
   - Run the Bahikhaata scripts with your Splitwise Python (these are the only programs it runs).
   - Read Fold transactions (read only, no changes to Fold).
   - Search and read Gmail messages (no sending, deleting or labelling).
   - Read Swiggy and Instamart orders (no ordering).
   - Write to your review page's database, send you a notification, and use a helper agent for bulk reading.
   - **Blocked:** reading or editing your Splitwise keys file.
   Note what isn't on the list: adding to Splitwise always happens through `add.py`, which only adds your approved and opted-in rows.
4. Offer a test with `run_scheduled_task` now, or wait for tomorrow.

## 8. Done
Mark everything done, then sum up in 4 lines: page link, what's auto-added, when the daily run happens, and how to change things ("just tell me: 'gym stuff is personal'"). Suggest they tell their flatmate before a backlog lands in the group.

## 9. Dry run (testing, or "show me first")
For a demo, or for anyone (including the plugin author) testing changes: `python3 -I $E/scripts/dry_run.py` builds a throwaway workspace with fake people and data and runs every step against a fake Splitwise and a fake page store. It touches no real account or page. Use `--keep` to inspect the result.
