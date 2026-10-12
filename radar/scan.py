#!/usr/bin/env python3
# Praktikums-Radar – Scan ohne KI: liest Stellenlisten direkt (ATS-APIs/HTML) und filtert per Wortliste.
# Eingabe:  $RADAR_DIR/in/startups/*.json, $RADAR_DIR/in/scans/latest.json (optional), $RADAR_DIR/meta.json
# Ausgabe:  $RADAR_DIR/latest.json, $RADAR_DIR/run.json, Zusammenfassung auf stdout
import json, os, re, glob, html, datetime, threading, time, urllib.request, urllib.error, urllib.parse
import concurrent.futures as cf
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

D = os.environ.get('RADAR_DIR', '/tmp/radar')
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
TYP = re.compile(r"\bintern(s|ship|ships)?\b|praktik|werkstud|working student|studentische|student assistant|\bhiwi\b|praxissemester|thesis|abschlussarbeit|masterarbeit|bachelorarbeit", re.I)
TRACK = re.compile(r"founder|founding associate|founding generalist|gründer|chief of staff|entrepreneur|\beir\b|ceo office|office of the ceo|ceo's office|cfo office|coo office|assistant to the ceo|ceo assistant|assistenz der geschäftsführung|venture develop|venture build|venture architect|venture associate|venture analyst|venture capital|company build|business builder", re.I)
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
        jobs = [(p.findtext('name') or '', p.findtext('office') or '', f'https://{org}.jobs.personio.{t}/job/{p.findtext("id")}') for p in root.iter('position')]
        return jobs, len(jobs)
    raise last or HttpErr('Personio nicht gefunden')
def a_ashby(org):
    d = getjson(f'https://api.ashbyhq.com/posting-api/job-board/{org}')
    jobs = [(j.get('title'), j.get('location') or '', j.get('jobUrl') or f'https://jobs.ashbyhq.com/{org}') for j in d.get('jobs', []) if j.get('isListed', True)]
    return jobs, len(jobs)
def a_greenhouse(org, eu):
    hosts = ['boards-api.eu.greenhouse.io', 'boards-api.greenhouse.io'] if eu else ['boards-api.greenhouse.io', 'boards-api.eu.greenhouse.io']
    last = None
    for h in hosts:
        try: d = getjson(f'https://{h}/v1/boards/{org}/jobs')
        except HttpErr as e: last = e; continue
        jobs = [(j.get('title'), (j.get('location') or {}).get('name', ''), j.get('absolute_url')) for j in d.get('jobs', [])]
        return jobs, len(jobs)
    raise last
def a_lever(org, eu):
    hosts = ['api.eu.lever.co', 'api.lever.co'] if eu else ['api.lever.co', 'api.eu.lever.co']
    last = None
    for h in hosts:
        try: d = getjson(f'https://{h}/v0/postings/{org}?mode=json')
        except HttpErr as e: last = e; continue
        if isinstance(d, dict) and not d.get('ok', True): last = HttpErr('Lever: ' + str(d.get('error', ''))[:60]); continue
        jobs = [(j.get('text'), (j.get('categories') or {}).get('location', ''), j.get('hostedUrl')) for j in d]
        return jobs, len(jobs)
    raise last
def a_workable(org):
    d = getjson(f'https://apply.workable.com/api/v1/widget/accounts/{org}')
    jobs = [(j.get('title'), ', '.join(x for x in (j.get('city'), j.get('country')) if x), j.get('url') or f'https://apply.workable.com/{org}/j/{j.get("shortcode")}') for j in d.get('jobs', [])]
    return jobs, len(jobs)
def a_recruitee(org):
    d = getjson(f'https://{org}.recruitee.com/api/offers/')
    jobs = [(j.get('title'), j.get('location') or j.get('city') or '', j.get('careers_url') or f'https://{org}.recruitee.com/o/{j.get("slug")}') for j in d.get('offers', [])]
    return jobs, len(jobs)
def a_smartrecruiters(org):
    jobs, off, total = [], 0, None
    while True:
        d = getjson(f'https://api.smartrecruiters.com/v1/companies/{org}/postings?limit=100&offset={off}')
        total = d.get('totalFound', 0)
        for j in d.get('content', []):
            loc = j.get('location') or {}
            jobs.append((j.get('name'), loc.get('city') or loc.get('country') or '', f'https://jobs.smartrecruiters.com/{org}/{j.get("id")}'))
        off += 100
        if off >= total or not d.get('content'): break
    return jobs, total
def a_join(org):
    base, txt = get(f'https://join.com/companies/{org}')
    jobs = []
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', txt, re.S)
    if m:
        def walk(x):
            if isinstance(x, dict):
                t = x.get('title'); jid = x.get('idParam') or x.get('id')
                if isinstance(t, str) and jid and ('employmentType' in x or 'idParam' in x or 'workplaceType' in x):
                    city = ''
                    c = x.get('city')
                    if isinstance(c, dict): city = c.get('cityName') or c.get('name') or ''
                    elif isinstance(c, str): city = c
                    slug = x.get('idParam') or jid
                    jobs.append((t, city, f'https://join.com/companies/{org}/{slug}'))
                for v in x.values(): walk(v)
            elif isinstance(x, list):
                for v in x: walk(v)
        try: walk(json.loads(m.group(1)))
        except Exception: pass
    if not jobs:
        jobs = [(t, '', u) for u, t in links(base, txt) if f'/companies/{org}/' in u and t]
    seen, out = set(), []
    for j in jobs:
        if j[2] not in seen: seen.add(j[2]); out.append(j)
    return out, len(out)
def a_teamtailor(host):
    base, txt = get(f'https://{host}/jobs')
    jobs = [(t, '', u) for u, t in links(base, txt) if re.search(r'/jobs/\d+', u) and t]
    seen, out = set(), []
    for j in jobs:
        if j[2] not in seen: seen.add(j[2]); out.append(j)
    return out, len(out)
def a_web(url):
    # Generisch: alle Links, deren Text nach Stelle aussieht (Titel-Filter kommt später)
    base, txt = get(url)
    jobs, seen = [], set()
    for u, t in links(base, txt):
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

def main():
    t0 = time.time()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    meta = json.load(open(f'{D}/meta.json'))
    st = {}
    for f in glob.glob(f'{D}/in/startups/*.json'):
        x = json.load(open(f))
        if isinstance(x, dict) and isinstance(x.get('data'), dict) and ('version' in x or 'id' in x): x = x['data']
        st[os.path.basename(f)[:-5]] = x
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
        for t, l, u in r['jobs']:
            t = clean(t)[:160]
            if not want(t) or t.lower() in seen: continue
            seen.add(t.lower())
            h.append({'id': i, 't': t, 'l': clean(l)[:80], 'u': str(u or '')[:300], 'fs': fs_of.get((i, t.lower())) or now})
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

if __name__ == '__main__':
    main()
