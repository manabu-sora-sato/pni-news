import streamlit as st
import json
import os
from datetime import datetime

# ===== 設定 =====
RAW_FILE = "data/raw_news.jsonl"
FEEDBACK_FILE = "data/user_feedback_log.jsonl"
MAX_DISPLAY = 10

# ===== データ読み込み =====
def load_raw_articles():
    articles = []
    if not os.path.exists(RAW_FILE):
        return articles

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                articles.append(json.loads(line))
            except:
                continue

    # 日付でソート（新しい順）
    articles.sort(key=lambda x: x.get("published", ""), reverse=True)

    return articles[:MAX_DISPLAY]

# ===== フィードバック保存 =====
def save_feedback(article, feedback_type):
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "title": article.get("title", ""),
        "url": article.get("url", ""),
        "feedback": feedback_type
    }

    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

# ===== UI =====
st.set_page_config(page_title="PNI News", layout="wide")

st.title("📰 PNI News (Raw Mode)")
st.sidebar.title("メニュー")
st.sidebar.write("（仮）フィルタは後で実装")

st.markdown("AI未使用：全件表示 + Good/Bad収集")

articles = load_raw_articles()

st.write(f"表示件数: {len(articles)}")

if not articles:
    st.warning("記事がありません（raw_news.jsonlを確認してください）")

# ===== 表示ループ =====
for i, article in enumerate(articles):
    title = article.get("title", "No Title")
    url = article.get("url", "#")
    published = article.get("published", "")

    st.markdown("---")

    st.markdown(f"### {title}")

    if published:
        st.caption(published)

    st.markdown(f"[記事を開く]({url})")

    col1, col2 = st.columns(2)

    # Goodボタン
    if col1.button(f"👍 Good_{i}"):
        save_feedback(article, "good")
        st.success("Goodを記録しました")

    # Badボタン
    if col2.button(f"👎 Bad_{i}"):
        save_feedback(article, "bad")
        st.info("Badを記録しました")
