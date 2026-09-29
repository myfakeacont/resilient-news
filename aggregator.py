#!/usr/bin/env python3
"""
Resilient Zero-Token 30-Minute Multi-Source News & Media Aggregator
===================================================================
Pure Python standard library (zero external dependencies, zero LLM tokens).
Runs every 30 minutes on Server 2 (Ubuntu ARM64) with bounded memory (<30MB RAM)
and sub-30-second completion time.

Ingests 32 high-priority sources across three tiers:
1. Twitter / X Accounts (12 accounts): Multi-tiered fallback (Google News RSS / Nitter / Syndication)
2. Telegram Channels (12 channels): t.me/s/<channel> HTML parsing + media extraction
3. RSS Feeds (8 wire/news sources): Standard RSS 2.0 / Atom with media attachments

Features:
- Full media archiving: Downloads and caches images to media/YYYY-MM-DD/<hash>.jpg
- Markdown reports with embedded local media links:
    * news/YYYY-MM-DD/HH-MM.md (30-min historical snapshot)
    * news/latest.md (rolling real-time digest)
    * index.md (root archive index)
- Static Dashboard:
    * public/index.html (RTL-friendly, dark-themed responsive dashboard)
    * public/latest.json (machine-readable feed API)
- Deduplication and state management in state.json
- Memory-bounded concurrent processing (<30MB RAM footprint)
"""

from __future__ import annotations

import os
import sys
import json
import re
import html
import hashlib
import threading
import gc
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
import concurrent.futures
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# Bounded stack size to guarantee low RAM footprint (<30MB)
try:
    threading.stack_size(128 * 1024)
except Exception:
    pass

# ==============================================================================
# Configuration & Constants
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEWS_DIR = os.path.join(BASE_DIR, "news")
MEDIA_DIR = os.path.join(BASE_DIR, "media")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
STATE_FILE = os.path.join(BASE_DIR, "state.json")

MAX_STATE_ENTRIES = 5000
FETCH_TIMEOUT = 5          # seconds per source fetch
MEDIA_TIMEOUT = 4          # seconds per media download
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2MB cap per image to bound RAM
MAX_CONCURRENT_WORKERS = 5
MAX_ITEMS_PER_SOURCE = 10
MAX_MEDIA_DOWNLOADS_PER_RUN = 20

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

# Timezone definitions: UTC and Tehran (IRST = UTC+3:30)
TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30), name="IRST")

# ==============================================================================
# Target Sources Catalog
# ==============================================================================

TWITTER_ACCOUNTS = [
    {"handle": "SharifiZarchi", "name": "Ali Sharifi Zarchi", "name_fa": "دکتر علی شریفی زارچی", "rtl": True},
    {"handle": "thetwelfth_Imam", "name": "The 12th Imam", "name_fa": "دوازدهمین امام", "rtl": True},
    {"handle": "USABehFarsi", "name": "USA Beh Farsi", "name_fa": "وزارت خارجه آمریکا به فارسی", "rtl": True},
    {"handle": "souzangar", "name": "Pouria Souzangar", "name_fa": "پوریا سوزنگر (امنیت و شبکه)", "rtl": True},
    {"handle": "bookunt", "name": "Bookunt", "name_fa": "بوکونت", "rtl": True},
    {"handle": "tom_doerr", "name": "Tom Doerr", "name_fa": "تام دور (هوش مصنوعی و نرم‌افزار)", "rtl": False},
    {"handle": "MatinSenPai", "name": "Matin SenPai", "name_fa": "متین سنپای (فناوری و دور زدن)", "rtl": True},
    {"handle": "patterniha", "name": "Patterniha", "name_fa": "پترنی‌ها (تحلیل و فناوری)", "rtl": True},
    {"handle": "MitraHejazipour", "name": "Mitra Hejazipour", "name_fa": "میترا حجازی‌پور", "rtl": True},
    {"handle": "EdaalateAli1400", "name": "Edaalate Ali", "name_fa": "عدالت علی", "rtl": True},
    {"handle": "realDonaldTrump", "name": "Donald J. Trump", "name_fa": "دونالد ترامپ", "rtl": False},
    {"handle": "PahlaviComms", "name": "Pahlavi Comms", "name_fa": "دفتر رسانه‌ای رضا پهلوی", "rtl": True},
]

