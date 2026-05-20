"""
data_loader.py - simplified version (RAW BASED)
RSS → RAW表示 → feedback学習構造
"""

import json
from pathlib import Path

DATA_DIR = Path("data")
RAW_FILE = DATA_DIR / "raw_news.jsonl"


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


def count_articles(unread_only: bool = False, category: str = None) -> int:
    articles = load_jsonl(RAW_FILE)

    if category and category != "ALL":
        articles = [a for a in articles if a.get("master_category") == category]

    if unread_only:
        articles = [a for a in articles if not a.get("is_read", False)]

    return len(articles)


def count_fallback_articles() -> int:
    # RAW構造では未処理概念は廃止（互換のため0固定）
    return 0


def load_articles(unread_only: bool = False, category: str = None) -> list:
    articles = load_jsonl(RAW_FILE)

    # カテゴリフィルタ
    if category and category != "ALL":
        articles = [a for a in articles if a.get("master_category") == category]

    # 既読フィルタ
    if unread_only:
        articles = [a for a in articles if not a.get("is_read", False)]

    # フィードバック除外（学習済みは非表示）
    try:
        from utils.feedback import load_feedback
        fb = load_feedback()
        fb_ids = {f["article_id"] for f in fb}
        articles = [a for a in articles if a["article_id"] not in fb_ids]
    except Exception:
        pass

    # 既読フラグをUIに反映（重要）
    try:
        from utils.feedback import load_read_state
        read_ids = load_read_state()
        for a in articles:
            a["is_read"] = a["article_id"] in read_ids
    except Exception:
        pass

    # 並び順（新しい順）
    articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    # ★ 表示件数制限（要件）
    return articles[:10]


def mark_as_read(article_id: str):
    from utils.feedback import add_read_state
    add_read_state(article_id)


def mark_all_as_read(article_ids: list):
    from utils.feedback import add_read_state
    for aid in article_ids:
        add_read_state(aid)
