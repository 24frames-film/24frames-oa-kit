# 排版规格（SPEC）

数值以 `kit.json` 和 `logo/logo_spec.json` 为准；`bin/selfcheck.py` 自动检查其中大部分。

## 1. 颜色
| Token | 值 | 用途 |
|---|---|---|
| 强调色 | `#D3381C` | 图注、dek、♪ 音乐行、「」括号、rail 起头词 |
| 正文 | `#3E3E3E` | 正文、署名、credits、二维码标签 |
| 黑 | `#141414` | logo、词标、标题条（SVG `currentColor`） |
| 个签 | `#999999` | 署名下的个签 |

全文只用一个强调色。所有标签用绯红直角括号「」，不用圆括号。

## 2. 字体
- HTML 文字：读者设备字体（`PingFang SC` → `Noto Sans CJK SC` 等），300，加粗 600。
- 章节编号：Bebas Neue。栏目词 Screen / Play / Portrait：Montserrat Alternates Medium。词标英文：SemiBold。Read more / Follow us：Bold。
- 中文标题、「」、二维码标签、「24帧/文」：Noto Sans CJK SC Bold（ttc index 2）。CTA、Read more 卡片标题：Noto Sans CJK SC Regular。
- **文字 SVG 只能由字体字形轮廓生成**（`bin/textsvg.py`），禁止把位图描成 path。selfcheck 会拒绝描图或未登记的 SVG。

## 3. 字号（HTML，CSS px）
| 角色 | 字号 / 字重 / 行高 / 字距 | 颜色 |
|---|---|---|
| 正文 | 14 / 300 / 1.8 / 1.5px，两端对齐，无首行缩进 | #3E3E3E |
| dek、图注、♪ 音乐行 | 12 / 300 / 1.8 / 1px | #D3381C |
| credits、个签 | 12 / 300 / 1.8 / 1px | #3E3E3E / #999999 |
| rail | 同正文，宽 85%、左缩 15%，起头词 600 绯红 | #3E3E3E |

烘焙文字按 383 宽手机（栏宽 353）定显示字号：`baked_px = display_px × canvas_w ÷ 353`。层级（@383 显示 px）：词标编号 43.4、词标中文 19.4、刊头栏目词 16.8、Read more / Follow us / 「24帧/文」16.8、卡片标题 13.0、二维码标签 12.0。

## 4. 布局
- 检查宽度：347 / 383 / 677。所有块都在左右 15px 边线内，没有出血；墨迹落在边线 ±1px。
- 只用 `%`、`auto` 和 15px 内边距；禁止 px 宽、`max-width`、`height=`、`overflow:`、`display:inline`、负 margin。`flex` / `inline-block` / % 宽只允许在二维码行。
- 字距补偿：14px 文字 `padding:0 13.5px 0 15px`；12px 文字 `padding:0 14px 0 15px`；♪ 行 `text-indent:-3px`。
- 每块只写 `margin-top`（build 按墨迹自动算），`margin-bottom` 为 0。

## 5. 纵向间距（墨迹到墨迹，±1px）
- **16**：图 → 图注；署名块内（「24帧/文」→ 名字 → 个签）。
- **24**：头图 → dek；同组 rail 条目之间。
- **48**：其余同级块；所有小标题上下（词标、Read more、Follow us 都是 48 / 48）；署名块前后；credits → 页脚 → Read more → 卡片 → Follow us → 二维码。
- 刊头：文章顶 → logo 24，刊头 → 头图 32；文章底 padding 40。

## 6. 深色模式
- 文章外层 `data-role="article"` 用纯白图片做背景（`assets/whitebase.jpg`，repeat-y，100% auto），不写 background-color。微信深色算法会跳过背景图上的文字，阅读区保持白底深字。
- 禁止 `light-dark()`、`color-scheme` 或任何按系统偏好切换颜色的写法（会让编辑器里的字变白）。
- 文字 SVG 用 `fill="currentColor"` + 外层 `color`；「」用固定 `#D3381C`。

## 7. 资产
| 资产 | 规格 |
|---|---|
| 刊头 | `assets/masthead.svg`：官方 logo（拍平成 path，含通栏横杠）+ Screen「Play」Portrait 行，栏宽 100% |
| 页脚 | `assets/footer.svg`：只有 logo，无底色无卡片 |
| 章节词标 | `## NN 中文 \| ENGLISH` → `bin/wordmarks.py`：编号 Bebas 152、英文 SemiBold 40 + 「」80、中文 Bold 68（画布 px）；中文约 18 字一行，放不下报错 |
| Read more 卡片 | `bin/readmore.py`：上一篇的 2.35:1 封面放大到 1218 宽，底部渐变，标题 Regular 45 白色；整张包 `<a href>` |
| 标题条 / 署名条 / 二维码标签 | `assets/read_more.svg`、`follow_head.svg`、`byline_label.svg`、`follow_qr_labels.svg`（`bin/textsvg.py strips` 生成） |
| 二维码 | `assets/qr_oa.png`、`qr_xhs.png`、`qr_helper.png`：540×540，白色圆角底；三张独立 `<img>`（微信一张图只识别一个码），宽 26.656%，间距 10.016% |
| 封面 | `bin/cover.py`：1800×766，亮度 0.72，白色 logo 墨迹宽 518 居中，栏目词 Montserrat Medium 44 + 「」80 带光晕；1:1 裁切 x 517–1283；另出 1080×1080 |
| 内容图 | 宽 ≥1080（GIF ≥480）；JPG/PNG ≥1MB 上传时自动重编码 |

换成自己的品牌：替换 `logo/24frames_official.svg` 和 `assets/qr_*.png`，改 `bin/textsvg.py` 里的标签文字，再跑 `python3 bin/textsvg.py strips`。

## 8. 文章结构
刊头 → 头图 → dek → 正文与配图 → 章节（词标 + 文字 / 图 / rail / ♪）→ 署名块 → credits → 页脚 logo → Read more + 卡片 → Follow us + 三个二维码。页脚之后的部分由 build 自动生成。

## 9. 图片
- 图文交替；每张图放在它描绘的段落后面；不放重复场景。
- 影片剧照图注只写 `《片名》年份`，不加标点和画面描述；同一部片连着几张只在第一张写。人物写最短称呼。非影片配图可写一句看得见的内容。
- 血腥画面只用非特写，并标注。换图前先让用户确认。

## 10. 公众号接口
- 只允许 `kit.json → safety.allowed_endpoints`；发布、群发、删除草稿在 `lib/wechat.py` 里被拦截。
- 一篇只 `draft/add` 一次；之后只 `draft/update` 同一 media_id 的 index 0，在 `draft/get` 读回的内容上局部改，保留 title / digest / thumb / 评论 / cover_info / author。回传前把 `&#39;` 换成 `'`。
- 用户在编辑器里加的音乐卡片（`mp-common-clmusic`）、音频（`mp-common-mpaudio`）和图片单独成块，原样保留；用 `draft.py get` 读回后局部改，不重建整篇。背景音乐接口加不了，提醒用户在后台手动加。
- 微信正文图片最宽 1280px。`media/uploadimg` 单张上限 1MB；10MB 以内用 `draft.py upload --material`。
- 核对以真实预览页为准（`bin/preview_verify.py`），不以 draft/get 为准。运行机器的出口 IP 要在公众号后台的 IP 白名单里。
