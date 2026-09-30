"""(1+1)-ES 本体（paper.md アルゴリズム1）。core/ の関数を組み合わせる層。"""

import random
from typing import Callable

from src.example_es.core.objectives import sphere
from src.example_es.core.step_size import update_step_size


def one_plus_one_es(
    f: Callable[[list[float]], float],
    x0: list[float],
    sigma0: float,
    max_evals: int,
    rng: random.Random,
    window: int = 10,
    c: float = 0.85,
    f_target: float | None = None,
) -> dict:
    """(1+1)-ES を実行し、探索の軌跡と結果を返す。

    軌跡（trajectory）は各世代の親の位置。C2（単調変換への不変性）の検証に使う。
    """
    x = list(x0)
    fx = f(x)
    sigma = sigma0
    evals = 1
    successes = 0
    trajectory = [list(x)]
    evals_to_target = evals if f_target is not None and fx <= f_target else None

    generation = 0
    while evals < max_evals:
        y = [xi + sigma * rng.gauss(0.0, 1.0) for xi in x]
        fy = f(y)
        evals += 1
        generation += 1
        if fy <= fx:
            x, fx = y, fy
            successes += 1
        trajectory.append(list(x))

        if generation % window == 0:
            sigma = update_step_size(sigma, successes / window, c)
            successes = 0

        if f_target is not None and evals_to_target is None and fx <= f_target:
            evals_to_target = evals
            break

    return {
        "best_x": x,
        "best_f": fx,
        "evals": evals,
        "evals_to_target": evals_to_target,
        "trajectory": trajectory,
    }


def run_experiment(params: dict, seed: int) -> dict:
    """scripts/run.py から呼ばれる入口。1つの乱数の種について結果の数値を返す。"""
    rng = random.Random(seed)
    dim = params["dim"]
    x0 = [rng.uniform(params["init_low"], params["init_high"]) for _ in range(dim)]
    result = one_plus_one_es(
        f=sphere,
        x0=x0,
        sigma0=params["sigma0"],
        max_evals=params["max_evals"],
        rng=rng,
        window=params.get("window", 10),
        c=params.get("c", 0.85),
        f_target=params["f_target"],
    )
    reached = result["evals_to_target"] is not None
    return {
        "reached": reached,
        "evals_to_target": result["evals_to_target"] if reached else params["max_evals"],
        "best_f": result["best_f"],
    }
