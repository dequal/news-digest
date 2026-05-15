#!/usr/bin/env python3
"""
fetch_news.py — 每日新闻采集 + HTML 生成 + 邮件发送

用法:
    python3 fetch_news.py                    # 完整流程（邮件版）
    python3 fetch_news.py --no-send          # 仅生成邮件版 HTML
    python3 fetch_news.py --wx               # 生成公众号兼容版 HTML
    python3 fetch_news.py --wx --no-send     # 仅生成公众号版，不发送
"""
import feedparser, json, subprocess, sys, os, re, base64, ssl
from datetime import datetime, timedelta, timezone
from html import escape, unescape
from pathlib import Path

if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

TZ_SH = timezone(timedelta(hours=8))
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "sources.json"
OUTPUT_DIR = BASE_DIR / "output"
HERO_SCRIPT = Path(__file__).resolve().parent / "generate_hero.py"
SEND_SCRIPT = Path(__file__).resolve().parent / "send_email.py"
PROSEARCH = os.path.expanduser(
    "~/Library/Application Support/QClaw/openclaw/config/skills/online-search/scripts/prosearch.cjs")

# ── RSS 采集 ──

def strip_tags(text):
    if not text: return ""
    return unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'\s+', ' ', text)).strip())

def parse_date(entry):
    if not entry.get("published"): return None
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(entry["published"])
    except:
        try: return datetime.fromisoformat(entry["published"].replace("Z", "+00:00"))
        except: return None

def fetch_rss(url, label, category, hours=48):
    try:
        feed = feedparser.parse(url)
        items, now = [], datetime.now(TZ_SH)
        for e in feed.entries[:50]:
            dt = parse_date(e)
            age = (now - dt.replace(tzinfo=TZ_SH)).total_seconds() / 3600 if dt else 999
            if age <= hours or dt is None:
                items.append({"title": e.get("title",""), "summary": strip_tags(e.get("summary", e.get("description","")))[:200], "link": e.get("link",""), "date": dt.isoformat() if dt else "", "source": label, "category": category, "age_hours": age})
        return items
    except Exception as ex:
        print(f"  [WARN] RSS {label}: {ex}", file=sys.stderr)
        return []

def search_prosearch(keyword, category, max_r=6):
    if not os.path.exists(PROSEARCH): return []
    try:
        r = subprocess.run(["node", PROSEARCH, f"--keyword={keyword}", "--freshness=24h", "--industry=news", "--cnt=10"], capture_output=True, text=True, timeout=30)
        docs = []
        try:
            data = json.loads(r.stdout)
            for d in data.get("data",{}).get("docs",[])[:max_r]:
                url = d.get("url","")
                if url and d.get("title") and "stcn.com/quotes" not in url:
                    docs.append({"title": d["title"], "summary": strip_tags(d.get("passage",""))[:150], "link": url, "date": d.get("date",""), "source": d.get("site","搜索"), "category": category, "age_hours": 0})
        except: pass
        return docs
    except: return []

def generate_hero(title, date_str):
    hero_path = OUTPUT_DIR / f"hero_{datetime.now(TZ_SH).strftime('%Y%m%d')}.png"
    subprocess.run(["python3", str(HERO_SCRIPT), title, str(hero_path)], check=True, capture_output=True)
    if hero_path.exists():
        with open(hero_path, "rb") as f: b64 = base64.b64encode(f.read()).decode()
        return f"data:image/png;base64,{b64}"
    return ""

# ── 邮件版 HTML（保留 <style>） ──

