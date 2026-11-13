# Agents

The two scheduled Claude Code tasks, versioned as prompts. They are written in German, like the app.

| Prompt | Schedule | What it does |
|---|---|---|
| `scan-run.prompt.md` | daily 06:55 | Writes `scanner/scan.py` into the sandbox, runs it phase by phase, pushes live progress to the app, rates new postings (fit / impact / startup) and stores results. |
| `mail-sync.prompt.md` | 07:12, 12:12, 19:12 | Reads Gmail (read-only), matches mails to applications, moves statuses forward, appends dated notes, creates interview entries and researches a one-pager per interview. |

`build_prompt.py` renders a prompt for deployment: `{{ARTIFACT_URL}}` comes from `RADAR_ARTIFACT_URL`, and `{{SCAN_PY}}` is replaced with the current scanner source. The sandbox does not clone this repository, so the script travels inside the prompt.
