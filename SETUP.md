# PNI セットアップガイド
## Personalized News Intelligence v3.6

---

## 📋 全体の流れ

```
[1] Gemini APIキー取得（5分）
[2] GitHubリポジトリ作成・コードアップロード（10分）
[3] GitHub Secrets設定（2分）
[4] Streamlit Cloud デプロイ（5分）
[5] 初回動作確認（3分）
```

---

## STEP 1: Gemini APIキーの取得（無料）

1. ブラウザで https://aistudio.google.com/ を開く
2. Googleアカウントでログイン
3. 左メニューの **「Get API key」** をクリック
4. **「Create API key」** → **「Create API key in new project」** をクリック
5. 表示されたAPIキー（`AIza...` で始まる文字列）を**コピーして安全な場所に保存**

> ⚠️ APIキーは一度しか表示されません。必ずメモしてください。

---

## STEP 2: GitHubリポジトリの作成

### 2-1. GitHubアカウントがない場合
https://github.com/join でアカウントを作成してください。

### 2-2. リポジトリ作成
1. https://github.com/new を開く
2. 以下のように入力:
   - **Repository name**: `pni-news`（任意の名前でOK）
   - **Visibility**: ✅ **Private**（必須！APIキーを守るため）
   - **Add a README file**: チェックしない
3. **「Create repository」** をクリック

### 2-3. コードのアップロード

#### 方法A: GitHub Desktop（推奨・GUIで簡単）
1. https://desktop.github.com/ からGitHub Desktopをインストール
2. 「Clone a repository」→ 作成した `pni-news` を選択
3. クローン先のフォルダに、このファイル一式をコピーする
4. GitHub Desktopで「Commit to main」→「Push origin」

#### 方法B: コマンドライン（gitがある場合）
```bash
cd このフォルダのパス
git init
git remote add origin https://github.com/あなたのユーザー名/pni-news.git
git add .
git commit -m "initial commit"
git branch -M main
git push -u origin main
```

### 2-4. アップロードするファイル構成の確認
```
pni-news/
├── .github/
│   └── workflows/
│       ├── fetch_rss.yml
│       └── process_articles.yml
├── .streamlit/
│   └── config.toml
├── utils/
│   ├── __init__.py
│   ├── data_loader.py
│   └── feedback.py
├── data/
│   └── .gitkeep
├── app.py
├── fetch_rss.py
├── process_articles.py
├── feeds.yaml
├── requirements.txt
└── .gitignore
```

---

## STEP 3: GitHub SecretsにAPIキーを登録

1. GitHubの `pni-news` リポジトリを開く
2. **「Settings」** タブをクリック
3. 左メニュー **「Secrets and variables」** → **「Actions」** をクリック
4. **「New repository secret」** をクリック
5. 以下を入力:
   - **Name**: `GEMINI_API_KEY`
   - **Secret**: STEP 1 でコピーしたAPIキー
6. **「Add secret」** をクリック

---

## STEP 4: Streamlit Cloudへのデプロイ

1. https://streamlit.io/cloud を開く
2. **「Sign up」** → **「Continue with GitHub」** でGitHubアカウントでログイン
3. **「New app」** をクリック
4. 以下を選択:
   - **Repository**: `あなたのユーザー名/pni-news`
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. **「Deploy!」** をクリック

> デプロイには1〜3分かかります。完了するとURLが発行されます（例: `https://あなたの名前-pni-news.streamlit.app`）

---

## STEP 5: 初回動作確認

### 5-1. GitHub ActionsでRSS取得を手動実行
1. GitHubの `pni-news` → **「Actions」** タブを開く
2. 左メニューの **「Fetch RSS」** をクリック
3. 右側の **「Run workflow」** → **「Run workflow」** をクリック
4. 緑のチェックマーク ✅ になれば成功

### 5-2. 記事処理を手動実行
1. 同じくActionsタブで **「Process Articles」** をクリック
2. **「Run workflow」** → **「Run workflow」** をクリック
3. ✅ になるまで待つ（2〜5分）

### 5-3. Streamlit Cloudで確認
1. Streamlit CloudのアプリURLを開く
2. 記事が表示されていれば完了！
3. 👍/👎 ボタンで学習を開始できます

---

## ⏰ 自動実行スケジュール

設定済みのスケジュール（JST）:
| 時間 | 動作 |
|------|------|
| 6:00 | RSS取得 → 記事処理 |
| 12:00 | RSS取得 → 記事処理 |
| 18:00 | RSS取得 → 記事処理 |

---

## ❓ よくあるトラブル

### Q: Actions実行時に「Permission denied」エラーが出る
**A**: リポジトリの Settings → Actions → General → Workflow permissions で「Read and write permissions」を選択してください。

### Q: Gemini APIのエラーが出る
**A**: APIキーが正しく設定されているか確認してください。STEP 3 を再確認してください。

### Q: 記事が表示されない
**A**: データフォルダが空の状態です。STEP 5 の手動実行を行ってください。

### Q: Streamlit Cloudで「Module not found」エラー
**A**: requirements.txt がリポジトリルートにあるか確認してください。

---

## 📂 データの場所

| ファイル | 内容 | 保持期間 |
|---------|------|---------|
| `data/raw_news.jsonl` | RSS取得データ | 7日 |
| `data/processed_news.jsonl` | AI解析済み記事 | 7日 |
| `data/user_feedback_log.jsonl` | フィードバックログ | **永続** |

---

## 🔧 RSSフィードのカスタマイズ

`feeds.yaml` を編集することでフィードを追加・削除できます:

```yaml
feeds:
  DEV:
    - name: "追加したいフィード名"
      url: "https://example.com/rss"
      lang: "ja"  # または "en"
```

編集後はGitHubにプッシュすると次回から反映されます。
