"""
app.py - Streamlit UI
PNI: Personalized News Intelligence
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.data_loader import load_articles, mark_as_read, mark_all_as_read
from utils.feedback import save_feedback



# ─── ページ設定 ─────────────────────────────────
st.set_page_config(
    page_title="PNI - パーソナル・ニュース・インテリジェンス",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── カスタムCSS ─────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans JP', sans-serif;
}

/* カード */
.news-card {
    background: #1a1a2e;
    border: 1px solid #16213e;
    border-left: 4px solid #0f3460;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 10px;
    transition: border-left-color 0.2s;
}
.news-card:hover {
    border-left-color: #e94560;
}
.news-card.is-read {
    opacity: 0.5;
}

/* カテゴリバッジ */
.badge {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.05em;
    margin-right: 6px;
}
.badge-NEWS   { background: #1a2a3a; color: #79c0ff; border: 1px solid #79c0ff44; }
.badge-DEV    { background: #0f3460; color: #58a6ff; border: 1px solid #58a6ff44; }
.badge-ECON   { background: #1a3a1a; color: #56d364; border: 1px solid #56d36444; }
.badge-HEALTH { background: #3a1a1a; color: #f78166; border: 1px solid #f7816644; }
.badge-THOUGHT{ background: #2a1a3a; color: #bc8cff; border: 1px solid #bc8cff44; }
.badge-OTHER  { background: #2a2a2a; color: #8b949e; border: 1px solid #8b949e44; }
.badge-FB     { background: #1a2a1a; color: #3fb950; border: 1px solid #3fb95044; }

/* スコアバー */
.score-bar-wrap { height: 4px; background: #0d1117; border-radius: 2px; margin: 6px 0 2px 0; }
.score-bar { height: 4px; border-radius: 2px; background: linear-gradient(90deg, #0f3460, #e94560); }

/* タグ */
.tag {
    display: inline-block;
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 4px;
    background: #0d1117;
    color: #8b949e;
    border: 1px solid #30363d;
    margin: 2px 2px 0 0;
}

/* サマリー */
.summary-text {
    font-size: 13px;
    color: #c9d1d9;
    line-height: 1.6;
    margin: 6px 0 8px 0;
}

/* タイトル */
.article-title a {
    font-size: 15px;
    font-weight: 700;
    color: #e6edf3;
    text-decoration: none;
}
.article-title a:hover { color: #e94560; }

/* フォールバック表示 */
.fallback-note {
    font-size: 10px;
    color: #6e7681;
    font-style: italic;
}

/* 統計 */
.stat-box {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 16px;
    text-align: center;
}
.stat-num { font-size: 28px; font-weight: 700; color: #e6edf3; }
.stat-label { font-size: 11px; color: #8b949e; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

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

    unread_only = st.toggle("未読のみ表示", value=False)
    st.markdown("---")

    # 統計
    all_articles = load_articles()
    unread_count = sum(1 for a in all_articles if not a.get("is_read", False))
    liked_count = 0
    try:
        from utils.feedback import load_feedback
        fb = load_feedback()
        liked_count = sum(1 for f in fb if f["action"] == "like")
    except Exception:
        pass

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-num">{len(all_articles)}</div>
            <div class="stat-label">総記事数</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-num">{unread_count}</div>
            <div class="stat-label">未読</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="stat-box" style="margin-top:8px">
        <div class="stat-num">👍 {liked_count}</div>
        <div class="stat-label">学習済みフィードバック</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 一括操作")
    if st.button("✅ 表示中を全既読"):
        articles_to_mark = load_articles(unread_only=unread_only, category=selected_category)
        mark_all_as_read([a["article_id"] for a in articles_to_mark])
        st.rerun()

    st.markdown("---")
    st.caption("v3.6 | GitHub Actions + Gemini API")

# ─── メインコンテンツ ─────────────────────────────────
st.markdown(f"### {CATEGORY_LABELS.get(selected_category, selected_category)}")

articles = load_articles(unread_only=unread_only, category=selected_category)

if not articles:
    st.info("📭 表示できる記事がありません。GitHub Actionsでフェッチを実行してください。")
    st.markdown("""
    **初回セットアップ後の手順:**
    1. リポジトリの Actions タブを開く
    2. `Fetch RSS` ワークフローを手動実行
    3. `Process Articles` ワークフローを手動実行
    4. このページをリロード
    """)
else:
    st.caption(f"{len(articles)} 件表示中")

    for article in articles:
        article_id = article["article_id"]
        category = article.get("master_category", "OTHER")
        is_read = article.get("is_read", False)
        tags = article.get("tags", [])
        score = article.get("adjusted_score", article.get("final_score", 0.5))
        is_fallback = article.get("is_fallback", False)

        card_class = "news-card is-read" if is_read else "news-card"

        # バッジHTML
        badge_html = f'<span class="badge badge-{category}">{category}</span>'
        if is_fallback:
            badge_html += '<span class="badge badge-FB">RAW</span>'

        # タグHTML
        tags_html = " ".join(f'<span class="tag">{t}</span>' for t in tags[:5])

        # スコアバー
        score_pct = int(score * 100)
        score_bar = f"""
        <div class="score-bar-wrap">
            <div class="score-bar" style="width:{score_pct}%"></div>
        </div>
        <span style="font-size:10px;color:#6e7681;font-family:monospace">score: {score:.3f}</span>
        """

        # ソース・日時
        pub = article.get("published_at", "")[:10]
        source = article.get("source", "")
        meta = f'<span style="font-size:11px;color:#6e7681">{source} · {pub}</span>'

        st.markdown(f"""
        <div class="{card_class}">
            {badge_html}
            {meta}
            <div class="article-title">
                <a href="{article['url']}" target="_blank">{article.get('title','')}</a>
            </div>
            <div class="summary-text">{article.get('summary','')}</div>
            {tags_html}
            {score_bar}
        </div>
        """, unsafe_allow_html=True)

        # ボタン行
        col1, col2, col3, col4 = st.columns([1, 1, 1, 6])
        with col1:
            if st.button("👍", key=f"like_{article_id}", help="興味あり（学習に使われます）"):
                save_feedback(article_id, tags, category, "like")
                mark_as_read(article_id)
                st.rerun()
        with col2:
            if st.button("👎", key=f"dislike_{article_id}", help="興味なし（学習に使われます）"):
                save_feedback(article_id, tags, category, "dislike")
                mark_as_read(article_id)
                st.rerun()
        with col3:
            if not is_read:
                if st.button("✓", key=f"read_{article_id}", help="既読にする"):
                    mark_as_read(article_id)
                    st.rerun()
