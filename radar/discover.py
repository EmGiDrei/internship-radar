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

def discover(sid, d):
    out = {'id': sid}
    try:
        site, smtxt = website_of(d['sm_url'])
    except Exception as e:
        out['err'] = 'startupmap: ' + str(e)[:80]; return out
    cands = find_ats(smtxt)
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
