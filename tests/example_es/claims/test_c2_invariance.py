"""C2: 目的関数に単調増加な変換をかけても、同じ乱数列なら探索の軌跡が一致する（4章）。"""

import math
import random
import unittest

from src.example_es.algorithm.es import one_plus_one_es
from src.example_es.core.objectives import sphere


class TestC2Invariance(unittest.TestCase):
    def run_with(self, f, seed):
        return one_plus_one_es(f, x0=[3.0, -2.0, 1.0], sigma0=1.0, max_evals=300, rng=random.Random(seed))

    def test_単調変換をかけても軌跡が一致する(self):
        transforms = {
            "平方根": lambda v: math.sqrt(v),
            "指数": lambda v: math.exp(min(v, 700.0)),
            "定数倍と平行移動": lambda v: 3.0 * v + 10.0,
        }
        for name, g in transforms.items():
            for seed in (0, 1, 2):
                with self.subTest(transform=name, seed=seed):
                    base = self.run_with(sphere, seed)
                    transformed = self.run_with(lambda x: g(sphere(x)), seed)
                    self.assertEqual(base["trajectory"], transformed["trajectory"])


if __name__ == "__main__":
    unittest.main()
