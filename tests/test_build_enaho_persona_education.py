from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "_interno/scripts/build_enaho_persona_education.py"
OUTPUT = ROOT / "_interno/bases/procesadas/enaho_persona_anual_2019_2025.csv.gz"
SPEC = importlib.util.spec_from_file_location("build_enaho_persona_education", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class EnahoEducationTests(unittest.TestCase):
    def test_education_map_matches_notebook_codes(self) -> None:
        self.assertEqual(set(MODULE.EDU_MAP), set(range(1, 13)))
        self.assertEqual(MODULE.EDU_MAP[1], "sin nivel")
        self.assertEqual(MODULE.EDU_MAP[11], "maestría/doctorado")
        self.assertEqual(MODULE.EDU_MAP[12], "básica especial")

    def test_labels_from_complete_files_map_to_expected_codes(self) -> None:
        for code, label in MODULE.EDU_MAP.items():
            self.assertEqual(MODULE.education_label_to_code(label), code)
        self.assertEqual(MODULE.education_label_to_code("educaci�n inicial"), 2)
        self.assertEqual(MODULE.education_label_to_code("maestr�a/doctorado"), 11)

    def test_rebuild_changes_only_education_code(self) -> None:
        processed = pd.DataFrame(
            {
                "year": [2025, 2025],
                "month": [1, 1],
                "cluster_id": [12, 12],
                "dwelling_id": [3, 3],
                "household_id": [1, 1],
                "person_id": [1, 2],
                "ubigeo": [150101, 150101],
                "domain_code": [8, 8],
                "strata_code": [4, 4],
                "occupation_code_4d": [212, 5212],
                "education_code": [pd.NA, pd.NA],
            }
        )
        keys = MODULE.build_person_key(processed)
        complete = pd.DataFrame(
            {
                "codigo_unico": keys,
                "education_code": [11, 6],
                "nivel educativo": ["maestría/doctorado", "secundaria completa"],
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            complete_dir = directory / "complete"
            complete_dir.mkdir()
            input_path = directory / "before.csv.gz"
            output_path = directory / "after.csv.gz"
            processed.to_csv(input_path, index=False, compression="gzip")
            complete.to_csv(complete_dir / "ENAHO_complete_2025.csv", index=False)
            result = MODULE.rebuild_education(
                input_path,
                output_path,
                complete_dir,
                2025,
                2025,
            )
            before = pd.read_csv(input_path)
            after = pd.read_csv(output_path)

        pd.testing.assert_frame_equal(
            before.drop(columns="education_code"),
            after.drop(columns="education_code"),
            check_dtype=False,
        )
        self.assertEqual(after["education_code"].tolist(), [11, 6])
        self.assertTrue(result["other_columns_unchanged"])

    def test_real_output_has_education_in_every_year(self) -> None:
        data = pd.read_csv(OUTPUT, usecols=["year", "education_code"])
        counts = data.groupby("year")["education_code"].count()
        self.assertEqual(set(counts.index), set(range(2019, 2026)))
        self.assertTrue((counts > 0).all())
        self.assertTrue(set(data["education_code"].dropna().astype(int)).issubset(MODULE.EDU_MAP))


if __name__ == "__main__":
    unittest.main()
