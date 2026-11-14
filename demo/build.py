#!/usr/bin/env python3
"""Build the public demo (docs/index.html, served by GitHub Pages) from the real app source.

app/index.html is the exact page that runs as the claude.ai artifact. The demo wraps it with
demo/mock-runtime.js (a stand-in for the artifact runtime) and demo/data.json (fictional sample data).
Run `python3 demo/make_data.py && python3 demo/build.py` after changing the app.
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
app = (ROOT / 'app' / 'index.html').read_text()
data = json.loads((ROOT / 'demo' / 'data.json').read_text())
mock = (ROOT / 'demo' / 'mock-runtime.js').read_text()

banner = """
<div id="demo-bar" role="note">
  <span><b>Live demo</b><i> · fictional companies and data</i></span>
  <a href="https://github.com/EmGiDrei/internship-radar">GitHub</a>
  <button type="button" onclick="radarDemoReset()">Reset</button>
</div>
<style>
#demo-bar { position: fixed; left: 50%; bottom: 14px; transform: translateX(-50%); z-index: 100; display: flex; gap: 12px; align-items: center;
  padding: 8px 14px; border-radius: 999px; background: #111827; color: #f9fafb; font: 500 12.5px/1.2 Montserrat, system-ui, sans-serif;
  box-shadow: 0 8px 24px rgba(0,0,0,.25); max-width: calc(100vw - 24px); white-space: nowrap; }
#demo-bar a { color: #93c5fd; text-decoration: none; }
#demo-bar button { border: 0; border-radius: 999px; padding: 4px 10px; background: #374151; color: inherit; font: inherit; cursor: pointer; }
#demo-bar i { font-style: normal; }
@media (max-width: 640px) { #demo-bar i { display: none; } #demo-bar { bottom: 10px; } }
</style>
"""

head = ('<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="description" content="Internship Radar – live demo with fictional data">\n'
        '<style>body{margin:0;padding:0}img{max-width:100%}[hidden]:not([hidden=until-found i]){display:none!important}</style>\n'
        '<script>window.__DEMO_DATA = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + ';</script>\n'
        '<script>\n' + mock + '</script>\n</head>\n<body>\n')
out = head + app + banner + '\n</body>\n</html>\n'
(ROOT / 'docs').mkdir(exist_ok=True)
(ROOT / 'docs' / 'index.html').write_text(out)
print('docs/index.html', len(out) // 1024, 'KB')
