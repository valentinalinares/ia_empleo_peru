from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "_interno/scripts/analizar_sensibilidad_factores.py"
BASE = REPO_ROOT / "_interno/bases/procesadas/epen_persona_departamentos_anual_2022_2025.csv.gz"
MANIFEST = BASE.with_suffix(BASE.suffix + ".build.json")
SPEC = importlib.util.spec_from_file_location("analizar_sensibilidad_factores", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SensitivityFactorTests(unittest.TestCase):
    def test_processed_base_sha256_is_frozen_and_matches_manifest(self) -> None:
        digest = MODULE.sha256(BASE)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(digest, MODULE.BASELINE_BASE_SHA256)
        self.assertEqual(digest, manifest["output_sha256"])

    def test_official_2022_regions_sum_to_national_total(self) -> None:
        self.assertEqual(sum(MODULE.OFFICIAL_REGIONS_2022.values()), 17_336_500)
        self.assertEqual(MODULE.OFFICIAL_REGIONS_2022["15"], 6_049_500)

    def test_nonresponse_adjustment_and_uncovered_cell(self) -> None:
        frame = pd.DataFrame({
            "year": [2024] * 6, "month": [1] * 6,
            "region_code": ["01"] * 4 + ["02"] * 2,
            "strata_code": ["1"] * 6, "area_raw": ["1"] * 6,
            "weight": [10.0, 0.0, np.nan, np.nan, np.nan, np.nan],
        })
        adjusted, cells = MODULE.build_adjusted_weights(frame)
        first = cells.loc[cells["region_code"].eq("01")].iloc[0]
        second = cells.loc[cells["region_code"].eq("02")].iloc[0]
        self.assertEqual(first["adjustment_multiplier"], 2.0)
        self.assertEqual(first["uncovered_persons"], 0)
        self.assertTrue(pd.isna(second["adjustment_multiplier"]))
        self.assertEqual(second["uncovered_persons"], 2)
        self.assertEqual(adjusted["adjusted_weight"].sum(), 20.0)
        first_weights_c = adjusted.loc[
            adjusted["region_code"].eq("01"), "imputed_calibrated_weight"
        ].tolist()
        self.assertEqual(first_weights_c, [5.0, 0.0, 2.5, 2.5])
        self.assertEqual(first["version_c_weight_sum"], first["original_weight_sum"])

    def test_version_c_preserves_each_real_cell_total(self) -> None:
        columns = [*MODULE.ADJUSTMENT_KEYS, "weight"]
        frame = pd.read_csv(BASE, usecols=columns, low_memory=False)
        _, cells = MODULE.build_adjusted_weights(frame)
        covered = cells["persons_with_factor"].gt(0)
        maximum_error = cells.loc[covered, "version_c_minus_original"].abs().max()
        self.assertLess(maximum_error, 1e-8)
        self.assertEqual(int(cells.loc[~covered, "uncovered_persons"].sum()), 0)

    def test_overlap_difference_recovers_known_contrast(self) -> None:
        frame = pd.DataFrame({
            "year": [2024] * 8, "month": [1] * 8,
            "region_code": ["01"] * 8, "area_raw": ["1"] * 8,
            "factor_missing": [False] * 4 + [True] * 4,
            "value": [0.0, 1.0, 0.0, 1.0, 1.0, 2.0, 1.0, 2.0],
        })
        result = MODULE.overlap_difference(frame, "value", MODULE.MATCH_KEYS)
        self.assertAlmostEqual(result["mean_with_factor"], 0.5)
        self.assertAlmostEqual(result["mean_without_factor"], 1.5)
        self.assertAlmostEqual(result["difference_without_minus_with"], 1.0)
        self.assertEqual(result["matched_cells"], 1)

    def test_writing_an_unrelated_output_does_not_touch_base(self) -> None:
        before = MODULE.sha256(BASE)
        with tempfile.TemporaryDirectory() as directory:
            pd.DataFrame({"value": [1]}).to_csv(Path(directory) / "small.csv", index=False)
        self.assertEqual(MODULE.sha256(BASE), before)


if __name__ == "__main__":
    unittest.main()
