import os
import requests
import base64
from pathlib import Path

def sync_actions_to_github():
    """
    HFローカルにある user_actions.jsonl の中身を、GitHub側へ安全にアップロードする。
    ニュース取得（2時間ごと）とは完全に独立して動作する。
    """
    local_path = Path("data/user_actions.jsonl")
    if not local_path.exists() or local_path.stat().st_size == 0:
        print("[Sync] 送信するデータがありません。")
        return

    # 環境変数からGitHubの情報を取得
    github_token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")  # 例: "username/repository"
    
    if not github_token or not repo:
        print("[Sync] GitHubの連携設定（TOKEN/REPO）が環境変数に見つかりません。")
        return

    file_path_in_repo = "data/user_actions.jsonl"
    url = f"https://api.github.com/repos/{repo}/contents/{file_path_in_repo}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        # HFローカルの最新データを読み込む
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        content_bytes = content.encode("utf-8")
        base64_content = base64.b64encode(content_bytes).decode("utf-8")

        # GitHub側の既存ファイルのSHA（識別番号）を取得する（上書きに必須）
        res = requests.get(url, headers=headers)
        sha = None
        if res.status_code == 200:
            sha = res.json().get("sha")

        # 送信データ（コミットメッセージと中身）の組み立て
        payload = {
            "message": "sync: update user actions from Hugging Face",
            "content": base64_content
        }
        if sha:
            payload["sha"] = sha

        # GitHub側へ一方通行のプッシュ（上書き保存）を実行
        put_res = requests.put(url, headers=headers, json=payload)
        if put_res.status_code in [200, 201]:
            print(f"[Sync] GitHubへのデータバックアップに成功しました。ステータス: {put_res.status_code}")
        else:
            print(f"[Sync] GitHubへのアップロードに失敗しました。: {put_res.text}")

    except Exception as e:
        print(f"[Sync] 同期処理中に例外エラーが発生しました: {str(e)}")
