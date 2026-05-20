"""
data_loader.py - データ読み込みユーティリティ
FALLBACK LOGIC: processed → raw の順で必ずデータを返す
"""
import json
from pathlib import Path
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


def _get_combined_all_articles() -> list:
    """内部用：PROCESSEDデータをベースにし、存在しないRAWデータのみを補完する"""
    processed = load_jsonl(PROCESSED_FILE)
    raw = load_jsonl(RAW_FILE)

    processed_ids = {a["article_id"] for a in processed}

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
                "summary": raw_article.get("title", ""),
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
    return processed


def count_articles(unread_only: bool = False, category: str = None) -> int:
    """統計用カウント（RAWとPROCESSEDを合算した正確な数値）"""
    articles = _get_combined_all_articles()
    
    try:
        from utils.feedback import load_feedback
        fb = load_feedback()
        fb_ids = {f["article_id"] for f in fb}
        articles = [a for a in articles if a["article_id"] not in fb_ids]
    except Exception:
        pass

    if unread_only:
        articles = [a for a in articles if not a.get("is_read", False)]
    if category and category != "ALL":
        articles = [a for a in articles if a.get("master_category") == category]
    return len(articles)


def count_fallback_articles() -> int:
    """未処理（fallback）記事のカウント（フィードバック済みを除く）"""
    articles = _get_combined_all_articles()
    try:
        from utils.feedback import load_feedback
        fb = load_feedback()
        fb_ids = {f["article_id"] for f in fb}
        articles = [a for a in articles if a["article_id"] not in fb_ids]
    except Exception:
        pass
    return sum(1 for a in articles if a.get("is_fallback", False))


def load_articles(unread_only: bool = False, category: str = None) -> list:
    processed = _get_combined_all_articles()

    for article in processed:
        article["adjusted_score"] = adjust_score_by_feedback(article)

    if unread_only:
        processed = [a for a in processed if not a.get("is_read", False)]
    if category and category != "ALL":
        processed = [a for a in processed if a.get("master_category") == category]
    
    try:
        from utils.feedback import load_feedback
        fb = load_feedback()
        fb_ids = {f["article_id"] for f in fb}
        processed = [a for a in processed if a["article_id"] not in fb_ids]
    except Exception:
        pass

    processed.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return processed[:20]


def mark_as_read(article_id: str):
    if not PROCESSED_FILE.exists():
        return
    records = load_jsonl(PROCESSED_FILE)
    updated = []
    
    found = False
    for r in records:
        if r["article_id"] == article_id:
            r["is_read"] = True
            found = True
        updated.append(json.dumps(r, ensure_ascii=False))
        
    if not found:
        articles = _get_combined_all_articles()
        target = next((a for a in articles if a["article_id"] == article_id), None)
        if target:
            target["is_read"] = True
            updated.append(json.dumps(target, ensure_ascii=False))

    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(updated) + ("\n" if updated else ""))


def mark_all_as_read(article_ids: list):
    if not PROCESSED_FILE.exists():
        return
    records = load_jsonl(PROCESSED_FILE)
    id_set = set(article_ids)
    updated = []
    
    for r in records:
        if r["article_id"] in id_set:
            r["is_read"] = True
            id_set.remove(r["article_id"])
        updated.append(json.dumps(r, ensure_ascii=False))
        
    if id_set:
        articles = _get_combined_all_articles()
        for a_id in id_set:
            target = next((a for a in articles if a["article_id"] == a_id), None)
            if target:
                target["is_read"] = True
                updated.append(json.dumps(target, ensure_ascii=False))

    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(updated) + ("\n" if updated else ""))
