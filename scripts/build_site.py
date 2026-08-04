#!/usr/bin/env python3
"""从 scientists/ 下的 md 文章生成展示站 index.html（GitHub Pages 用）。
自包含单文件：全文内嵌，零依赖，无需构建工具。"""
import glob
import json
import re
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "scientists")
OUT = os.path.join(ROOT, "index.html")

FIELD_COLOR = {
    "物理": "#5B8DEF", "数学": "#8A6FE8", "化学": "#4FB477", "生物": "#3CB6A6",
    "天文": "#3AA0DD", "宇宙学": "#2D8BBD", "天体物理": "#2D8BBD", "医学": "#E8835B",
    "计算机": "#E6A23C", "工程": "#C25B8B", "发明": "#C25B8B", "心理学": "#B4774F",
    "地质": "#7A8B6F", "地理": "#7A8B6F", "神经科学": "#B4774F", "生理": "#4FB477",
    "信息论": "#E6A23C", "科学哲学": "#7A8B6F", "科学方法": "#7A8B6F", "考古": "#7A8B6F",
    "航天": "#3AA0DD", "生态": "#3CB6A6", "遗传": "#3CB6A6", "生态学": "#3CB6A6",
    "生物/遗传": "#3CB6A6", "化学/生物": "#4FB477", "物理/化学": "#5B8DEF",
    "物理/天文": "#5B8DEF", "物理/数学": "#5B8DEF", "物理/政治": "#5B8DEF",
    "数学/哲学": "#8A6FE8", "数学/逻辑": "#8A6FE8", "物理/医学": "#5B8DEF",
    "心理学/医学": "#B4774F", "医学/统计": "#E8835B", "医学/流行病": "#E8835B",
    "科学/艺术": "#8A6FE8", "地理/自然": "#7A8B6F", "物理/工程": "#5B8DEF",
    "物理/能源": "#5B8DEF", "物理/天体物理": "#5B8DEF", "计算机/数学": "#E6A23C",
    "科技/商业": "#E6A23C", "化学/物理": "#4FB477", "生命科学": "#3CB6A6",
    "哲学/天文": "#7A8B6F", "信息论/计算机": "#E6A23C", "物理/声学": "#5B8DEF",
    "工程/教育": "#C25B8B", "古生物": "#7A8B6F", "材料科学": "#C25B8B",
}

def parse_md(path):
    raw = open(path, encoding="utf-8").read()
    lines = raw.split("\n")
    # 标题 = 第一行 # 
    title = ""
    for ln in lines:
        if ln.startswith("# "):
            title = ln[2:].strip()
            break
    # 副题 = 第一个 ## 
    subtitle = ""
    for ln in lines:
        if ln.startswith("## "):
            subtitle = ln[3:].strip()
            break
    # 领域：从副题尾部猜不出，读 data/pool.json 匹配
    # 日期从文件名的 MM-DD 来
    fn = os.path.basename(path)
    m = re.match(r"(\d{2})-(\d{2})-", fn)
    date = f"{m.group(1)}-{m.group(2)}" if m else "00-00"
    slug = fn.replace(".md", "")
    return {"title": title, "subtitle": subtitle, "date": date, "slug": slug,
            "file": os.path.relpath(path, ROOT), "content": raw}

def month_label(mm):
    return f"{int(mm)} 月"

