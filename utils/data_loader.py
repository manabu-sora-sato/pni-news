import json
import os
from pathlib import Path
from datetime import datetime

class ActionDataLoader:
    def __init__(self):
        self.file_path = Path("data/user_actions.jsonl")
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """データフォルダとファイルが物理的に存在することを確認する"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            with open(self.file_path, "w", encoding="utf-8") as f:
                pass

    def save_action(self, article_id: str, action_type: str):
        """
        ユーザーのアクション（good / bad / read）をHFローカルファイルに即座に追記する。
        GitHubへの通信はここでは一切行わない。
        """
        record = {
            "article_id": article_id,
            "action": action_type,
            "timestamp": datetime.now().isoformat()
        }
        
        # 既存の同一記事に対する重複アクションを排除したい場合はここでフィルタリング可能ですが、
        # 高速化のため、愚直にログとして末尾追記（アペンド）する最も安全な方法をとります。
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load_processed_ids(self) -> set:
        """
        画面から除外すべき処理済み（既読・GOOD・BADすべて）の記事IDをセットとして返す。
        ファイル解析エラーが発生しても、既存のデータを破壊せず、読み込める行だけで処理する。
        """
        processed_ids = set()
        if not self.file_path.exists():
            return processed_ids

        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "article_id" in data:
                        processed_ids.add(data["article_id"])
                except Exception:
                    # 破損行があっても無視して次の行の読み込みを継続する
                    continue
        return processed_ids

    def get_action_counts(self) -> dict:
        """フィードバックの統計（GOOD/BAD数）を正確にカウントして返す"""
        counts = {"good": 0, "bad": 0, "read": 0}
        if not self.file_path.exists():
            return counts

        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    action = data.get("action")
                    if action in counts:
                        counts[action] += 1
                except Exception:
                    continue
        return counts
