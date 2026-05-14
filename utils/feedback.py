"""
feedback.py - FEEDBACK LAYER
👍/👎 永続保存・学習用スコア補正
"""

import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path("data")
FEEDBACK_FILE = DATA_DIR / "user_feedback_log.jsonl"

def save_feedback(article_id: str, tags: list, category: str, action: str):
    """
    action: "like" or "dislike"
    永続保存（削除禁止）
    """
    DATA_DIR.mkdir(exist_ok=True)
    record = {
        "article_id": article_id,
        "tags": tags,
        "category": category,
        "action": action,  # "like" or "dislike"
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def load_feedback() -> list:
    records = []
    if not FEEDBACK_FILE.exists():
        return records
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records

def get_tag_preference_scores() -> dict:
    """
    タグ別の好感度スコアを計算
    Returns: {tag: score} score>0=好き, score<0=嫌い
    """
    feedback = load_feedback()
    scores = {}
    for record in feedback:
        weight = 1.0 if record["action"] == "like" else -1.0
        for tag in record.get("tags", []):
            scores[tag] = scores.get(tag, 0.0) + weight
    return scores

def get_category_preference_scores() -> dict:
    """カテゴリ別の好感度スコア"""
    feedback = load_feedback()
    scores = {}
    for record in feedback:
        cat = record.get("category", "OTHER")
        weight = 1.0 if record["action"] == "like" else -1.0
        scores[cat] = scores.get(cat, 0.0) + weight
    return scores

def adjust_score_by_feedback(article: dict) -> float:
    """
    フィードバック学習を反映したfinal_scoreを再計算
    既存スコアにタグ・カテゴリ適合度を加算補正
    """
    tag_scores = get_tag_preference_scores()
    cat_scores = get_category_preference_scores()

    tag_bonus = 0.0
    for tag in article.get("tags", []):
        tag_bonus += tag_scores.get(tag, 0.0) * 0.05  # 1フィードバック=0.05点

    cat_bonus = cat_scores.get(article.get("master_category", "OTHER"), 0.0) * 0.02

    raw_score = article.get("final_score", 0.5)
    adjusted = max(0.0, min(1.0, raw_score + tag_bonus + cat_bonus))
    return round(adjusted, 4)
