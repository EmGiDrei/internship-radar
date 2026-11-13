#!/usr/bin/env python3
"""Generate demo/data.json: fictional sample data in the shape of the real artifact database.

All companies, people and job postings are invented. Timestamps are relative to BASE; the demo runtime shifts
them by whole days at load time so the data always looks current.
"""
import json, random, re, datetime as dt, pathlib

random.seed(7)
OUT = pathlib.Path(__file__).with_name('data.json')
BASE = dt.datetime(2026, 11, 13, 0, 0, tzinfo=dt.timezone.utc)
RUN_HOUR = 5.9166  # 06:55 CET = 05:55 UTC

def iso(d): return d.astimezone(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
def run_time(days_ago, minutes=0): return BASE - dt.timedelta(days=days_ago) + dt.timedelta(hours=RUN_HOUR, minutes=minutes)
def slug(s): return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
def norm(u): return re.sub(r'/+$', '', re.sub(r'[?#].*$', '', u.lower()))

# ---------------------------------------------------------------- fictional startups
CO = [  # name, city, stage, sector, ats
    ('Voltwerk', 'Berlin', 'Series A', 'Energy software for installers', 'ashby'),
    ('Kranich Robotics', 'Munich', 'Seed', 'Warehouse robotics', 'personio'),
    ('Ledgerly', 'Berlin', 'Series B', 'AI accounts payable for mid-market', 'greenhouse'),
    ('Nordlicht Energy', 'Hamburg', 'Seed', 'Battery storage for apartment buildings', 'personio'),
    ('Fabrikant AI', 'Munich', 'Series A', 'AI copilots for manufacturing procurement', 'ashby'),
    ('Quellwerk', 'Berlin', 'Pre-Seed', 'Water analytics for utilities', 'join'),
    ('Baustein Labs', 'Berlin', 'Seed', 'Construction tendering software', 'ashby'),
    ('Pulsar Health', 'Berlin', 'Series A', 'Clinic operations platform', 'greenhouse'),
    ('Lumen Logistics', 'Hamburg', 'Series A', 'Freight booking for SMEs', 'lever'),
    ('Mosaik Finance', 'Frankfurt', 'Seed', 'Embedded lending API', 'workable'),
    ('Talwind Mobility', 'Munich', 'Series B', 'EV fleet charging', 'smartrecruiters'),
    ('Kompass Legal', 'Berlin', 'Seed', 'Contract AI for in-house teams', 'recruitee'),
    ('Heliograph', 'Cologne', 'Pre-Seed', 'Solar asset monitoring', 'join'),
    ('Ostwind Capital', 'Berlin', 'Fund', 'Early-stage climate VC', 'personio'),
    ('Sprungbrett', 'Berlin', 'Seed', 'Upskilling platform for trades', 'teamtailor'),
    ('Cargoflux', 'Hamburg', 'Seed', 'Port logistics data', 'ashby'),
    ('Mikrokosmos Bio', 'Munich', 'Seed', 'Microbial fertilizers', 'personio'),
    ('Ankerpunkt', 'Berlin', 'Series A', 'HR operations for blue-collar teams', 'ashby'),
    ('Polaris Payments', 'Berlin', 'Series A', 'Payment orchestration', 'greenhouse'),
    ('Werkbank OS', 'Stuttgart', 'Seed', 'Shopfloor software for SMEs', 'join'),
    ('Isarflow', 'Munich', 'Seed', 'Data pipelines for insurers', 'lever'),
    ('Grünraum', 'Berlin', 'Pre-Seed', 'Heat pump financing', 'join'),
    ('Atlas Analytics', 'Berlin', 'Series B', 'Revenue intelligence', 'greenhouse'),
    ('Sonnenfeld', 'Leipzig', 'Seed', 'Agri-PV project development', 'personio'),
    ('Tessera Security', 'Munich', 'Series A', 'Identity security for SaaS', 'ashby'),
    ('Elbe Dynamics', 'Hamburg', 'Seed', 'Drone inspections', 'recruitee'),
    ('Kaskade', 'Berlin', 'Seed', 'Workflow automation for agencies', 'workable'),
    ('Fernweh Travel', 'Berlin', 'Series A', 'B2B travel booking', 'smartrecruiters'),
    ('Rheinmetrik', 'Düsseldorf', 'Seed', 'Building energy benchmarks', 'personio'),
    ('Novalis Learning', 'Berlin', 'Seed', 'AI tutoring', 'ashby'),
    ('Brückenkopf', 'Berlin', 'Venture Studio', 'Company builder', 'personio'),
    ('Seidenweg Commerce', 'Munich', 'Series A', 'Cross-border e-commerce ops', 'teamtailor'),
]
ATS_URL = {
    'ashby': lambda s: f'https://jobs.ashbyhq.com/{s}',
    'personio': lambda s: f'https://{s}.jobs.personio.de/',
    'greenhouse': lambda s: f'https://job-boards.greenhouse.io/{s}',
    'lever': lambda s: f'https://jobs.lever.co/{s}',
    'workable': lambda s: f'https://apply.workable.com/{s}/',
    'join': lambda s: f'https://join.com/companies/{s}',
    'smartrecruiters': lambda s: f'https://careers.smartrecruiters.com/{s}',
    'recruitee': lambda s: f'https://{s}.recruitee.com/',
    'teamtailor': lambda s: f'https://{s}.teamtailor.com/jobs',
}
def job_url(ats, s, n):
    return {'ashby': f'https://jobs.ashbyhq.com/{s}/{n:08x}-demo', 'personio': f'https://{s}.jobs.personio.de/job/{n}',
            'greenhouse': f'https://job-boards.greenhouse.io/{s}/jobs/{n}', 'lever': f'https://jobs.lever.co/{s}/{n:08x}-demo',
            'workable': f'https://apply.workable.com/{s}/j/{n:X}/', 'join': f'https://join.com/companies/{s}/{n}-demo',
            'smartrecruiters': f'https://jobs.smartrecruiters.com/{s}/{n}', 'recruitee': f'https://{s}.recruitee.com/o/demo-{n}',
            'teamtailor': f'https://{s}.teamtailor.com/jobs/{n}-demo'}[ats]

startups = {}
for name, city, stage, sector, ats in CO:
    s = slug(name).replace('-', '')
    startups[slug(name)] = {'name': name, 'stadt': city, 'typ': 'VC / Investor' if stage == 'Fund' else 'Venture Studio' if stage == 'Venture Studio' else 'Startup',
                            'stage': '' if stage in ('Fund', 'Venture Studio') else stage, 'liste': random.choice(['eigene', 'startupmap', 'startupmap', 'jobbörse']),
                            'active': True, 'ats': ats, 'source_url': ATS_URL[ats](s), 'career_url': ATS_URL[ats](s), 'sm_url': '', 'li_url': '',
                            'note': sector, 'added': iso(BASE - dt.timedelta(days=random.randint(20, 40)))}
for name in ('Morgenrot Media', 'Kiesel Apps', 'Tiefsee Data'):
    startups[slug(name)] = {'name': name, 'stadt': 'Berlin', 'typ': 'Startup', 'stage': 'Seed', 'liste': 'startupmap', 'active': False, 'ats': '',
                            'source_url': '', 'career_url': '', 'sm_url': '', 'li_url': '', 'note': 'keine Karriereseite gefunden', 'added': iso(BASE - dt.timedelta(days=30))}

# ---------------------------------------------------------------- job titles (some fit the profile, some are filtered out)
FIT = ["Founder's Associate Intern (m/f/d)", 'Founders Associate Praktikum (m/w/d)', 'Venture Development Intern', 'Chief of Staff Intern',
       'Intern Strategy & Operations', 'Praktikum Business Development (m/w/d)', "Founder's Office Intern – Growth", 'Entrepreneur in Residence Intern',
       'Werkstudent Strategy & BizOps (m/w/d)', 'Intern GTM Strategy & Automation', 'Praktikum Corporate Development / M&A', 'AI Automation Intern (Ops)']
NOFIT = ['Werkstudent Softwareentwicklung (m/w/d)', 'Marketing Intern – Social Media', 'Praktikum HR & Recruiting', 'Working Student Customer Support',
         'Praktikum Buchhaltung', 'Intern Frontend Engineering']
LOC = {'Berlin': 'Berlin', 'Munich': 'München', 'Hamburg': 'Hamburg', 'Frankfurt': 'Frankfurt am Main', 'Cologne': 'Köln', 'Stuttgart': 'Stuttgart',
       'Leipzig': 'Leipzig', 'Düsseldorf': 'Düsseldorf'}

latest_start, latest_end = run_time(0), run_time(0, 23)
hits, n = [], 4000
active = [k for k, v in startups.items() if v['active']]
for i, sid in enumerate(active):
    st = startups[sid]; s = st['source_url']
    titles = random.sample(FIT, random.choice([0, 1, 1, 2, 2, 3])) + random.sample(NOFIT, random.choice([0, 0, 1]))
    for t in titles:
        n += 37
        age = random.choice([0, 0, 1, 2, 3, 4, 6, 8, 11, 15, 19])
        fs = latest_end if age == 0 else run_time(age, 23)
        hits.append({'id': sid, 't': t, 'l': LOC[st['stadt']] + (', Hybrid' if random.random() < .3 else ''), 'u': job_url(st['ats'], slug(st['name']).replace('-', ''), n),
                     'fs': iso(fs), 'pd': (fs - dt.timedelta(days=random.randint(0, 9))).date().isoformat()})
errors = random.sample(active, 3)
results = {sid: {'s': 'ok', 'n': random.randint(3, 60), 'e': '', 'h': sum(1 for h in hits if h['id'] == sid), 'at': iso(latest_end)} for sid in active}
for sid, e in zip(errors, ['HTTP 404', 'TimeoutError: The read operation timed out', 'Hauptquelle fehlgeschlagen – über Ersatzquelle gelesen']):
    results[sid].update(s='err', e=e)
latest = {'run_id': latest_start.strftime('%Y%m%d-%H%M'), 'started_at': iso(latest_start), 'finished_at': iso(latest_end), 'mode': 'geplant', 'engine': 'skript',
          'checked': len(active), 'ok': len(active) - 3, 'errors': 3, 'hits_total': len(hits), 'new_hits': sum(1 for h in hits if h['fs'] == iso(latest_end)),
          'results': results, 'hits': hits}

# ---------------------------------------------------------------- external job boards + candidate companies
BOARD_SRC = ['Y Combinator Jobs', 'Getro · Climate VC Portfolio', 'Berlin Startup Jobs', 'Arbeitnow']
BCO = [('Fjord AI', 'yc'), ('Halde Recycling', 'getro'), ('Linde & Lumen', 'bsj'), ('Pixelhafen', 'bsj'), ('Wattbox', 'getro'), ('Gleis 9', 'yc'),
       ('Stellwerk HR', 'arbeitnow'), ('Kompost Kollektiv', 'getro'), ('Nebula Insure', 'yc'), ('Spreeweg Studio', 'bsj')]
bhits = []
for co, kind in BCO:
    src = {'yc': BOARD_SRC[0], 'getro': BOARD_SRC[1], 'bsj': BOARD_SRC[2], 'arbeitnow': BOARD_SRC[3]}[kind]
    for t in random.sample(FIT, random.choice([1, 1, 2])):
        n += 53; age = random.choice([0, 1, 3, 5, 9])
        u = {'yc': f'https://www.ycombinator.com/companies/{slug(co)}/jobs/{n:x}-demo', 'getro': f'https://jobs.ashbyhq.com/{slug(co).replace("-", "")}/{n:08x}-demo',
             'bsj': f'https://berlinstartupjobs.com/internships/{slug(t)}-{slug(co)}/', 'arbeitnow': f'https://www.arbeitnow.com/jobs/companies/{slug(co)}/{slug(t)}-{n}'}[kind]
        fs = latest_end if age == 0 else run_time(age, 23)
        bhits.append({'id': 'board:' + slug(co), 't': t, 'l': random.choice(['Berlin', 'München', 'Berlin / Remote Germany', 'Paris']), 'u': u, 'co': co, 'src': src,
                      'fs': iso(fs), 'pd': (fs - dt.timedelta(days=random.randint(0, 6))).date().isoformat()})
boards = {'run_id': latest['run_id'], 'finished_at': iso(latest_end), 'hits_total': len(bhits), 'new_hits': sum(1 for h in bhits if h['fs'] == iso(latest_end)),
          'results': {slug(s): {'s': 'ok', 'n': random.randint(80, 900), 'e': '', 'h': sum(1 for h in bhits if h['src'] == s), 'dup': random.randint(0, 12), 'at': iso(latest_end)} for s in BOARD_SRC},
          'hits': bhits}
cands = {}
for co, kind in BCO[:7]:
    if kind == 'arbeitnow': continue
    ts = [h['t'] for h in bhits if h['co'] == co]
    cands[slug(co)] = {'name': co, 'board': f'https://jobs.ashbyhq.com/{slug(co).replace("-", "")}', 'ats': 'ashby',
                       'src': [h['src'] for h in bhits if h['co'] == co][:1], 'titles': ts[:3], 'n': len(ts), 'fs': iso(run_time(random.randint(0, 6), 23)),
                       'ls': iso(latest_end), 'status': random.choice(['neu', 'neu', 'neu', 'abgelehnt'])}
candidates = {'updated_at': iso(latest_end), 'count': len(cands), 'candidates': cands}

# ---------------------------------------------------------------- applications (Bewerberliste)
APPS = [  # company, title, status, comment lines
    ('Voltwerk', "Founder's Associate Intern (m/f/d)", 'Gespräch', ['Mail: Eingangsbestätigung', 'Mail: Einladung Erstgespräch', 'Termin gebucht']),
    ('Fabrikant AI', 'Venture Development Intern', '2. Interview', ['Mail: Eingangsbestätigung', 'Mail: Einladung Erstgespräch', 'Mail: Einladung Hiring-Manager-Interview']),
    ('Nordlicht Energy', 'Founders Associate Praktikum (m/w/d)', 'Gespräch', ['Mail: Einladung Kennenlernen (Calendly)']),
    ('Ledgerly', 'Chief of Staff Intern', 'Beworben', ['Mail: Eingangsbestätigung']),
    ('Baustein Labs', 'Entrepreneur in Residence Intern', 'Beworben', ['Mail: Eingangsbestätigung']),
    ('Polaris Payments', 'Intern Strategy & Operations', 'Beworben', ['Mail: Eingangsbestätigung']),
    ('Atlas Analytics', "Founder's Office Intern – Growth", 'Absage', ['Mail: Eingangsbestätigung', 'Mail: Absage']),
    ('Pulsar Health', 'Intern Strategy & Operations', 'Absage', ['Mail: Absage']),
    ('Kranich Robotics', 'Praktikum Business Development (m/w/d)', 'Anschreiben nötig', []),
    ('Grünraum', "Founder's Associate Intern (m/f/d)", 'Unbedingt bewerben', []),
    ('Tessera Security', 'Intern GTM Strategy & Automation', 'Offen', []),
    ('Mosaik Finance', 'Praktikum Corporate Development / M&A', 'Offen', []),
    ('Lumen Logistics', 'Venture Development Intern', 'Offen', []),
    ('Kompass Legal', "Founder's Associate Intern (m/f/d)", 'Offen', []),
    ('Sonnenfeld', 'Founders Associate Praktikum (m/w/d)', 'Offen', []),
    ('Cargoflux', 'Chief of Staff Intern', 'Offen', []),
    ('Isarflow', 'AI Automation Intern (Ops)', 'Offen', []),
    ('Werkbank OS', 'Praktikum Business Development (m/w/d)', 'Offen', []),
    ('Ankerpunkt', "Founder's Office Intern – Growth", 'Offen', []),
    ('Novalis Learning', 'Intern Strategy & Operations', 'Offen', []),
    ('Fernweh Travel', 'Marketing Intern – Social Media', 'Nicht relevant', []),
    ('Fjord AI', "Founder's Associate Intern (m/f/d)", 'Offen', []),
    ('Wattbox', 'Venture Development Intern', 'Offen', []),
    ('Talwind Mobility', 'Werkstudent Strategy & BizOps (m/w/d)', 'Offen', []),
]
by_name = {v['name']: k for k, v in startups.items()}
apps, details = {}, {}
for i, (co, title, status, lines) in enumerate(APPS, 1):
    st = startups.get(by_name.get(co, ''), {})
    h = next((x for x in hits + bhits if (x.get('co') == co or x['id'] == by_name.get(co)) and x['t'] == title), None)
    url = h['u'] if h else job_url(st.get('ats', 'join'), slug(co).replace('-', ''), 9000 + i)
    added = BASE - dt.timedelta(days=random.randint(8, 24))
    d0 = added + dt.timedelta(days=1)
    comment = '\n'.join(f'{(d0 + dt.timedelta(days=2 * j)).strftime("%d.%m.")} {l}' for j, l in enumerate(lines))
    hist = {'Beworben': iso(d0)} if status in ('Beworben', 'Gespräch', '2. Interview', 'Absage') else {}
    if status in ('Gespräch', '2. Interview'): hist['Gespräch'] = iso(d0 + dt.timedelta(days=3))
    if status == '2. Interview': hist['2. Interview'] = iso(d0 + dt.timedelta(days=6))
    apps[f'demo-{i:02d}'] = {'nr': i, 'company': co, 'title': title, 'url': url, 'status': status, 'status_at': iso(d0 + dt.timedelta(days=2)),
                             'comment': comment, 'added': iso(added), 'source': 'radar' if h else 'manuell', 'hist': hist}
    sd = random.choice(['ab sofort', 'Januar 2027', '01.02.2027', 'Q1 2027', '', '', 'flexibel'])
    details[norm(url)] = {k: v for k, v in {'sd': sd, 'pd': (added - dt.timedelta(days=random.randint(2, 30))).date().isoformat(), 'chk': iso(latest_end)}.items() if v}
details[norm(apps['demo-13']['url'])]['off'] = iso(run_time(2, 20))                       # Lumen Logistics: posting went offline
details[norm(apps['demo-17']['url'])]['moved'] = apps['demo-17']['url'].rstrip('/') + '-v2'  # Isarflow: re-posted under a new id

# ---------------------------------------------------------------- AI ratings (fit / impact / startup strength → prio)
def prio(fit, imp, su):
    s = round(.45 * fit + .35 * imp + .2 * su)
    return s, 'D' if fit < 35 else 'A' if s >= 75 else 'B' if s >= 62 else 'C' if s >= 48 else 'D'
WHY = {
    "Founder's Associate": 'FA direkt mit den Gründern, Seed/Series A, Berlin – starker Fit',
    'Venture Development': 'Neue Produkte von 0 auf 1 bauen – passt zu Venture-Development-Erfahrung',
    'Chief of Staff': 'Rechte Hand der Geschäftsführung, viel Ownership',
    'Strategy & Operations': 'Strategie + Umsetzung, aber eher größeres Team',
    'Business Development': 'BD mit strategischem Anteil, teils Vertrieb',
    'Entrepreneur in Residence': 'EIR: neues Geschäftsfeld end-to-end aufbauen',
    'Werkstudent': 'Werkstudent – nur zweite Wahl laut Wünschen',
    'GTM': 'GTM + Automatisierung – Skills passen gut',
    'Corporate Development': 'M&A/Corporate Development – passt zu Strategy-Erfahrung',
    'AI Automation': 'Make/n8n-Automatisierungen und KI-Agenten – exakt das Profil',
    'Marketing': 'Reines Marketing – No-Go laut Profil',
    'Founders Associate': 'FA im Gründerteam, Energie-Domäne – sehr guter Fit',
    "Founder's Office": "Founder's Office mit Growth-Fokus",
}
ratings = {}
for h in hits + bhits + [{'u': a['url'], 't': a['title']} for a in apps.values()]:
    k = norm(h['u'])
    if k in ratings or (h['t'] in NOFIT and 'Marketing' not in h['t']): continue
    key = next((w for w in WHY if w.lower() in h['t'].lower()), None)
    if not key: continue
    base_fit = {'Marketing': 15, 'Werkstudent': 52}.get(key, random.randint(58, 90))
    fit, imp, su = base_fit, random.randint(55, 90), random.randint(45, 88)
    s, p = prio(fit, imp, su)
    ratings[k] = {'fit': fit, 'imp': imp, 'su': su, 's': s, 'p': p, 'why': WHY[key], 'at': iso(latest_end), 'pa': iso(BASE - dt.timedelta(days=12))}
ratings_doc = {'updated_at': iso(latest_end), 'profile_at': iso(BASE - dt.timedelta(days=12)), 'count': len(ratings), 'by_url': ratings}

# ---------------------------------------------------------------- interviews + one-pagers
def at(days, hh, mm):  # local CET time → UTC
    return iso(BASE + dt.timedelta(days=days, hours=hh - 1, minutes=mm))
interviews = {
    'voltwerk-erstgespraech': {'company': 'Voltwerk', 'title': "Founder's Associate Intern (m/f/d)", 'app_id': 'demo-01', 'kind': 'Erstgespräch (30 Min.)', 'status': 'gebucht',
        'start': at(1, 10, 0), 'dur_min': 30, 'with': 'Lena Brandt (Co-Founder & CEO)', 'booking_url': '', 'join_url': 'https://meet.google.com/demo-demo-demo', 'source': 'mail',
        'mail_at': at(-3, 9, 41),
        'onepager': {'tagline': 'Software für Solar- und Wärmepumpen-Installateure: Angebot, Planung und Montage in einem Tool.',
            'facts': [['Sitz', 'Berlin'], ['Gegründet', '2022'], ['Finanzierung', '€14 Mio. Series A (fiktiv)'], ['Investoren', 'Ostwind Capital, Business Angels (fiktiv)'],
                      ['Gründer', 'Lena Brandt (CEO), Jonas Weber (CTO)'], ['Traktion', '~900 Installationsbetriebe als Kunden (Demo-Daten)']],
            'sections': [{'h': 'Produkt', 'items': ['Angebots-Konfigurator mit Förder-Check', 'Montageplanung und Material-Disposition', 'KI-Assistent für Aufmaß aus Fotos']},
                         {'h': 'ICP – wer kauft', 'items': ['Installationsbetriebe mit 5–80 Mitarbeitenden in DACH', 'Käufer: Geschäftsführung bzw. Inhaber', 'Nutzer: Vertrieb, Planung, Monteure']},
                         {'h': 'Geschäftsmodell', 'items': ['SaaS pro Nutzer und Monat', 'Upsell: Finanzierungs- und Förder-Services', 'Land & Expand über Partner-Großhändler']},
                         {'h': 'Wettbewerb', 'items': ['Branchensoftware der Großhändler', 'Allgemeine Handwerkersoftware', 'Status quo: Excel + WhatsApp']},
                         {'h': 'Aktuell / worauf achten', 'items': ['Expansion nach Österreich angekündigt (fiktiv)', 'FA-Rolle: Pricing, Partnerschaften, Automatisierung']}],
            'questions': ['Welcher Kanal bringt heute die meisten Neukunden?', 'Wie wird Erfolg des Founder\'s Associate nach 3 Monaten gemessen?',
                          'Welche Prozesse wollt ihr als Nächstes automatisieren?', 'Wie sieht die Roadmap für Österreich aus?'],
            'pitch': ['Venture-Development-Erfahrung im Energiebereich (Markteintritt, Pricing)', 'Make.com/n8n-Automatisierungen und eigener KI-Agent'],
            'sources': [{'t': 'Demo – fiktive Daten', 'u': '#'}], 'at': iso(BASE - dt.timedelta(days=2))}},
    'fabrikant-ai-zweitgespraech': {'company': 'Fabrikant AI', 'title': 'Venture Development Intern', 'app_id': 'demo-02', 'kind': 'Hiring-Manager-Interview (45 Min.)',
        'status': 'gebucht', 'start': at(3, 16, 30), 'dur_min': 45, 'with': 'Tobias Krämer (Head of Venture Development)', 'booking_url': '', 'source': 'mail', 'mail_at': at(-1, 14, 5),
        'onepager': {'tagline': 'KI-Copiloten für den Einkauf mittelständischer Industrieunternehmen.',
            'facts': [['Sitz', 'München'], ['Gegründet', '2021'], ['Finanzierung', '€22 Mio. Series A (fiktiv)'], ['Gründer', 'Dr. Mira Albers, Felix Hartmann'],
                      ['Traktion', '120 Industriekunden (Demo-Daten)']],
            'sections': [{'h': 'Produkt', 'items': ['Spend-Analyse über alle Warengruppen', 'Automatisierte Preisanfragen', 'Lieferanten-Risikoscore']},
                         {'h': 'ICP – wer kauft', 'items': ['Industrie-Mittelstand mit 100–2.000 Mio. € Umsatz', 'Käufer: CPO / Einkaufsleitung']},
                         {'h': 'Wettbewerb', 'items': ['Große Procurement-Suiten', 'Spend-Analytics-Spezialisten', 'Status quo: ERP + Excel']}],
            'questions': ['Welche neuen Produktlinien entwickelt Venture Development gerade?', 'Wie läuft eine Validierung von der Idee bis zum Pilotkunden?'],
            'pitch': ['Corporate-Strategy-Erfahrung in der Industrie', 'Marktanalysen und Business Cases auf Vorstandsniveau'],
            'sources': [{'t': 'Demo – fiktive Daten', 'u': '#'}], 'at': iso(BASE - dt.timedelta(days=1))}},
    'nordlicht-energy-erstgespraech': {'company': 'Nordlicht Energy', 'title': 'Founders Associate Praktikum (m/w/d)', 'app_id': 'demo-03', 'kind': 'Kennenlernen (20 Min.)',
        'status': 'einladung', 'start': None, 'dur_min': 20, 'with': 'Paul Seidel', 'booking_url': 'https://calendly.com/', 'source': 'mail', 'mail_at': at(0, 8, 12)},
    'atlas-analytics-erstgespraech': {'company': 'Atlas Analytics', 'title': "Founder's Office Intern – Growth", 'app_id': 'demo-07', 'kind': 'Erstgespräch (30 Min.)',
        'status': 'gebucht', 'start': at(-6, 11, 0), 'dur_min': 30, 'with': 'Sara Okafor', 'source': 'mail', 'mail_at': at(-10, 10, 0)},
}

# ---------------------------------------------------------------- past runs (progress log as written by scanner/scan.py)
runs = {}
for d in range(0, 9):
    t0 = run_time(d); t1 = run_time(d, 23 - (d % 3))
    rid = t0.strftime('%Y%m%d-%H%M')
    log = [[iso(t0), 'ok', f'Lauf {rid} gestartet (geplant)'], [iso(t0), 'ok', f'Datenbank gelesen: {len(startups)} Startups ({len(active)} aktiv), 4 Jobbörsen, {len(apps)} Bewerbungen'],
           [iso(t0 + dt.timedelta(minutes=9)), 'ok', f'Startups: {len(active) - 3} ok, 3 Fehler · {len(hits)} Treffer, davon {random.randint(0, 5)} neu'],
           [iso(t0 + dt.timedelta(minutes=17)), 'ok', f'Jobbörsen: {len(bhits)} Treffer ({random.randint(0, 3)} neu) aus 4 Quellen · {len(cands)} Kandidaten'],
           [iso(t0 + dt.timedelta(minutes=20)), 'ok', f'Bewerberliste: {len(apps)} Links · Startdatum bei 14 · Online-Datum bei 19 · 1 offline'],
           [iso(t1), 'ok', f'KI-Bewertung: {random.randint(0, 6)} Stellen bewertet'], [iso(t1), 'ok', f'Fertig nach {23 - (d % 3)}:0{d % 6} min']]
    runs[rid] = {'run_id': rid, 'status': 'done', 'started_at': iso(t0), 'finished_at': iso(t1), 'mode': 'geplant', 'engine': 'skript', 'checked': len(active),
                 'ok': len(active) - 3, 'errors': 3, 'hits_total': len(hits), 'new_hits': random.randint(0, 5), 'seconds': (23 - d % 3) * 60, 'phase': 'fertig', 'pct': 100,
                 'log': log, 'dur': {'daten': 20, 'startups': 520, 'boards': 480, 'details': 160, 'bewerten': 120}}

# ---------------------------------------------------------------- hits that appear when "Jetzt scannen" is pressed in the demo
sim = []
for sid, t in (('voltwerk', 'AI Automation Intern (Ops)'), ('sonnenfeld', 'Venture Development Intern'), ('kaskade', "Founder's Associate Intern (m/f/d)")):
    st = startups[sid]; n += 101
    u = job_url(st['ats'], slug(st['name']).replace('-', ''), n)
    fit, imp, su = random.randint(70, 90), random.randint(65, 88), random.randint(55, 85); s, p = prio(fit, imp, su)
    sim.append({'id': sid, 't': t, 'l': LOC[st['stadt']], 'u': u, 'pd': BASE.date().isoformat(),
                'rating': {'fit': fit, 'imp': imp, 'su': su, 's': s, 'p': p, 'why': 'Neu im Demo-Lauf gefunden und direkt von der KI bewertet', 'pa': ratings_doc['profile_at']}})

store = {
    'startups': startups,
    'applications': apps,
    'interviews': interviews,
    'runs': runs,
    'trash': {'demo-trash': {'nr': 99, 'company': 'Kiesel Apps', 'title': 'Praktikum Product', 'status': 'Offen', 'url': '', 'deleted_at': iso(BASE - dt.timedelta(days=2))}},
    'scans': {'latest': latest, 'boards': boards, 'candidates': candidates, 'details': {'updated_at': iso(latest_end), 'count': len(details), 'by_url': details}, 'ratings': ratings_doc},
    'config': {'main': {'trigger_id': 'demo-trigger', 'schedule_text': 'täglich um 06:55', 'approved': []},
               'profile': {'cv': 'DEMO-PROFIL (fiktiv): M.Sc. Management, Erfahrung in Venture Development, Corporate Strategy und Beratung; '
                                 'Automatisierung mit Make.com, n8n, SQL und Python; eigene KI-Agenten. ' * 2,
                           'wishes': 'Founders Associate / Venture Development / Chief of Staff in Startups (Pre-Seed bis Series B), Berlin bevorzugt, Start Januar 2027.',
                           'updated_at': ratings_doc['profile_at']}},
    'prefs': {'hidden': {'by_url': {norm(hits[-1]['u']): True}}},
}
json.dump({'base': iso(BASE), 'store': store, 'simulated': sim}, OUT.open('w'), ensure_ascii=False, separators=(',', ':'))
print(f'{OUT.name}: {len(startups)} startups, {len(hits)} hits, {len(bhits)} board hits, {len(apps)} applications, {len(interviews)} interviews, {len(ratings)} ratings')
