"""
process_articles.py - PROCESS LAYER
raw_news.jsonl → Gemini API解析 → processed_news.jsonl
英語記事も日本語要約に統一
"""

import json
import os
import time
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
import google.generativeai as genai

DATA_DIR = Path("data")
RAW_FILE = DATA_DIR / "raw_news.jsonl"
PROCESSED_FILE = DATA_DIR / "processed_news.jsonl"
RETENTION_DAYS = 7

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

PROMPT_TEMPLATE = """
あなたはニュース記事を分析・要約するAIです。
以下の記事を分析し、必ず**日本語で**JSON形式のみを返してください。

記事タイトル: {title}
カテゴリヒント: {category}
記事URL: {url}

カテゴリ:
- NEWS / DEV / ECON / HEALTH / THOUGHT / OTHER

出力形式（JSONのみ）:
{{
  "summary": "1〜2文の日本語要約",
  "tags": ["タグ1", "タグ2"],
  "master_category": "NEWS/DEV/ECON/HEALTH/THOUGHT/OTHER",
  "score_interest": 0.0,
  "score_quality": 0.0
}}
"""

def load_processed_ids():
    ids = set()
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    ids.add(json.loads(line)["article_id"])
                except:
                    pass
    return ids

def load_raw_articles():
    articles = []
    if not RAW_FILE.exists():
        return articles
    with open(RAW_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                articles.append(json.loads(line))
            except:
                pass
    return articles

def extract_json(text):
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```", "", text)
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1:
        raise ValueError("JSON not found")
    return json.loads(text[start:end])

def process_with_gemini(article, model):
    prompt = PROMPT_TEMPLATE.format(
        title=article.get("title", ""),
        category=article.get("master_category", "OTHER"),
        url=article.get("url", "")
    )
    response = model.generate_content(prompt)
    if not response or not hasattr(response, "text"):
        raise ValueError("Empty response")
    return extract_json(response.text)

def fallback_record(article):
    return {
        "summary": article.get("title", ""),
        "tags": [article.get("master_category", "OTHER")],
        "master_category": article.get("master_category", "OTHER"),
        "score_interest": 0.5,
        "score_quality": 0.5,
        "is_fallback": True,
    }

def calc_final_score(i, q, n):
    return round(i*0.4 + q*0.3 + n*0.3, 4)

def process_all():
    DATA_DIR.mkdir(exist_ok=True)

    if not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY missing")
        return

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash-lite")

    processed_ids = load_processed_ids()
    raw_articles = load_raw_articles()
    unprocessed = [a for a in raw_articles if a["article_id"] not in processed_ids]

    print(f"[process] {len(unprocessed)} articles")

    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        for i, article in enumerate(unprocessed):
            print(f"[{i+1}] {article.get('title','')[:40]}")

            try:
                ai_result = process_with_gemini(article, model)
                is_fallback = False

            except Exception as e:
                print(f"[ERROR] {e}")

                # 429対応
                if "429" in str(e):
                    match = re.search(r"seconds:\s*(\d+)", str(e))
                    wait = int(match.group(1)) if match else 60
                    print(f"[WAIT] {wait}s")
                    time.sleep(wait)

                    try:
                        ai_result = process_with_gemini(article, model)
                        is_fallback = False
                    except Exception as e2:
                        print(f"[RETRY FAIL] {e2}")
                        ai_result = fallback_record(article)
                        is_fallback = True
                else:
                    ai_result = fallback_record(article)
                    is_fallback = True

            record = {
                "article_id": article["article_id"],
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "published_at": article.get("published_at", ""),
                "source": article.get("source", ""),
                "master_category": ai_result.get("master_category", "OTHER"),
                "summary": ai_result.get("summary", article.get("title", "")),
                "tags": ai_result.get("tags", []),
                "score_interest": float(ai_result.get("score_interest", 0.5)),
                "score_quality": float(ai_result.get("score_quality", 0.5)),
                "score_novelty": 1.0,
                "final_score": calc_final_score(
                    float(ai_result.get("score_interest", 0.5)),
                    float(ai_result.get("score_quality", 0.5)),
                    1.0
                ),
                "is_fallback": is_fallback,
                "is_read": False,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }

            f.write(json.dumps(record, ensure_ascii=False) + "\n")

            # 通常インターバル
            time.sleep(20)

    print("[done]")

if __name__ == "__main__":
    process_all()
