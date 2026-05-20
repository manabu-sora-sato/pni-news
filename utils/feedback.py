"""
feedback.py - フィードバック記録のみ（学習・スコア補正は後回し）
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
    """GitHubにフィードバックファイルをバックアップ"""
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
    except Exception as e:
        print(f"[github] get sha error: {e}")
        return
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
    """フィードバックを記録する（like / dislike / read）"""
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

    # like/dislike のみGitHubにバックアップ（readは省略してAPI節約）
    if action in ("like", "dislike"):
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
