"""
fetch_rss.py - RAW LAYER (UTC CORRECTED)
RSS取得 → raw_news.jsonl に追記（過去24時間以内の記事のみ取得）
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

def parse_published_datetime(entry) -> datetime:
    """feedparserのstruct_timeを環境に依存せず正しくUTCのdatetimeに変換する"""
    try:
        t = entry.get("published_parsed") or entry.get("updated_parsed")
        if t:
            # ローカル時間に変換するタイムスタンプを経由せず、直接UTCで生成する
            return datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, tzinfo=timezone.utc)
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

                        # 記事の公開日時を取得（正しいUTCマッピング）
                        pub_dt = parse_published_datetime(entry)

                        # 過去24時間以内のデータでなければスキップ
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
                    print(f"  [ERROR] {name}: {e}")

    print(f"[fetch] done. new articles: {new_count}")

if __name__ == "__main__":
    purge_old_records()
    fetch_all()
