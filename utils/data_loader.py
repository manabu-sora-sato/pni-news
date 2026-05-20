"""
utils/data_loader.py - データ読み込み・既読管理ユーティリティ
すべての仕分け履歴（既読・GOOD・BAD）をHFローカルの統合ファイルに一括保存します
"""
import json
import os
from pathlib import Path
from utils.feedback import adjust_score_by_feedback

DATA_DIR = Path("data")
RAW_FILE = DATA_DIR / "raw_news.jsonl"
# すべてのユーザーアクション（read, like, dislike）をこの1つのファイルに統合します
ACTIONS_FILE = DATA_DIR / "user_actions.jsonl"


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
                    # 万が一破損した行が混入しても、そこで止めずにスキップして読み込む
                    pass
    return records


def _get_action_status_maps() -> tuple:
    """
    統合ファイルから各記事のアクション状態を解析して、高速に逆引きできるマップとセットを作る。
    """
    actions = load_jsonl(ACTIONS_FILE)
    
    read_status_map = {}
    feedback_ids = set()
    
    for act in actions:
        article_id = act.get("article_id")
        if not article_id:
            continue
            
        action_type = act.get("action")
        
        # 既読状態の判定マッピング
        if action_type == "read":
            read_status_map[article_id] = True
        elif action_type in ["like", "dislike"]:
            read_status_map[article_id] = True  # GOOD/BAD押下時も画面から消すため既読扱い
            feedback_ids.add(article_id)
            
    return read_status_map, feedback_ids


def _get_combined_all_articles() -> list:
    """内部用：RAWデータをマスターとし、HFローカルに蓄積された仕分け履歴をマッピングする"""
    raw = load_jsonl(RAW_FILE)
    read_status_map, _ = _get_action_status_maps()

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
    """統計用カウント（完全にHF手元のデータのみで完結）"""
    articles = _get_combined_all_articles()
    
    # フィルタリング対象のフィードバックIDを取得
    _, fb_ids = _get_action_status_maps()
    articles = [a for a in articles if a["article_id"] not in fb_ids]

    if unread_only:
        articles = [a for a in articles if not a.get("is_read", False)]
    if category and category != "ALL":
        articles = [a for a in articles if a.get("master_category") == category]
    return len(articles)


def count_fallback_articles() -> int:
    """未処理記事カウント"""
    articles = _get_combined_all_articles()
    _, fb_ids = _get_action_status_maps()
    articles = [a for a in articles if a["article_id"] not in fb_ids]
    return sum(1 for a in articles if a.get("is_fallback", False))


def load_articles(unread_only: bool = False, category: str = None) -> list:
    """フィルタリングされた記事一覧を取得（完全にHF手元のデータのみで完結）"""
    articles = _get_combined_all_articles()

    for article in articles:
        article["adjusted_score"] = adjust_score_by_feedback(article)

    if unread_only:
        articles = [a for a in articles if not a.get("is_read", False)]
    if category and category != "ALL":
        articles = [a for a in articles if a.get("master_category") == category]
    
    # フィードバック済みの記事を除外
    _, fb_ids = _get_action_status_maps()
    articles = [a for a in articles if a["article_id"] not in fb_ids]

    articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return articles[:10]


def mark_as_read(article_id: str):
    """
    既読（✓）アクションをHFローカルの統合ファイルにログ形式で即座に追記。
    GitHubへのリアルタイムAPI送信は行わない。
    """
    import datetime
    ACTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    new_record = {
        "article_id": article_id, 
        "action": "read", 
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    with open(ACTIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(new_record, ensure_ascii=False) + "\n")


def mark_all_as_read(article_ids: list):
    """
    一括既読アクションをHFローカルの統合ファイルにログ形式で即座に追記。
    """
    import datetime
    ACTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().isoformat()
    updated = []
    
    for a_id in article_ids:
        new_record = {
            "article_id": a_id, 
            "action": "read", 
            "timestamp": timestamp
        }
        updated.append(json.dumps(new_record, ensure_ascii=False))

    if updated:
        file_content = "\n".join(updated) + "\n"
        with open(ACTIONS_FILE, "a", encoding="utf-8") as f:
            f.write(file_content)
