#!/usr/bin/env python3
# Praktikums-Radar – Scan ohne KI: liest Stellenlisten direkt (ATS-APIs/HTML) und filtert per Wortliste.
# Eingabe:  $RADAR_DIR/in/startups/*.json, $RADAR_DIR/in/scans/latest.json (optional), $RADAR_DIR/meta.json
#           optional $RADAR_DIR/in/boards/*.json (externe Jobbörsen), $RADAR_DIR/in/scans/boards.json, …/scans/candidates.json,
#           $RADAR_DIR/in/applications/*.json (Bewerberliste, nur gelesen), $RADAR_DIR/in/scans/details.json
# Ausgabe:  $RADAR_DIR/latest.json, $RADAR_DIR/run.json, ggf. boards.json + candidates.json + details.json, progress.json, Zusammenfassung auf stdout
# Aufruf:   python3 scan.py [init|daten|startups|boards|details|fertig]  – ohne Argument alle Phasen nacheinander
import json, os, re, glob, html, datetime, threading, time, urllib.request, urllib.error, urllib.parse
import concurrent.futures as cf
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

D = os.environ.get('RADAR_DIR', '/tmp/radar')
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
TYP = re.compile(r"\bintern(s|ship|ships)?\b|praktik|werkstud|working student|studentische|student assistant|\bhiwi\b|praxissemester|thesis|abschlussarbeit|masterarbeit|bachelorarbeit", re.I)
TRACK = re.compile(r"founder|founding associate|founding generalist|gründer|chief of staff|entrepreneur|\beir\b|ceo office|office of the ceo|ceo's office|cfo office|coo office|assistant to the ceo|ceo assistant|assistenz der geschäftsführung|venture develop|venture build|venture architect|venture associate|venture analyst|venture capital|company build|business builder", re.I)
SOCIAL = re.compile(r'(^|\.)(linkedin|twitter|x|facebook|instagram|youtube|xing|tiktok|github|medium)\.com$', re.I)
def want(t): return bool(t) and bool(TYP.search(t) or TRACK.search(t))

# ---------------------------------------------------------------- HTTP (pro Host höchstens 4 parallel)
_hostsem, _hl = {}, threading.Lock()
def _sem(host):
    with _hl:
        return _hostsem.setdefault(host, threading.Semaphore(4))
class HttpErr(Exception): pass
def get(url, timeout=25, accept='*/*'):
    host = urllib.parse.urlsplit(url).hostname or ''
    with _sem(host):
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': accept, 'Accept-Language': 'de,en;q=0.8'})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read(6_000_000)
                cs = r.headers.get_content_charset() or 'utf-8'
                return r.geturl(), raw.decode(cs, 'replace')
        except urllib.error.HTTPError as e:
            raise HttpErr('HTTP %s' % e.code)
        except Exception as e:
            raise HttpErr(type(e).__name__ + (': ' + str(e)[:80] if str(e) else ''))
def getjson(url, **kw): return json.loads(get(url, accept='application/json', **kw)[1])

def pdate(x):
    # Veröffentlichungsdatum vereinheitlichen → 'YYYY-MM-DD' (ISO, Unix-s/-ms, RFC-822, relativ wie „6 days“); sonst ''
    try:
        if x in (None, ''): return ''
        if isinstance(x, (int, float)) or re.fullmatch(r'\d{9,13}', str(x)):
            v = float(x); v = v / 1000 if v > 1e11 else v
            return datetime.datetime.fromtimestamp(v, datetime.timezone.utc).strftime('%Y-%m-%d')
        x = str(x).strip()
        if m := re.match(r'(\d{4}-\d{2}-\d{2})', x): return m.group(1)
        if m := re.fullmatch(r'(?:about |over |almost )?(\d+|an?) (minute|hour|day|week|month|year)s?(?: ago)?', x, re.I):
            n = 1 if m.group(1).lower() in ('a', 'an') else int(m.group(1))
            d = {'minute': 1 / 1440, 'hour': 1 / 24, 'day': 1, 'week': 7, 'month': 30, 'year': 365}[m.group(2).lower()] * n
            return (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=d)).strftime('%Y-%m-%d')
        import email.utils
        return email.utils.parsedate_to_datetime(x).strftime('%Y-%m-%d')
    except Exception:
        return ''

def clean(s): return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', str(s or '')))).strip()

# ---------------------------------------------------------------- HTML: Links mit Text einsammeln
class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.out = []; self.stack = []
    def handle_starttag(self, tag, a):
        if tag == 'a': self.stack.append([dict(a).get('href') or '', []])
    def handle_endtag(self, tag):
        if tag == 'a' and self.stack:
            href, txt = self.stack.pop(); self.out.append((href, ' '.join(txt)))
    def handle_data(self, d):
        for s in self.stack: s[1].append(d)
def links(base, text):
    p = Links()
    try: p.feed(text)
    except Exception: pass
    out = []
    for href, t in p.out:
        t = clean(t)
        if not href or href.startswith(('mailto:', 'tel:', 'javascript:', '#')): continue
        out.append((urllib.parse.urljoin(base, href), t))
    return out

# ---------------------------------------------------------------- Adapter: liefern [(titel, ort, url)], gesamtzahl
def a_personio(org, tld):
    last = None
    for t in [tld] + [x for x in ('de', 'com') if x != tld]:
        try: _, txt = get(f'https://{org}.jobs.personio.{t}/xml')
        except HttpErr as e: last = e; continue
        root = ET.fromstring(txt.encode('utf-8'))
        jobs = [(p.findtext('name') or '', p.findtext('office') or '', f'https://{org}.jobs.personio.{t}/job/{p.findtext("id")}', pdate(p.findtext('createdAt'))) for p in root.iter('position')]
        return jobs, len(jobs)
    raise last or HttpErr('Personio nicht gefunden')
