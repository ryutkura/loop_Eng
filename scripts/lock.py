"""【人間専用】主張・目標値・主張テストを承認し、ロックする。エージェントは実行してはいけない。

    python scripts/lock.py <名前>

papers/<名前>/claims.md、papers/<名前>/targets.json、tests/<名前>/claims/ 以下の .py の
ハッシュを .agent/locks.json に記録する。以後 scripts/check.py がこれらの改変を検出する。
内容を修正して承認し直す場合も、同じコマンドを再実行する。
"""

import json
import sys

from _lab import d, load_config, load_locks, rel, sha256


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    name = sys.argv[1]
    config = load_config()
    files = [
        d(config, "sources") / name / "claims.md",
        d(config, "sources") / name / "targets.json",
        *sorted((d(config, "tests") / name / "claims").rglob("*.py")),
    ]
    missing = [rel(p) for p in files if not p.exists()]
    if missing:
        print("見つからないファイルがあります: " + ", ".join(missing))
        return 1

    locks = load_locks(config)
    locks[name] = {rel(p): sha256(p) for p in files}
    path = d(config, "agent") / "locks.json"
    path.write_text(json.dumps(locks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{name} をロックしました（{len(files)} ファイル）:")
    for p in files:
        print(f"  {rel(p)}")
    print("エージェントに「開発再開」と伝えてください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
