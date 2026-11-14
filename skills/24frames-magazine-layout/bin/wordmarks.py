#!/usr/bin/env python3
"""Chapter wordmarks → ink-tight inline SVGs from FONT OUTLINES (bitmap tracing of text is forbidden).
Bebas Neue 152 number · 「ENGLISH」 Montserrat Alternates SemiBold 40 + 「」 Noto Sans CJK SC Bold 80 · Chinese title Noto Sans CJK SC
Bold 68; solid ink spans 1236.9 canvas px (= 15px column at 347, @2x). Layout + emit live in bin/textsvg.py (wordmark()).
usage: python3 bin/wordmarks.py <article_dir>   (## NN 中文 | ENGLISH lines → out/svg/wm_NN.svg + out/svg/wordmarks.json)"""
import os, sys, subprocess
subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "textsvg.py"), "wordmarks", *sys.argv[1:]], check=True)