def a_ashby(org):
    d = getjson(f'https://api.ashbyhq.com/posting-api/job-board/{org}')
    jobs = [(j.get('title'), j.get('location') or '', j.get('jobUrl') or f'https://jobs.ashbyhq.com/{org}', pdate(j.get('publishedAt'))) for j in d.get('jobs', []) if j.get('isListed', True)]
    return jobs, len(jobs)
def a_greenhouse(org, eu):
    # Die US-API liefert auch EU-Boards; boards-api.eu.greenhouse.io ist nicht überall erreichbar → nur Ersatz
    last = None
    for h in ('boards-api.greenhouse.io', 'boards-api.eu.greenhouse.io'):
        try: d = getjson(f'https://{h}/v1/boards/{org}/jobs')
        except HttpErr as e:
            if last is None or not str(last).startswith('HTTP'): last = e   # aussagekräftigsten Fehler (HTTP-Status) behalten
            continue
        jobs = [(j.get('title'), (j.get('location') or {}).get('name', ''), j.get('absolute_url'), pdate(j.get('first_published') or j.get('updated_at'))) for j in d.get('jobs', [])]
        return jobs, len(jobs)
    raise last
def a_lever(org, eu):
    hosts = ['api.eu.lever.co', 'api.lever.co'] if eu else ['api.lever.co', 'api.eu.lever.co']
    last = None
    for h in hosts:
        try: d = getjson(f'https://{h}/v0/postings/{org}?mode=json', timeout=45)
        except HttpErr as e:
            if last is None: last = e   # Fehler des Haupt-Hosts melden, nicht den 404 des Ersatz-Hosts
            continue
        if isinstance(d, dict) and not d.get('ok', True): last = HttpErr('Lever: ' + str(d.get('error', ''))[:60]); continue
        jobs = [(j.get('text'), (j.get('categories') or {}).get('location', ''), j.get('hostedUrl'), pdate(j.get('createdAt'))) for j in d]
        return jobs, len(jobs)
    raise last
def a_workable(org):
    d = getjson(f'https://apply.workable.com/api/v1/widget/accounts/{org}')
    jobs = [(j.get('title'), ', '.join(x for x in (j.get('city'), j.get('country')) if x), j.get('url') or f'https://apply.workable.com/{org}/j/{j.get("shortcode")}', pdate(j.get('published_on') or j.get('created_at'))) for j in d.get('jobs', [])]
    return jobs, len(jobs)
def a_recruitee(org):
    d = getjson(f'https://{org}.recruitee.com/api/offers/')
    jobs = [(j.get('title'), j.get('location') or j.get('city') or '', j.get('careers_url') or f'https://{org}.recruitee.com/o/{j.get("slug")}', pdate(j.get('published_at') or j.get('created_at'))) for j in d.get('offers', [])]
    return jobs, len(jobs)
def a_smartrecruiters(org):
    jobs, off, total = [], 0, None
    while True:
        d = getjson(f'https://api.smartrecruiters.com/v1/companies/{org}/postings?limit=100&offset={off}')
        total = d.get('totalFound', 0)
        for j in d.get('content', []):
            loc = j.get('location') or {}
            jobs.append((j.get('name'), loc.get('city') or loc.get('country') or '', f'https://jobs.smartrecruiters.com/{org}/{j.get("id")}', pdate(j.get('releasedDate'))))
        off += 100
        if off >= total or not d.get('content'): break
    return jobs, total
def _join_state(url):
    base, txt = get(url)
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', txt, re.S)
    try: return base, txt, json.loads(m.group(1))['props']['pageProps']['initialState']['jobs']
    except Exception: return base, txt, None
def a_join(org):
    # join.com rendert pro Seite nur 5 Stellen → alle Seiten (?page=N) über initialState.jobs lesen
    base, txt, st = _join_state(f'https://join.com/companies/{org}')
    jobs = []
    if st is not None:
        pages = min(int((st.get('pagination') or {}).get('pageCount') or 1), 40)
        items = list(st.get('items') or [])
        for p in range(2, pages + 1):
            items += (_join_state(f'https://join.com/companies/{org}?page={p}')[2] or {}).get('items') or []
        for x in items:
            c = x.get('city') or {}
            city = (c.get('cityName') or '') if isinstance(c, dict) else str(c)
            jobs.append((x.get('title') or '', city, f'https://join.com/companies/{org}/{x.get("idParam") or x.get("id")}', pdate(x.get('createdAt'))))
        total = (st.get('pagination') or {}).get('total')
        if not jobs and total:   # z. B. nur Initiativbewerbung, die nicht in items steht
            jobs = [(t, '', u) for u, t in links(base, txt) if f'/companies/{org}/' in u and t]
    else:
        jobs = [(t, '', u) for u, t in links(base, txt) if f'/companies/{org}/' in u and t]
        total = None
    seen, out = set(), []
    for j in jobs:
        if j[2] not in seen: seen.add(j[2]); out.append(j)
    return out, total if isinstance(total, int) else len(out)
def a_teamtailor(host):
    # RSS-Feed enthält alle Stellen (die HTML-Liste lädt nach); Umleitung auf eigene Domain = Board nicht mehr aktiv
    base, txt = get(f'https://{host}/jobs.rss')
    if urllib.parse.urlsplit(base).hostname != host: raise HttpErr('Teamtailor umgeleitet auf ' + base[:80])
    root = ET.fromstring(txt.encode('utf-8'))
    jobs = []
    for it in root.iter('item'):
        locs = [clean(e.text) for e in it.iter() if e.tag.endswith('}city') and e.text]
        jobs.append((it.findtext('title') or '', ', '.join(dict.fromkeys(locs)), it.findtext('link') or f'https://{host}/jobs', pdate(it.findtext('pubDate'))))
    return jobs, len(jobs)
