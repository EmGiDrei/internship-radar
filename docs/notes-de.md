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
Hit in `scans/boards.hits[]`: `id` ("board:<firmen-slug>"), `t` (Titel), `l` (Ort), `u` (Link zur Stelle), `co` (Firmenname), `src` (Name der Quelle), `fs` (zuerst gesehen, ISO-UTC), optional `pd` (online seit, `YYYY-MM-DD`).
Dokument: `run_id`, `finished_at`, `hits_total`, `new_hits`, `results` (je Quellen-ID: `s` ok/err, `n` gelesene Stellen, `e` Fehler, `h` Treffer, `dup` weggelassene Duplikate, `at`), `hits`.

## Kandidaten für die Startup-Liste (`scans/candidates`)
Firmen aus YC, den VC-Portfolios und Berlin Startup Jobs (nicht Arbeitnow), deren Stellen-Link ein vom Scanner vollständig lesbares Board ergibt
(Ashby, Greenhouse, Lever, Personio, Join, Workable, Recruitee, SmartRecruiters, Teamtailor, YC-Firmenseite, BSJ-Firmenseite).
Nichts wird automatisch in `startups` übernommen; die Entscheidung trifft der Nutzer.

Dokument: `updated_at`, `count`, `candidates` = Objekt `{<firmen-slug>: Kandidat}`.
Kandidat: `name`, `board` (Board-URL, als `source_url`/`career_url` übernehmbar), `ats` (personio, ashby, greenhouse, …, ycco, bsjco),
`src` (Liste der Quellen), `titles` (bis 3 passende Titel), `n` (passende Stellen im Lauf), `fs`/`ls` (zuerst/zuletzt gesehen),
`status` (`neu` | `übernehmen` | `abgelehnt` | `übernommen`; bleibt über Läufe erhalten), optional `in_startups` (ID eines **deaktivierten** Startups gleichen Namens → Reaktivierung mit neuer Quelle).
Nicht mehr gesehene Kandidaten bleiben 30 Tage bzw. dauerhaft, wenn schon entschieden.

## Online seit und Startdatum (`pd`, `scans/details`)
`pd` (Veröffentlichungsdatum der Anzeige, `YYYY-MM-DD`) steht optional an jedem Treffer in `scans/latest` und `scans/boards`.
Quelle: Greenhouse `first_published`, Lever `createdAt`, Ashby `publishedAt`, Personio `createdAt`, SmartRecruiters `releasedDate`, Teamtailor `pubDate`,
Recruitee `published_at`, Join `createdAt`, Getro `createdAt`, Arbeitnow `created_at`, YC `createdAt` (relativ, z. B. „6 days“). Berlin Startup Jobs liefert keins.

Für die Bewerberliste liest `scan.py` die Collection `applications` (nur lesend) und lädt jede Stellenseite.
Gesucht wird per Wortmuster (DE/EN/FR, keine KI) nach Startangaben wie „Start: ab sofort“, „Starting in January 2027“, „Beginn: Sommersemester 2027“, „à partir de janvier 2027“, „Q4 2026“; unklar → leer.
Ergebnis in `scans/details`: `updated_at`, `count`, `by_url` = `{<normalisierter Link>: {sd, pd, at}}` (Link klein geschrieben, ohne `?…`/`#…` und End-Schrägstrich).
`sd` = Startdatum als Text (≤ 40 Zeichen), `pd` = online seit (aus den Treffern oder `datePosted` der Seite), `at` = zuletzt geladen. Gefundene Startdaten werden 14 Tage lang nicht neu geladen.
Das Artefakt zeigt beides in der Bewerberliste als Spalten „Online seit“ und „Start“; die Praktika-Liste zeigt „online <Datum>“, wenn bekannt.

## Live-Fortschritt (`runs/<Lauf-ID>`)
Der Lauf ruft `scan.py` in Phasen auf (`init`, `daten`, `startups`, `boards`, `details`, `fertig`). Nach jeder Phase schreibt er `/tmp/radar/progress.json` per `update` nach `runs/<Lauf-ID>`.
Felder: `phase` (aktive Phase), `pct` (Start-% dieser Phase: 0/3/8/30/88/100), `phase_at` (Beginn der Phase), `log` (bis 40 Einträge `[ISO-Zeit, ok|run|err|info, Text]`), `dur` (Sekunden je beendeter Phase).
Das Artefakt zeigt daraus oben einen Ladebalken mit Phasen-Abschnitten, die Schritte und die Konsole. Innerhalb einer Phase wird der Balken anhand von `dur` des letzten fertigen Laufs geschätzt (Anzeige „~“). Fertige Läufe bleiben 20 Minuten sichtbar; das Protokoll jedes Laufs steht im Reiter „Läufe“.
Nach jeder Phase sind deren Ergebnisse schon gespeichert (z. B. `scans/latest` nach `startups`).

