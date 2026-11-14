#!/usr/bin/env python3
"""One command: wordmarks → Read more card → content.html → (optional) cover. Local only, no network.
usage: python3 bin/make.py <article_dir> [--cover]"""
import os, sys, subprocess, json; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")); import kit
B = os.path.dirname(os.path.abspath(__file__)); adir = os.path.abspath(sys.argv[1])
sys.path.insert(0, B); import build
fm, _ = build.parse(open(f"{adir}/article.md", encoding="utf-8").read())
def run(*a): print("$", " ".join(a)); subprocess.run([sys.executable, *a], check=True)
run(f"{B}/wordmarks.py", adir)
_lab = fm.get("cover_label", "Play")
if _lab != "Play":
    run(f"{B}/textsvg.py", "masthead", _lab, f"{adir}/out/svg")
run(f"{B}/readmore.py", os.path.join(adir, fm["readmore_cover"]), fm["readmore_title"], f"{adir}/out/readmore_card.jpg")
run(f"{B}/build.py", adir)
if "--cover" in sys.argv: run(f"{B}/cover.py", os.path.join(adir, fm["cover_still"]), f"{adir}/out/cover", fm.get("cover_label", "Play"))
