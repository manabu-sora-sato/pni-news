"""
app.py - Streamlit UI (v4.1: ヘッダー検知型エンドポイント搭載)
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

from utils.data_loader import load_articles, mark_as_read, mark_all_as_read, count_articles, count_fallback_articles
from utils.feedback import save_feedback, load_feedback

# ─── GitHub Actions専用のエンドポイント（ヘッダー検知方式） ───
# Actionsからの通信に含まれる特定のヘッダーを検知し、ログテキストを出力します。
from streamlit.web.server.websocket_headers import _get_websocket_headers
headers = _get_websocket_headers()

if headers and headers.get("X-Download-Token") == "pni-secure-sync":
    fb_records = load_feedback()
    if fb_records:
        import json
        output = "\n".join(json.dumps(r, ensure_ascii=False) for r in fb_records) + "\n"
        st.text(output)
    else:
        st.text("")
    st.stop()

st.set_page_config(
    page_title="PNI - パーソナル・ニュース・インテリジェンス",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

with st.sidebar:
    st.markdown("## 📰 PNI")
    st.markdown("Personalized News Intelligence")
    
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
    
    def handle_bulk_read(cats=selected_category, unread=unread_only):
        articles_to_mark = load_articles(unread_only=unread, category=cats)
        mark_all_as_read([a["article_id"] for a in articles_to_mark])

    def handle_bulk_bad(cats=selected_category, unread=unread_only):
        articles_to_bad = load_articles(unread_only=unread, category=cats)
        for a in articles_to_bad:
            save_feedback(a["article_id"], a.get("tags", []), a.get("master_category", "OTHER"), "dislike")

    st.button("✅ 表示中を全既読", on_click=handle_bulk_read)
    st.button("👎 表示中を全BAD", on_click=handle_bulk_bad)

    st.markdown("---")
    st.caption("v4.1 | GitHub Actions")

# ─── メインコンテンツ ─────────────────────────────────
st.markdown(f"### {CATEGORY_LABELS.get(selected_category, selected_category)}")

# ─── 動的検証表示 ───
target_file = Path("/tmp/pni-data/user_feedback_log.jsonl")
if not target_file.exists():
    target_file = Path(__file__).parent.parent / "data" / "user_feedback_log.jsonl"

if target_file.exists():
    file_size = target_file.stat().st_size
    st.success(f"【最新版コード動的検証】ファイル存在確認: OK / サイズ: {file_size} bytes")
else:
    st.warning("【最新版コード動的検証】まだフィードバックデータが書き込まれていません。ボタンを押してください。")

total_matched_count = count_articles(unread_only=unread_only, category=selected_category)
articles = load_articles(unread_only=unread_only, category=selected_category)

def handle_action(action_type, aid, atags, acat):
    if action_type == "like":
        save_feedback(aid, atags, acat, "like")
    elif action_type == "dislike":
        save_feedback(aid, atags, acat, "dislike")
    elif action_type == "read":
        mark_as_read(aid)

if not articles:
    st.info("📭 表示できる記事がありません。")
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
