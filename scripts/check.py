"""Checker その1：形式の検査。内側のループは毎周これを実行する。

    python scripts/check.py

検査項目（上から順に。1つでも失敗したら終了コード1）:
  1. ロックされたファイル（承認済みの主張・目標値・主張テスト）が改変されていないか
  2. runs/ の結果が実行後に書き換えられていないか
  3. core/ 層が禁止された import をしていないか
  4. progress.md の状態表の証拠欄が実在する runs/ を指しているか
  5. lab.config.json の check_commands（テストなど）が通るか

エラーメッセージは「何が・どこで・どう直すか」をAIへの指示として書く。
"""

import ast
import json
import os
import re
import subprocess
import sys

from _lab import ROOT, d, load_config, load_locks, rel, sha256


def check_locks(config: dict) -> list[str]:
    errors = []
    for paper, files in load_locks(config).items():
        for path_str, expected in files.items():
            path = ROOT / path_str
            if not path.exists():
                errors.append(
                    f"[ロック] {path_str} が削除されています（{paper} の承認済みファイル）。"
                    f"`git checkout -- {path_str}` で復元してください。"
                )
            elif sha256(path) != expected:
                errors.append(
                    f"[ロック] {path_str} が承認後に変更されています。"
                    f"このファイルはエージェントが編集してはいけません。"
                    f"`git diff -- {path_str}` で差分を確認し、`git checkout -- {path_str}` で戻してください。"
                    f"主張・目標値・主張テストの変更が本当に必要なら、理由を progress.md に書いて人間に報告し、止まってください。"
                )
    return errors


def check_runs(config: dict) -> list[str]:
    runs_dir = d(config, "runs")
    index_path = runs_dir / "INDEX.jsonl"
    indexed = {}
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                indexed[entry["run"]] = entry["metrics_sha256"]

    errors = []
    for run_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        name = run_dir.name
        metrics = run_dir / "metrics.json"
        if name not in indexed:
            errors.append(
                f"[結果] {rel(run_dir)} は scripts/run.py 以外の方法で作られています（INDEX.jsonl に記録がない）。"
                f"runs/ は scripts/run.py だけが書く場所です。実験は experiments/ に設定を置いて scripts/run.py で実行し直してください。"
            )
        elif not metrics.exists() or sha256(metrics) != indexed[name]:
            errors.append(
                f"[結果] {rel(metrics)} が実行後に書き換えられています。結果は編集してはいけません。"
                f"`git checkout -- {rel(metrics)}` で戻すか、実験をやり直して新しい run を作ってください。"
            )
    return errors


def check_pure_layers(config: dict) -> list[str]:
    rule = config["pure_layer"]
    forbidden = set(rule["forbidden_imports"])
    errors = []
    for layer_dir in d(config, "src").glob(f"*/{rule['dir_name']}"):
        for py in layer_dir.rglob("*.py"):
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.level > 0 and node.module and not node.module.startswith(rule["dir_name"]):
                        names = ["." * node.level + node.module]
                    else:
                        names = [node.module or ""]
                else:
                    continue
                for name in names:
                    top = name.split(".")[0]
                    outside_layer = name.startswith(config["dirs"]["src"] + ".") and f".{rule['dir_name']}" not in name
                    if top in forbidden or outside_layer or name.startswith(".."):
                        errors.append(
                            f"[依存方向] {rel(py)}:{node.lineno} が `{name}` を import しています。"
                            f"{rule['dir_name']}/ は数式をそのまま関数にした層で、入出力・乱数の生成・他の層に依存してはいけません。"
                            f"必要な値は引数で受け取る形にし、呼び出し側（algorithm/ など）で用意してください。"
                        )
    return errors


def check_evidence(config: dict) -> list[str]:
    errors = []
    runs_name = config["dirs"]["runs"]
    pattern = re.compile(rf"{re.escape(runs_name)}/\d{{8}}T\d{{6}}_[\w.\-]+")
    progress = d(config, "agent") / "progress.md"
    if not progress.exists():
        return errors
    for lineno, line in enumerate(progress.read_text(encoding="utf-8").splitlines(), 1):
        for ref in pattern.findall(line):
            if not (ROOT / ref).is_dir():
                errors.append(
                    f"[証拠] {rel(progress)}:{lineno} の `{ref}` は存在しません。"
                    f"証拠欄には scripts/run.py が作った実在の run フォルダだけを書いてください。"
                )
    # コード以外の仕事の証拠（スクリーンショット・出典一覧など）。dirs.evidence がある場合だけ
    evidence_name = config["dirs"].get("evidence")
    if evidence_name:
        ev_pattern = re.compile(rf"{re.escape(evidence_name)}/[\w.\-/]+")
        for lineno, line in enumerate(progress.read_text(encoding="utf-8").splitlines(), 1):
            for ref in ev_pattern.findall(line):
                if not (ROOT / ref.rstrip("/.")).exists():
                    errors.append(
                        f"[証拠] {rel(progress)}:{lineno} の `{ref}` は存在しません。"
                        f"証拠欄には実在するファイルだけを書いてください。証拠が無いなら、状態を「検証済み」にしてはいけません。"
                    )
    return errors


def run_commands(config: dict) -> list[str]:
    errors = []
    for cmd in config["check_commands"]:
        print(f"  $ {' '.join(cmd)}")
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            output = (proc.stdout + proc.stderr).strip()
            errors.append(
                f"[テスト] `{' '.join(cmd)}` が失敗しました（終了コード {proc.returncode}）。"
                f"出力の末尾を読み、失敗したテスト名と理由から直してください。"
                f"主張テスト（tests/*/claims/）は編集禁止なので、直すのは実装（src/）の側です。\n"
                + "\n".join(output.splitlines()[-40:])
            )
    return errors


def main() -> int:
    config = load_config()
    steps = [
        ("ロックの検査", check_locks),
        ("結果の改変検査", check_runs),
        ("依存方向の検査", check_pure_layers),
        ("証拠の実在検査", check_evidence),
        ("テスト", run_commands),
    ]
    all_errors = []
    for title, fn in steps:
        print(f"■ {title}")
        errors = fn(config)
        print("  OK" if not errors else f"  NG（{len(errors)}件）")
        all_errors += errors

    if all_errors:
        print("\n===== check 失敗 =====")
        for e in all_errors:
            print(f"- {e}")
        print("\n失敗理由を .agent/progress.md の「直近の失敗理由」に書いてから直してください。")
        return 1
    print("\n===== check 成功 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
