"""ベンチマーク関数（paper.md 式(3)）。"""


def sphere(x: list[float]) -> float:
    return sum(v * v for v in x)
