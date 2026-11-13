# Relevance filter – ported 1:1 to the page (JS). Terms: plain substring (<=3 chars: whole word) or /regex/.
import re
DEFAULT = {
 "typ": ["/\\bintern(s|ship|ships)?\\b/", "praktik", "werkstud", "working student", "studentische", "student assistant", "/\\bhiwi\\b/", "praxissemester", "thesis", "abschlussarbeit", "masterarbeit", "bachelorarbeit"],
 "track": ["founder", "founding associate", "founding generalist", "gründer", "chief of staff", "entrepreneur", "eir", "ceo office", "office of the ceo", "ceo's office", "cfo office", "coo office", "cpo office", "cgo office", "assistant to the ceo", "ceo assistant", "assistenz der geschäftsführung", "assistenz geschäftsführung", "venture develop", "venture build", "venture architect", "venture associate", "venture analyst", "venture capital", "company build", "business builder"],
 "track_exclude": ["engineer", "co-founder", "technical founder"],
 "strong": ["consult", "strateg", "business development", "bizdev", "venture", "m&a", "investment", "gtm", "go-to-market", "automation", "automatisier", "product manage", "produktmanage", "chief of staff", "founder"],
 "topics": {
  "AI": ["ai", "ki", "artificial intelligence", "künstliche intelligenz", "genai", "generative", "llm", "agent", "agentic", "prompt"],
  "Automation": ["automation", "automatisier", "automate", "no-code", "nocode", "low-code", "workflow", "process automation", "process optimi", "process management", "process excellence", "business process", "prozessautomatisierung", "prozessoptimierung", "prozessmanagement", "digitalisierung", "digital transformation", "efficiency", "effizienz"],
  "Strategy": ["strateg", "consult", "beratung", "transformation", "special project", "sonderprojekt", "corporate development", "unternehmensentwicklung", "m&a", "innovation", "new business"],
  "BizDev & Growth": ["business development", "bizdev", "bd", "geschäftsentwicklung", "growth", "go-to-market", "go to market", "gtm", "expansion", "market entry", "markteintritt", "launch", "partner", "pricing", "revenue operations", "revops", "commercial", "sales operations", "market analysis", "marktanalyse", "market research", "marktforschung"],
  "Operations": ["operations", "operational", "ops", "bizops", "operativ", "project", "projekt", "program management", "programm", "pmo"],
  "Venture & Startup": ["venture", "investment", "investor", "private equity", "fundraising", "corporate finance", "accelerator", "ecosystem", "startup", "start-up", "gründung"],
  "Product": ["product", "produktmanagement", "produktmanager"],
  "Analytics": ["analyst", "analytics", "business intelligence", "bi", "data", "insights", "reporting", "kpi"],
  "Generalist": ["generalist", "allround", "rotation", "business", "general management", "start-up management", "startup management", "geschäftsführung", "ceo", "coo", "cpo", "cgo"]
 },
 "exclude": ["development representative", "office", "quality", "annotation", "labeling", "labelling", "data collection", "data science", "lab", "cleanroom", "r&d", "engineer", "developer", "entwickler", "software", "frontend", "backend", "fullstack", "full-stack", "full stack", "devops", "firmware", "embedded", "hardware", "mechanical", "mechani", "mechatron", "elektro", "electrical", "electronic", "chemi", "labor", "laboratory", "physik", "physics", "scientist", "researcher", "cad", "qa", "quality assurance", "security", "cyber", "design", "ux", "ui", "graphic", "grafik", "video", "social media", "content", "community", "influencer", "copywrit", "redakt", "recruit", "talent", "human resources", "hr", "people & culture", "people and culture", "people operations", "people ops", "personalwesen", "legal", "jurist", "recht", "tax", "steuer", "accounting", "buchhalt", "account manag", "account executive", "sdr", "sales development", "telesales", "inside sales", "customer support", "customer service", "customer care", "kundenservice", "logistik", "warehouse", "lager", "driver", "fahrer"],
 # words that may appear in a "generic" posting (e.g. "Open Internship Application", "Munich - Internship")
 "generic": ["open", "application", "applications", "initiativ", "initiativbewerbung", "unsolicited", "general", "spontaneous", "at", "for", "in", "the", "our", "and", "all", "genders", "team", "munich", "münchen", "berlin", "hamburg", "cologne", "köln", "frankfurt", "remote", "hybrid", "germany", "deutschland", "m", "w", "d", "f", "x", "gn", "div", "mwd", "fmd"]
}
def term_re(t):
    t=t.strip()
    if not t: return None
    if len(t)>2 and t.startswith('/') and t.endswith('/'): return t[1:-1]
    e=re.escape(t.lower())
    return r'\b'+e+r'\b' if len(t)<=3 else e
def compile_list(lst):
    parts=[p for p in (term_re(t) for t in lst) if p]
    return re.compile('|'.join(parts), re.I) if parts else None
def make(f=DEFAULT):
    return {k:compile_list(f[k]) for k in ('typ','track','track_exclude','strong','exclude')} | {
        'topics':{k:compile_list(v) for k,v in f['topics'].items()}, 'generic':set(f['generic'])}
def is_generic(t, C, company=''):
    s=C['typ'].sub(' ', t.lower())
    words=[w for w in re.split(r'[^a-zäöüß0-9]+', s) if w]
    co=set(w for w in re.split(r'[^a-zäöüß0-9]+', company.lower()) if w)
    rest=[w for w in words if w not in C['generic'] and w not in co]
    return bool(C['typ'].search(t)) and not rest
def classify(title, C, company=''):
    t=title.lower()
    track=bool(C['track'].search(t)) and not (C['track_exclude'] and C['track_exclude'].search(t))
    typ=bool(C['typ'].search(t))
    topics=[k for k,r in C['topics'].items() if r and r.search(t)]
    excl=bool(C['exclude'].search(t)); strong=bool(C['strong'].search(t))
    generic=is_generic(title, C, company)
    fit = track or generic or (typ and bool(topics) and (not excl or strong))
    return fit, track, typ, topics, excl, generic
