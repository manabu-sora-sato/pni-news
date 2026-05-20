import os
import requests
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.data_loader import load_articles, mark_as_read, count_articles
from utils.feedback import save_feedback


# ─── 初期化 ─────────────────────────────────
st.set_page_config(page_title="PNI", layout="wide")

# ─── カテゴリ ─────────────────────────────────
CATEGORIES = ["ALL", "NEWS", "DEV", "ECON", "HEALTH", "THOUGHT", "OTHER"]
CATEGORY_LABELS = {
    "ALL": "🌐 すべて",
    "NEWS": "📰 ニュース",
    "DEV": "💻 テック",
    "ECON": "📈 経済",
    "HEALTH": "💪 健康",
    "THOUGHT": "🧠 思想",
    "OTHER": "📌 その他",
}

# ─── サイドバー ─────────────────────────────────
with st.sidebar:
    st.title("📰 PNI")

    selected_category = st.radio(
        "カテゴリ",
        CATEGORIES,
        format_func=lambda c: CATEGORY_LABELS.get(c, c),
    )

    unread_only = st.toggle("未読のみ", value=True)

    total_count = count_articles()
    unread_count = count_articles(unread_only=True)

    st.write(f"総記事数: {total_count}")
    st.write(f"未読: {unread_count}")

# ─── メイン ─────────────────────────────────
st.markdown(f"### {CATEGORY_LABELS.get(selected_category)}")

articles = load_articles(unread_only=unread_only, category=selected_category)

if not articles:
    st.info("記事がありません")
else:
    st.write(f"{len(articles)} 件（最大20件）")

    for article in articles:
        article_id = article["article_id"]
        category = article.get("master_category", "OTHER")

        col1, col2 = st.columns([1, 10])

        with col1:
            if st.button("👍", key=f"like_{article_id}"):
                save_feedback(article_id, [], category, "like")
                mark_as_read(article_id)
                st.rerun()

            if st.button("👎", key=f"dislike_{article_id}"):
                save_feedback(article_id, [], category, "dislike")
                mark_as_read(article_id)
                st.rerun()

        with col2:
            st.markdown(f"[{article.get('title','')}]({article.get('url','')})")
