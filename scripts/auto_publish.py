#!/usr/bin/env python3
"""
每天认识一位科学家 — 自动补写引擎 / Auto Publisher

工作流程：
  1. 取今天（或 --date 指定）对应的 pool 条目（date == MM/DD）
  2. 检查 scientists/MM/MM-DD-*.md 是否已有叙事卡，有则跳过
  3. 调用 LLM（OpenAI 兼容 API，本地 relay）生成 800-1200 字叙事散文卡
  4. 自检（字数 / 小节数 / 禁用词 / 中文标点），失败自动重试一次
  5. 写卡到 scientists/MM/、更新 pool.json status=published
  6. 跑 daily_pick.py（重建 archive + README）+ build_site.py（重建展示站）
  7. commit + push

用法：
  python3 scripts/auto_publish.py                  # 今天缺卡则自动补写
  python3 scripts/auto_publish.py --date 2026-08-09   # 指定日期（测试/补发）
  python3 scripts/auto_publish.py --dry-run        # 只输出计划
  python3 scripts/auto_publish.py --push           # 提交后立即 push（本地定时任务用）

环境变量（launchd plist 注入）：
  LLM_API_KEY   必填（本地 relay 可不校验）
  LLM_BASE_URL  默认 http://127.0.0.1:8317
  LLM_MODEL     默认 claude-sonnet-4-6
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
POOL_PATH = ROOT / "data" / "pool.json"
SCIENTISTS_DIR = ROOT / "scientists"

BANNED_PHRASES = [
    "令人叹为观止", "不禁让人", "在那个时代", "深远影响", "无与伦比", "他的一生充满传奇",
    "不仅仅", "不朽的", "众所周知", "显而易见", "综上所述", "总而言之", "值得注意",
    "值得一提的是", "献身科学", "孜孜不倦", "孜孜以求", "熠熠生辉", "匠心独运", "巧夺天工",
    "岁月如梭", "光阴荏苒", "谱写", "奏响", "翻开新篇章", "奠定基础", "作出巨大贡献",
    "享誉世界", "闻名遐迩", "千古流芳", "永远活在我们心中", "激励着一代又一代",
]

SYSTEM_PROMPT = """你是科学史写作研究员，为中文读者撰写"每天认识一位科学家"的原创叙事散文卡。写作纪律（每条都是硬性要求）：

1. 正文字数 800-1200 字（不含标题）。
2. 不讲百科履历，不从出生写到去世。只挑 1-3 个改变人生轨迹的时刻深挖，讲关键时刻、关键选择与代价。
3. 场景化开场：第一段必须是一个具体画面/场景/冲突，禁止「XX 是著名的 XX 家」这种介绍体。
4. 小节标题 2-4 个，每个是一句有信息量的话，禁止「他是谁」「他的贡献」这类空壳标题。
5. 具体 > 形容词：写「在 58 个晚上被拒绝 237 次」而不是「非常努力」。年份、地点、数字必须具体真实。
6. 讲代价与冲突：这个人付出了什么、失去了什么。
7. 「他说过」只写真引语，没有可靠引语就整节删除。
8. 禁止出现以下词语（出现即整卡不合格）：令人叹为观止、不禁让人、在那个时代、深远影响、无与伦比、他的一生充满传奇、不仅仅、不朽的、众所周知、显而易见、综上所述、值得一提、献身科学、孜孜不倦、谱写、奏响、翻开新篇章、奠定基础、享誉世界、闻名遐迩、永远活在我们心中。
9. 全文用中文标点（，。！？；：""''），中文句内禁止出现英文标点。
10. 语言风格：口语化、直接、有节奏感，像说话一样写；不用「然而」「因此」「综上所述」；段落要短，一段不超过 3-4 句。破折号全文不超过 3 个。
11. 年份、数字、引语必须真实可查；不确定的年份写「约」，禁止编造细节和引语。

输出格式（直接输出 markdown，不要代码块围栏，不要输出其他任何文字）：

# {一句有吸引力的标题，不点破主题，让人想读}

## {人物名}｜{M}月{D}日诞辰

{开场钩子段落}