def build_html(news, today_str, hero_b64, top_title):
    tech, econ, intl = [n for n in news if n["category"]=="tech"][:10], [n for n in news if n["category"]=="econ"][:10], [n for n in news if n["category"]=="intl"][:10]
    def items_html(lst):
        h = ""
        for i, it in enumerate(lst, 1):
            t, l, d, s = escape(it["title"]), escape(it["link"]), escape(it["summary"]), escape(it["source"])
            age = f'<span class="age">{int(it["age_hours"])}h</span>' if it["age_hours"] < 999 else ""
            h += f'<div class="item"><span class="num">{i}</span><div><a href="{l}" class="t">{t}</a><div class="desc">{d}</div><div class="meta">{s}{age}</div></div></div>'
        return h
    hero_img = f'<img src="{hero_b64}" alt="hero" style="width:100%;height:auto;border-radius:16px 16px 0 0;display:block;">' if hero_b64 else ""
    return f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f0f2f7}}.c{{max-width:680px;margin:20px auto}}.hero{{border-radius:16px 16px 0 0;overflow:hidden}}.hd{{background:linear-gradient(135deg,#4F62E8,#7B5EE8);color:#fff;padding:28px 24px;text-align:center;border-radius:0 0 16px 16px;margin-top:-4px}}.hd h1{{font-size:22px;font-weight:700;margin-bottom:6px}}.hd p{{font-size:13px;opacity:.85}}.bar{{background:#fff;text-align:center;padding:10px;font-size:12px;color:#888;border-bottom:1px solid #eee}}.sec{{background:#fff;margin-bottom:12px;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.06)}}.st{{padding:14px 20px 12px;font-size:14px;font-weight:600;display:flex;align-items:center;gap:8px}}.tech .st{{background:linear-gradient(90deg,#EEF3FF,#F5F7FF);color:#3B5BDB;border-bottom:2px solid #EEF3FF}}.econ .st{{background:linear-gradient(90deg,#EEF8F1,#F3FAF5);color:#2E7D32;border-bottom:2px solid #EEF8F1}}.geo .st{{background:linear-gradient(90deg,#FFF4E8,#FFF9F5);color:#C74B15;border-bottom:2px solid #FFF4E8}}.item{{padding:12px 20px;border-bottom:1px solid #f5f5f5;display:flex;align-items:flex-start;gap:10px}}.item:last-child{{border-bottom:none}}.num{{display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;background:#F0F0F0;border-radius:50%;font-size:11px;font-weight:700;color:#888;flex-shrink:0;margin-top:2px}}.t{{font-size:14px;font-weight:600;color:#1a1a1a;line-height:1.4;text-decoration:none}}.t:hover{{color:#4F62E8}}.desc{{font-size:12px;color:#666;margin-top:4px;line-height:1.5}}.meta{{font-size:11px;color:#aaa;margin-top:4px}}.age{{background:#f5f5f5;padding:1px 6px;border-radius:8px;margin-left:6px}}.ft{{text-align:center;color:#aaa;font-size:11px;padding:16px;background:#fff;border-radius:0 0 16px 16px;line-height:1.8}}
</style></head><body><div class="c">{hero_img}<div class="hd"><h1>📰 每日新闻精选</h1><p>科技 · 经济 · 国际局势 · {today_str}</p></div><div class="bar">📡 数据更新时间：{today_str} {datetime.now(TZ_SH).strftime("%H:%M")}</div><div class="sec tech"><div class="st">💻 科技新闻 Top {len(tech)}</div>{items_html(tech)}</div><div class="sec econ"><div class="st">💰 经济新闻 Top {len(econ)}</div>{items_html(econ)}</div><div class="sec geo"><div class="st">🌍 国际局势 Top {len(intl)}</div>{items_html(intl)}</div><div class="ft">由 阿尔法的1号机器人 自动生成 · 仅供参考</div></div></body></html>'''

# ── 公众号兼容版 HTML（基于用户参考设计） ──

def build_html_wx(news, today_str, hero_b64):
    """
    微信公众号兼容版：参照用户提供的参考排版。
    结构：头条卡片(配图+标题) + 科技/经济/国际板块 + 页脚。
    公众号兼容：纯行内样式，flex→table，border-radius/box-shadow 保留(公众号支持)，
    gradient→纯色，外链图片→base64内嵌，gap→padding。
    """
    tech  = [n for n in news if n["category"] == "tech"][:5]
    econ  = [n for n in news if n["category"] == "econ"][:5]
    intl  = [n for n in news if n["category"] == "intl"][:5]

    top = news[0] if news else {"title": "每日新闻精选", "summary": "", "link": ""}
    now_hm = datetime.now(TZ_SH).strftime("%H:%M")

    # ── 头条卡片（已移除图片区域） ──
    headline_card = (
        f'<div style="background:#ffffff;margin:16px;border-radius:12px;padding:16px 20px;">'
        # 红点 + BREAKING
        f'<div style="margin-bottom:8px;">'
        f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#d93025;vertical-align:middle;"></span> '
        f'<span style="font-size:12px;color:#666;">BREAKING · {today_str} {now_hm}</span>'
        f'</div>'
        # 标题
        f'<h2 style="margin:0 0 8px;font-size:18px;color:#111;font-weight:600;">{escape(top["title"])}</h2>'
        # 摘要
        f'<p style="margin:0;font-size:13px;color:#666;line-height:1.5;">{escape(top["summary"])}</p>'
        f'</div>'
    )

    # ── 板块内新闻条目（table 替代 flex，保留参考设计风格） ──
    def news_item(idx, item, color, is_last=False):
        t = escape(item["title"])
        d = escape(item["summary"])
        l = item.get("link", "")
        mb = "" if is_last else "margin-bottom:12px;"
        # 圆形序号 badge
        badge = (
            f'<span style="display:inline-block;width:22px;height:22px;line-height:22px;'
            f'text-align:center;border-radius:50%;background:{color};color:#ffffff;'
            f'font-size:12px;font-weight:bold;vertical-align:middle;">{idx}</span>'
        )
        # 标题带链接
        if l:
            title_html = f'<a href="{escape(l)}" style="color:#111;text-decoration:none;font-size:14px;font-weight:500;">{t}</a>'
        else:
            title_html = f'<span style="font-size:14px;font-weight:500;color:#111;">{t}</span>'
        return (
            f'<table style="width:100%;{mb}border:none;border-collapse:collapse;" border="0" cellspacing="0" cellpadding="0"><tr>'
            f'<td style="vertical-align:top;width:32px;padding:4px 0;border:none;">{badge}</td>'
            f'<td style="padding:0 0 0 12px;vertical-align:top;border:none;">'
            f'<p style="margin:0 0 4px;">{title_html}</p>'
            f'<p style="margin:0;font-size:12px;color:#666;line-height:1.5;">{d}</p>'
            f'</td></tr></table>'
        )

    svg_tech = '<svg width="16" height="16" viewBox="0 0 24 24" fill="#3B5BDB"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>'
    svg_econ = '<svg width="16" height="16" viewBox="0 0 24 24" fill="#2E7D32"><path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/></svg>'
    svg_intl = '<svg width="16" height="16" viewBox="0 0 24 24" fill="#C74B15"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>'

    def news_section(svg_icon, title, color, items):
        rows = ""
        for i, it in enumerate(items, 1):
            rows += news_item(i, it, color, is_last=(i == len(items)))
        return (
            f'<div style="background:#ffffff;margin:16px;border-radius:12px;padding:16px 20px;">'
            # 板块标题
            f'<div style="margin-bottom:16px;">'
            f'<span style="font-size:16px;color:{color};font-weight:600;">{svg_icon} {title}</span>'
            f'</div>'
            # 分隔线
            f'<div style="border-top:1px solid #f0f0f0;padding-top:12px;">'
            f'{rows}'
            f'</div>'
            f'</div>'
        )

    html = (
        f'<section style="max-width:677px;margin:0 auto;background:#f9f9f9;padding-top:8px;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',\'Microsoft YaHei\',sans-serif;font-size:15px;line-height:1.6;">'
        # 头条卡片
        f'{headline_card}'
        # 科技
        f'{news_section(svg_tech, "科技新闻", "#3B5BDB", tech)}'
        # 经济
        f'{news_section(svg_econ, "经济新闻", "#2E7D32", econ)}'
        # 国际
        f'{news_section(svg_intl, "国际局势", "#C74B15", intl)}'
        # 页脚
        f'<div style="text-align:center;padding:20px 16px;font-size:12px;color:#666;">'
        f'<p style="margin:0 0 4px;">每日新闻精选 · GLOBAL NEWS NETWORK</p>'
        f'<p style="margin:0;">© 2026 Global News Network. Disclaimer: AI-curated for informational purposes.</p>'
        f'</div>'
        f'</section>'
    )
    return html

# ── 主流程 ──

def main():
    now = datetime.now(TZ_SH)
    today_str = now.strftime("%Y年%m月%d日")
    no_send = "--no-send" in sys.argv
    wx_mode = "--wx" in sys.argv

    print(f"📡 [{now.strftime('%H:%M')}] 开始采集新闻...")

    cfg = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}
    all_news = []

    for src in cfg.get("rss", []):
        print(f"  → {src['label']}...", end=" ", flush=True)
        items = fetch_rss(src["url"], src["label"], src["category"])
        print(f"{len(items)} 条")
        all_news.extend(items)

    for sr in cfg.get("search", []):
        print(f"  → 搜索补充 ({sr['category']})...", end=" ", flush=True)
        items = search_prosearch(sr["keyword"], sr["category"], sr.get("max_results", 6))
        print(f"{len(items)} 条")
        all_news.extend(items)

    seen, deduped = set(), []
    for n in all_news:
        k = n["title"][:50].lower().strip()
        if k and k not in seen: seen.add(k); deduped.append(n)

    print(f"\n📊 去重后共 {len(deduped)} 条新闻")

    top_title = deduped[0]["title"] if deduped else "每日新闻精选"
    hero_text = top_title[:20] + ("..." if len(top_title) > 20 else "")
    print(f"🖼️ 生成 Hero 图: {hero_text}")
    hero_b64 = generate_hero(hero_text, today_str)

    OUTPUT_DIR.mkdir(exist_ok=True)
    date_tag = now.strftime('%Y%m%d')

    if wx_mode:
        html = build_html_wx(deduped, today_str, hero_b64)
        html_file = OUTPUT_DIR / f"news_wx_{date_tag}.html"
        html_file.write_text(html, encoding="utf-8")
        print(f"💾 公众号版 HTML 已保存: {html_file}")
        if not no_send:
            subj = f"每日新闻精选 · {now.strftime('%Y-%m-%d')}"
            print("[send email]...")
            r = subprocess.run(["python3", str(SEND_SCRIPT), subj, str(html_file), str(html_file)], capture_output=True, text=True, timeout=60)
            print(r.stdout[:300])
            if r.stderr: print(r.stderr[:200], file=sys.stderr)
        return

    html = build_html(deduped, today_str, hero_b64, top_title)
    html_file = OUTPUT_DIR / f"news_{date_tag}.html"
    html_file.write_text(html, encoding="utf-8")
    print(f"💾 HTML 已保存: {html_file}")

    if not no_send:
        subj = f"每日新闻精选 · {now.strftime('%Y-%m-%d')}"
        print(f"\n✉️  发送邮件...")
        r = subprocess.run(["python3", str(SEND_SCRIPT), subj, str(html_file), str(html_file)], capture_output=True, text=True, timeout=60)
        print(r.stdout[:300])
        if r.stderr: print(r.stderr[:200], file=sys.stderr)
    else:
        print("\n⏭️  --no-send 模式")

if __name__ == "__main__":
    main()
