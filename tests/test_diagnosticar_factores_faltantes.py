from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "_interno/scripts/diagnosticar_factores_faltantes.py"
BASE = (
    REPO_ROOT
    / "_interno/bases/procesadas/epen_persona_departamentos_anual_2022_2025.csv.gz"
)
RAW_ROOT = REPO_ROOT.parent / "data/raw/inei_data_core/epen_departamentos"

SPEC = importlib.util.spec_from_file_location("diagnosticar_factores_faltantes", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class MissingFactorDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.output_dir = Path(cls.temporary.name)
        cls.before_sha = MODULE.sha256(BASE)
        cls.summary = MODULE.write_diagnostic(RAW_ROOT, BASE, cls.output_dir)
        cls.after_sha = MODULE.sha256(BASE)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_processed_base_is_unchanged(self) -> None:
        self.assertEqual(self.before_sha, self.after_sha)
        self.assertEqual(
            self.summary["processed_base_sha256_before"],
            self.summary["processed_base_sha256_after"],
        )
        self.assertTrue(self.summary["base_unchanged"])

    def test_raw_and_processed_missing_counts_match(self) -> None:
        source = pd.read_csv(self.output_dir / "resumen_origen.csv")
        self.assertTrue(source["raw_processed_rows_match"].all())
        self.assertTrue(source["raw_processed_missing_match"].all())
        self.assertEqual(source["raw_occupied_missing_rows"].sum(), 23_290)
        self.assertEqual(
            source.set_index("year")["raw_occupied_missing_rows"].to_dict(),
            {2022: 0, 2023: 1113, 2024: 7778, 2025: 14399},
        )

    def test_no_alternative_factor_is_present_in_raw_csvs(self) -> None:
        factors = pd.read_csv(self.output_dir / "variables_factor.csv")
        self.assertEqual(set(factors["factor_variable"]), {"FAC300_ANUAL"})
        self.assertEqual(
            factors["nonmissing_among_occupied_without_annual_factor"].sum(),
            0,
        )

    def test_missing_weights_are_complete_households_and_dwellings(self) -> None:
        integrity = pd.read_csv(self.output_dir / "integridad_unidades.csv")
        mixed = integrity.loc[integrity["status"].eq("unidad_mixta")]
        mixed_by_level = mixed.set_index("level")["missing_rows"].to_dict()
        self.assertEqual(mixed_by_level.get("hogar", 0), 0)
        self.assertEqual(mixed_by_level.get("vivienda", 0), 0)


if __name__ == "__main__":
    unittest.main()