## {小节标题 1}

{叙事段落}

## {小节标题 2}

{叙事段落}

## 他说过

> {真实引语}
"""


def log(msg):
    print(msg, flush=True)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"  ✅ 已保存: {path.name}")


def call_llm(prompt, api_key, base_url, model, retries=2):
    """调用 OpenAI 兼容 chat completions，输出 markdown 文本。"""
    url = base_url.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 4000,
    }
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "OneScientistADay/1.0",
                },
            )
            resp = json.load(urllib.request.urlopen(req, timeout=300))
            content = resp["choices"][0]["message"]["content"]
            content = re.sub(r"^```(?:markdown)?\s*", "", content.strip())
            content = re.sub(r"\s*```$", "", content.strip())
            return content
        except Exception as e:
            log(f"  [WARN] LLM 调用第 {attempt + 1} 次失败: {e}")
            if attempt < retries:
                time.sleep(8 * (attempt + 1))
    return None


def build_prompt(entry, target_date):
    m, d = entry["date"].split("/")
    ty = {"birth": "诞辰", "death": "忌日", "event": "事件"}.get(entry["type"], entry["type"])
    link = entry.get("link", "")
    return f"""请为以下科学家撰写一张"每天认识一位科学家"卡片（{target_date}）。

科学家档案：
- 人物: {entry['person']}
- 领域: {entry['field']}
- 日期: {entry['date']}（{ty}）
- 一句话简介: {entry['one_line']}
- 参考链接（事实来源）: {link}

