from __future__ import annotations

import importlib.util
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

    def test_build_occupied_uses_raw_code_and_filters_occupied_people(self) -> None:
        raw = pd.DataFrame(
            {
                "ANIO": ["2024", "2024"],
                "MES": ["01", "01"],
                "CCDD": ["15", "15"],
                "CONGLOMERADO": ["0001", "0001"],
                "SELVIV": ["001", "001"],
                "HOGAR": ["1", "1"],
                "C207": ["1", "2"],
                "C208": ["30", "40"],
                "OCUP300": ["1", "4"],
                "C308_COD": ["212", "2120"],
                "C318_T": ["40", ""],
                "INGTOT": ["1200", ""],
                "INGTOTP": ["1100", ""],
                "ingtrabw": ["1250", ""],
                "FAC300_ANUAL": ["100.5", "100.5"],
                "C366": ["6", "6"],
                "C311": ["5", "5"],
                "AREA": ["1", "1"],
            }
        )

        result, audit = MODULE.build_occupied(raw)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.loc[0, "occupation_code_raw"], 212)
        self.assertEqual(result.loc[0, "occupation_code_4d"], "0212")
        self.assertEqual(audit["codes_changed_from_legacy_right_padding"], 1)


if __name__ == "__main__":
    unittest.main()
