"""
utils/data_loader.py - データ読み込み・既読管理ユーティリティ
既読データをローカル保存およびGitHubへリアルタイム同期します
"""
import json
import os
import base64
import requests
from pathlib import Path
from utils.feedback import adjust_score_by_feedback

DATA_DIR = Path("data")
RAW_FILE = DATA_DIR / "raw_news.jsonl"
PROCESSED_FILE = DATA_DIR / "processed_news.jsonl"

GITHUB_REPO = "manabu-sora-sato/pni-news"
GITHUB_FILE_PATH = "data/processed_news.jsonl"


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


def _save_processed_to_github(content: str):
    """GitHub APIで既読データを直接更新（永続化）"""
    token = os.environ.get("GITHUB_TOKEN_READ", "")
    if not token:
        return

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    sha = None
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            sha = r.json().get("sha")
    except Exception:
        pass

    try:
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        body = {"message": "update processed status from web ui", "content": encoded}
        if sha:
            body["sha"] = sha
        requests.put(url, headers=headers, json=body, timeout=10)
    except Exception as e:
        print(f"[github] save processed error: {e}")


def _get_combined_all_articles() -> list:
    """内部用：RAWデータをマスターとし、GitHubから同期された既読フラグをマッピングする"""
    raw = load_jsonl(RAW_FILE)
    processed = load_jsonl(PROCESSED_FILE)

    read_status_map = {}
    for p_article in processed:
        if "article_id" in p_article:
            read_status_map[p_article["article_id"]] = p_article.get("is_read", False)

    combined = []
    for raw_article in raw:
        article_id = raw_article["article_id"]
        is_read = read_status_map.get(article_id, False)

        fallback = {
            "article_id": article_id,
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
            "is_read": is_read,
            "processed_at": raw_article.get("fetched_at", ""),
        }
        combined.append(fallback)
        
    return combined


def count_articles(unread_only: bool = False, category: str = None) -> int:
    """統計用カウント"""
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
    """未処理記事カウント"""
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
    articles = _get_combined_all_articles()

    for article in articles:
        article["adjusted_score"] = adjust_score_by_feedback(article)

    if unread_only:
        articles = [a for a in articles if not a.get("is_read", False)]
    if category and category != "ALL":
        articles = [a for a in articles if a.get("master_category") == category]
    
    try:
        from utils.feedback import load_feedback
        fb = load_feedback()
        fb_ids = {f["article_id"] for f in fb}
        articles = [a for a in articles if a["article_id"] not in fb_ids]
    except Exception:
        pass

    articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return articles[:10]


def mark_as_read(article_id: str):
    records = load_jsonl(PROCESSED_FILE)
    updated = []
    found = False
    for r in records:
        if r.get("article_id") == article_id:
            r["is_read"] = True
            found = True
        updated.append(json.dumps(r, ensure_ascii=False))
        
    if not found:
        new_record = {"article_id": article_id, "is_read": True}
        updated.append(json.dumps(new_record, ensure_ascii=False))

    file_content = "\n".join(updated) + ("\n" if updated else "")
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        f.write(file_content)
    
    _save_processed_to_github(file_content)


def mark_all_as_read(article_ids: list):
    records = load_jsonl(PROCESSED_FILE)
    id_set = set(article_ids)
    updated = []
    
    for r in records:
        r_id = r.get("article_id")
        if r_id in id_set:
            r["is_read"] = True
            id_set.remove(r_id)
        updated.append(json.dumps(r, ensure_ascii=False))
        
    for a_id in id_set:
        new_record = {"article_id": a_id, "is_read": True}
        updated.append(json.dumps(new_record, ensure_ascii=False))

    file_content = "\n".join(updated) + ("\n" if updated else "")
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        f.write(file_content)
        
    _save_processed_to_github(file_content)
