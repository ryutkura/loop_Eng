"""エージェントが自由に足してよい細かいテストの例。ロック対象外。"""

import random
import unittest

from src.example_es.algorithm.es import one_plus_one_es
from src.example_es.core.objectives import sphere
from src.example_es.core.step_size import update_step_size


class TestBasic(unittest.TestCase):
    def test_sphereの最小値は原点で0(self):
        self.assertEqual(sphere([0.0, 0.0, 0.0]), 0.0)

    def test_評価回数の上限を超えない(self):
        result = one_plus_one_es(sphere, [1.0] * 5, 1.0, max_evals=50, rng=random.Random(0))
        self.assertLessEqual(result["evals"], 50)

    def test_不正なcを拒否する(self):
        with self.assertRaises(ValueError):
            update_step_size(1.0, 0.5, c=1.0)


if __name__ == "__main__":
    unittest.main()
