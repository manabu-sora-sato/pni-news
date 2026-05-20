import streamlit as st
import json
from pathlib import Path
from utils.data_loader import ActionDataLoader
from utils.github_sync import sync_actions_to_github
from apscheduler.schedulers.background import BackgroundScheduler

# ページ基本設定
st.set_page_config(page_title="PNI News Reader", layout="wide")

# 1. バックグラウンドタイマーの初期化（1時間ごとにGitHubへ送信）
@st.cache_resource
def init_background_sync():
    scheduler = BackgroundScheduler()
    # 1時間(60分)ごとにsync_actions_to_github関数を実行する
    scheduler.add_job(sync_actions_to_github, 'interval', minutes=60)
    scheduler.start()
    return scheduler

# タイマーを起動（Streamlitの再描画で二重起動しないようcache_resource化）
init_background_sync()

# データローダーの呼び出し
db = ActionDataLoader()

# テスト用のダミーRSSニュースデータ（本来はRSSから読み込まれた news_list.jsonl 等を展開）
# ※ 実際の環境に合わせて、ここのニュース読み込み元を設定してください
def load_raw_news():
    # 本来のニュースソースファイルを読み込む想定のプレースホルダー
    # ここでは仮の構造を示しています
    return [
        {"article_id": "3fd158b12f01", "title": "上海 飲食店で傷害事件か 外務省...", "url": "https://example.com/1"},
        {"article_id": "fde2081f330a", "title": "兵庫 たつの 住宅で親子の女性2人...", "url": "https://example.com/2"},
        {"article_id": "82c95635f000", "title": "1〜3月のGDP 年率換算+2.1%...", "url": "https://example.com/3"}
    ]

raw_articles = load_raw_news()

# 2. HFローカルの仕分けデータを読み込む
processed_ids = db.load_processed_ids()

# 3. 画面に表示する未読ニュースのフィルタリング（HFローカルのデータのみを参照）
display_articles = [a for a in raw_articles if a["article_id"] not in processed_ids]

# UIコンポーネントの描画
st.title("PNI News Reader")

# カウンターや統計の表示
counts = db.get_action_counts()
st.sidebar.metric("未読件数", len(display_articles))
st.sidebar.write(f"👍 GOOD: {counts['good']} 件")
st.sidebar.write(f"👎 BAD: {counts['bad']} 件")
st.sidebar.write(f"✓ 既読: {counts['read']} 件")

# 手動同期ボタン（動作確認用）
if st.sidebar.button("今すぐGitHubにバックアップ"):
    with st.spinner("送信中..."):
        sync_actions_to_github()
    st.sidebar.success("同期処理を要求しました（ログを確認してください）")

st.write("---")

# ニュース一覧の表示
if not display_articles:
    st.info("未読のニュースはありません。すべて処理済みです。")
else:
    for article in display_articles:
        a_id = article["article_id"]
        
        col1, col2, col3, col4 = st.columns([6, 1, 1, 1])
        
        with col1:
            st.write(f"[{article['title']}]({article['url']})")
            
        with col2:
            if st.button("👍 GOOD", key=f"good_{a_id}"):
                db.save_action(a_id, "good")
                st.rerun()
                
        with col3:
            if st.button("👎 BAD", key=f"bad_{a_id}"):
                db.save_action(a_id, "bad")
                st.rerun()
                
        with col4:
            if st.button("✓ 既読", key=f"read_{a_id}"):
                db.save_action(a_id, "read")
                st.rerun()
        st.write("---")
