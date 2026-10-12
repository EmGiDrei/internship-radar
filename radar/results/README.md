# Ergebnisse Testlauf 2026-10-12 (Cloud-Session)

- `discovery.json` – `discover.py` für die 500 aktiven startupmap-Firmen. startupmap.one blockt Cloud-IPs (Cloudflare, HTTP 403),
  daher kamen alle Links über den Fallback (Website raten / ATS-Slug prüfen, jeweils mit Abgleich des Firmennamens).
  Feld `conf`: `hoch` = ATS-Link auf der eigenen Website, `mittel` = über Namen gefunden + Website bekannt,
  `pruefen` = kurzer Name oder keine Website → Namensvetter möglich (z. B. mo-re, maze, roger), vor Übernahme ansehen.
  Ergebnis: 242 ATS-Boards (hoch 50 / mittel 114 / pruefen 78), 66 nur Karriereseite, 192 nichts.
- `latest.json`, `run.json` – Volllauf `scan.py` über alle aktiven Firmen. Für startupmap-Firmen wurden in einer **Kopie**
  der Daten die gefundenen Boards bzw. Karriereseiten als Quelle eingesetzt (Karriereseiten mit `conf=pruefen` nicht).
  Die DB wurde nur gelesen, nicht geändert. Vergleich mit unveränderten DB-Quellen aus der Cloud: 107 ok / 515 Fehler;
  mit Discovery: 397 ok / 225 Fehler (Rest v. a. startupmap 403 für Firmen ohne Fund).
