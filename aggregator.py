#!/usr/bin/env python3
"""
Resilient Zero-Token Hourly News Aggregator
===========================================
Pure Python standard library (zero external dependencies, zero LLM tokens).
Parses RSS/Atom feeds from high-trust Persian and international news sources,
normalizes metadata, deduplicates entries, and outputs clean Markdown files
and a lightweight static web dashboard.

Supported Sources:
- BBC Persian (BBC فارسی)
- Radio Farda (رادیو فردا)
- Iran International (ایران اینترنشنال)
- Euronews Persian (یورونیوز فارسی)
- DW Persian (دویچه‌وله فارسی)
- Reuters Wire (رویترز)
- AP News Wire (اسوشیتد پرس)
- Hacker News (اخبار فناوری و برنامه‌نویسی)
"""

import os
import sys
import json
import re
import html
import hashlib
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# Constants & Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEWS_DIR = os.path.join(BASE_DIR, "news")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
MAX_STATE_ENTRIES = 10000
FEED_TIMEOUT = 12  # seconds per feed fetch
MAX_ITEMS_PER_FEED = 25

# Timezones: UTC and Tehran (IRST = UTC+3:30)
TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30), name="IRST")

# News Sources Catalog
SOURCES = [
    {
        "id": "bbc_persian",
        "name": "BBC Persian",
        "name_fa": "بی‌بی‌سی فارسی",
        "category": "persian",
        "url": "https://feeds.bbci.co.uk/persian/rss.xml",
        "format": "rss",
        "rtl": True
    },
    {
        "id": "radio_farda",
        "name": "Radio Farda",
        "name_fa": "رادیو فردا",
        "category": "persian",
        "url": "https://www.radiofarda.com/api/zrttpol-vomx-tpeoogpi",
        "format": "rss",
        "rtl": True
    },
    {
        "id": "iran_intl",
        "name": "Iran International",
        "name_fa": "ایران اینترنشنال",
        "category": "persian",
        "url": "https://www.iranintl.com/feed",
        "format": "rss",
        "rtl": True
    },
    {
        "id": "euronews_persian",
        "name": "Euronews Persian",
        "name_fa": "یورونیوز فارسی",
        "category": "persian",
        "url": "https://fa.euronews.com/rss",
        "format": "rss",
        "rtl": True
    },
    {
        "id": "dw_persian",
        "name": "DW Persian",
        "name_fa": "دویچه‌وله فارسی",
        "category": "persian",
        "url": "https://rss.dw.com/xml/rss-per-all",
        "format": "rss",
        "rtl": True
    },
    {
        "id": "reuters_wire",
        "name": "Reuters Wire",
        "name_fa": "خبرگزاری رویترز",
        "category": "wire",
        "url": "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US&gl=US&ceid=US:en",
        "format": "rss",
        "rtl": False
    },
    {
        "id": "ap_news_wire",
        "name": "AP News Wire",
        "name_fa": "اسوشیتد پرس",
        "category": "wire",
        "url": "https://news.google.com/rss/search?q=site:apnews.com&hl=en-US&gl=US&ceid=US:en",
        "format": "rss",
        "rtl": False
    },
    {
        "id": "hacker_news",
        "name": "Hacker News",
        "name_fa": "هکر نیوز (تکنولوژی)",
        "category": "tech",
        "url": "https://hnrss.org/frontpage",
        "format": "rss",
        "rtl": False
    }
]

CATEGORY_METADATA = {
    "persian": {
        "title": "اخبار فارسی (Persian News)",
        "desc": "مهم‌ترین تحولات ایران و جهان از منابع معتبر فارسی",
        "rtl": True
    },
    "wire": {
        "title": "اخبار بین‌الملل و خبرگزاری‌های مادر (Global Wire)",
        "desc": "گزارش‌های فوری بین‌المللی از رویترز و اسوشیتد پرس",
        "rtl": False
    },
    "tech": {
        "title": "فناوری و مهندسی نرم‌افزار (Tech & Hacker News)",
        "desc": "عناوین برتر جامعه متن‌باز و اکوسیستم فناوری از Hacker News",
        "rtl": False
    }
}