日期要求：卡片副标题写「## {entry['person']}｜{int(m)}月{int(d)}日{ty}」。
写作依据以你的知识为准，参考链接用于事实核实，不要复制原文。
"""


def validate_card(content):
    """自检：字数 / 小节数 / 标题 / 禁用词 / 中文标点。返回 (ok, 问题列表)。"""
    problems = []
    if not content.startswith("# "):
        problems.append("首行不是 # 标题")
    body = re.sub(r"^#.*$", "", content, flags=re.M)
    chars = len(re.sub(r"\s", "", body))
    if chars < 700 or chars > 1500:
        problems.append(f"正文字数 {chars}（要求 800-1200，容差 700-1500）")
    sections = len(re.findall(r"^## ", content, flags=re.M))
    if sections < 3:
        problems.append(f"## 小节数 {sections}（要求 ≥3，含诞辰行）")
    for phrase in BANNED_PHRASES:
        if phrase in content:
            problems.append(f"含禁用词: {phrase}")
    bad = re.findall(r"[\u4e00-\u9fff][,.;!?]", content)
    if bad:
        problems.append(f"中文后跟英文标点: {bad[:5]}")
    ascii_quotes = re.findall(r'"([^"]{1,40})"', content)
    if ascii_quotes:
        problems.append(f"含 ASCII 双引号（应改用中文引号“”）：{ascii_quotes[:3]}")
    if content.count("——") > 3:
        problems.append("破折号超过 3 个")
    return (not problems), problems


def card_files_for(entry):
    m, d = entry["date"].split("/")
    month_dir = SCIENTISTS_DIR / m
    if not month_dir.exists():
        return []
    return sorted(month_dir.glob(f"{m}-{d}-*.md"))


def slug_for(entry):
    en = entry.get("en_person") or entry["person"]
    slug = re.sub(r"[^a-z0-9]+", "-", en.lower()).strip("-")
    return slug


def git(*args):
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def commit_and_push(files, message, do_push=False):
    git("add", "--", *files)
    code, _ = git("diff", "--cached", "--quiet")
    if code == 0:
        log("  无变更，跳过提交")
        return True
    env = dict(os.environ)
    env["GIT_EDITOR"] = "true"
    r = subprocess.run(["git", "-C", str(ROOT), "commit", "-m", message], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        log(f"  [ERROR] commit 失败: {r.stderr[:300]}")
        return False
    log(f"  ✅ commit: {message}")
    if do_push:
        r = subprocess.run(["git", "-C", str(ROOT), "push"], capture_output=True, text=True)
        if r.returncode != 0:
            log(f"  [ERROR] push 失败: {r.stderr[:300]}")
            return False
        log("  ✅ push 成功")
    return True


def main():
    parser = argparse.ArgumentParser(description="每天认识一位科学家 — 自动补写引擎")
    parser.add_argument("--date", help="指定日期 (YYYY-MM-DD)", default=None)
    parser.add_argument("--dry-run", action="store_true", help="只输出计划")
    parser.add_argument("--push", action="store_true", help="提交后立即 push（本地定时任务用）")
    parser.add_argument("--llm-api-key", default=None)
    parser.add_argument("--llm-base-url", default=None)
    parser.add_argument("--llm-model", default=None)
    args = parser.parse_args()

    api_key = args.llm_api_key or os.environ.get("LLM_API_KEY", "")
    base_url = args.llm_base_url or os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8317")
    model = args.llm_model or os.environ.get("LLM_MODEL", "claude-sonnet-4-6")

    target_date = args.date or datetime.date.today().isoformat()
    m, d = target_date[5:7], target_date[8:10]
    date_str = f"{m}/{d}"

    pool = load_json(POOL_PATH)
    entries = [e for e in pool if e["date"] == date_str]
    if not entries:
        log(f"NO_ENTRY {date_str}")
        return
    missing = [e for e in entries if not card_files_for(e)]
    if not missing:
        log(f"SKIP {date_str}: 当天科学家均有叙事卡，无需补写")
        return

    if args.dry_run:
        for e in missing:
            log(f"  [DRY] {e['date']} {e['person']} — 缺卡，将调用 LLM 补写")
        return

    if not api_key:
        log("❌ 缺少 LLM_API_KEY（环境变量）")
        sys.exit(1)

    for entry in missing:
        log(f"✍️ 补写 {date_str} {entry['person']} ...")
        prompt = build_prompt(entry, target_date)
        content = call_llm(prompt, api_key, base_url, model)
        if not content:
            log(f"❌ LLM 生成失败，{entry['person']} 未补写")
            continue
        ok, problems = validate_card(content)
        if not ok:
            log(f"⚠️ 自检未通过，重试一次: {problems}")
            fix_hint = ("\n\n上次生成被驳回，原因如下，请逐条修正后重新输出：\n- " + "\n- ".join(problems))
            content = call_llm(prompt + fix_hint, api_key, base_url, model, retries=1)
            if content:
                ok, problems = validate_card(content)
            if not ok:
                log(f"❌ 自检仍未通过，{entry['person']} 未发布: {problems}")
                continue
        log("  ✅ 自检通过")

        month_dir = SCIENTISTS_DIR / m
        month_dir.mkdir(parents=True, exist_ok=True)
        card_path = month_dir / f"{m}-{d}-{slug_for(entry)}.md"
        note = "\n\n<!-- 本卡由自动补写引擎生成，事实与引语请人工核对 -->\n"
        card_path.write_text(content.rstrip() + note, encoding="utf-8")
        log(f"  ✅ 已写卡: {card_path.name}")

        for e in pool:
            if e["date"] == date_str and e["person"] == entry["person"]:
                e["status"] = "published"
        save_json(POOL_PATH, pool)

    log("📦 重建 archive + README + 展示站 ...")
    subprocess.run([sys.executable, str(SCRIPT_DIR / "daily_pick.py"), "--date", target_date], check=False)
    archive = ROOT / "archive" / f"{target_date}.md"
    if archive.exists() and "写作中" in archive.read_text(encoding="utf-8"):
        archive.unlink()
        subprocess.run([sys.executable, str(SCRIPT_DIR / "daily_pick.py"), "--date", target_date], check=False)
    subprocess.run([sys.executable, str(SCRIPT_DIR / "build_site.py")], check=False)

    files = [str(SCRIPT_DIR / "daily_pick.py"), str(SCIENTISTS_DIR / m), str(POOL_PATH),
             str(ROOT / "README.md"), str(ROOT / "archive"), str(ROOT / "index.html")]
    commit_and_push(files, f"Auto scientist {target_date}", do_push=args.push)


if __name__ == "__main__":
    main()
