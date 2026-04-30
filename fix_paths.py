#!/usr/bin/env python3
"""
fix_paths.py  —  One-time fix for built HTML files.
Replaces all absolute /static/ paths with relative static/ paths
so files work when opened directly via file:// as well as on Vercel.
"""
import os
from pathlib import Path

DIST_DIR = Path(__file__).resolve().parent / "dist" / "default"

fixes = {
    'href="/static/': 'href="static/',
    'src="/static/':  'src="static/',
}

patched = 0
for html_file in DIST_DIR.glob("*.html"):
    text = html_file.read_text(encoding="utf-8")
    original = text
    for bad, good in fixes.items():
        text = text.replace(bad, good)
    if text != original:
        html_file.write_text(text, encoding="utf-8")
        patched += 1
        print(f"  [✓] Fixed: {html_file.name}")

print(f"\nDone! Patched {patched} files.")
