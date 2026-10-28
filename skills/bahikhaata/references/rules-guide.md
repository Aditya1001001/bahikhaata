# Changing rules

When the user corrects a classification ("gym gear is always personal", "Licious is shared", "stop auto-adding Instamart"), edit the workspace files:

| They say | Edit |
|---|---|
| "X is always shared" | add to `rules.json` `learned`: `{"match": "x", "tag": "likely shared", "why": "You said X is shared", "desc": "…", "cat": "Groceries"}` |
| "X is always mine" | `learned` with `"tag": "likely personal"` |
| "Never add X" | `never_add`: `{"match": "x", "why": "…"}` |
| "Auto-add X" | Add an `auto_categories` entry if X doesn't have one yet (`match`; plus `item: true` when X is one item inside mixed orders), add its id to `auto_add`, and confirm the cap. **Only on the user's explicit request.** |
| "Stop auto-adding X" | remove it from `auto_add` |
| Home, rent, names, sources | `setup_workspace.py set …`, then `render` |

After editing, run `setup_workspace.py render` so CLAUDE.md matches. Confirm the change in one line. Regexes are case-insensitive. Keep patterns specific: `licious` is fine, but `rice` would also match "price", so write `\brice\b`.

Categories: Groceries, Dining out, Household supplies, Cleaning, Maintenance, Furniture, Rent, Electricity, Utilities, TV/Phone/Internet, General.