def a_web(url):
    # Generisch: alle Links, deren Text nach Stelle aussieht (Titel-Filter kommt später)
    base, txt = get(url)
    jobs, seen = [], set()
    for u, t in links(base, txt):
        if SOCIAL.search(urllib.parse.urlsplit(u).netloc): continue   # z. B. LinkedIn-Profile „Co-Founder & CEO“
        if 4 <= len(t) <= 160 and want(t) and (u, t) not in seen:
            seen.add((u, t)); jobs.append((t, '', u))
    return jobs, None
def a_startupmap(url):
    base, txt = get(url)
    jobs, seen = [], set()
    for u, t in links(base, txt):
        if 4 <= len(t) <= 160 and want(t) and t.lower() not in seen:
            seen.add(t.lower()); jobs.append((t, '', u))
    n = len(set(t.lower() for u, t in links(base, txt) if 'apply=' in u)) or None
    return jobs, n

def a_ycco(slug):
    # YC-Firmenseite (ycombinator.com/companies/<slug>/jobs): Stellen als JSON im data-page-Attribut
    _, txt = get(f'https://www.ycombinator.com/companies/{slug}/jobs')
    p = json.loads(html.unescape(re.search(r'data-page="([^"]*)"', txt).group(1)))['props']
    jobs = [(j.get('title') or '', j.get('location') or '', 'https://www.ycombinator.com' + (j.get('url') or ''), pdate(j.get('createdAt'))) for j in p.get('jobPostings') or []]
    return jobs, len(jobs)
def a_bsjco(slug):
    # Firmenseite bei Berlin Startup Jobs: dieselben Stellenkarten wie die Listen
    _, txt = get(f'https://berlinstartupjobs.com/companies/{slug}/')
    jobs = [(clean(m.group(2)), 'Berlin', m.group(1)) for m in re.finditer(r'<h4 class="bjs-jlid__h"><a href="([^"]+)">(.*?)</a>', txt, re.S)]
    return jobs, len(jobs)

def route(u):
    u = (u or '').strip()
    if m := re.match(r'https?://([^./]+)\.jobs\.personio\.(de|com)', u): return a_personio, (m.group(1), m.group(2))
    if m := re.search(r'(?:api\.ashbyhq\.com/posting-api/job-board|jobs\.ashbyhq\.com)/([^/?#]+)', u): return a_ashby, (m.group(1),)
    if m := re.search(r'(boards-api|job-boards|boards)(\.eu)?\.greenhouse\.io/(?:v1/boards/)?([^/?#]+)', u): return a_greenhouse, (m.group(3), bool(m.group(2)))
    if m := re.search(r'(?:api|jobs)(\.eu)?\.lever\.co/(?:v0/postings/)?([^/?#]+)', u): return a_lever, (m.group(2), bool(m.group(1)))
    if m := re.search(r'apply\.workable\.com/(?:api/v1/widget/accounts/)?([^/?#]+)', u): return a_workable, (m.group(1),)
    if m := re.match(r'https?://([^./]+)\.recruitee\.com', u): return a_recruitee, (m.group(1),)
    if m := re.search(r'(?:api|careers|jobs)\.smartrecruiters\.com/(?:v1/companies/)?([^/?#]+)', u): return a_smartrecruiters, (m.group(1),)
    if m := re.search(r'join\.com/companies/([^/?#]+)', u): return a_join, (m.group(1),)
    if m := re.match(r'https?://([^/]+\.teamtailor\.com)', u): return a_teamtailor, (m.group(1),)
    if m := re.search(r'ycombinator\.com/companies/([^/?#]+)', u): return a_ycco, (m.group(1),)
    if m := re.search(r'berlinstartupjobs\.com/companies/([^/?#]+)', u): return a_bsjco, (m.group(1),)
    if 'startupmap.one/startup/' in u: return a_startupmap, (u,)
    return a_web, (u,)

def fetch_one(sid, d):
    tried, first = [], 'keine Quelle'
    for u in [d.get('source_url'), d.get('career_url'), d.get('sm_url')]:
        if not u or u in tried: continue
        tried.append(u)
        fn, args = route(u)
        try:
            jobs, total = fn(*args)
            return {'id': sid, 's': 'ok', 'n': total, 'jobs': jobs, 'via': u if len(tried) > 1 else '', 'e': ''}
        except Exception as e:
            err = str(e)[:120] or type(e).__name__
            if len(tried) == 1: first = err
    return {'id': sid, 's': 'err', 'e': first, 'jobs': [], 'n': None}

# ---------------------------------------------------------------- Fortschritt ($D/progress.json → runs/<Lauf-ID>, Live-Anzeige im Artefakt)
# Phasen mit Anteil am Ladebalken (Start-%); log = [[ISO-Zeit, ok|run|err|info, Text], …]
PHASES = [('start', 0), ('daten', 3), ('startups', 8), ('boards', 30), ('details', 88), ('fertig', 100)]
def utcnow(): return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
def progress(phase, *lines):
    pf = f'{D}/progress.json'
    p = json.load(open(pf)) if os.path.exists(pf) else {}
    t = utcnow()
    if not p:
        meta = json.load(open(f'{D}/meta.json'))
        p = {'run_id': meta['run_id'], 'status': 'running', 'started_at': meta['started_at'], 'mode': meta.get('mode', 'geplant'),
             'engine': 'skript', 'log': [], 'dur': {}}
    if p.get('phase') and p.get('phase_at') and p['phase'] != phase:   # Dauer der beendeten Phase (Schätzung fürs nächste Mal)
        p['dur'][p['phase']] = round((datetime.datetime.fromisoformat(t) - datetime.datetime.fromisoformat(p['phase_at'])).total_seconds())
    p.update(phase=phase, pct=dict(PHASES)[phase], phase_at=t)
    p['log'] = (p['log'] + [[t, k, str(m)[:160]] for k, m in lines])[-40:]
    json.dump(p, open(pf, 'w'), ensure_ascii=False)
    for _, k, m in p['log'][-len(lines):] if lines else []: print(f'[{k}] {m}')
    return p

