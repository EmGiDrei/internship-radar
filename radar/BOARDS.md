# Externe Jobbörsen (Collection `boards` → `scans/boards`)

Zusätzlich zu den Startups aus `startups` liest `scan.py` externe Jobbörsen, um Firmen zu finden, die nicht in der Liste stehen.
Quellen stehen als Dokumente in der Collection `boards` (`name`, `url`, `adapter`, `active`) und lassen sich dort ein- und ausschalten.
Ergebnis: `scans/boards` (getrennt von `scans/latest`, das fast an der 235-KB-Grenze ist).

## Prüfung der Quellen (27.10.2026, aus der Cloud-Umgebung)

| Quelle | Ergebnis | Format / Weg | Hinweise |
|---|---|---|---|
| YC (ycombinator.com/jobs) | läuft | JSON im Seitenquelltext (`data-page`), je Seite 50 Stellen | robots.txt erlaubt `/jobs` und `/companies/<name>/jobs`; nur `/companies?*` gesperrt. Echte Standortseiten nur Berlin, München, Paris (Hamburg/Lille/Germany fallen auf eine generische Liste zurück) |
| Earlybird (jobs.earlybird.com) | läuft | Getro-Board, `__NEXT_DATA__` | Crawl-delay 10 s |
| Cherry Ventures (talent.cherry.vc) | läuft | Getro-Board | Crawl-delay 1 s |
| Speedinvest (careers.speedinvest.com) | läuft | Getro-Board | Crawl-delay 10 s |
| Point Nine (jobs.pointnine.com) | läuft | Getro-Board | Crawl-delay 10 s |
| Creandum (careers.creandum.com) | läuft | Getro-Board | Crawl-delay 1 s |
| Atomico (careers.atomico.com) | läuft | Getro-Board | Crawl-delay 1 s |
| HV Capital (jobs.hvcapital.com) | läuft | Getro-Board | Crawl-delay 1 s |
| Getro-API (api.getro.com) | nicht genutzt | JSON-API | robots.txt `Disallow: /` → stattdessen die Suche der Board-Seiten (`/jobs?q=…`, serverseitig je Begriff die ersten 20 Treffer) |
| Project A | läuft nicht | – | kein Portfolio-Jobboard gefunden (nur eigene Greenhouse-Boards) |
| Lakestar | läuft nicht | – | kein Portfolio-Jobboard gefunden |
| World Fund | läuft nicht | – | nur eigene Karriereseite, kein Portfolio-Board |
| Berlin Startup Jobs | läuft | HTML-Listen (`/internships/`, Kategorien), RSS nur neueste 12 | robots.txt erlaubt; keine Klausel gegen automatisches Lesen gefunden |
| Arbeitnow | läuft | öffentliche JSON-API (`/api/job-board-api`, 300/Seite) | ausdrücklich freie API („please do not abuse“); breiter als Startups, viele Nicht-Startups |
| Welcome to the Jungle | läuft nicht | – | AWS-WAF-Challenge (HTTP 202 + `x-amzn-waf-action: challenge`) → wie Cloudflare-Sperre behandelt, übersprungen |

## Filter
Titel müssen `want()` (TYP/TRACK wie bisher) **und** `STRICT` (Praktikum/Werkstudent/Thesis/Founders- bzw. Founding-Associate/Stage/Alternance) erfüllen,
Ort muss Deutschland oder Paris/Lille sein (oder Remote mit EU/DACH/DE/FR-Bezug). Startdatum wird nicht gefiltert (steht selten im Titel).
Firmen, die als **aktive** Startups gescannt werden (gleicher normalisierter Name oder Job-Link beginnt mit deren Board-URL), werden weggelassen.
Deaktivierte Startups (z. B. startupmap-Sperre) dürfen über Jobbörsen wieder auftauchen.

## Felder
Hit in `scans/boards.hits[]`: `id` ("board:<firmen-slug>"), `t` (Titel), `l` (Ort), `u` (Link zur Stelle), `co` (Firmenname), `src` (Name der Quelle), `fs` (zuerst gesehen, ISO-UTC).
Dokument: `run_id`, `finished_at`, `hits_total`, `new_hits`, `results` (je Quellen-ID: `s` ok/err, `n` gelesene Stellen, `e` Fehler, `h` Treffer, `dup` weggelassene Duplikate, `at`), `hits`.
