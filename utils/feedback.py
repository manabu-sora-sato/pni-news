import json
import os
from datetime import datetime, timezone
from pathlib import Path

# 絶対パスで固定
DATA_DIR = Path(__file__).parent.parent / "data"
ACTIONS_FILE = DATA_DIR / "user_actions.jsonl"

def save_feedback(article_id: str, tags: list, category: str, action: str):
    # フォルダと空ファイルを強制的に物理生成
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not ACTIONS_FILE.exists():
        ACTIONS_FILE.touch()
        
    record = {
        "article_id": article_id,
        "action": action,
        "category": category,
        "tags": tags,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(ACTIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def load_feedback() -> list:
    records = []
    if not ACTIONS_FILE.exists():
        return records
    with open(ACTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    if data.get("action") in ["like", "dislike"]:
                        records.append(data)
                except Exception:
                    pass
    return records

def get_tag_preference_scores() -> dict:
    feedback = load_feedback()
    scores = {}
    for record in feedback:
        weight = 1.0 if record["action"] == "like" else -1.0
        for tag in record.get("tags", []):
            scores[tag] = scores.get(tag, 0.0) + weight
    return scores

def get_category_preference_scores() -> dict:
    feedback = load_feedback()
    scores = {}
    for record in feedback:
        cat = record.get("category", "OTHER")
        weight = 1.0 if record["action"] == "like" else -1.0
        scores[cat] = scores.get(cat, 0.0) + weight
    return scores

def adjust_score_by_feedback(article: dict) -> float:
    tag_scores = get_tag_preference_scores()
    cat_scores = get_category_preference_scores()
    tag_bonus = 0.0
    for tag in article.get("tags", []):
        tag_bonus += tag_scores.get(tag, 0.0) * 0.05
    cat_bonus = cat_scores.get(article.get("master_category", "OTHER"), 0.0) * 0.02
    raw_score = article.get("final_score", 0.5)
    adjusted = max(0.0, min(1.0, raw_score + tag_bonus + cat_bonus))
    return round(adjusted, 4)