## Abbrechen
„■ Abbrechen“ im Live-Panel (mit Rückfrage) unterbricht die Cloud-Sitzung sofort (`interrupt_session`, die `cse_…`-ID wird angenommen). Die Sitzungs-ID kommt bei „Jetzt scannen“ aus der Antwort von `fire_trigger` (gespeichert in `config/main.last_session`), bei geplanten Läufen aus `get_trigger` (`last_run.session_id`).
Dann wird `runs/<Lauf-ID>` auf `status: "cancelled"` gesetzt. Klappt das Unterbrechen nicht, setzt das Artefakt nur `cancel_requested`.
Der Lauf merkt das beim nächsten Schreiben am Versionskonflikt und hört nach der aktuellen Phase auf. Ein nur angeforderter, noch nicht gestarteter Lauf wird über `config/main.last_manual_cancel` verworfen.

## Quellen-Labels
Jede Stelle zeigt, woher sie kommt: „Startup-Liste · Personio“ bzw. „Meine Liste · Ashby“ (Bewerbungssystem aus dem Link, sonst die Website), „Jobbörse · Earlybird-Portfolio“ für Treffer aus `scans/boards`.
In der Bewerberliste steht das System bzw. die Plattform unter dem Link.

## Stelle offline (`scans/details.by_url[].off` / `.moved`)
Jeder Lauf prüft alle Links der Bewerberliste. Offline ist eine Stelle, wenn ihr Board (Personio, Ashby, Greenhouse, …) in diesem Lauf vollständig gelesen wurde und sie fehlt, wenn die Seite 404/410 liefert oder auf die Übersicht umleitet.
`off` = seit wann offline. Leitet die alte Anzeige auf eine neue Stelle desselben Boards weiter, steht der neue Link in `moved` („neu ausgeschrieben“).

## KI-Bewertung (`config/profile` → `scans/ratings`)
Profil im Artefakt (Reiter „Profil“): `config/profile` = `{cv, wishes, updated_at}`.
Der Lauf (`scan.py bewerten`) gibt Claude nur Neues: Stellen der Bewerberliste, die noch keine Bewertung zum aktuellen Profil haben, und Treffer, die in diesem Lauf neu dazugekommen sind (`fs` ≥ `started_at` des Laufs). Ältere Treffer werden nicht nachträglich bewertet; `RATE_MAX` (150) ist nur eine Sicherheitsgrenze, falls eine neue Quelle sehr viele Treffer auf einmal bringt. Grobe Vorauswahl über die Titel; Engineering, Design, HR u. Ä. fallen raus. Jede Stelle kommt mit Anzeigentext, bevorzugt aus der JSON-LD-JobPosting-Beschreibung.
Claude vergibt `fit`, `imp` (Impact), `su` (Startup-Stärke), je 0–100, plus `why`. Das Skript berechnet `s = 0,45·fit + 0,35·imp + 0,2·su` und daraus die Prio: A ≥ 75, B ≥ 62, C ≥ 48, sonst D (D auch bei fit < 35).
`scans/ratings.by_url[<normalisierter Link>] = {fit, imp, su, s, p, why, at, pa}`. `pa` ist der Profilstand; nach einer Profiländerung wird die Bewerberliste neu bewertet (ältere Treffer nicht). Einträge älter als 60 Tage fallen weg.

## Pipeline
Statuswechsel im Artefakt schreiben `status_at` und `hist[<Status>]` in `applications/<id>`. Die Pipeline zählt je Stufe, wie viele Bewerbungen sie erreicht haben (aktueller Status oder Verlauf). Board-Ansicht mit Drag & Drop.

`config/main.trigger_id` muss auf die aktive Aufgabe „Praktikums-Radar Scan“ zeigen. Die alten, deaktivierten Aufgaben laufen in einer Umgebung ohne Netzwerkzugriff.

## Termine (Kalender + One-Pager)

Reiter „Termine“ im Artefakt: Monatsansicht plus Liste „Nächste Termine“ / „Eingeladen – noch zu buchen“ / „Vorbei“. Daten: Collection `interviews`, je Gespräch ein Dokument `<firma>-<runde>` = `{company, title, app_id, kind, status: einladung|gebucht|abgesagt, start (ISO|null), dur_min, with, booking_url, join_url, mail_at, source, onepager}`.
`onepager` = `{tagline, facts: [[k, v]], sections: [{h, items}], questions, pitch, sources: [{t, u}], at}`; ein Klick auf einen Eintrag öffnet ihn. Datum/Uhrzeit lassen sich im One-Pager setzen (falls die Buchungsbestätigung nicht in Gmail landet).
Gepflegt vom Mail-Abgleich (geplante Aufgabe „Bewerbungs-Mails abgleichen“, 07:12/12:12/19:12): Einladungen und Terminbestätigungen → Eintrag, fehlender One-Pager → Web-Recherche (höchstens 5 Suchen).
