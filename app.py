# メイン部分だけ抜粋（そのまま置き換え）

st.markdown(f"### {CATEGORY_LABELS.get(selected_category)}")

articles = load_articles(unread_only=unread_only, category=selected_category)

if not articles:
    st.info("📭 表示できる記事がありません")
else:
    st.caption(f"{len(articles)} 件（最大20件表示）")

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