def _docs(sub):
    out = {}
    for f in glob.glob(f'{D}/in/{sub}/*.json'):
        x = json.load(open(f))
        if isinstance(x, dict) and isinstance(x.get('data'), dict) and ('version' in x or 'id' in x): x = x['data']
        out[os.path.basename(f)[:-5]] = x
    return out
def load_startups(): return _docs('startups')

def cmd_init():
    meta = json.load(open(f'{D}/meta.json'))
    progress('daten', ('ok', f"Lauf {meta['run_id']} gestartet ({meta.get('mode', 'geplant')})"), ('run', 'Lese Startups, Jobbörsen und Bewerberliste aus der Datenbank …'))

def cmd_daten():
    st = load_startups()
    act = sum(1 for d in st.values() if d.get('active') and d.get('source_url'))
    nb = sum(1 for d in _docs('boards').values() if isinstance(d, dict) and d.get('active'))
    na = len(_docs('applications'))
    progress('startups', ('ok', f'Datenbank gelesen: {len(st)} Startups ({act} aktiv), {nb} Jobbörsen, {na} Bewerbungen'),
             ('run', f'Scanne {act} Karriereseiten (24 parallel, max. 4 je Host) …'))

def cmd_startups():
    r = scan_startups()
    progress('boards', ('ok' if r['errors'] < r['checked'] / 2 else 'err', f"Startups: {r['ok']} ok, {r['errors']} Fehler · {r['hits_total']} Treffer, davon {r['new_hits']} neu"),
             ('run', 'Lese externe Jobbörsen (YC, VC-Portfolios, Berlin Startup Jobs, Arbeitnow) …'))

def cmd_boards():
    now = json.load(open(f'{D}/latest.json'))['finished_at'] if os.path.exists(f'{D}/latest.json') else utcnow()
    if not os.path.isdir(f'{D}/in/boards'):
        return progress('details', ('info', 'Jobbörsen: keine Quellen geladen – übersprungen'), ('run', 'Prüfe Bewerberliste auf Startdatum und Online-Datum …'))
    try:
        b = boards_main(load_startups(), now) or {}
        c = json.load(open(f'{D}/candidates.json')) if os.path.exists(f'{D}/candidates.json') else {}
        errs = [k for k, v in (b.get('results') or {}).items() if v['s'] == 'err']
        line = ('ok', f"Jobbörsen: {b.get('hits_total', 0)} Treffer ({b.get('new_hits', 0)} neu) aus {len(b.get('results') or {})} Quellen"
                + (f", Fehler bei {', '.join(errs)}" if errs else '') + f" · {c.get('count', 0)} Kandidaten")
    except Exception as e:
        line = ('err', f'Jobbörsen: Fehler {type(e).__name__} {str(e)[:100]}')
    progress('details', line, ('run', 'Prüfe Bewerberliste auf Startdatum und Online-Datum …'))

def cmd_details():
    now = utcnow()
    if not os.path.isdir(f'{D}/in/applications'):
        return progress('fertig', ('info', 'Bewerberliste: nicht geladen – übersprungen'), ('run', 'Speichere Ergebnisse …'))
    try:
        d = details_main(now) or {}
        line = ('ok', f"Bewerberliste: {d.get('n', 0)} Links · Startdatum bei {d.get('sd', 0)} · Online-Datum bei {d.get('pd', 0)}")
    except Exception as e:
        line = ('err', f'Bewerberliste: Fehler {type(e).__name__} {str(e)[:100]}')
    progress('fertig', line, ('run', 'Speichere Ergebnisse …'))

def cmd_fertig():
    p = json.load(open(f'{D}/progress.json'))
    run = json.load(open(f'{D}/run.json'))
    secs = round((datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(p['started_at'].replace('Z', '+00:00'))).total_seconds())
    p = progress('fertig', ('ok', f'Fertig nach {secs // 60}:{secs % 60:02d} min'))
    run.update(status='done', finished_at=utcnow(), seconds=secs, phase='fertig', pct=100, log=p['log'], dur=p['dur'])
    json.dump(run, open(f'{D}/run.json', 'w'), ensure_ascii=False)
    print(json.dumps({k: run[k] for k in ('checked', 'ok', 'errors', 'hits_total', 'new_hits', 'seconds')}, ensure_ascii=False))

def main():
    # Alles in einem Aufruf (lokal); der geplante Lauf ruft die Phasen einzeln auf und meldet dazwischen den Fortschritt
    for f in (cmd_init, cmd_daten, cmd_startups, cmd_boards, cmd_details, cmd_fertig): f()

