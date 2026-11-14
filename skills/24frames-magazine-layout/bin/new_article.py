#!/usr/bin/env python3
"""Scaffold a new article folder: article.md (from templates/article_template.md) + images/.
usage: python3 bin/new_article.py <article_dir>"""
import os, sys, shutil
K = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")); d = os.path.abspath(sys.argv[1])
if os.path.exists(f"{d}/article.md"): sys.exit(f"{d}/article.md exists — not overwriting")
os.makedirs(f"{d}/images", exist_ok=True); shutil.copy(f"{K}/templates/article_template.md", f"{d}/article.md"); print("created", d)