def main():
    articles = []
    for p in sorted(glob.glob(os.path.join(SRC, "**", "*.md"), recursive=True)):
        a = parse_md(p)
        if a["title"] and a["subtitle"]:
            articles.append(a)
    articles.sort(key=lambda x: x["date"])

    # 领域：用 pool.json 的 field 映射
    pool_path = os.path.join(ROOT, "data", "pool.json")
    pool = {}
    if os.path.exists(pool_path):
        for r in json.load(open(pool_path, encoding="utf-8")):
            if "date" in r:
                pool[r["date"]] = r

    fields = []
    for a in articles:
        mm, dd = a["date"].split("-")
        r = pool.get(f"{mm}/{dd}")
        a["field"] = (r or {}).get("field", "科学")
        f = a["field"].split("/")[0]
        if f not in fields:
            fields.append(f)
    fields.sort()

    # 生成 HTML
    css = open(os.path.join(ROOT, "_meta", "site-style.css"), encoding="utf-8").read() if os.path.exists(os.path.join(ROOT, "_meta", "site-style.css")) else ""
    js_data = json.dumps(articles, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>每天认识一位科学家 · One Scientist A Day</title>
<style>
{css}
</style>
</head>
<body>
<header class="hero">
  <p class="kicker">ONE SCIENTIST A DAY</p>
  <h1>每天认识一位科学家</h1>
  <p class="tagline">不讲百科履历，只讲他人生里最要紧的几个时刻：<br>怎么走到那一步，付出了什么，又放弃了什么。</p>
  <div class="stats">
    <div class="stat"><span class="n" id="stat-n">0</span><span class="l">篇人物特写</span></div>
    <div class="stat"><span class="n" id="stat-f">0</span><span class="l">个领域</span></div>
    <div class="stat"><span class="n" id="stat-m">0</span><span class="l">个月份覆盖</span></div>
  </div>
</header>

<nav class="field-nav" id="field-nav"></nav>

<main id="gallery"></main>

<footer class="foot">
  <p>选题日历参考 PanSci《科学史上的今天》日期锚点（公开事实），<br>全部文字原创撰写 · 每日自动更新，一年 365 天。</p>
</footer>

<!-- 文章全文数据 -->
<script id="articles-data" type="application/json">
{js_data}
</script>

<script>
const ARTICLES = JSON.parse(document.getElementById('articles-data').textContent);
const FIELDS = {json.dumps(fields, ensure_ascii=False)};

document.getElementById('stat-n').textContent = ARTICLES.length;
document.getElementById('stat-f').textContent = FIELDS.length;
document.getElementById('stat-m').textContent = new Set(ARTICLES.map(a=>a.date.slice(0,2))).size;

const nav = document.getElementById('field-nav');
const allBtn = document.createElement('button');
allBtn.textContent = '全部';
allBtn.className = 'active';
allBtn.onclick = () => render();
nav.appendChild(allBtn);
FIELDS.forEach(f => {{
  const b = document.createElement('button');
  b.textContent = f;
  b.onclick = () => render(f);
  nav.appendChild(b);
}});

function esc(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}

function mdToHtml(text) {{
  const lines = text.split('\\n');
  let out = [];
  for (let ln of lines) {{
    if (ln.startsWith('# ')) continue;
    if (ln.startsWith('## ')) {{ out.push('<h3>' + esc(ln.slice(3)) + '</h3>'); }}
    else if (ln.startsWith('> ')) {{ out.push('<blockquote>' + esc(ln.slice(2)) + '</blockquote>'); }}
    else if (ln.trim() === '') {{ out.push('<br>'); }}
    else if (ln.startsWith('参考')) {{ }}
    else {{ out.push('<p>' + esc(ln) + '</p>'); }}
  }}
  return out.join('\\n');
}}

function render(field) {{
  const gal = document.getElementById('gallery');
  const list = ARTICLES.filter(a => !field || a.field.split('/')[0] === field);
  let months = {{}};
  list.forEach(a => {{
    const mm = a.date.slice(0,2);
    (months[mm] = months[mm] || []).push(a);
  }});
  const mmKeys = Object.keys(months).sort();
  gal.innerHTML = mmKeys.map(mm => {{
    const cards = months[mm].map(a => {{
      return `<article class="card" data-slug="${{a.slug}}">
        <div class="card-date">${{a.date.slice(5)}}</div>
        <h2>${{esc(a.title)}}</h2>
        <p class="card-sub">${{esc(a.subtitle)}}</p>
        <span class="tag">${{esc(a.field)}}</span>
      </article>`;
    }}).join('');
    return `<section class="month" id="m${{mm}}"><h2 class="month-head">${{mm}} 月</h2><div class="cards">${{cards}}</div></section>`;
  }}).join('');
  gal.querySelectorAll('.card').forEach(c => c.onclick = () => openArticle(c.dataset.slug));
}}

function openArticle(slug) {{
  const a = ARTICLES.find(x => x.slug === slug);
  if (!a) return;
  const overlay = document.createElement('div');
  overlay.className = 'overlay';
  const color = 'var(--ink)';
  overlay.innerHTML = `<div class="modal" onclick="event.stopPropagation()">
    <button class="close">×</button>
    <p class="modal-date">${{a.date}}</p>
    <h1>${{esc(a.title)}}</h1>
    <h2 class="modal-sub">${{esc(a.subtitle)}}</h2>
    <div class="modal-body">${{mdToHtml(a.content)}}</div>
  </div>`;
  overlay.onclick = () => overlay.remove();
  overlay.querySelector('.close').onclick = () => overlay.remove();
  document.body.appendChild(overlay);
  document.body.style.overflow = 'hidden';
}}

render();
</script>
</body>
</html>"""
    open(OUT, "w", encoding="utf-8").write(html)
    print(f"生成 {OUT}：{len(articles)} 篇，{len(fields)} 个领域")

if __name__ == "__main__":
    main()
