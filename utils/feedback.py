"""
feedback.py - FEEDBACK LAYER
👍/👎 永続保存・学習用スコア補正
"""
import json
import os
import base64
import requests
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path("data")
FEEDBACK_FILE = DATA_DIR / "user_feedback_log.jsonl"

GITHUB_REPO = "manabu-sora-sato/pni-news"
GITHUB_FILE_PATH = "data/user_feedback_log.jsonl"

def _save_to_github(content: str):
    """GitHub APIでフィードバックファイルを直接更新"""
    token = os.environ.get("GITHUB_TOKEN_READ", "")
    if not token:
        print("[github] GITHUB_TOKEN_READ not found")
        return

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # 現在のファイルのSHAを取得
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    sha = None
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            sha = r.json().get("sha")
    except Exception as e:
        print(f"[github] get sha error: {e}")
        return

    # ファイルを更新
    try:
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        body = {
            "message": f"backup: feedback {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "content": encoded,
        }
        if sha:
            body["sha"] = sha
        r = requests.put(url, headers=headers, json=body, timeout=15)
        print(f"[github] save status: {r.status_code}")
    except Exception as e:
        print(f"[github] save error: {e}")

def save_feedback(article_id: str, tags: list, category: str, action: str):
    DATA_DIR.mkdir(exist_ok=True)
    record = {
        "article_id": article_id,
        "tags": tags,
        "category": category,
        "action": action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # GitHubに直接保存
    content = FEEDBACK_FILE.read_text(encoding="utf-8")
    _save_to_github(content)

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
