"""1/5 成功則によるステップサイズの更新（paper.md 式(2)）。

core/ は数式をそのまま関数にした層。乱数・入出力・他の層に依存しない。
"""

TARGET_SUCCESS_RATE = 0.2


def update_step_size(sigma: float, success_rate: float, c: float = 0.85) -> float:
    """成功率が 1/5 より高ければ sigma を広げ、低ければ狭める。

    c は paper.md で 0.817 <= c < 1 とされる定数。値の選択は journal/decisions.md の D1。
    """
    if not 0.0 < c < 1.0:
        raise ValueError(f"c は 0 < c < 1 である必要があります: c={c}")
    if success_rate > TARGET_SUCCESS_RATE:
        return sigma / c
    if success_rate < TARGET_SUCCESS_RATE:
        return sigma * c
    return sigma
