"""C1: 成功率が 1/5 より高ければ σ は増え、低ければ減り、ちょうど 1/5 なら変わらない（式(2)）。"""

import unittest

from src.example_es.core.step_size import update_step_size


class TestC1StepSize(unittest.TestCase):
    def test_成功率が高いとσが増える(self):
        self.assertGreater(update_step_size(1.0, 0.5), 1.0)

    def test_成功率が低いとσが減る(self):
        self.assertLess(update_step_size(1.0, 0.0), 1.0)

    def test_成功率がちょうど5分の1ならσは変わらない(self):
        self.assertEqual(update_step_size(1.0, 0.2), 1.0)

    def test_論文の範囲のcならどれでも向きが正しい(self):
        for c in (0.817, 0.85, 0.9, 0.99):
            with self.subTest(c=c):
                self.assertGreater(update_step_size(1.0, 0.3, c), 1.0)
                self.assertLess(update_step_size(1.0, 0.1, c), 1.0)


if __name__ == "__main__":
    unittest.main()
