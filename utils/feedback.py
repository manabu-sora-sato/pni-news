import json
import os
from datetime import datetime, timezone
from pathlib import Path

# ─── 修正箇所：GitHub Actionsのバックアップファイル名とパスに完全に統一 ───
DATA_DIR = Path(__file__).parent.parent / "data"
ACTIONS_FILE = DATA_DIR / "user_feedback_log.jsonl"

def save_feedback(article_id: str, tags: list, category: str, action: str):
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        # ディレクトリ作成権限が制限されている場合はスキップして書き込みへ移行
        pass

    record = {
        "article_id": article_id,
        "action": action,
        "category": category,
        "tags": tags,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # 既存ファイルへの追記（"a"）は一般ユーザー権限でも許可されるケースに対応
    try:
        with open(ACTIONS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except PermissionError:
        # 万が一制限が厳しい場合は代替の自由領域へ書き込みを逃がす
        ALT_DIR = Path("/tmp/pni-data")
        ALT_DIR.mkdir(parents=True, exist_ok=True)
        with open(ALT_DIR / "user_feedback_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

def load_feedback() -> list:
    records = []
    # 正常ルートと代替ルートの両方からログを読み込む
    paths = [ACTIONS_FILE, Path("/tmp/pni-data/user_feedback_log.jsonl")]
    for path in paths:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
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
