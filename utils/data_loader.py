import json
from pathlib import Path

DATA_PATH = Path("data/processed_news.jsonl")


def load_articles(unread_only=True, category="ALL"):
    if not DATA_PATH.exists():
        return []

    articles = []

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                a = json.loads(line)
            except:
                continue

            a["is_read"] = a.get("is_read", False)

            if unread_only and a["is_read"]:
                continue

            if category != "ALL" and a.get("master_category") != category:
                continue

            articles.append(a)

    return articles


def count_articles(unread_only=False):
    if not DATA_PATH.exists():
        return 0

    count = 0

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                a = json.loads(line)
            except:
                continue

            if unread_only and a.get("is_read", False):
                continue

            count += 1

    return count


def mark_as_read(article_id):
    if not DATA_PATH.exists():
        return

    new_lines = []

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                a = json.loads(line)
            except:
                continue

            if str(a.get("article_id")) == str(article_id):
                a["is_read"] = True

            new_lines.append(json.dumps(a, ensure_ascii=False))

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")