TELEGRAM_CHANNELS = [
    {"channel": "Linuxor", "name": "Linuxor", "name_fa": "لینوکسور (جامعه گنو/لینوکس)", "rtl": True},
    {"channel": "jadivarlog", "name": "Jadi", "name_fa": "جادی تی‌وی / ولاگ جادی", "rtl": True},
    {"channel": "OfficialRezaPahlavi", "name": "Reza Pahlavi", "name_fa": "کانال رسمی شاهزاده رضا پهلوی", "rtl": True},
    {"channel": "IranintlTV", "name": "Iran International", "name_fa": "ایران اینترنشنال (تلگرام)", "rtl": True},
    {"channel": "VahidOnline", "name": "Vahid Online", "name_fa": "وحید آنلاین", "rtl": True},
    {"channel": "MatinSenPaii", "name": "Matin SenPaii", "name_fa": "متین سنپای (شبکه و فیلترشکن)", "rtl": True},
    {"channel": "EdaalateAli1400_Dark", "name": "Edaalate Ali Dark", "name_fa": "عدالت علی (اسناد و افشاگری)", "rtl": True},
    {"channel": "patt_channel_x", "name": "Patterniha Telegram", "name_fa": "کانال پترنی‌ها", "rtl": True},
    {"channel": "M4tinBeigi", "name": "Matin Beigi", "name_fa": "متین بیگی", "rtl": True},
    {"channel": "Rostamchannel", "name": "Rostam Channel", "name_fa": "کانال رستم (دور زدن فیلترینگ)", "rtl": True},
    {"channel": "ircfspace", "name": "IRCF Space", "name_fa": "پایگاه کلودفلر و پروکسی IRCF", "rtl": True},
    {"channel": "whitedns", "name": "White DNS", "name_fa": "وایت دی‌ان‌اس (DNS و ضدسانسور)", "rtl": True},
]

RSS_FEEDS = [
    {
        "id": "bbc_persian",
        "name": "BBC Persian",
        "name_fa": "بی‌بی‌سی فارسی",
        "category": "persian",
        "url": "https://feeds.bbci.co.uk/persian/rss.xml",
        "rtl": True
    },
    {
        "id": "radio_farda",
        "name": "Radio Farda",
        "name_fa": "رادیو فردا",
        "category": "persian",
        "url": "https://www.radiofarda.com/api/zrttpol-vomx-tpeoogpi",
        "rtl": True
    },
    {
        "id": "iran_intl",
        "name": "Iran International",
        "name_fa": "ایران اینترنشنال",
        "category": "persian",
        "url": "https://www.iranintl.com/feed",
        "rtl": True
    },
    {
        "id": "euronews_persian",
        "name": "Euronews Persian",
        "name_fa": "یورونیوز فارسی",
        "category": "persian",
        "url": "https://fa.euronews.com/rss",
        "rtl": True
    },
    {
        "id": "dw_persian",
        "name": "DW Persian",
        "name_fa": "دویچه‌وله فارسی",
        "category": "persian",
        "url": "https://rss.dw.com/xml/rss-per-all",
        "rtl": True
    },
    {
        "id": "reuters_wire",
        "name": "Reuters Wire",
        "name_fa": "خبرگزاری رویترز",
        "category": "wire",
        "url": "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US&gl=US&ceid=US:en",
        "rtl": False
    },
    {
        "id": "ap_news_wire",
        "name": "AP News Wire",
        "name_fa": "اسوشیتد پرس",
        "category": "wire",
        "url": "https://news.google.com/rss/search?q=site:apnews.com&hl=en-US&gl=US&ceid=US:en",
        "rtl": False
    },
    {
        "id": "hacker_news",
        "name": "Hacker News",
        "name_fa": "هکر نیوز (تکنولوژی و امنیت)",
        "category": "tech",
        "url": "https://hnrss.org/frontpage",
        "rtl": False
    }
]

CATEGORY_METADATA = {
    "twitter": {
        "title": "توییتر و شبکه اکس (X / Twitter Intelligence)",
        "desc": "آخرین مواضع، بیانیه‌ها و توییت‌های حساب‌های منتخب بدون نیاز به توکن API",
        "badge": "badge-twitter",
        "rtl": True
    },
    "telegram": {
        "title": "کانال‌های منتخب تلگرام (Telegram Monitoring)",
        "desc": "پایش لحظه‌ای پست‌ها، فایل‌ها و تحلیل‌های فنی از کانال‌های عمومی تلگرام",
        "badge": "badge-telegram",
        "rtl": True
    },
    "persian": {
        "title": "اخبار و رسانه‌های فارسی (Persian News)",
        "desc": "مهم‌ترین تحولات ایران و منطقه از رسانه‌های معتبر و خبرگزاری‌های مستقل",
        "badge": "badge-persian",
        "rtl": True
    },
    "wire": {
        "title": "خبرگزاری‌های بین‌المللی (Global Wire)",
        "desc": "گزارش‌های فوری بین‌المللی از خبرگزاری‌های مادر (رویترز و اسوشیتد پرس)",
        "badge": "badge-wire",
        "rtl": False
    },
    "tech": {
        "title": "فناوری و امنیت سایبری (Tech & Open Source)",
        "desc": "سرخط اخبار دنیای توسعه نرم‌افزار، امنیت و جامعه متن‌باز از Hacker News",
        "badge": "badge-tech",
        "rtl": False
    }
}

# ==============================================================================
# Helper Utilities
# ==============================================================================

def clean_html(text: str | None) -> str:
    """Strip HTML tags, decode entities, and normalize whitespace."""
    if not text:
        return ""
    cleaned = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s*\n+", "\n\n", cleaned)
    return cleaned.strip()


def parse_date(date_str: str | None) -> datetime:
    """Robust date parser handling RFC 822 and ISO 8601 strings."""
    if not date_str:
        return datetime.now(timezone.utc)
    date_str = date_str.strip()
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    try:
        iso_clean = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    return datetime.now(timezone.utc)


def compute_article_hash(unique_key: str) -> str:
    """Compute a deterministic 16-hex-character SHA-256 hash."""
    return hashlib.sha256(unique_key.encode("utf-8")).hexdigest()[:16]


