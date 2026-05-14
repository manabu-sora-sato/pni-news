"""
fetch_rss.py - RAW LAYER
RSS取得 → raw_news.jsonl に追記（7日保持）
"""

import feedparser
import json
import yaml
import hashlib
import os
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

def purge_old_records():
    """7日以上古いレコードを削除"""
    if not RAW_FILE.exists():
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    kept = []
    with open(RAW_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                pub = datetime.fromisoformat(record.get("published_at", "2000-01-01T00:00:00+00:00"))
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=timezone.utc)
                if pub >= cutoff:
                    kept.append(line)
            except Exception:
                kept.append(line)
    with open(RAW_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(kept) + ("\n" if kept else ""))
    print(f"[purge] {RAW_FILE}: kept {len(kept)} records")

def parse_published(entry) -> str:
    try:
        import time
        t = entry.get("published_parsed") or entry.get("updated_parsed")
        if t:
            dt = datetime(*t[:6], tzinfo=timezone.utc)
            return dt.isoformat()
    except Exception:
        pass
    return datetime.now(timezone.utc).isoformat()

def fetch_all():
    DATA_DIR.mkdir(exist_ok=True)
    feeds_config = load_feeds()
    existing_ids = load_existing_ids()
    new_count = 0

    with open(RAW_FILE, "a", encoding="utf-8") as f:
        for category, feeds in feeds_config.items():
            for feed_info in feeds:
                url = feed_info["url"]
                lang = feed_info.get("lang", "en")
                name = feed_info.get("name", url)
                print(f"[fetch] {name} ({category})")
                try:
                    d = feedparser.parse(url)
                    for entry in d.entries[:20]:  # 最大20件/フィード
                        link = entry.get("link", "")
                        if not link:
                            continue
                        article_id = make_article_id(link)
                        if article_id in existing_ids:
                            continue
                        record = {
                            "article_id": article_id,
                            "title": entry.get("title", ""),
                            "url": link,
                            "published_at": parse_published(entry),
                            "source": name,
                            "source_lang": lang,
                            "master_category": category,
                            "fetched_at": datetime.now(timezone.utc).isoformat(),
                        }
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        existing_ids.add(article_id)
                        new_count += 1
                except Exception as e:
                    print(f"  [ERROR] {name}: {e}")

    print(f"[fetch] done. new articles: {new_count}")

if __name__ == "__main__":
    purge_old_records()
    fetch_all()
