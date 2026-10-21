import math
import tempfile
import unittest
from pathlib import Path

import measure


class ErosionMetricsTest(unittest.TestCase):
    def test_empty_input_has_zero_erosion(self):
        self.assertEqual(measure.erosion_metrics([])["erosion"], 0.0)

    def test_threshold_is_strictly_greater_than_ten(self):
        funcs = [{"cc": 10, "sloc": 4}, {"cc": 11, "sloc": 4}]
        result = measure.erosion_metrics(funcs)
        self.assertEqual(result["functions_cc_gt_10"], 1)
        eroded = 11 * math.sqrt(4)
        total = eroded + 10 * math.sqrt(4)
        self.assertAlmostEqual(result["erosion"], round(eroded / total, 4))

    def test_no_eroded_function_gives_zero(self):
        self.assertEqual(measure.erosion_metrics([{"cc": 3, "sloc": 9}])["erosion"], 0.0)


class ScopeTest(unittest.TestCase):
    def test_measured_paths(self):
        self.assertTrue(measure.is_measured("feature/home/src/main/kotlin/A.kt"))
        self.assertFalse(measure.is_measured("feature/home/src/test/kotlin/A.kt"))
        self.assertFalse(measure.is_measured("feature/home/src/main/kotlin/HomePreview.kt"))
        self.assertFalse(measure.is_measured("konsistTest/src/main/kotlin/A.kt"))
        self.assertFalse(measure.is_measured("build-logic/convention/src/main/kotlin/A.kt"))


class CloneRatioTest(unittest.TestCase):
    def test_repeated_block_is_counted_once_per_line(self):
        block = "\n".join(f"val x{i} = {i}" for i in range(6)) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "A.kt", Path(tmp) / "B.kt"
            a.write_text(block, encoding="utf-8")
            b.write_text(block, encoding="utf-8")
            result = measure.clone_ratio([a, b])
        self.assertEqual(result["code_lines"], 12)
        self.assertEqual(result["clone_lines"], 12)

    def test_unique_code_has_no_clones(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "A.kt"
            a.write_text("\n".join(f"val y{i} = {i * 7}" for i in range(10)), encoding="utf-8")
            self.assertEqual(measure.clone_ratio([a])["clone_lines"], 0)


if __name__ == "__main__":
    unittest.main()