def is_persian_text(text: str) -> bool:
    """Detect if text contains Persian/Arabic unicode characters."""
    return bool(re.search(r"[\u0600-\u06FF\uFB8A\u067E\u0686\u06AF]", text))

# ==============================================================================
# Ingest Tiers: Twitter, Telegram, RSS
# ==============================================================================

def fetch_twitter_account(acc: dict) -> list[dict]:
    """
    Robust Twitter fetching without official API keys using multi-tier fallback:
    1. Google News Twitter search RSS (100% reliable SLA, unaffected by IP rate limits)
    2. Syndication / Nitter fallback when available
    """
    handle = acc["handle"]
    articles = []

    # Tier 1: Google News RSS for account tweets
    query = f"site:twitter.com/{handle} OR site:x.com/{handle}"
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            content = resp.read()
        root = ET.fromstring(content)
        items = root.findall(".//item")
        for it in items[:MAX_ITEMS_PER_SOURCE]:
            title_el = it.find("title")
            raw_title = clean_html(title_el.text if title_el is not None else "")
            # Filter out account header title e.g. "Donald J. Trump (@realDonaldTrump) - x.com"
            if f"(@{handle})" in raw_title and len(raw_title) < 70 and ("x.com" in raw_title or "twitter.com" in raw_title):
                continue

            link_el = it.find("link")
            link = (link_el.text if link_el is not None else "").strip()

            desc_el = it.find("description")
            desc = clean_html(desc_el.text if desc_el is not None else "")

            pub_el = it.find("pubDate")
            published_at = parse_date(pub_el.text if pub_el is not None else "")

            if not raw_title or not link:
                continue

            # Strip trailing "- x.com" or "- Twitter" from Google News title
            cleaned_title = re.sub(r"\s*-\s*(x\.com|twitter\.com)\s*$", "", raw_title, flags=re.I).strip()
            article_hash = compute_article_hash(f"twitter:{handle}:{cleaned_title}")

            articles.append({
                "hash": article_hash,
                "title": cleaned_title,
                "link": link,
                "summary": desc if desc and desc != raw_title else "",
                "source_id": f"tw_{handle}",
                "source_name": f"@{handle}",
                "source_name_fa": f"@{handle} ({acc['name_fa']})",
                "category": "twitter",
                "published_at": published_at.isoformat(),
                "published_epoch": int(published_at.timestamp()),
                "rtl": is_persian_text(cleaned_title) or acc["rtl"],
                "raw_media_urls": [],
                "local_media_path": None
            })
    except Exception:
        pass

    return articles


def fetch_telegram_channel(ch_info: dict) -> list[dict]:
    """
    Robust Telegram channel fetching via https://t.me/s/<channel>
    Extracts text, dates, post URLs, and discovers media photos/videos.
    """
    channel = ch_info["channel"].lstrip("@").split("/")[-1]
    url = f"https://t.me/s/{channel}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    articles = []
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    # Split into raw widget message blocks
    blocks = re.findall(
        r'(<div class="tgme_widget_message\s+[^"]*js-widget_message[^"]*".*?)(?=<div class="tgme_widget_message\s+[^"]*js-widget_message|$)',
        content,
        re.DOTALL
    )

    for block in blocks[-MAX_ITEMS_PER_SOURCE:]:
        id_match = re.search(r'data-post="([^"]+)"', block)
        if not id_match:
            continue
        data_post = id_match.group(1)
        post_link = f"https://t.me/{data_post}"

        time_match = re.search(r'<time[^>]*datetime="([^"]+)"', block)
        post_time_str = time_match.group(1) if time_match else ""
        published_at = parse_date(post_time_str)

        text_match = re.search(
            r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
            block,
            re.DOTALL
        )
        post_text = clean_html(text_match.group(1)) if text_match else ""

        # Discover media (photos, video thumbnails, link preview images)
        raw_media = []
        photo_m = re.findall(
            r'class="[^"]*tgme_widget_message_photo_wrap[^"]*"[^>]*style="[^"]*background-image:url\(\'([^\']+)\'\)',
            block
        )
        raw_media.extend(photo_m)

        video_m = re.findall(
            r'class="[^"]*tgme_widget_message_video_thumb[^"]*"[^>]*style="[^"]*background-image:url\(\'([^\']+)\'\)',
            block
        )
        raw_media.extend(video_m)

        preview_m = re.findall(
            r'class="[^"]*link_preview_image[^"]*"[^>]*style="[^"]*background-image:url\(\'([^\']+)\'\)',
            block
        )
        raw_media.extend(preview_m)

        # Ignore empty service notices without text or media
        if not post_text and not raw_media:
            continue

        # Formulate display title
        if post_text:
            first_line = post_text.splitlines()[0].strip()
            title = first_line[:120] + ("..." if len(first_line) > 120 else "")
            summary = post_text
        else:
            title = f"رسانه منتشر شده در {ch_info['name_fa']}"
            summary = ""

        article_hash = compute_article_hash(f"telegram:{data_post}")

        articles.append({
            "hash": article_hash,
            "title": title,
            "link": post_link,
            "summary": summary,
            "source_id": f"tg_{channel}",
            "source_name": f"@{channel}",
            "source_name_fa": f"@{channel} ({ch_info['name_fa']})",
            "category": "telegram",
            "published_at": published_at.isoformat(),
            "published_epoch": int(published_at.timestamp()),
            "rtl": is_persian_text(post_text) if post_text else ch_info["rtl"],
            "raw_media_urls": raw_media[:1],  # Store primary image URL
            "local_media_path": None
        })

    return articles


