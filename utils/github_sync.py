"""
utils/github_sync.py - /tmp 領域のログを本家GitHubリポジトリへ直接git pushして同期するユーティリティ
"""
import os
import subprocess
import shutil
from pathlib import Path

def sync_actions_to_github():
    """
    /tmp/pni-data/user_actions.jsonl を、GitHubリポジトリ側に直接 push して同期します。
    """
    # 認証用のGitHubトークン（またはHFトークン。GitHubへのプッシュ権限があるもの）
    token = os.environ.get("GH_TOKEN") or os.environ.get("HF_TOKEN")
    if not token:
        print("認証トークンが環境変数に設定されていないため、GitHub同期をスキップします。")
        return

    # 一時フォルダ側のソースファイル
    tmp_file = Path("/tmp/pni-data/user_actions.jsonl")
    if not tmp_file.exists():
        print("同期対象の一時ファイルが存在しません。")
        return

    # 現在稼働しているコンテナのルートパス
    repo_dir = Path(__file__).parent.parent
    dest_file = repo_dir / "data" / "user_actions.jsonl"

    try:
        # 1. /tmp の最新ログファイルを、Git管理下のフォルダへ安全にコピー配置
        repo_dir / "data"
        os.makedirs(repo_dir / "data", exist_ok=True)
        shutil.copyfile(tmp_file, dest_file)

        # 2. Gitユーザー名の一時設定
        subprocess.run(["git", "config", "user.name", "pni-sync-bot"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.email", "pni-sync-bot@example.com"], cwd=repo_dir, check=True)

        # 3. 本家GitHubリポジトリのURLにトークンを乗せてリモート設定を上書き
        # あなたのGitHubアカウント名とリポジトリ名に固定
        github_url = f"https://manabu-sora-sato:{token}@github.com/manabu-sora-sato/pni-news.git"
        subprocess.run(["git", "remote", "set-url", "origin", github_url], cwd=repo_dir, check=True)

        # 4. コンフリクトを防ぐために一度pull
        subprocess.run(["git", "pull", "origin", "main", "--rebase"], cwd=repo_dir, check=True)

        # 5. ステージングとコミット・プッシュ
        subprocess.run(["git", "add", "data/user_actions.jsonl"], cwd=repo_dir, check=True)
        
        status = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=repo_dir)
        if status.returncode != 0:
            subprocess.run(["git", "commit", "-m", "chore: update user_actions.jsonl from HF Space"], cwd=repo_dir, check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=repo_dir, check=True)
            print("GitHubへの git push 同期が正常に完了しました。")
        else:
            print("差分がないため同期をスキップしました。")

    except subprocess.CalledProcessError as e:
        print(f"GitHub同期中にエラーが発生しました: {e}")
