"""
utils/github_sync.py - バックグラウンド同期スクリプト
HFローカルの一括管理ファイルを、1時間ごとにGitHubへ一方通行でプッシュします
"""
import os
import requests
import base64
from pathlib import Path

def sync_actions_to_github():
    local_path = Path("data/user_actions.jsonl")
    if not local_path.exists() or local_path.stat().st_size == 0:
        print("[Sync] 送信するデータがありません。")
        return

    github_token = os.getenv("GITHUB_TOKEN_READ")  # app.pyの記述と統一
    repo = "manabu-sora-sato/pni-news"
    
    if not github_token:
        print("[Sync] GITHUB_TOKEN_READ が環境変数に見つかりません。")
        return

    file_path_in_repo = "data/user_actions.jsonl"
    url = f"https://api.github.com/repos/{repo}/contents/{file_path_in_repo}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        content_bytes = content.encode("utf-8")
        base64_content = base64.b64encode(content_bytes).decode("utf-8")

        res = requests.get(url, headers=headers, timeout=10)
        sha = None
        if res.status_code == 200:
            sha = res.json().get("sha")

        payload = {
            "message": "sync: update user actions from Hugging Face",
            "content": base64_content
        }
        if sha:
            payload["sha"] = sha

        put_res = requests.put(url, headers=headers, json=payload, timeout=15)
        if put_res.status_code in [200, 201]:
            print(f"[Sync] GitHubへの一方向バックアップに成功しました。: {put_res.status_code}")
        else:
            print(f"[Sync] GitHubへのアップロードに失敗しました。: {put_res.text}")

    except Exception as e:
        print(f"[Sync] 同期処理中に例外が発生しました: {str(e)}")
