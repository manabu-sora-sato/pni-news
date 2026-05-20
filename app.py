"""
app.py - Streamlit UI
PNI: Personalized News Intelligence
"""

import os
import requests
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.data_loader import load_articles, mark_as_read, count_articles
from utils.feedback import save_feedback, load_feedback


def restore_feedback_from_github():
    token = os.environ.get("GITHUB_TOKEN_READ", "")
    if not token:
        return

    feedback_path = Path("data/user_feedback_log.jsonl")
    feedback_path.parent.mkdir(exist_ok=True)

    if feedback_path.exists() and feedback_path.stat().st_size > 0:
        return

    try:
        url = "https://raw.githubusercontent.com/manabu-sora-sato/pni-news/main/data/user_feedback_log.jsonl"
        headers = {"Authorization": f"token {token}"}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            lines = [l for l in response.text.splitlines() if l.strip().startswith("{")]
            if lines:
                feedback_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    except Exception as e:
        print(f"[restore] failed: {e}")


# ─── 初期設定 ─────────────────────────────────
st.set_page_config(
    page_title="PNI",
    page_icon="📰",
    layout="wide",
)

if "init_done" not in st.session_state:
    restore_feedback_from_github()
    st.session_state["init_done"] = True


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
    st.markdown("## 📰 PNI")

    selected_category = st.radio(
        "カテゴリ",
        CATEGORIES,
        format_func=lambda c: CATEGORY_LABELS.get(c, c),
    )

    # ★ 未読のみデフォルトON
    unread_only = st.toggle("未読のみ表示", value=True)

    total_count = count_articles()
    unread_count = count_articles(unread_only=True)

    st.write(f"総記事数: {total_count}")
    st.write(f"未読: {unread_count}")

    if st.button("✅ 表示中を全既読"):
        articles_to_mark = load_articles(unread_only=unread_only, category=selected_category)
        for a in articles_to_mark:
            mark_as_read(a["article_id"])
        st.rerun()


# ─── メイン ─────────────────────────────────
st.markdown(f"### {CATEGORY_LABELS.get(selected_category)}")

articles = load_articles(unread_only=unread_only, category=selected_category)

if not articles:
    st.info("📭 表示できる記事がありません")
else:
    st.caption(f"{len(articles)} 件")

    for article in articles:
        article_id = article["article_id"]
        category = article.get("master_category", "OTHER")
        is_read = article.get("is_read", False)

        col1, col2 = st.columns([1, 10])

        with col1:
            # ★ GOOD → 既読化
            if st.button("👍", key=f"like_{article_id}"):
                save_feedback(article_id, [], category, "like")
                mark_as_read(article_id)
                st.rerun()

            # ★ BAD → 既読化
            if st.button("👎", key=f"dislike_{article_id}"):
                save_feedback(article_id, [], category, "dislike")
                mark_as_read(article_id)
                st.rerun()

            # 手動既読
            if not is_read:
                if st.button("✓", key=f"read_{article_id}"):
                    mark_as_read(article_id)
                    st.rerun()

        with col2:
            st.markdown(f"[{article.get('title','')}]({article.get('url','')})")
