"""実験を実行し、runs/ に新しいフォルダを作って結果を残す。runs/ に書くのはこのスクリプトだけ。

    python scripts/run.py experiments/<名前>/<実験>.json

実験設定（JSON）の形:
{
  "paper": "example_es",                       # papers/ のフォルダ名
  "claim": "C3",                               # 検証する主張の ID
  "entry": "src.example_es.algorithm.es:run_experiment",   # (params, seed) -> dict を返す関数
  "params": { ... },                           # entry に渡す値
  "seeds": [0, 1, 2, 3, 4],                    # 乱数の種。1つずつ entry を呼ぶ
  "aggregate": {                               # 種ごとの結果をまとめる方法
    "median_evals_to_target": ["median", "evals_to_target"]   # 出力名: [関数, 種ごとの値の名前]
  }
}
集約関数: mean / median / min / max / rate（真の割合）
"""

import contextlib
import importlib
import io
import json
import platform
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from _lab import ROOT, d, load_config, rel, sha256

AGGREGATORS = {
    "mean": statistics.mean,
    "median": statistics.median,
    "min": min,
    "max": max,
    "rate": lambda xs: sum(1 for x in xs if x) / len(xs),
}


def git_info() -> dict:
    def git(*args):
        proc = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
        return proc.stdout.strip() if proc.returncode == 0 else None

    commit = git("rev-parse", "HEAD")
    return {"commit": commit, "dirty": bool(git("status", "--porcelain")) if commit else None}


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    config = load_config()
    exp_path = (ROOT / sys.argv[1]).resolve()
    with open(exp_path, encoding="utf-8") as f:
        exp = json.load(f)

    sys.path.insert(0, str(ROOT))
    module_name, func_name = exp["entry"].split(":")
    entry = getattr(importlib.import_module(module_name), func_name)

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
        for seed in exp["seeds"]:
            result = entry(exp["params"], seed)
            per_seed.append({"seed": seed, **result})
            print(f"seed={seed} {json.dumps(result, ensure_ascii=False)}")

    metrics = {
        name: AGGREGATORS[func]([r[key] for r in per_seed])
        for name, (func, key) in exp["aggregate"].items()
    }
    meta = {
        "experiment": rel(exp_path),
        "paper": exp["paper"],
        "claim": exp["claim"],
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
