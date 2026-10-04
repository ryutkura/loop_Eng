"""実験を実行し、runs/ に新しいフォルダを作って結果を残す。runs/ に書くのはこのスクリプトだけ。

    python scripts/run.py experiments/<名前>/<実験>.json

実行の前に、仮説台帳（scripts/_ledger.py）で「この実験を回してよいか」を検査する。
だめなら理由を表示して、何も実行せずに終わる（終了コード 3）。

実験設定（JSON）の形:
{
  "paper": "example_es",                       # papers/ のフォルダ名
  "claim": "C3",                               # 検証する主張の ID
  "kind": "attempt",                           # attempt：目標に当てにいく試行 / diagnostic：問題の性質を調べる診断
  "hypothesis": {
    "text": "c を 0.85 にすると論文の値に合う",   # この周で何を確かめるか
    "type": "未確定点の解釈",                   # lab.config.json の explore.hypothesis_types のどれか
    "parent": "root",                          # どの run の設定から1つ変えたか。資料どおりの設定なら "root"
    "prediction": {"metric": "median_evals_to_target", "op": "approx", "value": 1000, "rel_tol": 0.2},
    "falsified_if": "予測が外れたら、c の値は原因ではないとみなす",
    "based_on": "<診断実験の run 名>"            # 任意。排除された型・探索モードで、新しい情報を根拠にするとき
  },
  "entry": "src.example_es.algorithm.es:run_experiment",   # (params, seed) -> dict を返す関数
  "params": { ... },                           # entry に渡す値
  "seeds": [0, 1, 2, 3, 4],                    # 乱数の種。1つずつ entry を呼ぶ
  "aggregate": {                               # 種ごとの結果をまとめる方法
    "median_evals_to_target": ["median", "evals_to_target"]   # 出力名: [関数, 種ごとの値の名前]
  },
  "sweep": {"param": "c", "values": [0.82, 0.9, 0.95]}       # diagnostic のときだけ。1つのパラメータを複数の値で回す
}
集約関数: mean / median / min / max / rate（真の割合）
attempt では prediction と falsified_if が必須（diagnostic では不要）。
"""

import contextlib
import importlib
import io
import json
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime

from _lab import AGGREGATORS, ROOT, d, load_config, rel, sha256
from _ledger import analyze, gate


def git_info() -> dict:
    def git(*args):
        proc = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
        return proc.stdout.strip() if proc.returncode == 0 else None

    commit = git("rev-parse", "HEAD")
    return {"commit": commit, "dirty": bool(git("status", "--porcelain")) if commit else None}


def aggregate(exp: dict, per_seed: list[dict]) -> dict:
    return {
        name: AGGREGATORS[func]([r[key] for r in per_seed])
        for name, (func, key) in exp["aggregate"].items()
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    config = load_config()
    exp_path = (ROOT / sys.argv[1]).resolve()
    with open(exp_path, encoding="utf-8") as f:
        exp = json.load(f)

    state = analyze(config, exp["paper"], exp["claim"])
    refusals = gate(config, state, exp)
    if refusals:
        print("この実験は実行しません（何も記録していません）：")
        for r in refusals:
            print(f"- {r}")
        print(f"\n今の台帳は `python scripts/ledger.py {exp['paper']} {exp['claim']}` で見られます。")
        return 3

    sys.path.insert(0, str(ROOT))
    module_name, func_name = exp["entry"].split(":")
    entry = getattr(importlib.import_module(module_name), func_name)
    kind = exp.get("kind", "attempt")

    git = git_info()
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    run_name = f"{stamp}_{exp['paper']}_{exp['claim']}_{(git['commit'] or 'nogit')[:7]}"
    run_dir = d(config, "runs") / run_name
    run_dir.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(exp_path, run_dir / "config.json")

    started = time.time()
    per_seed = []
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        if kind == "diagnostic":
            sweep = exp["sweep"]
            results = []
            for value in sweep["values"]:
                params = {**exp["params"], sweep["param"]: value}
                rows = []
                for seed in exp["seeds"]:
                    result = entry(params, seed)
                    rows.append({"seed": seed, sweep["param"]: value, **result})
                    print(f"{sweep['param']}={value} seed={seed} {json.dumps(result, ensure_ascii=False)}")
                per_seed += rows
                results.append({"value": value, "metrics": aggregate(exp, rows)})
            metrics = {"sweep": {"param": sweep["param"], "results": results}}
        else:
            for seed in exp["seeds"]:
                result = entry(exp["params"], seed)
                per_seed.append({"seed": seed, **result})
                print(f"seed={seed} {json.dumps(result, ensure_ascii=False)}")
            metrics = aggregate(exp, per_seed)

    meta = {
        "experiment": rel(exp_path),
        "paper": exp["paper"],
        "claim": exp["claim"],
        "kind": kind,
        "git": git,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "started": datetime.fromtimestamp(started).isoformat(timespec="seconds"),
        "duration_sec": round(time.time() - started, 3),
    }

    (run_dir / "log.txt").write_text(log.getvalue(), encoding="utf-8")
    with open(run_dir / "per_seed.jsonl", "w", encoding="utf-8") as f:
        for r in per_seed:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (run_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    with open(d(config, "runs") / "INDEX.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"run": run_name, "metrics_sha256": sha256(run_dir / "metrics.json")}) + "\n")

    if git["dirty"]:
        print("注意: 未コミットの変更がある状態で実行しました。再現のため、実験の前にコミットすることを推奨します。")
    print(f"run: {rel(run_dir)}")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"\n次: python scripts/compare.py {rel(run_dir)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
