#!/usr/bin/env python3
# Einmalig: für Firmen, die nur über ihr startupmap-Profil laufen, die echte Karriereseite / das ATS finden.
# Eingabe: $RADAR_DIR/in/startups/*.json   Ausgabe: $RADAR_DIR/discovery.json  {id: {...}}
import json, os, re, glob, sys, urllib.parse
import concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan

D = os.environ.get('RADAR_DIR', '/tmp/radar')
SOCIAL = re.compile(r'linkedin\.|twitter\.|x\.com|facebook\.|instagram\.|youtube\.|crunchbase\.|startupmap\.one|tiktok\.|xing\.|github\.com|medium\.com|apple\.com|google\.|wellfound|angel\.co|glassdoor|kununu|dealroom', re.I)
ATS = [
    ('personio', re.compile(r'https?://([a-z0-9-]+)\.jobs\.personio\.(de|com)', re.I), lambda m: f'https://{m.group(1).lower()}.jobs.personio.{m.group(2).lower()}/'),
    ('ashby', re.compile(r'jobs\.ashbyhq\.com/([A-Za-z0-9%._-]+)', re.I), lambda m: f'https://jobs.ashbyhq.com/{m.group(1)}'),
    ('greenhouse', re.compile(r'(?:job-boards|boards)(\.eu)?\.greenhouse\.io/(?:embed/job_board(?:/js)?\?for=)?([A-Za-z0-9_-]+)', re.I), lambda m: f'https://job-boards{m.group(1) or ""}.greenhouse.io/{m.group(2)}'),
    ('lever', re.compile(r'jobs(\.eu)?\.lever\.co/([A-Za-z0-9_-]+)', re.I), lambda m: f'https://jobs{m.group(1) or ""}.lever.co/{m.group(2)}'),
    ('join', re.compile(r'join\.com/companies/([A-Za-z0-9_-]+)', re.I), lambda m: f'https://join.com/companies/{m.group(1)}'),
    ('workable', re.compile(r'apply\.workable\.com/([A-Za-z0-9_-]+)', re.I), lambda m: f'https://apply.workable.com/{m.group(1)}/'),
    ('recruitee', re.compile(r'https?://([a-z0-9-]+)\.recruitee\.com', re.I), lambda m: f'https://{m.group(1).lower()}.recruitee.com/'),
    ('teamtailor', re.compile(r'https?://([a-z0-9-]+)\.teamtailor\.com', re.I), lambda m: f'https://{m.group(1).lower()}.teamtailor.com/jobs'),
    ('smartrecruiters', re.compile(r'(?:careers|jobs)\.smartrecruiters\.com/([A-Za-z0-9_-]+)', re.I), lambda m: f'https://careers.smartrecruiters.com/{m.group(1)}'),
]
BAD_SLUG = {'api', 'embed', 'widget', 'js', 'static', 'assets', 'jobs', 'www', 'companies', 'v1', 'apply', 'j'}
CAREER_HINT = re.compile(r'career|karriere|jobs?\b|join[- ]?us|work[- ]?with[- ]?us|we.?re[- ]?hiring|stellen|open[- ]?positions', re.I)

def find_ats(text):
    found = []
    for kind, rx, mk in ATS:
        for m in rx.finditer(text):
            slug = m.group(m.lastindex) if kind not in ('personio', 'recruitee', 'teamtailor', 'greenhouse', 'lever') else None
            url = mk(m)
            last = url.rstrip('/').split('/')[-1].split('.')[0]
            if (slug or last).lower() in BAD_SLUG: continue
            if (kind, url) not in found: found.append((kind, url))
    return found

def website_of(sm_url):
    base, txt = scan.get(sm_url)
    ext = [u for u, t in scan.links(base, txt) if u.startswith('http') and not SOCIAL.search(urllib.parse.urlsplit(u).netloc)]
    # bevorzugt Links mit Text wie "Website"/Domain, sonst der erste externe Link
    return (ext[0] if ext else None), txt

