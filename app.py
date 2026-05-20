"""
app.py - Streamlit UI
PNI: Personalized News Intelligence（RAW表示・フィードバック記録モード）
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


# ─── ページ設定 ─────────────────────────────────
st.set_page_config(
    page_title="PNI - パーソナル・ニュース・インテリジェンス",
    page_icon="📰",
    layout="wide",
)

# 初期化（1回だけ）
if "init_done" not in st.session_state:
    try:
        restore_feedback_from_github()
    except Exception as e:
        print(f"[restore error] {e}")
    st.session_state["init_done"] = True


# ─── カテゴリ定数 ─────────────────────────────────
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
    st.markdown("**Personalized News Intelligence**")
    st.markdown("---")

    selected_category = st.radio(
        "カテゴリ",
        CATEGORIES,
        format_func=lambda c: CATEGORY_LABELS.get(c, c),
    )

    unread_only = st.toggle("未読のみ表示", value=True)
    st.markdown("---")

    # ✅ 修正：ここを元に戻す
    total_count = count_articles()
    unread_count = count_articles(unread_only=True)

    try:
        fb = load_feedback()
        liked_count = sum(1 for f in fb if f.get("action") == "like")
        disliked_count = sum(1 for f in fb if f.get("action") == "dislike")
    except Exception:
        liked_count = disliked_count = 0

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-num">{total_count}</div>
            <div class="stat-label">総記事数</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-num">{unread_count}</div>
            <div class="stat-label">未読</div>
        </div>""", unsafe_allow_html=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown(f"""
        <div class="stat-box" style="margin-top:8px">
            <div class="stat-num" style="color:#3fb950">👍 {liked_count}</div>
            <div class="stat-label">good</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="stat-box" style="margin-top:8px">
            <div class="stat-num" style="color:#f85149">👎 {disliked_count}</div>
            <div class="stat-label">bad</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ✅ 修正：ここも戻す
    if st.button("✅ 表示中を全既読"):
        articles_to_mark = load_articles(unread_only=unread_only, category=selected_category)
        for a in articles_to_mark:
            mark_as_read(a["article_id"])
        st.rerun()

    st.markdown("---")
    st.caption("v4.0 | RAWモード（フィードバック収集中）")


# ─── メインコンテンツ ─────────────────────────────────
st.markdown(f"### {CATEGORY_LABELS.get(selected_category, selected_category)}")

# ✅ 修正：ここが一番重要
articles = load_articles(unread_only=unread_only, category=selected_category)

if not articles:
    st.info("📭 表示できる記事がありません。")
else:
    st.caption(f"{len(articles)} 件表示中")

    for article in articles:
        article_id = article["article_id"]
        category = article.get("master_category", "OTHER")
        is_read = article.get("is_read", False)
        pub = article.get("published_at", "")[:10]
        source = article.get("source", "")

        badge_html = f'<span class="badge badge-{category}">{category}</span>'

        btn_col, content_col = st.columns([1, 10])

        with btn_col:
            if st.button("👍", key=f"like_{article_id}"):
                save_feedback(article_id, [], category, "like")
                st.rerun()

            if st.button("👎", key=f"dislike_{article_id}"):
                save_feedback(article_id, [], category, "dislike")
                st.rerun()

            if not is_read:
                if st.button("✓", key=f"read_{article_id}"):
                    mark_as_read(article_id)
                    st.rerun()

        with content_col:
            read_class = "is-read" if is_read else ""
            st.markdown(f"""
            <div class="news-card {read_class}">
                {badge_html}
                <span style="font-size:11px;color:#6e7681">{source} · {pub}</span>
                <div class="article-title">
                    <a href="{article['url']}" target="_blank">{article.get('title','')}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
