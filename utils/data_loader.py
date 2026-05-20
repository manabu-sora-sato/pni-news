"""
data_loader.py - RAWデータから直接読み込む（API処理なし版）
"""
import json
from pathlib import Path

DATA_DIR = Path("data")
RAW_FILE = DATA_DIR / "raw_news.jsonl"
FEEDBACK_FILE = DATA_DIR / "user_feedback_log.jsonl"


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


def load_feedback_ids() -> set:
    """フィードバック済み記事IDのセットを返す"""
    records = load_jsonl(FEEDBACK_FILE)
    return {r["article_id"] for r in records}


def load_articles(unread_only: bool = False, category: str = None) -> list:
    articles = load_jsonl(RAW_FILE)
    feedback_ids = load_feedback_ids()

    # is_read フラグをフィードバック済みIDで付与
    for a in articles:
        a["is_read"] = a["article_id"] in feedback_ids

    if unread_only:
        articles = [a for a in articles if not a["is_read"]]
    if category and category != "ALL":
        articles = [a for a in articles if a.get("master_category") == category]

    articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return articles


def count_articles(unread_only: bool = False, category: str = None) -> int:
    return len(load_articles(unread_only=unread_only, category=category))


def mark_as_read(article_id: str):
    """フィードバックなしで既読にする（feedbackファイルにreadレコードを追記）"""
    from utils.feedback import save_feedback
    save_feedback(article_id, [], "", "read")