# ---------------------------------------------------------------- Fallback ohne startupmap (Cloudflare blockt Cloud-IPs)
LEGAL = re.compile(r'\b(gmbh|ag|se|inc|ltd|co|kg|ug|bv|sas|group|holding|technologies|technology|the)\b', re.I)
def norm(s): return re.sub(r'[^a-z0-9]', '', LEGAL.sub(' ', str(s or '').lower().replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')))
def ident(txt):
    # Selbstbezeichnung einer Seite: <title>, og:site_name, JSON "name"
    out = re.findall(r'<title[^>]*>([^<]{1,200})', txt, re.I)[:1]
    out += re.findall(r'og:site_name["\'][^>]*content=["\']([^"\']{1,100})', txt, re.I)[:1]
    out += re.findall(r'"name"\s*:\s*"([^"]{1,100})"', txt[:3000])[:1]
    return ' | '.join(scan.clean(x) for x in out)
def same_company(name, txt):
    n, i = norm(name), norm(ident(txt))
    return len(n) >= 3 and n in i
def slugs(sid, d):
    sm = urllib.parse.urlsplit(d.get('sm_url') or '').path.rstrip('/').split('/')[-1]
    sm_base = re.sub(r'_(de|com|io|ai|eu|tech|app|co)$', '', sm)
    words = [w for w in re.split(r'[^a-z0-9]+', LEGAL.sub(' ', str(d.get('name') or '').lower())) if w]
    out = []
    for c in (''.join(words), '-'.join(words), sm_base.replace('_', ''), sm_base.replace('_', '-'), sid):
        if c and len(c) >= 2 and c not in out: out.append(c)
    return out[:4], (re.search(r'_(de|com|io|ai|eu|tech|app|co)$', sm) or [None, None])[1]
def guess_site(sid, d):
    cands, tld_hint = slugs(sid, d)
    tlds = ['com', 'de', 'ai', 'io', 'tech', 'eu']
    if tld_hint: tlds = [tld_hint] + [t for t in tlds if t != tld_hint]
    tries = 0
    for c in cands[:2]:
        for t in tlds:
            if tries >= 10: return None, None
            tries += 1
            try: base, txt = scan.get(f'https://{c}.{t}', timeout=10)
            except Exception: continue
            if same_company(d.get('name'), txt) and not find_parked(txt): return base, txt
    return None, None
def find_parked(txt): return bool(re.search(r'domain (is )?for sale|domain kaufen|parked|sedo|this domain', txt[:20000], re.I))
def probe_ats(sid, d):
    # direkt bei den ATS nach dem Firmennamen fragen; nur übernehmen, wenn die Board-Seite den Firmennamen trägt
    cands, _ = slugs(sid, d)
    name = d.get('name')
    checks = [
        ('ashby',      lambda c: f'https://jobs.ashbyhq.com/{c}', None),
        ('greenhouse', lambda c: f'https://boards-api.greenhouse.io/v1/boards/{c}', lambda c: f'https://job-boards.greenhouse.io/{c}'),
        ('lever',      lambda c: f'https://jobs.lever.co/{c}', None),
        ('personio',   lambda c: f'https://{c}.jobs.personio.de/', None),
        ('personio',   lambda c: f'https://{c}.jobs.personio.com/', None),
        ('recruitee',  lambda c: f'https://{c}.recruitee.com/', None),
        ('teamtailor', lambda c: f'https://{c}.teamtailor.com/jobs', None),
        ('join',       lambda c: f'https://join.com/companies/{c}', None),
    ]
    for kind, mk, board in checks:
        for c in cands[:3]:
            u = mk(c)
            try: base, txt = scan.get(u, timeout=12)
            except Exception: continue
            if urllib.parse.urlsplit(base).netloc != urllib.parse.urlsplit(u).netloc: continue   # Umleitung = kein Board
            if kind == 'ashby' and '"organization":null' in txt.replace(' ', ''): continue
            if same_company(name, txt): return kind, (board(c) if board else u)
    return None

def discover(sid, d):
    out = {'id': sid}
    try:
        site, smtxt = website_of(d['sm_url'])
    except Exception as e:
        out['sm_err'] = str(e)[:80]
        site, smtxt = guess_site(sid, d)
        out['site_via'] = 'geraten' if site else ''
    cands = find_ats(smtxt or '')
    out['site'] = site
    pages = []
    if site:
        root = '{0.scheme}://{0.netloc}'.format(urllib.parse.urlsplit(site))
        try:
            base, txt = scan.get(root)
            pages.append((base, txt)); cands += find_ats(txt)
            for u, t in scan.links(base, txt):
                if (CAREER_HINT.search(t) or CAREER_HINT.search(urllib.parse.urlsplit(u).path)) and u not in [p[0] for p in pages] and len(pages) < 4:
                    if urllib.parse.urlsplit(u).netloc.endswith(urllib.parse.urlsplit(root).netloc.replace('www.', '')) or find_ats(u):
                        try:
                            b2, t2 = scan.get(u); pages.append((b2, t2)); cands += find_ats(b2 + ' ' + t2)
                            if not out.get('career'): out['career'] = b2
                        except Exception: pass
        except Exception as e:
            out['site_err'] = str(e)[:80]
    seen = []
    for c in cands:
        if c not in seen: seen.append(c)
    # verifizieren: erstes ATS, dessen API eine Stellenliste liefert
    if not seen or out.get('sm_err'):
        p = probe_ats(sid, d)
        if p and p not in seen: seen.append(p); out['ats_via'] = 'slug'
    for kind, url in seen[:5]:
        fn, args = scan.route(url)
        try:
            jobs, n = fn(*args)
            out.update(ats=kind, board=url, n=n if n is not None else len(jobs)); break
        except Exception as e:
            out.setdefault('ats_fail', []).append(f'{kind}: {str(e)[:40]}')
    return out

def main():
    st = {}
    for f in glob.glob(f'{D}/in/startups/*.json'):
        x = json.load(open(f)); st[os.path.basename(f)[:-5]] = x
    todo = {i: d for i, d in st.items() if d.get('sm_url') and str(d.get('source_url', '')).startswith('https://startupmap.one') and d.get('active')}
    only = set(sys.argv[1:])
    if only: todo = {i: d for i, d in todo.items() if i in only}
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        res = list(ex.map(lambda kv: discover(*kv), todo.items()))
    json.dump({r['id']: r for r in res}, open(f'{D}/discovery.json', 'w'), ensure_ascii=False, indent=0)
    n_ats = sum(1 for r in res if r.get('ats')); n_car = sum(1 for r in res if not r.get('ats') and r.get('career'))
    print(f'geprüft {len(res)} · ATS gefunden {n_ats} · nur Karriereseite {n_car} · nichts {len(res) - n_ats - n_car}')

if __name__ == '__main__':
    main()