def scan_startups():
    t0 = time.time()
    now = utcnow()
    meta = json.load(open(f'{D}/meta.json'))
    st = load_startups()
    pf = f'{D}/in/scans/latest.json'
    prev = json.load(open(pf)) if os.path.exists(pf) else {}
    if isinstance(prev.get('data'), dict): prev = prev['data']
    old = prev.get('hits') or []
    fs_of = {(h.get('id'), str(h.get('t', '')).lower()): h.get('fs') for h in old}
    old_by = {}
    for h in old: old_by.setdefault(h.get('id'), []).append(h)
    todo = {i: d for i, d in st.items() if d.get('active') and d.get('source_url')}
    with cf.ThreadPoolExecutor(max_workers=24) as ex:
        res_list = list(ex.map(lambda kv: fetch_one(*kv), todo.items()))
    results, hits = {}, []
    for r in res_list:
        i = r['id']; h, seen = [], set()
        for t, l, u, *x in r['jobs']:
            t = clean(t)[:160]
            if not want(t) or t.lower() in seen: continue
            seen.add(t.lower())
            h.append({'id': i, 't': t, 'l': clean(l)[:80], 'u': str(u or '')[:300], 'fs': fs_of.get((i, t.lower())) or now})
            if x and x[0]: h[-1]['pd'] = x[0]
        e = r['e']
        if r['s'] == 'ok' and r.get('via'): e = 'Hauptquelle fehlgeschlagen – über Ersatzquelle gelesen'
        if r['s'] != 'ok': h = old_by.get(i, [])            # letzte bekannte Treffer behalten
        results[i] = {'s': 'ok' if r['s'] == 'ok' and not r.get('via') else 'err', 'n': r['n'] if isinstance(r['n'], int) else None,
                      'e': e, 'h': len(h), 'at': now}
        hits += h
    sz = lambda o: len(json.dumps(o, ensure_ascii=False, separators=(',', ':')).encode())
    hits = hits[:1500]
    while hits and sz({'r': results, 'h': hits}) > 235000: hits = hits[:int(len(hits) * 0.9)]
    errs = sorted(k for k, v in results.items() if v['s'] == 'err')
    new = sum(1 for h in hits if h['fs'] == now)
    out = {'run_id': meta['run_id'], 'started_at': meta['started_at'], 'finished_at': now, 'mode': meta.get('mode', 'geplant'),
           'engine': 'skript', 'checked': len(results), 'ok': len(results) - len(errs), 'errors': len(errs),
           'hits_total': len(hits), 'new_hits': new, 'results': results, 'hits': hits}
    json.dump(out, open(f'{D}/latest.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    run = {k: out[k] for k in ('run_id', 'started_at', 'finished_at', 'mode', 'engine', 'checked', 'ok', 'errors', 'hits_total', 'new_hits')}
    run.update(status='done', error_ids=errs[:60], seconds=round(time.time() - t0))
    json.dump(run, open(f'{D}/run.json', 'w'), ensure_ascii=False)
    print(json.dumps(run, ensure_ascii=False))
    print('Fehler bei:', ', '.join(str(st[k].get('name', k)) for k in errs[:10]))
    return run

# ================================================================ Externe Jobbörsen (Collection boards → $D/boards.json)
# Liefern [(titel, ort, url, firma)]. Nur Praktikum/Werkstudent/Founders-Associate-artige Titel in DE bzw. Paris/Lille.
STRICT = re.compile(r"\bintern(s|ship|ships)?\b|praktik|werkstud|working student|studentische|student assistant|\bhiwi\b|thesis|abschlussarbeit"
                    r"|founder'?s'? associate|founding associate|stagiaire|\bstage\b|alternan", re.I)
LOC_OK = re.compile(r'germany|deutschland|\bde\b|berlin|m[üu]nchen|munich|hamburg|k[öo]ln|cologne|frankfurt|d[üu]sseldorf|stuttgart|leipzig'
                    r'|dresden|hannover|n[üu]rnberg|nuremberg|karlsruhe|mannheim|heidelberg|aachen|bonn|potsdam|freiburg|t[üu]bingen|darmstadt'
                    r'|paris|lille|[iî]le-de-france|hauts-de-france', re.I)
REMOTE_EU = re.compile(r'remote.{0,40}(europe|eu\b|emea|dach|germany|deutschland|france)|(europe|emea|dach).{0,10}remote', re.I)
def board_want(t, loc):
    return want(t) and bool(STRICT.search(t)) and bool(LOC_OK.search(loc or '') or REMOTE_EU.search(loc or ''))

_last, _ll = {}, threading.Lock()
def polite_get(url, delay, **kw):
    # Crawl-delay je Host einhalten (robots.txt der Getro-Boards: 1–10 s)
    host = urllib.parse.urlsplit(url).hostname
    while True:
        with _ll:
            wait = _last.get(host, 0) + delay - time.time()
            if wait <= 0: _last[host] = time.time(); break
        time.sleep(wait)
    return get(url, **kw)
def crawl_delay(root):
    try: m = re.search(r'(?im)^crawl-delay:\s*(\d+)', get(root.rstrip('/') + '/robots.txt', timeout=10)[1])
    except Exception: m = None
    return min(int(m.group(1)), 15) if m else 2

YC_PAGES = ['location/berlin', 'location/munich', 'location/paris'] + [f'role/{r}/{c}' for r in ('operations', 'sales', 'marketing', 'product') for c in ('berlin', 'munich', 'paris')]
def b_yc(url):
    jobs, errs = [], 0
    for p in YC_PAGES:
        try:
            _, txt = polite_get(f'https://www.ycombinator.com/jobs/{p}', 1)
            d = json.loads(html.unescape(re.search(r'data-page="([^"]*)"', txt).group(1)))
        except Exception: errs += 1; continue
        for j in d['props'].get('jobPostings') or []:
            jobs.append((j.get('title') or '', j.get('location') or '', 'https://www.ycombinator.com' + (j.get('url') or ''), j.get('companyName') or '', '', pdate(j.get('createdAt'))))
    if errs == len(YC_PAGES): raise HttpErr('YC: keine Seite lesbar')
    return jobs
GETRO_Q = ['intern', 'internship', 'praktikum', 'praktikant', 'werkstudent', 'working student', 'founders associate', "founder's associate",
           'founding associate', 'strategy intern', 'business development intern', 'operations intern', 'venture', 'stagiaire', 'stage', 'alternance']
def b_getro(url):
    root = '{0.scheme}://{0.netloc}'.format(urllib.parse.urlsplit(url))
    delay, jobs, ok = crawl_delay(root), [], 0
    for q in GETRO_Q:   # Seitensuche liefert serverseitig die ersten 20 Treffer je Begriff
        try:
            _, txt = polite_get(f'{root}/jobs?q={urllib.parse.quote(q)}', delay)
            d = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', txt, re.S).group(1))
            found = d['props']['pageProps']['initialState']['jobs']['found']; ok += 1
        except Exception: continue
        for j in found:
            jobs.append((j.get('title') or '', ' / '.join(j.get('locations') or []), j.get('url') or f"{root}/companies/{(j.get('organization') or {}).get('slug')}/jobs/{j.get('slug')}",
                         (j.get('organization') or {}).get('name') or '', '', pdate(j.get('createdAt'))))
    if not ok: raise HttpErr('Getro: keine Suche lesbar')
    return jobs
BSJ_PAGES = ['internships/', 'internships/page/2/', 'internships/page/3/', 'operations/', 'product-management/', 'sales/', 'marketing/', 'finance/', 'other/']
def b_bsj(url):
    jobs, ok = [], 0
    for p in BSJ_PAGES:
        try: base, txt = polite_get('https://berlinstartupjobs.com/' + p, 1)
        except HttpErr as e:
            if '404' in str(e): continue
            raise
        ok += 1
        for m in re.finditer(r'<h4 class="bjs-jlid__h"><a href="([^"]+)">(.*?)</a>.*?class="bjs-jlid__b"[^>]*>(.*?)</a>', txt, re.S):
            tag = re.search(r'<a[^>]*bjs-jlid__b[^>]*>', m.group(0))
            co_url = re.search(r'href="([^"]+)"', tag.group(0)) if tag else None
            jobs.append((clean(m.group(2)), 'Berlin', m.group(1), clean(m.group(3)), co_url.group(1) if co_url else ''))
    if not ok: raise HttpErr('BSJ: keine Seite lesbar')
    return jobs
def b_arbeitnow(url):
    jobs = []
    for page in range(1, 11):   # öffentliche API, 300 Stellen je Seite, neueste zuerst
        d = json.loads(polite_get(f'https://www.arbeitnow.com/api/job-board-api?page={page}', 1, accept='application/json')[1])
        for j in d.get('data') or []:
            loc = (j.get('location') or '') + (' / Germany' if not j.get('remote') else ' / Remote Germany')
            jobs.append((j.get('title') or '', loc, j.get('url') or '', j.get('company_name') or '', '', pdate(j.get('created_at'))))
        if not (d.get('links') or {}).get('next'): break
    return jobs
BOARD_ADAPTERS = {'yc': b_yc, 'getro': b_getro, 'bsj': b_bsj, 'arbeitnow': b_arbeitnow}

BAD_ORG = {'embed', 'job_app', 'jobs', 'v1', 'api', 'companies', 'o', 'j'}
def board_of(u):
    # Aus einem Stellen-Link die Board-URL ableiten, die route() vollständig lesen kann; sonst None
    fn, a = route(u)
    if fn is a_web or fn is a_startupmap or not a or str(a[0]).lower() in BAD_ORG: return None, None
    mk = {a_personio: lambda o, t: f'https://{o}.jobs.personio.{t}/', a_ashby: lambda o: f'https://jobs.ashbyhq.com/{o}',
          a_greenhouse: lambda o, eu: f'https://job-boards.greenhouse.io/{o}', a_lever: lambda o, eu: f'https://jobs{".eu" if eu else ""}.lever.co/{o}',
          a_workable: lambda o: f'https://apply.workable.com/{o}/', a_recruitee: lambda o: f'https://{o}.recruitee.com/',
          a_smartrecruiters: lambda o: f'https://careers.smartrecruiters.com/{o}', a_join: lambda o: f'https://join.com/companies/{o}',
          a_teamtailor: lambda h: f'https://{h}/jobs', a_ycco: lambda o: f'https://www.ycombinator.com/companies/{o}/jobs',
          a_bsjco: lambda o: f'https://berlinstartupjobs.com/companies/{o}/'}
    return mk[fn](*a), fn.__name__[2:]

def norm_co(s):
    s = str(s or '').lower().replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    s = re.sub(r'\b(gmbh|ag|se|inc|ltd|co|kg|ug|bv|sas|group|holding|technologies|labs|ai|hq|the)\b', ' ', s)
    return re.sub(r'[^a-z0-9]', '', s)
def slug(s): return re.sub(r'[^a-z0-9]+', '-', str(s or '').lower()).strip('-')[:60] or 'unbekannt'

def boards_main(st, now):
    srcs = {}
    for f in glob.glob(f'{D}/in/boards/*.json'):
        x = json.load(open(f))
        if isinstance(x, dict) and isinstance(x.get('data'), dict) and ('version' in x or 'id' in x): x = x['data']
        if x.get('active') and x.get('adapter') in BOARD_ADAPTERS: srcs[os.path.basename(f)[:-5]] = x
    if not srcs: return {}
    pf = f'{D}/in/scans/boards.json'
    prev = json.load(open(pf)) if os.path.exists(pf) else {}
    if isinstance(prev.get('data'), dict): prev = prev['data']
    fs_of = {(h.get('id'), str(h.get('t', '')).lower()): h.get('fs') for h in prev.get('hits') or []}
    # Firmen, die schon über die Collection startups gescannt werden (aktive), nicht doppelt zeigen: Name oder Board-/Domain-Präfix
    known_names = {norm_co(d.get('name')) for d in st.values() if d.get('active')} - {''}
    known_urls = []
    for d in st.values():
        if not d.get('active'): continue
        for u in (d.get('source_url'), d.get('career_url')):
            if u and 'startupmap.one' not in u: known_urls.append(u.split('?')[0].rstrip('/').lower())
    def known(co, u):
        if norm_co(co) in known_names: return True
        ul = (u or '').lower()
        return any(ul.startswith(k + '/') or ul == k for k in known_urls)
    by_name = {norm_co(d.get('name')): i for i, d in st.items() if not d.get('active')}   # deaktivierte → Reaktivierungs-Kandidat
    cand = {}
    def run(kv):
        k, s = kv
        try: return k, BOARD_ADAPTERS[s['adapter']](s.get('url')), ''
        except Exception as e: return k, None, str(e)[:120] or type(e).__name__
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(run, srcs.items()))
    results, hits, seen = {}, [], set()
    for k, jobs, err in res:
        name = srcs[k].get('name') or k
        if jobs is None:
            old = [h for h in prev.get('hits') or [] if h.get('src') == name]
            results[k] = {'s': 'err', 'n': None, 'e': err, 'h': len(old), 'dup': 0, 'at': now}; hits += old; continue
        h, dup = [], 0
        for t, l, u, co, *rest in jobs:
            hint, pd = (rest + ['', ''])[:2]
            t, l, co = clean(t)[:160], clean(l)[:80], clean(co)[:80]
            if not board_want(t, l): continue
            key = (norm_co(co), t.lower())
            if key in seen: continue
            seen.add(key)
            if known(co, u): dup += 1; continue
            i = 'board:' + slug(co)
            h.append({'id': i, 't': t, 'l': l, 'u': str(u or '')[:300], 'co': co, 'src': name, 'fs': fs_of.get((i, t.lower())) or now})
            if pd: h[-1]['pd'] = pd
            if srcs[k].get('adapter') != 'arbeitnow':   # Arbeitnow: viele Nicht-Startups → keine Kandidaten
                b, kind = board_of(hint or u)
                if b:
                    c = cand.setdefault(slug(co), {'name': co, 'board': b, 'ats': kind, 'src': [], 'titles': [], 'n': 0})
                    c['n'] += 1
                    if name not in c['src']: c['src'].append(name)
                    if len(c['titles']) < 3: c['titles'].append(t)
        results[k] = {'s': 'ok', 'n': len(jobs), 'e': '', 'h': len(h), 'dup': dup, 'at': now}
        hits += h
    sz = lambda o: len(json.dumps(o, ensure_ascii=False, separators=(',', ':')).encode())
    hits = hits[:1500]
    while hits and sz({'r': results, 'h': hits}) > 235000: hits = hits[:int(len(hits) * 0.9)]
    meta = json.load(open(f'{D}/meta.json'))
    out = {'run_id': meta['run_id'], 'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
           'hits_total': len(hits), 'new_hits': sum(1 for x in hits if x['fs'] == now), 'results': results, 'hits': hits}
    json.dump(out, open(f'{D}/boards.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    print('Jobbörsen:', json.dumps({k: (v['s'], v['h']) for k, v in results.items()}, ensure_ascii=False), '· Treffer', out['hits_total'], '· neu', out['new_hits'])
    write_candidates(cand, by_name, now)
    return out

def write_candidates(cand, by_name, now):
    # Firmen aus Jobbörsen mit lesbarem Board als Vorschlag für die Collection startups ($D/candidates.json → scans/candidates).
    # Entscheidung (status) setzt der Nutzer im Artefakt; sie bleibt über Läufe erhalten: neu | übernehmen | abgelehnt | übernommen
    pf = f'{D}/in/scans/candidates.json'
    prev = json.load(open(pf)) if os.path.exists(pf) else {}
    if isinstance(prev.get('data'), dict): prev = prev['data']
    old = prev.get('candidates') or {}
    out = {}
    for k, c in cand.items():
        o = old.get(k) or {}
        c.update(fs=o.get('fs') or now, ls=now, status=o.get('status') or 'neu')
        if by_name.get(norm_co(c['name'])): c['in_startups'] = by_name[norm_co(c['name'])]
        out[k] = c
    for k, o in old.items():   # nicht mehr gesehene behalten, wenn schon entschieden oder jünger als 30 Tage
        if k not in out and (o.get('status') not in (None, 'neu') or o.get('ls', '') >= (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)).isoformat()):
            out[k] = o
    doc = {'updated_at': now, 'count': len(out), 'candidates': out}
    json.dump(doc, open(f'{D}/candidates.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    print('Kandidaten:', len(out), '· neu in diesem Lauf', sum(1 for c in out.values() if c.get('fs') == now))

# ================================================================ Startdatum / Online seit für die Bewerberliste (Collection applications → $D/details.json)
# Nur lesend: lädt die Seite jeder Bewerbung, sucht per Wortmuster (DE/EN/FR) nach dem Startdatum; unklar → leer.
_MON = (r'jan(?:uar|uary|vier)?|feb(?:ruar|ruary|rier)?|f[ée]v(?:rier)?|m[äa]rz|mar(?:ch|s)?|apr(?:il)?|avr(?:il)?|mai|may|juin|jui?n[ie]?|june?|juil(?:let)?|july?|aug(?:ust)?|ao[ûu]t'
        r'|sep(?:t(?:ember|embre)?)?|o[ck]t(?:ober|obre)?|nov(?:ember|embre)?|de[zc](?:ember)?|d[ée]c(?:embre)?')
_SEAS = r'(?:spring|summer|fall|autumn|winter|frühjahr|frühling|sommer|herbst|printemps|été|automne|hiver)'
_DATE = (rf'(?:\d{{1,2}}\.\s?\d{{1,2}}\.(?:\s?(?:20)?\d{{2}})?'                                  # 01.03.2027 / 01.03.
         rf'|\d{{1,2}}(?:\.|st|nd|rd|th|er)?\s+(?:of\s+)?(?:{_MON})\.?(?:\s*,?\s*20\d{{2}})?'          # 1. März 2027
         rf'|(?:(?:early|mid|late|beginning of|end of|anfang|mitte|ende|début|fin|mi)[\s-]+)?(?:{_MON})\.?(?:\s+(?:or|oder|ou|/|-|–)\s+(?:{_MON}))?(?:\s*,?\s*20\d{{2}})?'
         rf'|(?:0?[1-9]|1[0-2])/20\d{{2}}|q[1-4]\s*/?\s*20\d{{2}}|20\d{{2}}-\d{{2}}-\d{{2}}'
         rf'|{_SEAS}\s+20\d{{2}}|(?:wintersemester|sommersemester|ws|ss)\s*20?\d{{2}}(?:/\d{{2}})?)')
_ASAP = r'(?:ab\s+sofort|sofort|(?:zum\s+)?n[äa]chstm[öo]glich(?:en\s+zeitpunkt)?|asap|as\s+soon\s+as\s+possible|immediately|d[èe]s\s+que\s+possible|imm[ée]diat(?:ement)?|flexib(?:el|le))'
_LEAD = (r'(?:start(?:ing)?(?:\s*date|\s*datum|termin|zeitpunkt)?|date\s+de\s+d[ée]but|eintritt(?:stermin|sdatum)?|beginn|einstieg|'
         r'verf[üu]gbare\s+slots?|(?:next\s+)?available\s+slots?|slots?|verf[üu]gbar(?:keit)?|availability|available|d[ée]but|[àa]\s+partir\s+d[eu]|d[èe]s|ab|from|as\s+of|commencing)')
SD_RE = re.compile(rf'(?<![\w-]){_LEAD}\b[\s:–\-,(]{{0,4}}(?:(?:the|on|in|im|am|le|en|du|from|ab|zum|des|de|earliest|\(earliest\)|frühestens|of|à|is|are|always|ist)[\s:]+){{0,3}}({_ASAP}|{_DATE})(?![\w])', re.I)

def page_text(b):
    t = b if isinstance(b, str) else b.decode('utf-8', 'replace')
    t = re.sub(r'(?is)<style.*?</style>', ' ', t)
    t = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), t).replace('\\n', ' ').replace('\\/', '/')
    t = html.unescape(re.sub(r'<[^>]+>', ' ', html.unescape(t)))
    return re.sub(r'\s+', ' ', t)

def start_of(text):
    for m in SD_RE.finditer(text):
        v = m.group(1).strip(' ,')
        if re.fullmatch(_ASAP, v, re.I): return 'ab sofort' if not re.match(r'flex', v, re.I) else 'flexibel'
        if v.lower() == 'may' and not re.search(r'(?i)\bmay\s+20\d\d', m.group(0)): continue   # englisches „may“ (Modalverb)
        return v[:40]
    return ''

def norm_url(u): return re.sub(r'/+$', '', re.sub(r'[?#].*$', '', str(u or '').lower()))

def details_main(now):
    apps = []
    for f in glob.glob(f'{D}/in/applications/*.json'):
        x = json.load(open(f))
        if isinstance(x, dict) and isinstance(x.get('data'), dict): x = x['data']
        if isinstance(x, dict) and str(x.get('url') or '').startswith('http'): apps.append(x)
    pf = f'{D}/in/scans/details.json'
    prev = json.load(open(pf)) if os.path.exists(pf) else {}
    if isinstance(prev.get('data'), dict): prev = prev['data']
    old = prev.get('by_url') or {}
    pd_of = {}
    for fn in ('latest.json', 'boards.json'):   # Online-seit aus den Treffern dieses Laufs
        if os.path.exists(f'{D}/{fn}'):
            for h in json.load(open(f'{D}/{fn}')).get('hits') or []:
                if h.get('pd'): pd_of[norm_url(h.get('u'))] = h['pd']
    fresh = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14)).isoformat()
    def one(a):
        k = norm_url(a['url']); o = dict(old.get(k) or {})
        if not (o.get('sd') and o.get('at', '') >= fresh):   # gefundenes Startdatum 14 Tage lang nicht neu laden
            try:
                b = get(a['url'])[1]
                raw = b if isinstance(b, str) else b.decode('utf-8', 'replace')
                o['sd'] = start_of(str(a.get('title') or '') + ' . ' + page_text(raw))
                if m := re.search(r'"datePosted"\s*:\s*"([^"]+)"', raw): o['pd'] = pdate(m.group(1))
                o['at'] = now
            except Exception:
                pass   # Seite nicht lesbar → letzten Stand behalten
        if pd_of.get(k): o['pd'] = pd_of[k]
        return k, {x: o[x] for x in ('sd', 'pd', 'at') if o.get(x)}
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        by = {k: v for k, v in ex.map(one, apps) if v}
    doc = {'updated_at': now, 'count': len(by), 'by_url': by}
    json.dump(doc, open(f'{D}/details.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    r = {'n': len(apps), 'sd': sum(1 for v in by.values() if v.get('sd')), 'pd': sum(1 for v in by.values() if v.get('pd'))}
    print('Bewerberliste:', r['n'], 'Links · Startdatum gefunden', r['sd'], '· Online seit', r['pd'])
    return r

if __name__ == '__main__':
    import sys
    cmds = {'init': cmd_init, 'daten': cmd_daten, 'startups': cmd_startups, 'boards': cmd_boards, 'details': cmd_details, 'fertig': cmd_fertig, 'alles': main}
    cmds[sys.argv[1] if len(sys.argv) > 1 else 'alles']()
