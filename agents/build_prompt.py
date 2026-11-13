#!/usr/bin/env python3
"""Render an agent prompt for a scheduled Claude Code task.

The scheduled tasks run in a fresh cloud sandbox without access to this repository,
so the scan prompt carries scanner/scan.py inline. The artifact URL is kept out of the repo.

Usage:  RADAR_ARTIFACT_URL=https://claude.ai/artifact/... python3 agents/build_prompt.py scan-run > prompt.txt
        RADAR_ARTIFACT_URL=... python3 agents/build_prompt.py mail-sync > prompt.txt
"""
import os, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

def render(name):
    tpl = (ROOT / 'agents' / f'{name}.prompt.md').read_text()
    url = os.environ.get('RADAR_ARTIFACT_URL', '{{ARTIFACT_URL}}')
    out = tpl.replace('{{ARTIFACT_URL}}', url)
    if '{{SCAN_PY}}' in out:
        src = (ROOT / 'scanner' / 'scan.py').read_text()
        out = out.replace('{{SCAN_PY}}', src if src.endswith('\n') else src + '\n')
    return out

if __name__ == '__main__':
    sys.stdout.write(render(sys.argv[1] if len(sys.argv) > 1 else 'scan-run'))
