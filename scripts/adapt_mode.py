"""【人間専用】組み替えモード（ADAPT）の切り替え。エージェントは実行してはいけない。

    python scripts/adapt_mode.py on    # キットの組み替えを許可する
    python scripts/adapt_mode.py off   # 組み替えが終わったら必ず戻す

on の間だけ、Claude Code のフック（scripts/hooks/guard.py）が
scripts/・lab.config.json・goal.md・runs/・ロック済みファイルなどへの書き込みを許可する。
（lock.py とこのスクリプトの実行だけは、on の間も拒否する）
"""

import sys

from _lab import d, load_config


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("on", "off"):
        print(__doc__)
        return 2
    flag = d(load_config(), "agent") / "ADAPT_MODE"
    if sys.argv[1] == "on":
        flag.write_text("このファイルがある間、guard.py は組み替えのための編集を許可する。\n", encoding="utf-8")
        print("組み替えモード: ON。終わったら `python scripts/adapt_mode.py off` を実行してください。")
    else:
        flag.unlink(missing_ok=True)
        print("組み替えモード: OFF。保護が有効に戻りました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
