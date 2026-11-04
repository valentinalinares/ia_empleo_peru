from __future__ import annotations

import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

import pandas as pd


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "_interno/scripts/build_epen_persona_departamentos.py"
)
SPEC = importlib.util.spec_from_file_location("build_epen_persona_departamentos", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class OccupationCodeTests(unittest.TestCase):
    def test_codes_are_padded_on_the_left_even_when_right_pad_is_valid(self) -> None:
        catalog = {"0212", "2120"}
        corrected = MODULE.normalise_cno_code("212")

        self.assertEqual(corrected, "0212")
        self.assertIn(corrected, catalog)
        self.assertNotEqual(corrected, MODULE.legacy_right_pad("212"))

    def test_invalid_codes_are_not_silently_rewritten(self) -> None:
        self.assertTrue(pd.isna(MODULE.normalise_cno_code("21A")))
        self.assertTrue(pd.isna(MODULE.normalise_cno_code("12345")))
        self.assertTrue(pd.isna(MODULE.normalise_cno_code(None)))

    def test_build_occupied_uses_raw_code_and_integer_code_serialization(self) -> None:
        raw = pd.DataFrame(
            {
                "ANIO": ["2024", "2024"],
                "MES": ["01", "01"],
                "CCDD": ["15", "15"],
                "MUESTRA": ["1", "1"],
                "ESTRATO": ["2", "2"],
                "CONGLOMERADO": ["0001", "0001"],
                "SELVIV": ["001", "001"],
                "HOGAR": ["1", "1"],
                "C201": ["1", "2"],
                "C300n": ["1", "2"],
                "C203": ["1", "2"],
                "C207": ["1", "2"],
                "C208": ["30", "40"],
                "OCUP300": ["1", "1"],
                "C308_COD": ["212", "2120"],
                "C310": ["3", "3"],
                "C317": ["5", ""],
                "C318_T": ["40", ""],
                "INGTOT": ["1200", ""],
                "INGTOTP": ["1100", ""],
                "ingtrabw": ["1250", ""],
                "C338": ["4", ""],
                "FAC300_ANUAL": ["100.5", "100.5"],
                "C366": ["6", "6"],
                "C311": ["5", "5"],
                "AREA": ["1", "1"],
            }
        )

        result, audit = MODULE.build_occupied(raw)

        self.assertEqual(len(result), 2)
        self.assertEqual(result.loc[0, "sample_id"], 1)
        self.assertEqual(result.loc[0, "occupation_code_raw"], 212)
        self.assertEqual(result.loc[0, "occupation_code_4d"], "0212")
        self.assertEqual(result.loc[0, "strata_code"], 2)
        self.assertEqual(result.loc[0, "person_id"], 1)
        self.assertEqual(result.loc[0, "relationship_code"], 1)
        self.assertEqual(result.loc[0, "occupational_category_code"], 3)
        self.assertEqual(result.loc[0, "firm_size_code"], 5)
        self.assertEqual(result.loc[0, "income_periodicity_code"], 4)
        self.assertTrue(pd.isna(result.loc[0, "ubigeo"]))
        self.assertTrue(pd.isna(result.loc[0, "domain_code"]))
        self.assertEqual(audit["codes_changed_from_legacy_right_padding"], 1)
        self.assertEqual(audit["person_code_mismatches"], 0)

        serialized = io.StringIO()
        result.to_csv(serialized, index=False)
        text_result = pd.read_csv(io.StringIO(serialized.getvalue()), dtype=str)
        for column in MODULE.NULLABLE_INTEGER_CODE_COLUMNS:
            values = text_result[column].dropna()
            self.assertFalse(values.str.endswith(".0").any(), column)

    def test_sample_disambiguates_reused_person_keys(self) -> None:
        raw = pd.DataFrame(
            {
                "ANIO": ["2024", "2024"],
                "MES": ["01", "01"],
                "CCDD": ["15", "15"],
                "MUESTRA": ["1", "2"],
                "ESTRATO": ["2", "2"],
                "CONGLOMERADO": ["0001", "0001"],
                "SELVIV": ["001", "001"],
                "HOGAR": ["1", "1"],
                "C201": ["1", "1"],
                "C300n": ["1", "1"],
                "C203": ["1", "1"],
                "C207": ["1", "1"],
                "C208": ["30", "30"],
                "OCUP300": ["1", "1"],
                "C308_COD": ["5212", "5212"],
                "C310": ["3", "3"],
                "C317": ["2", "2"],
                "C318_T": ["40", "40"],
                "C338": ["4", "4"],
                "INGTOT": ["1200", "1200"],
                "INGTOTP": ["1200", "1200"],
                "ingtrabw": ["1200", "1200"],
                "FAC300_ANUAL": ["100", "100"],
                "C366": ["6", "6"],
                "C311": ["5", "5"],
                "AREA": ["1", "1"],
            }
        )

        result, audit = MODULE.build_occupied(raw)

        self.assertEqual(audit["duplicate_person_key_rows_without_sample"], 2)
        self.assertEqual(audit["duplicate_person_key_rows_with_sample"], 0)
        self.assertEqual(audit["duplicate_output_person_key_rows_without_sample"], 2)
        self.assertEqual(audit["duplicate_output_person_key_rows_with_sample"], 0)
        output_key = [
            "year",
            "month",
            "sample_id",
            "cluster_id",
            "dwelling_id",
            "household_id",
            "person_id",
        ]
        self.assertFalse(result.duplicated(output_key).any())

    def test_comparison_allows_only_audited_identifier_columns(self) -> None:
        old_columns = [
            column for column in MODULE.OUTPUT_COLUMNS if column != "sample_id"
        ]
        base = pd.DataFrame([{column: pd.NA for column in old_columns}])
        base.loc[0, "source"] = "EPEN"
        base.loc[0, "occupation_code_raw"] = 212
        base.loc[0, "occupation_code_4d"] = "0212"
        regenerated = base.copy()
        regenerated.insert(8, "sample_id", 1)
        regenerated.loc[0, "strata_code"] = 2
        regenerated.loc[0, "person_id"] = 1

        with tempfile.TemporaryDirectory() as directory:
            old_path = Path(directory) / "old.csv.gz"
            new_path = Path(directory) / "new.csv.gz"
            base.to_csv(old_path, index=False)
            regenerated.to_csv(new_path, index=False)

            audit = MODULE.compare_datasets(old_path, new_path)
            self.assertEqual(
                audit["audited_identifier_mismatches"],
                {"sample_id": 1, "strata_code": 1, "person_id": 1},
            )
            self.assertEqual(audit["unexpected_mismatches"], {})

            regenerated.loc[0, "age"] = 30
            regenerated.to_csv(new_path, index=False)
            with self.assertRaises(ValueError):
                MODULE.compare_datasets(old_path, new_path)


if __name__ == "__main__":
    unittest.main()
