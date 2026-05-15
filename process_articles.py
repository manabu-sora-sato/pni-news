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

CATEGORY_TAGS = {
    "NEWS": ["政治", "社会", "国際", "事件", "災害", "スポーツ", "文化", "生活"],
    "DEV": ["Python", "AI", "LLM", "Automation", "Infrastructure", "機械学習", "クラウド", "セキュリティ"],
    "ECON": ["Finance", "Investment", "GlobalAffairs", "Markets", "仮想通貨", "為替", "株式"],
    "HEALTH": ["Fitness", "Diet", "Lifestyle", "Wellness", "医療", "栄養", "メンタル"],
    "THOUGHT": ["Philosophy", "Science", "Sociology", "SF", "倫理", "未来"],
    "OTHER": ["その他"],
}

PROMPT_TEMPLATE = """
あなたはニュース記事を分析・要約するAIです。
以下の記事を分析し、必ず**日本語で**JSON形式のみを返してください。

記事タイトル: {title}
カテゴリヒント: {category}
記事URL: {url}

カテゴリの定義:
- NEWS: 一般ニュース（政治・社会・国際・事件・災害・スポーツ・文化など）
- DEV: テクノロジー・AI・プログラミング・インフラ・セキュリティ
- ECON: 経済・投資・金融・マーケット・ビジネス
- HEALTH: 健康・医療・フィットネス・栄養・メンタル
- THOUGHT: 哲学・科学・社会学・SF・倫理・未来
- OTHER: 上記いずれにも属さないもの

出力形式（JSONのみ、説明文不要）:
{{
  "summary": "記事の内容を日本語で1〜2文に要約（英語記事も必ず日本語に翻訳して要約）",
  "tags": ["タグ1", "タグ2", "タグ3"],
  "master_category": "NEWS/DEV/ECON/HEALTH/THOUGHT/OTHERのいずれか",
  "score_interest": 0.0〜1.0の数値（フィードバック適合度推定）,
  "score_quality": 0.0〜1.0の数値（情報価値・信頼性）
}}
"""

def load_processed_ids() -> set:
    ids = set()
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        ids.add(json.loads(line)["article_id"])
                    except Exception:
                        pass
    return ids

def load_raw_articles() -> list:
    articles = []
    if not RAW_FILE.exists():
        return articles
    with open(RAW_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    articles.append(json.loads(line))
                except Exception:
                    pass
    return articles

def purge_old_processed():
    if not PROCESSED_FILE.exists():
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    kept = []
    with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                pub = datetime.fromisoformat(record.get("published_at", "2000-01-01T00:00:00+00:00"))
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=timezone.utc)
                if pub >= cutoff:
                    kept.append(line)
            except Exception:
                kept.append(line)
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(kept) + ("\n" if kept else ""))
    print(f"[purge] processed: kept {len(kept)} records")

def calc_novelty(article_id: str, all_processed: list) -> float:
    """Novelty = 既処理済み数に基づく新規性スコア（ルールベース）"""
    total = len(all_processed)
    if total == 0:
        return 1.0
    # 単純に新しいほど高スコア（処理順）
    for i, a in enumerate(all_processed):
        if a.get("article_id") == article_id:
            return max(0.1, 1.0 - (i / total))
    return 1.0

def calc_final_score(interest: float, quality: float, novelty: float) -> float:
    return round(interest * 0.4 + quality * 0.3 + novelty * 0.3, 4)

def extract_json(text: str) -> dict:
    """APIレスポンスからJSONを安全に抽出"""
    text = text.strip()
    # ```json ... ``` を除去
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    # 最初の { から最後の } を抽出
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("JSON not found in response")
    return json.loads(text[start:end])

def process_with_gemini(article: dict, model) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        title=article.get("title", ""),
        category=article.get("master_category", "OTHER"),
        url=article.get("url", ""),
    )
    response = model.generate_content(prompt)
    parsed = extract_json(response.text)
    return parsed

def fallback_record(article: dict) -> dict:
    """Gemini失敗時のルールベースフォールバック"""
    return {
        "summary": article.get("title", ""),
        "tags": [article.get("master_category", "OTHER")],
        "master_category": article.get("master_category", "OTHER"),
        "score_interest": 0.5,
        "score_quality": 0.5,
        "is_fallback": True,
    }

def process_all():
    DATA_DIR.mkdir(exist_ok=True)
    purge_old_processed()

    if not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY が設定されていません")
        return

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")  # 無料枠

    processed_ids = load_processed_ids()
    raw_articles = load_raw_articles()
    unprocessed = [a for a in raw_articles if a["article_id"] not in processed_ids]

    print(f"[process] unprocessed: {len(unprocessed)} articles")

    new_processed = []
    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        for i, article in enumerate(unprocessed):
            print(f"[{i+1}/{len(unprocessed)}] {article.get('title', '')[:50]}")
            try:
                ai_result = process_with_gemini(article, model)
                is_fallback = False
            except Exception as e:
                print(f"  [FALLBACK] {e}")
                ai_result = fallback_record(article)
                is_fallback = True

            novelty = calc_novelty(article["article_id"], new_processed)
            score_interest = float(ai_result.get("score_interest", 0.5))
            score_quality = float(ai_result.get("score_quality", 0.5))
            final_score = calc_final_score(score_interest, score_quality, novelty)

            record = {
                "article_id": article["article_id"],
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "published_at": article.get("published_at", ""),
                "source": article.get("source", ""),
                "source_lang": article.get("source_lang", ""),
                "master_category": ai_result.get("master_category", article.get("master_category", "OTHER")),
                "summary": ai_result.get("summary", article.get("title", "")),
                "tags": ai_result.get("tags", []),
                "score_interest": score_interest,
                "score_quality": score_quality,
                "score_novelty": novelty,
                "final_score": final_score,
                "is_fallback": is_fallback,
                "is_read": False,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            new_processed.append(record)

            # Gemini Free Tier: レート制限対策
            if not is_fallback:
                time.sleep(2)

    print(f"[process] done. processed: {len(new_processed)} articles")

if __name__ == "__main__":
    process_all()