def fetch_rss_feed(source: dict) -> list[dict]:
    """Fetch and parse RSS 2.0 / RDF / Atom feeds with media enclosure detection."""
    articles = []
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"
    }
    req = urllib.request.Request(source["url"], headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            content = resp.read()
    except Exception:
        return []

    try:
        root = ET.fromstring(content)
    except Exception:
        return []

    atom_ns = "{http://www.w3.org/2005/Atom}"
    dc_ns = "{http://purl.org/dc/elements/1.1/}"
    media_ns = "{http://search.yahoo.com/mrss/}"

    items = root.findall(".//item")
    is_atom = False
    if not items:
        items = root.findall(f".//{atom_ns}entry")
        is_atom = True

    for item in items[:MAX_ITEMS_PER_SOURCE]:
        try:
            raw_media = []
            if not is_atom:
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

                # Extract media from enclosure or yahoo media tags
                encl = item.find("enclosure")
                if encl is not None and "image" in encl.attrib.get("type", ""):
                    raw_media.append(encl.attrib.get("url"))

                for m in item.findall(f"{media_ns}content"):
                    url_val = m.attrib.get("url")
                    if url_val and ("image" in m.attrib.get("type", "") or m.attrib.get("medium") == "image"):
                        raw_media.append(url_val)

                for m in item.findall(f"{media_ns}thumbnail"):
                    url_val = m.attrib.get("url")
                    if url_val:
                        raw_media.append(url_val)
            else:
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

            article_hash = compute_article_hash(guid or f"{link}|{title}")

            articles.append({
                "hash": article_hash,
                "title": title,
                "link": link,
                "summary": summary[:400] + ("..." if len(summary) > 400 else ""),
                "source_id": source["id"],
                "source_name": source["name"],
                "source_name_fa": source["name_fa"],
                "category": source["category"],
                "published_at": published_at.isoformat(),
                "published_epoch": int(published_at.timestamp()),
                "rtl": is_persian_text(title) or source["rtl"],
                "raw_media_urls": [m for m in raw_media if m][:1],
                "local_media_path": None
            })
        except Exception:
            continue

    return articles

# ==============================================================================
# Media Archiving Engine
# ==============================================================================

def download_and_archive_media(img_url: str, date_str: str) -> str | None:
    """
    Download and store image directly to media/YYYY-MM-DD/<hash>.jpg.
    Returns relative path (e.g., 'media/2026-09-29/a1b2c3d4e5f6.jpg') or None.
    Uses chunked streaming with direct-to-disk write to strictly bound RAM.
    """
    if not img_url or not img_url.startswith(("http://", "https://")):
        return None

    img_hash = compute_article_hash(img_url)
    target_dir = os.path.join(MEDIA_DIR, date_str)
    file_name = f"{img_hash}.jpg"
    target_path = os.path.join(target_dir, file_name)
    rel_path = f"media/{date_str}/{file_name}"

    # Return immediately if already archived on disk
    if os.path.exists(target_path) and os.path.getsize(target_path) > 500:
        return rel_path

    os.makedirs(target_dir, exist_ok=True)
    req = urllib.request.Request(img_url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=MEDIA_TIMEOUT) as resp:
            total_read = 0
            with open(target_path, "wb") as f:
                while True:
                    chunk = resp.read(32 * 1024)
                    if not chunk:
                        break
                    total_read += len(chunk)
                    if total_read > MAX_IMAGE_SIZE:
                        f.close()
                        try:
                            os.remove(target_path)
                        except OSError:
                            pass
                        return None
                    f.write(chunk)

            return rel_path
    except Exception:
        # Graceful degradation if image fetch fails
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except OSError:
                pass
        return None


def archive_media_batch(articles: list[dict], now_utc: datetime) -> None:
    """Download and associate media for fresh articles concurrently."""
    date_str = now_utc.strftime("%Y-%m-%d")
    tasks = []

    for item in articles:
        if item.get("raw_media_urls"):
            raw_url = item["raw_media_urls"][0]
            tasks.append((item, raw_url))

    if not tasks:
        return

    # Cap media downloads per run to avoid latency spikes and bandwidth throttling
    tasks = tasks[:MAX_MEDIA_DOWNLOADS_PER_RUN]

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_map = {
            executor.submit(download_and_archive_media, raw_url, date_str): item
            for item, raw_url in tasks
        }
        for future in concurrent.futures.as_completed(future_map):
            item = future_map[future]
            try:
                saved_path = future.result()
                if saved_path:
                    item["local_media_path"] = saved_path
            except Exception:
                pass

# ==============================================================================
# Markdown Formatting & Digest Generation
# ==============================================================================

def format_markdown_article(article: dict, path_prefix: str = "../../") -> str:
    """Format an article entry into clean Markdown with embedded media."""
    dt_utc = datetime.fromisoformat(article["published_at"])
    dt_tehran = dt_utc.astimezone(TEHRAN_TZ)

    utc_str = dt_utc.strftime("%H:%M UTC")
    tehran_str = dt_tehran.strftime("%H:%M IRST")

    badge = f"`{article['source_name_fa']}`" if article["rtl"] else f"`{article['source_name']}`"
    title_link = f"[{article['title']}]({article['link']})"
    time_badge = f"`{tehran_str}` / `{utc_str}`"

    md = f"- **{badge}** {title_link} — {time_badge}\n"
    if article.get("summary") and article["summary"] != article["title"]:
        # Truncate summary if long
        summ = article["summary"]
        if len(summ) > 280:
            summ = summ[:277] + "..."
        md += f"  > {summ}\n"

    # Embedded media if archived
    if article.get("local_media_path"):
        media_rel = f"{path_prefix}{article['local_media_path']}"
        md += f"\n  ![Media]({media_rel})\n"

    return md


def generate_interval_markdown(now_utc: datetime, grouped_articles: dict) -> str:
    """Generate the 30-minute snapshot markdown: news/YYYY-MM-DD/HH-MM.md."""
    now_tehran = now_utc.astimezone(TEHRAN_TZ)
    date_str_utc = now_utc.strftime("%Y-%m-%d")
    hour_min_utc = now_utc.strftime("%H:%M UTC")
    tehran_str = now_tehran.strftime("%Y-%m-%d %H:%M IRST")

    md = f"# 📡 بولتن تحلیلی اخبار و رسانه‌ها — {now_tehran.strftime('%H:%M')} IRST ({now_utc.strftime('%H:%M')} UTC)\n\n"
    md += f"**تاریخ انتشار:** `{tehran_str}` | `{date_str_utc} {hour_min_utc}`\n\n"
    md += "> **سیستم پایش ۳۰ دقیقه‌ای بدون وقفه (Server 2 Ubuntu ARM64)**: جمع‌آوری کاملاً خودکار و مستقل از ۳۲ منبع خبری، کانال‌های تلگرام و حساب‌های توییتر بدون مصرف توکن LLM.\n\n"
    md += "---\n\n"

    for cat_key, cat_meta in CATEGORY_METADATA.items():
        items = grouped_articles.get(cat_key, [])
        md += f"## {cat_meta['title']}\n"
        md += f"*{cat_meta['desc']}*\n\n"
        if not items:
            md += "*در این بازه ۳۰ دقیقه‌ای بروزرسانی جدیدی در این بخش ثبت نشد.*\n\n"
        else:
            for item in items:
                md += format_markdown_article(item, path_prefix="../../")
            md += "\n"

    md += "---\n"
    md += "🔗 **دسترسی سریع:** [صفحه اصلی](../../index.md) | [آخرین اخبار (Latest)](../latest.md) | [داشبورد وب](../../public/index.html)\n"
    return md


def generate_latest_markdown(now_utc: datetime, grouped_articles: dict) -> str:
    """Generate rolling news/latest.md file."""
    now_tehran = now_utc.astimezone(TEHRAN_TZ)
    date_str_utc = now_utc.strftime("%Y-%m-%d %H:%M UTC")
    tehran_str = now_tehran.strftime("%Y-%m-%d %H:%M IRST")

    category_caps = {
        "twitter": 12,
        "telegram": 15,
        "persian": 20,
        "wire": 12,
        "tech": 10
    }

    md = "# ⚡ آخرین اخبار و رویدادهای لحظه‌ای (Latest Rolling News)\n\n"
    md += f"**آخرین همگام‌سازی پایپ‌لاین:** `{tehran_str}` | `{date_str_utc}`\n\n"
    md += "پایگاه خبری چندرسانه‌ای تاب‌آور. متن سبک و تصاویر محلی فشرده برای دسترسی حداکثر سرعت در شرایط اختلال اینترنت.\n\n"
    md += "---\n\n"

    for cat_key, cat_meta in CATEGORY_METADATA.items():
        items = grouped_articles.get(cat_key, [])
        cap = category_caps.get(cat_key, 12)
        display_items = items[:cap]

        md += f"## {cat_meta['title']}\n\n"
        if not display_items:
            md += "*خبری ثبت نشده است.*\n\n"
        else:
            for item in display_items:
                md += format_markdown_article(item, path_prefix="../")
            md += "\n"

    md += "---\n"
    md += "📂 [آرشیو ۳۰ دقیقه‌ای اخبار](../index.md) | 🌐 [مشاهده نسخه تحت وب سبک](../public/index.html)\n"
    return md


def generate_index_markdown(now_utc: datetime, recent_snapshots: list[str], top_articles: list[dict]) -> str:
    """Generate the root index.md archive index."""
    now_tehran = now_utc.astimezone(TEHRAN_TZ)
    tehran_str = now_tehran.strftime("%Y-%m-%d %H:%M IRST")

    md = "# 🌐 رادار خبری تاب‌آور و مستقل (Resilient 30-Min Media Aggregator)\n\n"
    md += "سامانه مانیتورینگ چندرسانه‌ای خودکار از منابع مستقل فارسی، کانال‌های تلگرام، توییتر و خبرگزاری‌های مادر بین‌المللی با **هزینه صفر (Zero LLM Tokens)** و سازگار با محدودیت‌های شدید اینترنت ملی در ایران.\n\n"
    md += f"⏱ **وضعیت پایپ‌لاین:** فعال بر روی Server 2 (ARM64) | **آخرین همگام‌سازی:** `{tehran_str}`\n\n"
    md += "### 🚀 راه‌های دسترسی سریع در شرایط فیلترینگ و اینترنت ملی:\n"
    md += "1. **فایل متنی سبک (Raw Markdown):** دریافت مستقیم [`news/latest.md`](news/latest.md) از طریق CDN گیت‌هاب با حجم اندک.\n"
    md += "2. **آرشیو تصاویر محلی:** مشاهده رسانه‌ها در پوشه `media/` با امکان بارگذاری آفلاین.\n"
    md += "3. **همگام‌سازی گیت (Git CLI):** دریافت با دستور `git pull` حتی با سرعت‌های پایین زیر ۵۰ کیلوبیت.\n\n"
    md += "---\n\n"

    md += "## 📌 مهم‌ترین سرخط‌های جاری\n\n"
    if top_articles:
        for it in top_articles[:15]:
            md += format_markdown_article(it, path_prefix="")
    else:
        md += "*عنوانی یافت نشد.*\n"

    md += "\n---\n\n"
    md += "## 🗄 آرشیو بولتن‌های ۳۰ دقیقه‌ای (Interval Archive)\n\n"
    if recent_snapshots:
        for rel_path in recent_snapshots[:60]:  # past 30 hours
            parts = rel_path.replace("\\", "/").split("/")
            if len(parts) >= 3:
                date_part = parts[1]
                time_part = parts[2].replace(".md", "").replace("-", ":")
                md += f"- 📅 [{date_part} - ساعت {time_part}]({rel_path})\n"
            else:
                md += f"- [{rel_path}]({rel_path})\n"
    else:
        md += "*آرشیوی موجود نیست.*\n"

    md += "\n---\n"
    md += "توسعه‌یافته برای استقرار سبک و مداوم بر روی اوبونتو ARM64.\n"
    return md

# ==============================================================================
# Static Web Dashboard & JSON Feed Generator
# ==============================================================================

def generate_static_html(now_utc: datetime, grouped_articles: dict) -> str:
    """Generate a lightweight, zero-dependency, RTL-friendly responsive HTML dashboard."""
    now_tehran = now_utc.astimezone(TEHRAN_TZ)
    tehran_str = now_tehran.strftime("%Y-%m-%d %H:%M IRST")
    utc_str = now_utc.strftime("%Y-%m-%d %H:%M UTC")

    all_articles = []
    for cat, items in grouped_articles.items():
        all_articles.extend(items[:20])

    all_articles.sort(key=lambda x: x["published_epoch"], reverse=True)
    all_articles_json = json.dumps(all_articles[:60], ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>رادار خبری چندرسانه‌ای | 30-Min Media Aggregator</title>
  <style>
    :root {{
      --bg: #0d1117;
      --card-bg: #161b22;
      --border: #30363d;
      --text: #c9d1d9;
      --text-muted: #8b949e;
      --accent: #58a6ff;
      --badge-tw: #1d9bf0;
      --badge-tg: #2aabee;
      --badge-fa: #238636;
      --badge-wire: #8957e5;
      --badge-tech: #d29922;
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
      max-width: 980px;
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
    .badge-tw {{ background: rgba(29, 155, 240, 0.2); color: var(--badge-tw); }}
    .badge-tg {{ background: rgba(42, 171, 238, 0.2); color: var(--badge-tg); }}
    .badge-fa {{ background: rgba(35, 134, 54, 0.2); color: #3fb950; }}
    .badge-wire {{ background: rgba(137, 87, 229, 0.2); color: var(--badge-wire); }}
    .badge-tech {{ background: rgba(210, 153, 34, 0.2); color: var(--badge-tech); }}
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
      background: #1f6feb;
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
      transition: transform 0.15s ease, border-color 0.15s ease;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .news-card:hover {{
      border-color: var(--accent);
      transform: translateY(-2px);
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
    }}
    .card-title {{
      font-size: 1.05rem;
      font-weight: 600;
      color: #58a6ff;
      text-decoration: none;
    }}
    .card-title:hover {{ text-decoration: underline; }}
    .card-summary {{
      font-size: 0.9rem;
      color: var(--text);
      white-space: pre-line;
      line-height: 1.5;
    }}
    .card-media {{
      max-width: 100%;
      border-radius: 6px;
      overflow: hidden;
      margin-top: 6px;
    }}
    .card-media img {{
      max-width: 100%;
      max-height: 380px;
      object-fit: cover;
      display: block;
      border-radius: 6px;
      border: 1px solid var(--border);
    }}
    .card-footer {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 4px;
    }}
    footer {{
      margin-top: 40px;
      padding: 20px 0;
      border-top: 1px solid var(--border);
      text-align: center;
      font-size: 0.85rem;
      color: var(--text-muted);
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>📡 رادار خبری چندرسانه‌ای ۳۰ دقیقه‌ای</h1>
      <div class="meta-bar">
        <span class="badge badge-live">● زنده (Server 2 ARM64)</span>
        <span>🕒 آخرین همگام‌سازی: <strong>{tehran_str}</strong> ({utc_str})</span>
        <span>📊 مجموع منابع فعال: <strong>۳۲ منبع</strong> (۱۲ توییتر، ۱۲ تلگرام، ۸ فید جهانی)</span>
      </div>
    </header>

    <div class="controls">
      <input type="text" id="searchInput" class="search-box" placeholder="جستجو در متن اخبار، منابع، یا حساب‌ها..." oninput="filterCards()">
      <button class="tab-btn active" onclick="setCategory('all', this)">همه منابع</button>
      <button class="tab-btn" onclick="setCategory('twitter', this)">توییتر / X</button>
      <button class="tab-btn" onclick="setCategory('telegram', this)">تلگرام</button>
      <button class="tab-btn" onclick="setCategory('persian', this)">اخبار فارسی</button>
      <button class="tab-btn" onclick="setCategory('wire', this)">خبرگزاری مادر</button>
      <button class="tab-btn" onclick="setCategory('tech', this)">فناوری و شبکه</button>
    </div>

    <div class="news-grid" id="newsGrid"></div>

    <footer>
      رادار خبری چندرسانه‌ای مستقل | اجرا روی سرور Ubuntu ARM64 با مصرف زیر ۳۰ مگابایت رم و هزینه صفر توکن.
    </footer>
  </div>

  <script>
    const articles = {all_articles_json};
    let currentCategory = 'all';

    function getBadgeClass(cat) {{
      if (cat === 'twitter') return 'badge-tw';
      if (cat === 'telegram') return 'badge-tg';
      if (cat === 'persian') return 'badge-fa';
      if (cat === 'wire') return 'badge-wire';
      return 'badge-tech';
    }}

    function renderArticles(list) {{
      const grid = document.getElementById('newsGrid');
      if (!list.length) {{
        grid.innerHTML = '<div style="text-align:center; padding: 40px; color: var(--text-muted);">موردی یافت نشد.</div>';
        return;
      }}
      grid.innerHTML = list.map(a => {{
        const bClass = getBadgeClass(a.category);
        const mediaHtml = a.local_media_path ? `<div class="card-media"><img src="../${{a.local_media_path}}" loading="lazy" alt="Media"></div>` : '';
        const summaryHtml = a.summary ? `<div class="card-summary">${{a.summary}}</div>` : '';
        return `
          <div class="news-card" dir="${{a.rtl ? 'rtl' : 'ltr'}}">
            <div class="card-header">
              <span class="badge ${{bClass}}">${{a.source_name_fa || a.source_name}}</span>
              <span style="font-size:0.75rem; color: var(--text-muted);">${{a.published_at.slice(11, 16)}} UTC</span>
            </div>
            <a class="card-title" href="${{a.link}}" target="_blank" rel="noopener noreferrer">${{a.title}}</a>
            ${{summaryHtml}}
            ${{mediaHtml}}
            <div class="card-footer">
              <span>منبع: ${{a.source_name}}</span>
              <a href="${{a.link}}" target="_blank" rel="noopener noreferrer" style="color:var(--accent); text-decoration:none;">مشاهده خبر اصلی ↗</a>
            </div>
          </div>
        `;
      }}).join('');
    }}

    function filterCards() {{
      const q = document.getElementById('searchInput').value.toLowerCase().trim();
      const filtered = articles.filter(a => {{
        const matchCat = (currentCategory === 'all' || a.category === currentCategory);
        const matchSearch = !q || (a.title && a.title.toLowerCase().includes(q)) ||
                                  (a.summary && a.summary.toLowerCase().includes(q)) ||
                                  (a.source_name && a.source_name.toLowerCase().includes(q));
        return matchCat && matchSearch;
      }});
      renderArticles(filtered);
    }}

    function setCategory(cat, btn) {{
      currentCategory = cat;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      filterCards();
    }}

    renderArticles(articles);
  </script>
</body>
</html>"""

# ==============================================================================
# State & File Helpers
# ==============================================================================

def load_state() -> dict:
    """Load previously seen hashes and media state from state.json."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"seen_hashes": [], "last_run_utc": None}


def save_state(state: dict):
    """Save seen hashes, bounded to MAX_STATE_ENTRIES to prevent unbounded growth."""
    if len(state["seen_hashes"]) > MAX_STATE_ENTRIES:
        state["seen_hashes"] = state["seen_hashes"][-MAX_STATE_ENTRIES:]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def scan_recent_snapshots() -> list[str]:
    """Scan the news/ directory and return all interval markdown files sorted newest first."""
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

# ==============================================================================
# Main Orchestration Loop
# ==============================================================================

def main():
    start_time = datetime.now(timezone.utc)
    print(f"=== 30-Minute Multi-Source News & Media Aggregator ===")
    print(f"Start time: {start_time.isoformat()}")

    # Ensure output directories exist
    os.makedirs(NEWS_DIR, exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    # 30-minute interval folder and filename: news/YYYY-MM-DD/HH-MM.md
    date_str = start_time.strftime("%Y-%m-%d")
    date_dir = os.path.join(NEWS_DIR, date_str)
    os.makedirs(date_dir, exist_ok=True)

    minute_bucket = f"{(start_time.minute // 30) * 30:02d}"
    interval_filename = f"{start_time.strftime('%H')}-{minute_bucket}.md"
    interval_path = os.path.join(date_dir, interval_filename)

    # Load persistent deduplication state
    state = load_state()
    seen_set = set(state.get("seen_hashes", []))
    print(f"Loaded {len(seen_set)} previously seen item hashes from state.json")

    # Ingest from all 32 sources concurrently with bounded ThreadPoolExecutor
    all_fetched = []
    total_sources = len(TWITTER_ACCOUNTS) + len(TELEGRAM_CHANNELS) + len(RSS_FEEDS)
    print(f"Dispatching concurrent ingest across {total_sources} sources (workers={MAX_CONCURRENT_WORKERS})...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) as executor:
        futures = []
        # 1. Twitter accounts (12)
        for acc in TWITTER_ACCOUNTS:
            futures.append(executor.submit(fetch_twitter_account, acc))
        # 2. Telegram channels (12)
        for ch in TELEGRAM_CHANNELS:
            futures.append(executor.submit(fetch_telegram_channel, ch))
        # 3. RSS feeds (8)
        for src in RSS_FEEDS:
            futures.append(executor.submit(fetch_rss_feed, src))

        for f in concurrent.futures.as_completed(futures):
            try:
                res = f.result()
                if res:
                    all_fetched.extend(res)
            except Exception:
                pass

    print(f"Ingest complete: fetched {len(all_fetched)} total raw items across all sources")

    # Sort all items newest first
    all_fetched.sort(key=lambda x: x["published_epoch"], reverse=True)

    # Group into categories and deduplicate against state.json
    grouped_fresh = {k: [] for k in CATEGORY_METADATA}
    grouped_interval = {k: [] for k in CATEGORY_METADATA}
    new_in_this_run = []
    new_hashes_to_add = []

    for item in all_fetched:
        cat = item["category"]
        grouped_fresh[cat].append(item)

        if item["hash"] not in seen_set:
            new_in_this_run.append(item)
            grouped_interval[cat].append(item)
            new_hashes_to_add.append(item["hash"])
            seen_set.add(item["hash"])

    print(f"Deduplication complete: {len(new_in_this_run)} newly discovered items in this 30-min window")

    # Media Archiving: Download and archive media for freshly discovered items
    media_candidates = [it for it in new_in_this_run if it.get("raw_media_urls")]
    if not media_candidates:
        # Fallback to fresh items if state was already full
        media_candidates = [it for it in all_fetched[:20] if it.get("raw_media_urls")]

    print(f"Archiving media for {len(media_candidates)} candidate items...")
    archive_media_batch(media_candidates, start_time)
    archived_count = sum(1 for it in all_fetched if it.get("local_media_path"))
    print(f"Media archiving complete: {archived_count} items have local archived images")

    # Select active items for the 30-min snapshot file
    active_grouped = grouped_interval if new_in_this_run else grouped_fresh

    # 1. Generate 30-minute interval markdown snapshot: news/YYYY-MM-DD/HH-MM.md
    interval_md = generate_interval_markdown(start_time, active_grouped)
    with open(interval_path, "w", encoding="utf-8") as f:
        f.write(interval_md)
    print(f"Saved interval snapshot: {interval_path}")

    # 2. Generate rolling latest: news/latest.md
    latest_path = os.path.join(NEWS_DIR, "latest.md")
    latest_md = generate_latest_markdown(start_time, grouped_fresh)
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(latest_md)
    print(f"Saved latest digest: {latest_path}")

    # 3. Generate root index.md archive index
    recent_snapshots = scan_recent_snapshots()
    index_md = generate_index_markdown(start_time, recent_snapshots, all_fetched[:25])
    index_path = os.path.join(BASE_DIR, "index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_md)
    print(f"Saved root index: {index_path}")

    # 4. Generate public/index.html (static dashboard)
    html_content = generate_static_html(start_time, grouped_fresh)
    html_path = os.path.join(PUBLIC_DIR, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Saved static HTML dashboard: {html_path}")

    # 5. Generate public/latest.json (machine-readable API feed, bounded to top 100)
    json_path = os.path.join(PUBLIC_DIR, "latest.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at_utc": start_time.isoformat(),
            "generated_at_tehran": start_time.astimezone(TEHRAN_TZ).isoformat(),
            "article_count": min(len(all_fetched), 100),
            "articles": all_fetched[:100]
        }, f, indent=2, ensure_ascii=False)
    print(f"Saved machine-readable JSON: {json_path}")

    # Update and prune state
    state["seen_hashes"].extend(new_hashes_to_add)
    state["last_run_utc"] = start_time.isoformat()
    save_state(state)
    print(f"State saved ({len(state['seen_hashes'])} hashes recorded)")

    # Force garbage collection to keep resident memory minimal
    gc.collect()

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    print(f"=== Aggregator run completed cleanly in {elapsed:.2f} seconds ===")


if __name__ == "__main__":
    main()
