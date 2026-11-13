// Demo runtime for the Praktikums-Radar app.
// The real app runs as a claude.ai artifact and talks to `window.claude` (artifact database, MCP connector to
// Claude Code Remote for starting / cancelling the scheduled scan). This file provides the same surface in the
// browser, backed by fictional sample data (window.__DEMO_DATA) and localStorage, so the UI can be explored
// without an account. "Jetzt scannen" plays back a simulated run through the same phases as scanner/scan.py.
(() => {
  "use strict";
  const KEY = "radar-demo-v1";
  const DAY = 864e5;

  // Sample data is generated at a fixed date; shift all timestamps by whole days so "new", "this morning's run"
  // and upcoming interviews stay current whenever the demo is opened.
  function rebase(data) {
    const shift = Math.max(0, Math.floor((Date.now() - new Date(data.base).getTime()) / DAY)) * DAY;
    const iso = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$/, day = /^\d{4}-\d{2}-\d{2}$/;
    const move = (v) => {
      if (typeof v === "string") {
        if (iso.test(v)) return new Date(new Date(v).getTime() + shift).toISOString();
        if (day.test(v)) return new Date(new Date(v + "T12:00:00Z").getTime() + shift).toISOString().slice(0, 10);
        return v;
      }
      if (Array.isArray(v)) return v.map(move);
      if (v && typeof v === "object") return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, move(x)]));
      return v;
    };
    return move(data.store);
  }
  function load() {
    try { const s = JSON.parse(localStorage.getItem(KEY) || "null"); if (s && s.v === window.__DEMO_DATA.base) return s.store; } catch (e) {}
    return rebase(window.__DEMO_DATA);
  }
  const store = load();   // { "<collection>": { "<id>": data } }
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify({ v: window.__DEMO_DATA.base, store })); } catch (e) {} };
  window.radarDemoReset = () => { try { localStorage.removeItem(KEY); } catch (e) {} location.reload(); };

  const clone = (x) => (x === undefined ? undefined : JSON.parse(JSON.stringify(x)));
  const split = (p) => { const i = p.indexOf("/"); return [p.slice(0, i), p.slice(i + 1)]; };
  const merge = (a, b) => {
    const out = { ...(a || {}) };
    for (const [k, v] of Object.entries(b || {})) out[k] = v && typeof v === "object" && !Array.isArray(v) && out[k] && typeof out[k] === "object" && !Array.isArray(out[k]) ? merge(out[k], v) : v;
    return out;
  };
  const listeners = new Set();
  const notify = () => { save(); setTimeout(() => listeners.forEach((f) => f()), 0); };

  function doc(path) {
    const [c, id] = split(path);
    const snap = () => { const d = store[c]?.[id]; return { id, exists: d !== undefined, data: () => clone(d) }; };
    return {
      get: async () => snap(),
      onSnapshot(cb) { const f = () => cb(snap()); listeners.add(f); f(); return () => listeners.delete(f); },
      async set(v) { (store[c] ||= {})[id] = clone(v); notify(); },
      async update(v) { (store[c] ||= {})[id] = merge(store[c][id], clone(v)); notify(); },
      async delete() { if (store[c]) delete store[c][id]; notify(); },
    };
  }
  function collection(c) {
    let order = null, lim = Infinity;
    const q = {
      limit(n) { lim = n; return q; },
      orderBy(f, dir) { order = [f, dir]; return q; },
      where() { return q; },
      onSnapshot(cb) {
        const f = () => {
          let docs = Object.entries(store[c] || {}).map(([id, d]) => ({ id, data: () => clone(d), _d: d }));
          if (order) docs.sort((a, b) => String(a._d[order[0]] ?? "").localeCompare(String(b._d[order[0]] ?? "")) * (order[1] === "desc" ? -1 : 1));
          cb({ docs: docs.slice(0, lim) });
        };
        listeners.add(f); f(); return () => listeners.delete(f);
      },
    };
    return q;
  }
  const db = { doc, collection };

  // ---------------------------------------------------------------- simulated scan run (phases as in scanner/scan.py)
  let running = null;
  const PHASES = [
    ["daten", 3, "ok", "Datenbank gelesen: {startups} Startups, 4 Jobbörsen, {apps} Bewerbungen", "Scanne {active} Karriereseiten (24 parallel, max. 4 je Host) …"],
    ["startups", 8, "ok", "Startups: {ok} ok, {err} Fehler · {hits} Treffer, davon 3 neu", "Lese externe Jobbörsen (YC, VC-Portfolios, Berlin Startup Jobs, Arbeitnow) …"],
    ["boards", 28, "ok", "Jobbörsen: {bhits} Treffer (1 neu) aus 4 Quellen · {cands} Kandidaten", "Prüfe Bewerberliste auf Startdatum und Online-Datum …"],
    ["details", 72, "ok", "Bewerberliste: {apps} Links · Startdatum bei 14 · Online-Datum bei 19 · 1 offline", "Bereite KI-Bewertung vor …"],
    ["bewerten", 78, "ok", "KI-Bewertung: 4 neue Stellen vorbereitet", "Claude bewertet 4 Stellen nach deinem Profil (Fit, Impact, Startup) …"],
    ["fertig", 100, "ok", "KI-Bewertung: 4 Stellen bewertet · Prio A 1 · B 2 · C 1 · D 0", "Speichere Ergebnisse …"],
  ];
  function simulateRun() {
    const t0 = new Date(), id = "demo-" + t0.toISOString().slice(0, 16).replace(/\D/g, "");
    const n = (c) => Object.keys(store[c] || {}).length;
    const st = Object.values(store.startups || {}), latest = store.scans?.latest || {};
    const vars = { startups: st.length, active: st.filter((s) => s.active).length, apps: n("applications"),
      ok: Object.values(latest.results || {}).filter((r) => r.s === "ok").length, err: Object.values(latest.results || {}).filter((r) => r.s === "err").length,
      hits: (latest.hits || []).length + 3, bhits: (store.scans?.boards?.hits || []).length + 1, cands: Object.keys(store.scans?.candidates?.candidates || {}).length };
    const fill = (s) => s.replace(/\{(\w+)\}/g, (_, k) => vars[k]);
    const log = [[t0.toISOString(), "ok", `Lauf ${id} gestartet (manuell)`], [t0.toISOString(), "run", "Lese Startups, Jobbörsen und Bewerberliste aus der Datenbank …"]];
    const run = { run_id: id, status: "running", started_at: t0.toISOString(), mode: "manuell", engine: "skript", phase: "daten", pct: 3, phase_at: t0.toISOString(), log, dur: { daten: 2, startups: 4, boards: 5, details: 3, bewerten: 3 } };
    (store.runs ||= {})[id] = run; notify();
    let i = 0;
    running = { id, timer: null };
    const step = () => {
      const r = store.runs[id]; if (!r || r.status !== "running") { running = null; return; }
      const [phase, pct, kind, done, next] = PHASES[i], now = new Date().toISOString();
      r.log = [...r.log, [now, kind, fill(done)], ...(phase === "fertig" ? [] : [[now, "run", fill(next)]])];
      const nextPhase = PHASES[i + 1];
      Object.assign(r, { phase: nextPhase ? nextPhase[0] : "fertig", pct: nextPhase ? nextPhase[1] : 100, phase_at: now });
      if (phase === "startups") addNewHits(t0);
      if (phase === "fertig") {
        const secs = Math.round((Date.now() - t0) / 1000);
        r.log.push([now, "ok", `Fertig nach 0:${String(secs).padStart(2, "0")} min`]);
        Object.assign(r, { status: "done", finished_at: now, seconds: secs, checked: vars.active, ok: vars.ok, errors: vars.err, hits_total: vars.hits, new_hits: 3 });
        running = null; notify(); return;
      }
      notify(); i++; running.timer = setTimeout(step, 2600);
    };
    running.timer = setTimeout(step, 2200);
    return id;
  }
  function addNewHits(t0) {
    const latest = store.scans.latest, now = new Date().toISOString(), extra = window.__DEMO_DATA.simulated || [];
    const fresh = extra.map((h) => ({ ...h, fs: now }));
    latest.hits = [...fresh, ...(latest.hits || []).filter((h) => !fresh.some((x) => x.u === h.u))];
    Object.assign(latest, { run_id: running?.id || latest.run_id, started_at: t0.toISOString(), finished_at: now, new_hits: fresh.length, hits_total: latest.hits.length });
    const rt = store.scans.ratings ||= { by_url: {} };
    for (const h of extra) if (h.rating) rt.by_url[h.u.toLowerCase().replace(/[?#].*$/, "").replace(/\/+$/, "")] = { ...h.rating, at: now };
    for (const h of latest.hits) delete h.rating;
  }
  const mcp = {
    async callTool(server, name, args) {
      if (name === "fire_trigger") { const id = simulateRun(); return { payload: { session_id: "cse_" + id } }; }
      if (name === "interrupt_session") { if (running) clearTimeout(running.timer); running = null; return { payload: { ok: true } }; }
      if (name === "get_trigger") return { payload: { trigger: { id: args.trigger_id, last_run: running ? { session_id: "cse_" + running.id, fired_at: new Date().toISOString() } : {} } } };
      if (name === "list_triggers") {
        const next = new Date(); next.setDate(next.getDate() + (next.getHours() >= 7 ? 1 : 0)); next.setHours(6, 55, 0, 0);
        return { payload: { data: [{ id: "demo-trigger", name: "Praktikums-Radar Scan", enabled: true, next_run_at: next.toISOString(), last_run: { status: "ROUTINE_RUN_STATUS_SUCCEEDED", fired_at: store.scans?.latest?.started_at } }] } };
      }
      return { payload: { ok: true } };
    },
  };
  const user = { can: async () => true };

  window.claude = { use: async (k) => ({ db, mcp, user }[k] ?? null) };
})();