def clean_html(text: str) -> str:
    """Remove HTML tags, decode entities, and normalize whitespace."""
    if not text:
        return ""
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities (&quot;, &amp;, etc.)
    cleaned = html.unescape(cleaned)
    # Remove repeated whitespaces and newlines
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def parse_date(date_str: str) -> datetime:
    """Parse RFC 822 or ISO 8601 date strings to UTC datetime."""
    if not date_str:
        return datetime.now(timezone.utc)
    date_str = date_str.strip()
    try:
        # RFC 822 format (common in RSS 2.0)
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    try:
        # ISO 8601 format (common in Atom)
        iso_clean = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    return datetime.now(timezone.utc)


def compute_article_hash(title: str, link: str, guid: str = "") -> str:
    """Compute a deterministic SHA-256 hash for deduplication."""
    # Use guid if available, otherwise link and normalized title
    key = guid.strip() or f"{link.strip()}|{title.strip()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def fetch_and_parse_feed(source: dict) -> list[dict]:
    """Fetch and parse RSS/Atom feed with resilience and zero dependencies."""
    articles = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"
    }
    req = urllib.request.Request(source["url"], headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=FEED_TIMEOUT) as resp:
            content = resp.read()
    except Exception as e:
        print(f"  [WARN] Failed to fetch {source['name']}: {e}", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(content)
    except Exception as e:
        print(f"  [WARN] XML parse error for {source['name']}: {e}", file=sys.stderr)
        return []

    # Namespace maps for Atom and Dublin Core
    atom_ns = "{http://www.w3.org/2005/Atom}"
    dc_ns = "{http://purl.org/dc/elements/1.1/}"

    # Try RSS 2.0 / RDF items first
    items = root.findall(".//item")
    is_atom = False
    if not items:
        # Fallback to Atom entry
        items = root.findall(f".//{atom_ns}entry")
        is_atom = True

    for item in items[:MAX_ITEMS_PER_FEED]:
        try:
            if not is_atom:
                # RSS / RDF parsing
                title_elem = item.find("title")
                title = clean_html(title_elem.text if title_elem is not None else "")

                link_elem = item.find("link")
                link = (link_elem.text if link_elem is not None else "").strip()

                desc_elem = item.find("description")
                summary = clean_html(desc_elem.text if desc_elem is not None else "")

                guid_elem = item.find("guid")
                guid = (guid_elem.text if guid_elem is not None else link).strip()

                pub_elem = item.find("pubDate")
                if pub_elem is None or not pub_elem.text:
                    pub_elem = item.find(f"{dc_ns}date")
                pub_str = pub_elem.text if pub_elem is not None else ""
                published_at = parse_date(pub_str)
            else:
                # Atom parsing
                title_elem = item.find(f"{atom_ns}title")
                title = clean_html(title_elem.text if title_elem is not None else "")

                link_elem = item.find(f"{atom_ns}link")
                link = ""
                if link_elem is not None:
                    link = link_elem.attrib.get("href", link_elem.text or "").strip()

                summary_elem = item.find(f"{atom_ns}summary")
                if summary_elem is None:
                    summary_elem = item.find(f"{atom_ns}content")
                summary = clean_html(summary_elem.text if summary_elem is not None else "")

                id_elem = item.find(f"{atom_ns}id")
                guid = (id_elem.text if id_elem is not None else link).strip()

                pub_elem = item.find(f"{atom_ns}published")
                if pub_elem is None or not pub_elem.text:
                    pub_elem = item.find(f"{atom_ns}updated")
                pub_str = pub_elem.text if pub_elem is not None else ""
                published_at = parse_date(pub_str)

            if not title or not link:
                continue

            # Truncate summary if excessively long for clean Markdown presentation
            if len(summary) > 320:
                summary = summary[:317] + "..."

            article_hash = compute_article_hash(title, link, guid)

            articles.append({
                "hash": article_hash,
                "title": title,
                "link": link,
                "summary": summary,
                "source_id": source["id"],
                "source_name": source["name"],
                "source_name_fa": source["name_fa"],
                "category": source["category"],
                "published_at": published_at.isoformat(),
                "published_epoch": int(published_at.timestamp()),
                "rtl": source["rtl"]
            })
        except Exception as e:
            continue

    return articles


def load_state() -> dict:
    """Load previously seen article hashes from state.json."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"seen_hashes": [], "last_run_utc": None}


def save_state(state: dict):
    """Save seen hashes, pruning to MAX_STATE_ENTRIES to prevent unbounded growth."""
    if len(state["seen_hashes"]) > MAX_STATE_ENTRIES:
        state["seen_hashes"] = state["seen_hashes"][-MAX_STATE_ENTRIES:]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def format_markdown_article(article: dict) -> str:
    """Format a single article entry into clean Markdown."""
    dt_utc = datetime.fromisoformat(article["published_at"])
    dt_tehran = dt_utc.astimezone(TEHRAN_TZ)

    utc_str = dt_utc.strftime("%H:%M UTC")
    tehran_str = dt_tehran.strftime("%H:%M IRST")

    rtl_attr = ' dir="rtl"' if article["rtl"] else ""
    title_display = f"[{article['title']}]({article['link']})"
    badge = f"`{article['source_name_fa']}`" if article["rtl"] else f"`{article['source_name']}`"
    time_badge = f"`{tehran_str}` / `{utc_str}`"

    md = f"- **{badge}** {title_display} — {time_badge}\n"
    if article["summary"]:
        # If RTL, wrap in blockquote or block
        md += f"  > {article['summary']}\n"
    return md


def generate_hourly_markdown(now_utc: datetime, grouped_articles: dict) -> str:
    """Generate the markdown content for news/YYYY-MM-DD/HH-00.md."""
    now_tehran = now_utc.astimezone(TEHRAN_TZ)
    date_str_utc = now_utc.strftime("%Y-%m-%d")
    hour_str_utc = now_utc.strftime("%H:00 UTC")
    tehran_str = now_tehran.strftime("%Y-%m-%d %H:%M IRST")

    md = f"# 📡 بولتن خبری ساعت {now_utc.strftime('%H:00')} UTC ({now_tehran.strftime('%H:00')} تهران)\n\n"
    md += f"**تاریخ انتشار:** `{tehran_str}` | `{date_str_utc} {hour_str_utc}`\n\n"
    md += "> این بولتن به صورت تمام‌اتوماتیک و **بدون مصرف توکن هوش مصنوعی (Zero-LLM-Cost)** توسط پایپ‌لاین سبک پایتون جمع‌آوری و منتشر شده است.\n\n"
    md += "---\n\n"

    for cat_key, cat_meta in CATEGORY_METADATA.items():
        items = grouped_articles.get(cat_key, [])
        md += f"## {cat_meta['title']}\n"
        md += f"*{cat_meta['desc']}*\n\n"
        if not items:
            md += "*در این ساعت خبر جدیدی در این بخش ثبت نشد.*\n\n"
        else:
            for item in items:
                md += format_markdown_article(item)
            md += "\n"

    md += "---\n"
    md += "🔗 **دسترسی سریع:** [صفحه اصلی](../../index.md) | [آخرین اخبار (Latest)](../latest.md) | [سورس مخزن در گیت‌هاب](https://github.com/)\n"
    return md


def generate_latest_markdown(now_utc: datetime, grouped_articles: dict) -> str:
    """Generate the rolling news/latest.md file (compact, high-speed digest)."""
    now_tehran = now_utc.astimezone(TEHRAN_TZ)
    date_str_utc = now_utc.strftime("%Y-%m-%d %H:%M UTC")
    tehran_str = now_tehran.strftime("%Y-%m-%d %H:%M IRST")

    category_caps = {
        "persian": 25,
        "wire": 15,
        "tech": 15
    }

    md = "# ⚡ آخرین اخبار لحظه‌ای (Latest Rolling News)\n\n"
    md += f"**آخرین به‌روزرسانی:** `{tehran_str}` | `{date_str_utc}`\n\n"
    md += "پایگاه خبری بدون سانسور و تاب‌آور در شرایط اینترنت ملی. متن کم‌حجم برای دسترسی فوق سریع در شرایط اختلال شدید شبکه.\n\n"
    md += "---\n\n"

    for cat_key, cat_meta in CATEGORY_METADATA.items():
        items = grouped_articles.get(cat_key, [])
        cap = category_caps.get(cat_key, 20)
        display_items = items[:cap]

        md += f"## {cat_meta['title']}\n\n"
        if not display_items:
            md += "*خبری ثبت نشده است.*\n\n"
        else:
            for item in display_items:
                md += format_markdown_article(item)
            md += "\n"

    md += "---\n"
    md += "📂 [آرشیو ساعت‌به‌ساعت اخبار](../index.md) | 🌐 [مشاهده نسخه وب سبک](../public/index.html)\n"
    return md


def generate_index_markdown(now_utc: datetime, recent_hourly_files: list[str], top_articles: list[dict]) -> str:
    """Generate the root index.md archive index."""
    now_tehran = now_utc.astimezone(TEHRAN_TZ)
    tehran_str = now_tehran.strftime("%Y-%m-%d %H:%M IRST")

    md = "# 🌐 پایگاه خبری تاب‌آور و مستقل (Resilient Zero-Token News Aggregator)\n\n"
    md += "سامانه مانیتورینگ خودکار اخبار از منابع مستقل فارسی و خبرگزاری‌های مادر بین‌المللی با **هزینه صفر (Zero LLM Tokens)** و سازگار با محدودیت‌های شدید اینترنت ملی در ایران.\n\n"
    md += f"⏱ **وضعیت پایپ‌لاین:** فعال | **آخرین سینک:** `{tehran_str}`\n\n"
    md += "### 🚀 راه‌های دسترسی فوق سریع در شرایط فیلترینگ و اینترنت ملی:\n"
    md += "1. **متن خام سبک (Raw Markdown):** دریافت مستقیم فایل [`news/latest.md`](news/latest.md) از طریق `raw.githubusercontent.com` با حجم کمتر از ۱۵ کیلوبایت.\n"
    md += "2. **نسخه وب ایستا (Vercel / GitHub Pages):** مشاهده داشبورد بدون تحریم روی سرورهای ابری با پهنای باند سبک.\n"
    md += "3. **سینک محلی گیت (Git CLI / SSH):** یک بار اجرای دستور `git pull` حتی با سرعت 10kbps برای دریافت کل آرشیو و مطالعه آفلاین در ابزارهایی مانند Obsidian.\n\n"
    md += "---\n\n"

    md += "## 📌 مهم‌ترین عناوین این ساعت\n\n"
    if top_articles:
        for it in top_articles[:15]:
            md += format_markdown_article(it)
    else:
        md += "*عنوانی یافت نشد.*\n"

    md += "\n---\n\n"
    md += "## 🗄 آرشیو گزارش‌های ساعتی (Hourly Archive)\n\n"
    if recent_hourly_files:
        for rel_path in recent_hourly_files[:48]:  # last 48 hours
            # e.g. news/2026-09-29/14-00.md
            parts = rel_path.replace("\\", "/").split("/")
            if len(parts) >= 3:
                date_part = parts[1]
                hour_part = parts[2].replace(".md", "")
                md += f"- 📅 [{date_part} - ساعت {hour_part}]({rel_path})\n"
            else:
                md += f"- [{rel_path}]({rel_path})\n"
    else:
        md += "*آرشیوی موجود نیست.*\n"

    md += "\n---\n"
    md += "سازمان‌دهی شده بر اساس UTC و ساعت رسمی ایران | توسعه‌یافته برای شرایط اضطراری قطع اینترنت.\n"
    return md


def generate_static_html(now_utc: datetime, grouped_articles: dict) -> str:
    """Generate a lightweight, zero-dependency, RTL-friendly static HTML dashboard."""
    now_tehran = now_utc.astimezone(TEHRAN_TZ)
    tehran_str = now_tehran.strftime("%Y-%m-%d %H:%M IRST")
    utc_str = now_utc.strftime("%Y-%m-%d %H:%M UTC")

    # Serialize articles for client-side search/filter
    all_articles = []
    for cat, items in grouped_articles.items():
        all_articles.extend(items)

    articles_json = json.dumps(all_articles, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>رادار خبری مستقل | Resilient News Dashboard</title>
  <style>
    :root {{
      --bg: #0d1117;
      --card-bg: #161b22;
      --border: #30363d;
      --text: #c9d1d9;
      --text-muted: #8b949e;
      --accent: #58a6ff;
      --accent-badge: #1f6feb;
      --persian-tag: #238636;
      --wire-tag: #8957e5;
      --tech-tag: #d29922;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Vazirmatn", Tahoma, sans-serif;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: var(--font-family);
      line-height: 1.6;
      padding: 16px;
    }}
    .container {{
      max-width: 960px;
      margin: 0 auto;
    }}
    header {{
      padding: 20px 0;
      border-bottom: 1px solid var(--border);
      margin-bottom: 20px;
    }}
    h1 {{
      font-size: 1.6rem;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .meta-bar {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: 8px;
    }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: 600;
    }}
    .badge-live {{ background: rgba(35, 134, 54, 0.2); color: #3fb950; border: 1px solid #238636; }}
    .badge-raw {{ background: rgba(88, 166, 255, 0.15); color: #58a6ff; }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 20px;
      align-items: center;
    }}
    .search-box {{
      flex: 1;
      min-width: 240px;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 12px;
      color: var(--text);
      font-size: 0.9rem;
    }}
    .search-box:focus {{ outline: none; border-color: var(--accent); }}
    .tab-btn {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.85rem;
      transition: all 0.2s;
    }}
    .tab-btn.active, .tab-btn:hover {{
      background: var(--accent-badge);
      color: #fff;
      border-color: var(--accent);
    }}
    .news-grid {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .news-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px 16px;
      transition: border-color 0.2s;
    }}
    .news-card:hover {{ border-color: var(--accent); }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
      margin-bottom: 6px;
    }}
    .source-tag {{
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      white-space: nowrap;
    }}
    .tag-persian {{ background: rgba(35, 134, 54, 0.25); color: #7ee787; }}
    .tag-wire {{ background: rgba(137, 87, 229, 0.25); color: #d2a8ff; }}
    .tag-tech {{ background: rgba(210, 153, 34, 0.25); color: #f0883e; }}
    .news-title {{
      font-size: 1rem;
      font-weight: 600;
      color: #58a6ff;
      text-decoration: none;
      flex: 1;
    }}
    .news-title:hover {{ text-decoration: underline; }}
    .news-summary {{
      font-size: 0.88rem;
      color: var(--text-muted);
      margin-top: 6px;
    }}
    .card-footer {{
      margin-top: 8px;
      font-size: 0.75rem;
      color: var(--text-muted);
      display: flex;
      gap: 12px;
    }}
    .ltr {{ direction: ltr; text-align: left; }}
    footer {{
      margin-top: 40px;
      padding: 20px 0;
      border-top: 1px solid var(--border);
      font-size: 0.8rem;
      color: var(--text-muted);
      text-align: center;
    }}
    footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>📡 رادار اخبار لحظه‌ای و تاب‌آور</h1>
      <div class="meta-bar">
        <span class="badge badge-live">● به‌روزرسانی زنده ساعتی</span>
        <span>تهران: <strong>{tehran_str}</strong></span>
        <span>UTC: <strong>{utc_str}</strong></span>
        <a class="badge badge-raw" href="../news/latest.md" target="_blank">📄 نسخه کم‌حجم Markdown</a>
      </div>
    </header>

    <div class="controls">
      <input type="text" id="searchInput" class="search-box" placeholder="جستجو در عناوین و گزارش‌ها...">
      <button class="tab-btn active" data-cat="all">همه اخبار</button>
      <button class="tab-btn" data-cat="persian">فارسی</button>
      <button class="tab-btn" data-cat="wire">خبرگزاری‌های مادر</button>
      <button class="tab-btn" data-cat="tech">فناوری</button>
    </div>

    <div id="newsContainer" class="news-grid"></div>

    <footer>
      <p>طراحی شده برای شرایط اختلال و قطعی شبکه با حداقل مصرف ترافیک | داده‌ها مستقیماً از خوراک‌های رسمی گردآوری شده است.</p>
      <p style="margin-top:6px;"><a href="https://github.com/">مشاهده کد مخزن در GitHub</a> | Zero-LLM Cost Architecture</p>
    </footer>
  </div>

  <script>
    const articles = {articles_json};
    let currentCategory = 'all';
    let searchQuery = '';

    function render() {{
      const container = document.getElementById('newsContainer');
      const filtered = articles.filter(a => {{
        const matchCat = currentCategory === 'all' || a.category === currentCategory;
        const matchSearch = !searchQuery || 
          a.title.toLowerCase().includes(searchQuery) || 
          (a.summary && a.summary.toLowerCase().includes(searchQuery)) ||
          a.source_name.toLowerCase().includes(searchQuery) ||
          a.source_name_fa.includes(searchQuery);
        return matchCat && matchSearch;
      }});

      if (filtered.length === 0) {{
        container.innerHTML = '<div style="text-align:center; padding: 40px; color: var(--text-muted);">موردی یافت نشد.</div>';
        return;
      }}

      container.innerHTML = filtered.map(a => {{
        const tagClass = 'tag-' + a.category;
        const ltrClass = a.rtl ? '' : 'ltr';
        const srcLabel = a.rtl ? a.source_name_fa : a.source_name;
        const pubDate = new Date(a.published_at);
        const timeStr = pubDate.toLocaleTimeString('fa-IR', {{ hour: '2-digit', minute: '2-digit' }});

        return `
          <article class="news-card ${{ltrClass}}">
            <div class="card-header">
              <a href="${{a.link}}" target="_blank" rel="noopener noreferrer" class="news-title">${{a.title}}</a>
              <span class="source-tag ${{tagClass}}">${{srcLabel}}</span>
            </div>
            ${{a.summary ? `<p class="news-summary">${{a.summary}}</p>` : ''}}
            <div class="card-footer">
              <span>ساعت انتشار: ${{timeStr}}</span>
              <a href="${{a.link}}" target="_blank" rel="noopener noreferrer" style="color:var(--accent); text-decoration:none;">لینک منبع ↗</a>
            </div>
          </article>
        `;
      }}).join('');
    }}

    document.querySelectorAll('.tab-btn').forEach(btn => {{
      btn.addEventListener('click', (e) => {{
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentCategory = e.target.getAttribute('data-cat');
        render();
      }});
    }});

    document.getElementById('searchInput').addEventListener('input', (e) => {{
      searchQuery = e.target.value.trim().toLowerCase();
      render();
    }});

    render();
  </script>
</body>
</html>
"""
    return html_content


def scan_recent_hourly_files() -> list[str]:
    """Scan the news/ directory and return all hourly files sorted newest first."""
    files = []
    if not os.path.exists(NEWS_DIR):
        return []
    for root, _, filenames in os.walk(NEWS_DIR):
        for f in filenames:
            if f.endswith(".md") and f != "latest.md":
                rel = os.path.relpath(os.path.join(root, f), BASE_DIR)
                files.append(rel)
    files.sort(reverse=True)
    return files


def main():
    print(f"=== Resilient Zero-Token News Aggregator ===")
    now_utc = datetime.now(timezone.utc)
    print(f"Start time: {now_utc.isoformat()}")

    # Ensure directories exist
    os.makedirs(NEWS_DIR, exist_ok=True)
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    date_dir = os.path.join(NEWS_DIR, now_utc.strftime("%Y-%m-%d"))
    os.makedirs(date_dir, exist_ok=True)

    # Load state
    state = load_state()
    seen_set = set(state.get("seen_hashes", []))
    print(f"Loaded {len(seen_set)} previously seen article hashes from state.json")

    # Ingest from all sources
    all_fetched = []
    new_in_this_run = []

    for src in SOURCES:
        print(f"Fetching {src['name']} ({src['category']})...")
        items = fetch_and_parse_feed(src)
        print(f"  -> Got {len(items)} items")
        all_fetched.extend(items)

    # Sort all items newest first
    all_fetched.sort(key=lambda x: x["published_epoch"], reverse=True)

    # Deduplicate and categorize
    grouped_current_run = {"persian": [], "wire": [], "tech": []}
    grouped_all_fresh = {"persian": [], "wire": [], "tech": []}

    new_hashes_to_add = []

    for item in all_fetched:
        cat = item["category"]
        grouped_all_fresh[cat].append(item)

        if item["hash"] not in seen_set:
            new_in_this_run.append(item)
            grouped_current_run[cat].append(item)
            new_hashes_to_add.append(item["hash"])
            seen_set.add(item["hash"])

    print(f"Deduplication complete: {len(new_in_this_run)} newly discovered articles in this run")

    # If this is the very first run, populate current run with the fresh items
    active_grouped = grouped_current_run if new_in_this_run else grouped_all_fresh

    # 1. Generate hourly file: news/YYYY-MM-DD/HH-00.md
    hourly_filename = f"{now_utc.strftime('%H')}-00.md"
    hourly_path = os.path.join(date_dir, hourly_filename)
    hourly_md = generate_hourly_markdown(now_utc, active_grouped)
    with open(hourly_path, "w", encoding="utf-8") as f:
        f.write(hourly_md)
    print(f"Saved hourly snapshot: {hourly_path}")

    # 2. Generate rolling latest: news/latest.md
    latest_path = os.path.join(NEWS_DIR, "latest.md")
    latest_md = generate_latest_markdown(now_utc, grouped_all_fresh)
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(latest_md)
    print(f"Saved latest snapshot: {latest_path}")

    # 3. Generate root index.md
    recent_files = scan_recent_hourly_files()
    index_md = generate_index_markdown(now_utc, recent_files, all_fetched[:20])
    index_path = os.path.join(BASE_DIR, "index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_md)
    print(f"Saved index file: {index_path}")

    # 4. Generate public/index.html (static site for Vercel / GitHub Pages)
    html_content = generate_static_html(now_utc, grouped_all_fresh)
    html_path = os.path.join(PUBLIC_DIR, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Saved static HTML dashboard: {html_path}")

    # 5. Generate public/latest.json (machine readable feed)
    json_path = os.path.join(PUBLIC_DIR, "latest.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at_utc": now_utc.isoformat(),
            "generated_at_tehran": now_utc.astimezone(TEHRAN_TZ).isoformat(),
            "article_count": len(all_fetched),
            "articles": all_fetched
        }, f, indent=2, ensure_ascii=False)
    print(f"Saved machine-readable JSON: {json_path}")

    # Update and save state
    state["seen_hashes"].extend(new_hashes_to_add)
    state["last_run_utc"] = now_utc.isoformat()
    save_state(state)
    print("State updated successfully.")
    print("=== Aggregator run completed cleanly ===")


if __name__ == "__main__":
    main()
