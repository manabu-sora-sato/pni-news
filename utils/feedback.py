"""
feedback.py - FEEDBACK LAYER
👍/👎 永続保存・学習用スコア補正
すべてのフィードバック（GOOD/BAD）をHFローカルの統合ファイルに一括保存し、スコアを計算します
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path("data")
# すべてのアクションを管理する共通の統合ファイルを参照します
ACTIONS_FILE = DATA_DIR / "user_actions.jsonl"


def save_feedback(article_id: str, tags: list, category: str, action: str):
    """
    GOOD（like）/ BAD（dislike）アクションを統合ファイルにログ形式で即座に追記。
    GitHubへのリアルタイムAPI送信は一切行いません。
    """
    DATA_DIR.mkdir(exist_ok=True)
    record = {
        "article_id": article_id,
        "action": action,  # "like" または "dislike"
        "category": category,
        "tags": tags,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(ACTIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_feedback() -> list:
    """
    統合ファイルから GOOD/BAD（like/dislike）のレコードだけを抽出して返す（統計・スコア計算用）
    """
    records = []
    if not ACTIONS_FILE.exists():
        return records
    with open(ACTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    # アクションが like または dislike のものだけをフィードバックとして扱う
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
    """統合ファイルから得られた傾向を元にスコアを補正（プラマイゼロの既読は影響なし）"""
    tag_scores = get_tag_preference_scores()
    cat_scores = get_category_preference_scores()
    tag_bonus = 0.0
    for tag in article.get("tags", []):
        tag_bonus += tag_scores.get(tag, 0.0) * 0.05
    cat_bonus = cat_scores.get(article.get("master_category", "OTHER"), 0.0) * 0.02
    raw_score = article.get("final_score", 0.5)
    adjusted = max(0.0, min(1.0, raw_score + tag_bonus + cat_bonus))
    return round(adjusted, 4)
