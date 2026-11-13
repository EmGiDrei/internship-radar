# Architecture

Praktikums-Radar has three runtime parts, and none of them needs a server of its own:

| Part | Where it runs | Code |
|---|---|---|
| Web app | claude.ai artifact (single HTML file plus document database) | `app/index.html` |
| Daily scan | scheduled Claude Code task in a cloud sandbox, 06:55 Europe/Berlin | `scanner/scan.py`, `agents/scan-run.prompt.md` |
| Inbox sync | scheduled Claude Code task, 07:12 / 12:12 / 19:12 | `agents/mail-sync.prompt.md` |

The artifact database is the only shared state. The app subscribes to it live, and both agents read and write it through the artifact data API. Every write carries `if_version` (optimistic concurrency).

## Data model

| Document / collection | Written by | Content |
|---|---|---|
| `startups/<id>` | app, user | `name, stadt, typ, stage, liste, active, ats, source_url, career_url, note` |
| `scans/latest` | scan | `run_id, started_at, finished_at, checked, ok, errors, results{id: {s, n, e, h}}, hits[{id, t, l, u, fs, pd}]` (`fs` = first seen, `pd` = posted date) |
| `scans/boards` | scan | hits from job boards and VC portfolios (`co` = company, `src` = source), per-source results |
| `scans/candidates` | scan, user decides | companies found on boards whose ATS is readable: `name, board, ats, src[], titles[], status` |
| `scans/details` | scan | per application link: `sd` start date, `pd` posted, `off` offline since, `moved` re-posted URL, `chk` |
| `scans/ratings` | scan + Claude | per normalised URL: `fit, imp, su, s, p, why, at, pa` (`pa` = profile version) |
| `applications/<id>` | app, inbox sync | `nr, company, title, url, status, status_at, hist{status: ts}, comment, added, source` |
| `interviews/<company>-<round>` | inbox sync, app | `company, app_id, kind, status, start, dur_min, with, li, booking_url, join_url, onepager{…}` |
| `runs/<run_id>` | scan | live progress: `status, phase, pct, log[[ts, kind, text]], dur{phase: s}`, final counts |
| `config/profile` | app | CV and preferences used for rating and for one-pagers |
| `config/main`, `config/mail` | app, agents | trigger id, schedule, processed mail ids, last changes |

## Daily scan: phases

The scheduled task writes `scan.py` into the sandbox and calls it phase by phase. After each phase it pushes `progress.json` to `runs/<id>`, which drives the progress bar and terminal log in the app.

1. **init / daten**: read startups, boards, applications, previous results, profile and ratings.
2. **startups**: fetch every active source with up to 24 workers and at most 4 per host. Dispatch by URL to the ATS adapter (`route()`): Personio XML (with an HTML fallback), Ashby posting API, Greenhouse boards API (US with EU fallback), Lever (US/EU), Workable widget API, Recruitee offers API, SmartRecruiters postings API (paginated), Join (Next.js `__NEXT_DATA__`, paginated), Teamtailor RSS, YC company pages, Berlin Startup Jobs company pages, and a generic HTML link extractor. Titles are filtered by role-type and track keywords. `fs` is kept from earlier runs, so "new" means new.
3. **boards**: YC Jobs (location and role pages), Getro VC portfolio boards (site search per keyword, honouring each robots.txt `Crawl-delay`), Berlin Startup Jobs, Arbeitnow API. Only internship-type titles in DE, Paris or Lille are kept. Companies already scanned directly are skipped. Companies with a readable ATS become candidates.
4. **details**: for each application link, extract the start date from free text (regex over DE/EN/FR phrasing), get `datePosted` from JSON-LD, and run the offline check. The check marks a job offline if its board was read completely in step 2 and the job is missing, or if the link redirects to the listing page. It also recognises a re-posted job, where the same link resolves to a new job ID on the same board.
5. **bewerten (rate)**: build `rate_in.json` with the profile plus the job text of every unrated application and every posting first seen in this run. A relevance pre-filter on the title runs first, with a safety cap of 150. The agent reads it, writes `{fit, imp, su, why}` per job, and `scan.py bewerten-speichern` computes `s = 0.45·fit + 0.35·imp + 0.2·su` and the priority (A ≥ 75, B ≥ 62, C ≥ 48, otherwise D; D whenever fit < 35).
6. **fertig (done)**: finalise the run document.

**Cancel:** the app marks `runs/<id>.cancel_requested` and interrupts the cloud session through the Claude Code Remote MCP connector. If that fails, the agent's next write to the run document hits a version conflict, it re-reads the document, sees the cancel flag and stops.

## Inbox sync: rules

- Read only (search and get thread). Never send, label or delete.
- Matching: sender name and domain, subject and body against the company names in the application list. ATS and scheduling senders (Ashby, Greenhouse, Personio, Join, Calendly, HubSpot meetings, …) map to the company named in the mail. Several roles at one company are told apart by job title. Stealth companies are matched by the "Stealth" wording and the join.com relay domain.
- Status transitions only move forward (`Offen < Anschreiben nötig < Beworben < Gespräch < Zusage`). A rejection may replace anything except an offer, and a newer invite replaces a rejection. Manual statuses win.
- Notes are append-only: one line `DD.MM. Mail: <kind>` per mail. Processed message ids are stored, so nothing is counted twice.
- An interview invite or booking confirmation creates or updates `interviews/<company>-<round>`. If the entry has no one-pager yet, the agent researches the company (at most 5 web searches plus the website and the job ad, no LinkedIn fetching) and stores a structured one-pager with sources.

## Responsible scraping

- At most 4 concurrent requests per host, a browser User-Agent, timeouts and no retries in a loop.
- `Crawl-delay` from robots.txt is honoured for job boards. The Getro API is disallowed by robots.txt, so the board's own search pages are used instead.
- Nothing behind a login or a bot challenge (Cloudflare, AWS WAF) is read: Welcome to the Jungle is skipped for that reason. LinkedIn, Indeed and Wellfound are never scraped.

## Demo

`demo/make_data.py` generates fictional sample data in the shape above. `demo/mock-runtime.js` implements the subset of the artifact runtime the app uses (`db.doc/collection` with live snapshots and `set/update/delete`, an MCP `callTool` for scan, cancel and schedule, and `user.can`). `demo/build.py` wraps the unmodified `app/index.html` with both into `docs/index.html`. Timestamps are shifted by whole days at load time, so "this morning's run" and the upcoming interviews stay current.

Original German working notes on the job-board integration: [notes-de.md](notes-de.md).
