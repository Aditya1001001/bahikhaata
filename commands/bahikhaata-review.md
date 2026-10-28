---
description: What's waiting for review this week, and how much your flatmate owes
---
Load the `bahikhaata` skill. Read the user's review page database with ArtifactData (`runs` with status `review`, their `rows` and `auto`, and `summary/main`). Summarise in a few lines: how many are waiting (Baaki), how many are already stamped, what was auto-added this week, and the current balance. Link the page.

If the user decides rows here in chat ("B3 shared, F7 mine, A2 shared 50/50@190"), write each one to the page with ArtifactData `update` (`decision`, plus `d_split` if they gave one), so the page and the next run see the same decisions. Don't add anything to Splitwise from this command; the next run does that, or run `/bahikhaata-run`.

$ARGUMENTS
