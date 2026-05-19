"""
fetch_rss.py - RAW LAYER (DEBUG MODE)
RSS取得 → エラーログを詳細に出力
"""

import feedparser
import json
import yaml
import hashlib
import os
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA_DIR = Path("data")
RAW_FILE = DATA_DIR / "raw_news.jsonl"
FEEDS_FILE = Path("feeds.yaml")
RETENTION_DAYS = 7

def load_feeds() -> dict:
    with open(FEEDS_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["feeds"]

def make_article_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]

def load_existing_ids() -> set:
    ids = set()
    if RAW_FILE.exists():
        with open(RAW_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        ids.add(json.loads(line)["article_id"])
                    except Exception:
                        pass
    return ids

def parse_published_datetime(entry) -> datetime:
    try:
        import time
        t = entry.get("published_parsed") or entry.get("updated_parsed")
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    except Exception:
        pass
    return datetime.now(timezone.utc)

def fetch_all():
    DATA_DIR.mkdir(exist_ok=True)
    feeds_config = load_feeds()
    existing_ids = load_existing_ids()
    new_count = 0

    now_utc = datetime.now(timezone.utc)
    time_threshold = now_utc - timedelta(hours=24)

    print(f"[debug] Time threshold (UTC): {time_threshold.isoformat()}")

    with open(RAW_FILE, "a", encoding="utf-8") as f:
        for category, feeds in feeds_config.items():
            for feed_info in feeds:
                url = feed_info["url"]
                lang = feed_info.get("lang", "en")
                name = feed_info.get("name", url)
                print(f"[fetch] Trying: {name} ({category}) -> {url}")
                try:
                    d = feedparser.parse(url)
                    
                    # feedparserの解析結果自体にエラーがないかチェック
                    if hasattr(d, 'bozo') and d.bozo:
                        print(f"  [WARNING] Feedparser flagged an issue (bozo): {d.bozo_exception}")

                    if not d.entries:
                        print(f"  [INFO] No entries found in this feed. parsed status: {getattr(d, 'status', 'N/A')}")
                        continue

                    print(f"  [INFO] Found {len(d.entries)} entries in feed. Checking dates...")
                    for entry in d.entries[:20]:
                        link = entry.get("link", "")
                        if not link:
                            continue

                        pub_dt = parse_published_datetime(entry)

                        if pub_dt < time_threshold:
                            continue

                        article_id = make_article_id(link)
                        if article_id in existing_ids:
                            continue

                        record = {
                            "article_id": article_id,
                            "title": entry.get("title", ""),
                            "url": link,
                            "published_at": pub_dt.isoformat(),
                            "source": name,
                            "source_lang": lang,
                            "master_category": category,
                            "fetched_at": now_utc.isoformat(),
                        }
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        existing_ids.add(article_id)
                        new_count += 1
                except Exception as e:
                    print(f"  [CRITICAL ERROR] Failed to process feed {name}")
                    traceback.print_exc() # エラーのスタックトレースを強制出力

    print(f"[fetch] done. new articles: {new_count}")

if __name__ == "__main__":
    fetch_all()
