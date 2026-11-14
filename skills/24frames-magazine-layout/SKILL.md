---
name: 24frames-magazine-layout
description: >-
  24帧杂志排版：把影评 / 游戏评论排成 24帧（24FRAMES PROJECT）公众号文章，本地生成 HTML、封面并自检，可选存为公众号草稿（从不发布）。
  Use when the user says 「24帧杂志排版」「用24帧杂志排版」「杂志排版」, or asks to lay out a WeChat Official Account (公众号) article in the 24帧 style.
---
# 24帧杂志排版

`<skill>` = 本文件所在目录。所有脚本只用相对 `<skill>` 的路径，文章目录由用户指定（下文 `<dir>`）。
规格：`docs/SPEC.md`。完整例稿：`example/`。

## 流程
1. `python3 <skill>/bin/new_article.py <dir>` → 写 `<dir>/article.md`，图片放 `<dir>/images/`。
2. `python3 <skill>/bin/make.py <dir> --cover` → 词标、Read more 卡片、`out/content.html`、封面（1800×766 + 1080²）。
3. `python3 <skill>/bin/selfcheck.py <dir> --shots` → 必须全部 PASS。把截图和 `out/cover/cover_pair_preview.jpg` 给用户看。
4. 存草稿（需要公众号凭据，见 README）：`bin/draft.py <dir> dry-run`；用户对这一篇明确同意后才 `add --yes-add`。
5. `python3 <skill>/bin/preview_verify.py <dir>` 在真实预览页核对浅色和深色。

## article.md
Frontmatter：`title author hero cover_still cover_label byline_name byline_sig readmore_url readmore_title readmore_cover`，可选 `digest`、`music_*`。模板见 `templates/article_template.md`。

| 行 | 生成 |
|---|---|
| `### …` | dek（头图下 12px 绯红） |
| 普通段落、`**粗体**` | 14px 正文 |
| `## 01 中文标题 \| ENGLISH` | 章节词标（中文约 18 字以内） |
| `![《片名》年份](images/a.jpg)` / `![《片名》年份](images/a.jpg images/b.jpg)` | 单图 / 上下对图 |
| `>> **词**文字` | rail 侧栏条目 |
| `[[music-card]]` / `♪ …` | 音乐卡片 / 音乐行 |
| `[[byline]]` / `[credit] …` | 署名块 / credits |

## 动手前检查
- 栏目词（Screen / Play / Portrait）按文章类型定，影评用 Screen；封面和正文一致。build 后 `rg -n "Play|Portrait|Screen" <dir>/out/content.html` 确认。
- 封面不切头：准备一张留足头顶空间的 2.35:1 剧照，看 `cover_pair_preview.jpg` 的横版和 1:1，告诉用户 1:1 里谁被裁掉。
- 图注只写 `《片名》年份`；同一部片连续几张只写第一张。
- 图片保留高清（单张 ≤10MB，用 `draft.py upload --material`）；原图存 `images_orig/`。重试前先看 `out/wechat_state.json`，避免重复建草稿。

## 硬规则
- 不发布、不群发、不删除草稿（`lib/wechat.py` 拦截）。不打印、不复制、不提交凭据和 token。
- 每篇只 `draft/add` 一次；之后只 `draft/update` 同一 media_id，在 `draft.py get` 读回的内容上局部改，再 `update <file> --yes-update`。不整篇重建覆盖用户在编辑器里的修改。
- 以预览页为准，不以 draft/get 为准。
- 文字 SVG 只来自字体轮廓（`bin/textsvg.py`），不描图。logo 用官方 SVG 拍平；二维码是三张独立图片。
- 改规则时同时改脚本、`kit.json` 和 `docs/SPEC.md`，再对 `example/` 跑 make + selfcheck。
