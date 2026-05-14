"""
data_loader.py - データ読み込みユーティリティ
FALLBACK LOGIC: processed → raw の順で必ずデータを返す
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from utils.feedback import adjust_score_by_feedback

DATA_DIR = Path("data")
RAW_FILE = DATA_DIR / "raw_news.jsonl"
PROCESSED_FILE = DATA_DIR / "processed_news.jsonl"


def load_jsonl(path: Path) -> list:
    records = []
    if not path.exists():
        return records
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


def load_articles(unread_only: bool = False, category: str = None) -> list:
    """
    FALLBACK LOGIC:
    1. processed_news から読み込み
    2. 未処理のraw記事はフォールバック形式で追加
    3. スコア降順でソート
    """
    processed = load_jsonl(PROCESSED_FILE)
    raw = load_jsonl(RAW_FILE)

    processed_ids = {a["article_id"] for a in processed}

    # raw のうち未処理のものをフォールバックとして追加
    for raw_article in raw:
        if raw_article["article_id"] not in processed_ids:
            fallback = {
                "article_id": raw_article["article_id"],
                "title": raw_article.get("title", ""),
                "url": raw_article.get("url", ""),
                "published_at": raw_article.get("published_at", ""),
                "source": raw_article.get("source", ""),
                "source_lang": raw_article.get("source_lang", ""),
                "master_category": raw_article.get("master_category", "OTHER"),
                "summary": raw_article.get("title", ""),  # タイトルをsummaryに
                "tags": [raw_article.get("master_category", "OTHER")],
                "score_interest": 0.3,
                "score_quality": 0.3,
                "score_novelty": 0.5,
                "final_score": 0.37,
                "is_fallback": True,
                "is_read": False,
                "processed_at": raw_article.get("fetched_at", ""),
            }
            processed.append(fallback)

    # フィードバック学習スコア補正
    for article in processed:
        article["adjusted_score"] = adjust_score_by_feedback(article)

    # フィルタ
    if unread_only:
        processed = [a for a in processed if not a.get("is_read", False)]
    if category and category != "ALL":
        processed = [a for a in processed if a.get("master_category") == category]

    # スコア降順ソート
    processed.sort(key=lambda x: x.get("adjusted_score", 0), reverse=True)

    return processed


def mark_as_read(article_id: str):
    """記事を既読にする（JSONL更新）"""
    if not PROCESSED_FILE.exists():
        return
    records = load_jsonl(PROCESSED_FILE)
    updated = []
    for r in records:
        if r["article_id"] == article_id:
            r["is_read"] = True
        updated.append(json.dumps(r, ensure_ascii=False))
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(updated) + ("\n" if updated else ""))


def mark_all_as_read(article_ids: list):
    """一括既読"""
    if not PROCESSED_FILE.exists():
        return
    records = load_jsonl(PROCESSED_FILE)
    id_set = set(article_ids)
    updated = []
    for r in records:
        if r["article_id"] in id_set:
            r["is_read"] = True
        updated.append(json.dumps(r, ensure_ascii=False))
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(updated) + ("\n" if updated else ""))
