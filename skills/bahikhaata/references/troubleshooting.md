# Troubleshooting

Start with `$PY -I <workspace>/engine/scripts/doctor.py`. It never prints secrets.

| Symptom | Fix |
|---|---|
| `NEED_PYTHON` | `brew install python@3.12`, or install from python.org, then re-run the installer |
| `NEED_GIT` | `xcode-select --install` |
| `.env has no keys yet` | The user opens `splitwise-mcp/.env` and pastes the keys after the `=` signs, then saves |
| `values have spaces or quotes` | Remove them. Copy and paste the keys; don't retype them from a screenshot |
| `Splitwise server stopped` / auth error | Recheck the keys. Regenerate them at secure.splitwise.com/apps if they were ever pasted into a chat |
| Server crashes on start with an asyncio error | Re-run `install_splitwise_mcp.sh`. It applies the `server.run()` fix |
| `list_groups` shows something unrelated | That's Fold's tool. Splitwise's is `get_groups` |
| Scheduled run keeps asking for permission | Run `setup_workspace.py render` again (it merges the allowlist). Check that `connector_tools` holds the exact tool names |
| A connector's tool names changed (it was reconnected) | Record the new names with `set connector_tools.…=…`, then `render` |
| Something was added by mistake | Press Undo on the page, or ask Claude to delete it. Splitwise keeps deleted expenses and they can be restored |
| The page is empty after a run | Check that the `writes-N.json` batches were sent to *your* page URL (`review_page` in the config) |
| Plugin updated but runs use old code | `setup_workspace.py update-engine` |
