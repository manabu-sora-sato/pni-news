"""
app.py - Streamlit UI
PNI: Personalized News Intelligence
"""

import os
import requests
import streamlit as st
import sys
import datetime
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler

sys.path.insert(0, str(Path(__file__).parent))

# 一括管理化に伴い、読み書きはすべて共通のデータローダー（統合ファイル）に一元化します
from utils.data_loader import load_articles, mark_as_read, mark_all_as_read, count_articles, count_fallback_articles
from utils.feedback import save_feedback, load_feedback
from utils.github_sync import sync_actions_to_github

# ─── ページ設定（必ず最初に実行する） ───────────────────
st.set_page_config(
    page_title="PNI - パーソナル・ニュース・インテリジェンス",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── 1時間ごとの独立バックグラウンド同期タイマー ─────────────────
@st.cache_resource
def init_background_sync():
    scheduler = BackgroundScheduler()
    # ニュース取得(2時間)とは完全に切り離し、1時間(60分)ごとにGitHubへプッシュ
    scheduler.add_job(sync_actions_to_github, 'interval', minutes=60)
    scheduler.start()
    return scheduler

# ページ設定の直後でタイマーを起動
init_background_sync()

# ─── カスタムCSS ─────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans JP', sans-serif;
}

.news-card {
    background: #1a1a2e;
    border: 1px solid #16213e;
    border-left: 4px solid #0f3460;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 6px;
    transition: border-left-color 0.2s;
}
.news-card:hover { border-left-color: #e94560; }
.news-card.is-read { opacity: 0.5; }

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
.badge-DEV     { background: #0f3460; color: #58a6ff; border: 1px solid #58a6ff44; }
.badge-ECON   { background: #1a3a1a; color: #56d364; border: 1px solid #56d36444; }
.badge-HEALTH { background: #3a1a1a; color: #f78166; border: 1px solid #f7816644; }
.badge-THOUGHT{ background: #2a1a3a; color: #bc8cff; border: 1px solid #bc8cff44; }
.badge-OTHER  { background: #2a2a2a; color: #8b949e; border: 1px solid #8b949e44; }
.badge-FB     { background: #1a2a1a; color: #3fb950; border: 1px solid #3fb95044; }

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

.summary-text {
    font-size: 13px;
    color: #c9d1d9;
    line-height: 1.6;
    margin: 6px 0 4px 0;
}

.article-title a {
    font-size: 15px;
    font-weight: 700;
    color: #e6edf3;
    text-decoration: none;
}
.article-title a:hover { color: #e94560; }

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
    st.markdown("Personalized News Intelligence")
    
    # ─── 最終取得日時の表示 ──────────────────
    raw_path = Path("data/raw_news.jsonl")
    if raw_path.exists():
        mtime = raw_path.stat().st_mtime
        last_fetch_dt = datetime.datetime.fromtimestamp(mtime)
        last_fetch_str = last_fetch_dt.strftime("%m/%d %H:%M")
        st.markdown(f"⏱️ 最終取得: `{last_fetch_str}`")
    else:
        st.markdown("⏱️ 最終取得: `---`")
        
    st.markdown("---")

    selected_category = st.radio(
        "カテゴリ",
        CATEGORIES,
        format_func=lambda c: CATEGORY_LABELS.get(c, c),
    )

    unread_only = st.toggle("未読のみ表示", value=True)
    st.markdown("---")

    total_count = count_articles()
    unread_count = count_articles(unread_only=True)
    fallback_count = count_fallback_articles()
    
    # 手元の一括管理ファイルからフィードバック（GOOD/BAD数）を取得
    liked_count = 0
    try:
        fb = load_feedback()
        liked_count = len(fb)
    except Exception:
        pass

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

    st.markdown(f"""
    <div class="stat-box" style="margin-top:8px">
        <div class="stat-num">👍 {liked_count}</div>
        <div class="stat-label">学習済みフィードバック</div>
    </div>""", unsafe_allow_html=True)

    if fallback_count > 0:
        st.markdown(f"""
        <div class="stat-box" style="margin-top:8px">
            <div class="stat-num" style="color:#f85149">⚠️ {fallback_count}</div>
            <div class="stat-label">未処理記事</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 一括操作")
    
    # 一括操作のコールバック定義
    def handle_bulk_read(cats=selected_category, unread=unread_only):
        articles_to_mark = load_articles(unread_only=unread, category=cats)
        mark_all_as_read([a["article_id"] for a in articles_to_mark])

    def handle_bulk_bad(cats=selected_category, unread=unread_only):
        articles_to_bad = load_articles(unread_only=unread, category=cats)
        for a in articles_to_bad:
            save_feedback(a["article_id"], a.get("tags", []), a.get("master_category", "OTHER"), "dislike")
        mark_all_as_read([a["article_id"] for a in articles_to_bad])

    st.button("✅ 表示中を全既読", on_click=handle_bulk_read)
    st.button("👎 表示中を全BAD", on_click=handle_bulk_bad)

    st.markdown("---")
    st.caption("v3.6 | GitHub Actions")

# ─── メインコンテンツ ─────────────────────────────────
st.markdown(f"### {CATEGORY_LABELS.get(selected_category, selected_category)}")

total_matched_count = count_articles(unread_only=unread_only, category=selected_category)
articles = load_articles(unread_only=unread_only, category=selected_category)

# ─── 共通スコープのコールバック関数 ───
def handle_action(action_type, aid, atags, acat):
    if action_type == "like":
        save_feedback(aid, atags, acat, "like")
        mark_as_read(aid)
    elif action_type == "dislike":
        save_feedback(aid, atags, acat, "dislike")
        mark_as_read(aid)
    elif action_type == "read":
        mark_as_read(aid)

# ─── パス検証用テストコード ───
st.write("実際の書き込み先パス:", str(Path(__file__).parent / "data" / "user_actions.jsonl"))

if not articles:
    st.info("📭 表示できる記事がありません。GitHub Actionsでフェッチを実行してください。")
else:
    st.caption(f"{len(articles)} / {total_matched_count} 件表示中")

    for article in articles:
        article_id = article["article_id"]
        category = article.get("master_category", "OTHER")
        is_read = article.get("is_read", False)
        tags = article.get("tags", [])
        score = article.get("adjusted_score", article.get("final_score", 0.5))
        is_fallback = article.get("is_fallback", False)

        badge_html = f'<span class="badge badge-{category}">{category}</span>'
        if is_fallback:
            badge_html += '<span class="badge badge-FB">RAW</span>'

        tags_html = " ".join(f'<span class="tag">{t}</span>' for t in tags[:5])

        if score >= 0.70:
            score_color = "#3fb950"
            score_label = "◎"
        elif score >= 0.40:
            score_color = "#d29922"
            score_label = "○"
        else:
            score_color = "#f85149"
            score_label = "△"

        pub = article.get("published_at", "")[:10]
        source = article.get("source", "")

        btn_col, content_col = st.columns([1, 10])

        with btn_col:
            st.markdown("<div style='padding-top:8px'>", unsafe_allow_html=True)
            st.button("👍", key=f"like_{article_id}", help="興味あり", on_click=handle_action, args=("like", article_id, tags, category))
            st.button("👎", key=f"dislike_{article_id}", help="興味なし", on_click=handle_action, args=("dislike", article_id, tags, category))
            
            if not is_read:
                st.button("✓", key=f"read_{article_id}", help="既読にする", on_click=handle_action, args=("read", article_id, tags, category))
            st.markdown("</div>", unsafe_allow_html=True)

        with content_col:
            st.markdown(f"""
            <div class="news-card">
                {badge_html}
                <span style="font-size:11px;color:#6e7681">{source} · {pub}</span>
                <div class="article-title">
                    <a href="{article['url']}" target="_blank">{article.get('title','')}</a>
                </div>
                <div class="summary-text">{article.get('summary','')}</div>
                <div style="margin-top:4px">
                    {tags_html}
                    <span style="font-size:10px;color:{score_color};font-family:monospace;margin-left:6px">{score_label} {score:.3f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
