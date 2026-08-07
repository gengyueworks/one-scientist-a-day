#!/usr/bin/env python3
"""
每天认识一位科学家 · 每日挑选引擎

从 data/pool.json 中挑选"今天"对应日期的科学家：
1. 优先选 status == published 且与今天日期匹配的（人工已写好卡）
2. 没有则选 pool 状态中与今天日期匹配的条目，渲染一张"预告卡"
3. 写 README（BEGIN/END 区块）+ archive/YYYY-MM-DD.md

用法：
  python3 scripts/daily_pick.py             # 正式运行（写 README + archive）
  python3 scripts/daily_pick.py --dry-run   # 只打印今天会选谁，不改文件
  python3 scripts/daily_pick.py --date 2026-08-04  # 指定日期（补发/测试）
"""

import argparse
import datetime
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POOL_PATH = ROOT / "data" / "pool.json"
README_PATH = ROOT / "README.md"
ARCHIVE_DIR = ROOT / "archive"
SCIENTISTS_DIR = ROOT / "scientists"

BEGIN_MARK = "<!-- SCIENTIST-DAILY:BEGIN -->"
END_MARK = "<!-- SCIENTIST-DAILY:END -->"


def load_pool():
    with open(POOL_PATH, encoding="utf-8") as f:
        return json.load(f)


def md_of_date(date_str):
    """MM/DD -> scientists/MM/MM-DD-*.md 已写好的卡文件列表"""
    m, d = date_str.split("/")
    month_dir = SCIENTISTS_DIR / m
    if not month_dir.exists():
        return []
    return sorted(month_dir.glob(f"{m}-{d}-*.md"))


def find_entry(pool, date_str):
    return [e for e in pool if e["date"] == date_str]


def render_today(entries, card_files):
    """渲染今天的卡片内容。有已写卡读文件，否则用 pool 的 one_line 渲染预告卡。"""
    parts = []
    for e in entries:
        # 尝试匹配已写卡
        slug_key = (e.get("person") or "").lower()
        matched = []
        for cf in card_files:
            parts.append(f"\n---\n\n" + cf.read_text(encoding="utf-8").strip())
            matched.append(cf)
        if matched:
            continue
        ty = {"birth": "诞辰", "death": "忌日", "event": "事件"}.get(e["type"], e["type"])
        name = e["person"]
        parts.append(
            f"## {name}｜{e['date']} {ty}\n\n"
            f"**领域**：{e['field']}\n\n"
            f"> {e['one_line']}\n\n"
            f"（完整人物故事筹备中，敬请期待）\n"
        )
    return "\n\n".join(parts)


def update_readme(content_block):
    text = README_PATH.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(BEGIN_MARK) + r".*?" + re.escape(END_MARK), re.S)
    new_block = f"{BEGIN_MARK}\n\n{content_block}\n\n{END_MARK}"
    if pattern.search(text):
        text = pattern.sub(new_block, text)
    else:
        text = text + "\n\n" + new_block + "\n"
    README_PATH.write_text(text, encoding="utf-8")


def write_archive(date_obj, content):
    ARCHIVE_DIR.mkdir(exist_ok=True)
    fname = f"{date_obj:%Y-%m-%d}.md"
    fpath = ARCHIVE_DIR / fname
    if fpath.exists():
        return fpath, False
    header = f"# 每天认识一位科学家 · {date_obj:%Y-%m-%d}\n\n"
    fpath.write_text(header + content.strip() + "\n", encoding="utf-8")
    return fpath, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--date", type=str, help="YYYY-MM-DD")
    args = ap.parse_args()

    today = datetime.date.fromisoformat(args.date) if args.date else datetime.date.today()
    date_str = f"{today.month:02d}/{today.day:02d}"

    pool = load_pool()
    entries = find_entry(pool, date_str)
    card_files = md_of_date(date_str)

    if args.dry_run:
        print(f"今天 {date_str}")
        if entries:
            for e in entries:
                print(f"  - {e['person']} ({e['type']}) {e['one_line']}")
        else:
            print("  (选题池无此日期条目)")
        print(f"已写好卡的科学家: {[c.name for c in card_files]}")
        return

    if not entries:
        print(f"NO_ENTRY {date_str}")
        return

    content = render_today(entries, card_files)
    update_readme(content)
    fpath, created = write_archive(today, content)
    print(f"UPDATED {date_str}: {len(entries)} entries, archive={fpath.name} created={created}")


if __name__ == "__main__":
    main()
