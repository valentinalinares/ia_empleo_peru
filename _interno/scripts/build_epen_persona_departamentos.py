from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_ROOT = REPO_ROOT.parent / "data/raw/inei_data_core/epen_departamentos"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "_interno/bases/procesadas/epen_persona_departamentos_anual_2022_2025.csv.gz"
)

OUTPUT_COLUMNS = [
    "source",
    "survey_variant",
    "period_label",
    "year",
    "month",
    "region_code",
    "ubigeo",
    "domain_code",
    "strata_code",
    "cluster_id",
    "dwelling_id",
    "household_id",
    "person_id",
    "relationship_code",
    "sex_code",
    "sex",
    "age",
    "labor_status_code",
    "occupation_code_raw",
    "occupation_code_4d",
    "occupational_category_code",
    "firm_size_code",
    "hours_week",
    "income_periodicity_code",
    "labor_income_raw",
    "labor_income_monthly",
    "weight",
    "is_rural",
    "is_urban",
    "labor_income_work_weighted",
    "education_code",
    "institutional_sector_code",
    "area_raw",
]

NUMERIC_MAP = {
    "year": "ANIO",
    "month": "MES",
    "region_code": "CCDD",
    "cluster_id": "CONGLOMERADO",
    "dwelling_id": "SELVIV",
    "household_id": "HOGAR",
    "sex_code": "C207",
    "age": "C208",
    "labor_status_code": "OCUP300",
    "occupation_code_raw": "C308_COD",
    "hours_week": "C318_T",
    "labor_income_raw": "INGTOT",
    "labor_income_monthly": "INGTOTP",
    "weight": "FAC300_ANUAL",
    "labor_income_work_weighted": "ingtrabw",
    "education_code": "C366",
    "institutional_sector_code": "C311",
    "area_raw": "AREA",
}

REQUIRED_RAW_COLUMNS = set(NUMERIC_MAP.values()) | {"OCUP300", "C308_COD"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def portable_path(path: Path) -> str:
    """Return a stable repository-relative path when possible."""
    resolved = path.resolve()
    for root in (REPO_ROOT, REPO_ROOT.parent):
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            continue
    return str(resolved)


def clean_code(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = re.sub(r"\.0+$", "", str(value).strip())
    return text if text else None


def normalise_cno_code(value: object, width: int = 4) -> object:
    """Return a digit-only CNO code padded on the left.

    The raw value is authoritative. In particular, 212 must become 0212 even
    though 2120 is also a valid CNO code.
    """
    text = clean_code(value)
    if text is None or not text.isdigit() or len(text) > width:
        return pd.NA
    return text.zfill(width)


def legacy_right_pad(value: object, width: int = 4) -> object:
    """Reproduce the historical defect for audit comparisons only."""
    text = clean_code(value)
    if text is None or not text.isdigit() or len(text) > width:
        return pd.NA
    return text.ljust(width, "0")


def read_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        csv_files = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_files) != 1:
            raise ValueError(f"Expected one CSV in {path}, found {len(csv_files)}")
        with archive.open(csv_files[0]) as stream:
            return pd.read_csv(stream, dtype=str, encoding="utf-8-sig", low_memory=False)


def build_occupied(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    missing = sorted(REQUIRED_RAW_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"Missing required raw columns: {missing}")

    occupied_mask = df["OCUP300"].map(clean_code).eq("1")
    occupied = df.loc[occupied_mask].copy()
    output = pd.DataFrame(index=occupied.index)

    output["source"] = "EPEN"
    output["survey_variant"] = "departamentos_anual"
    output["period_label"] = "Anual - (Ene-Dic)"
    for target, source in NUMERIC_MAP.items():
        output[target] = pd.to_numeric(occupied[source], errors="coerce")

    raw_codes = occupied["C308_COD"]
    output["occupation_code_4d"] = raw_codes.map(normalise_cno_code).astype("string")
    legacy_codes = raw_codes.map(legacy_right_pad).astype("string")
    changed = output["occupation_code_4d"].notna() & legacy_codes.notna() & (
        output["occupation_code_4d"] != legacy_codes
    )

    output["sex"] = output["sex_code"].map({1.0: "Hombre", 2.0: "Mujer"})
    output["is_rural"] = output["area_raw"].eq(2).astype("int64")
    output["is_urban"] = output["area_raw"].eq(1).astype("int64")

    for column in OUTPUT_COLUMNS:
        if column not in output:
            output[column] = pd.NA

    audit = {
        "raw_rows": int(len(df)),
        "occupied_rows": int(len(output)),
        "codes_changed_from_legacy_right_padding": int(changed.sum()),
        "invalid_or_missing_occupation_codes": int(output["occupation_code_4d"].isna().sum()),
    }
    return output[OUTPUT_COLUMNS].reset_index(drop=True), audit


def discover_zips(raw_root: Path, years: list[int]) -> list[tuple[int, Path]]:
    found = []
    for year in years:
        candidates = sorted((raw_root / str(year)).glob("*/csv/*-Modulo76.zip"))
        if len(candidates) != 1:
            raise FileNotFoundError(
                f"Expected one annual module 76 ZIP for {year} under {raw_root}, "
                f"found {len(candidates)}"
            )
        found.append((year, candidates[0]))
    return found


def compare_datasets(existing: Path, regenerated: Path) -> dict[str, object]:
    """Compare two outputs by content while tolerating numeric serialization."""
    numeric_columns = set(NUMERIC_MAP) | {"is_rural", "is_urban"}
    mismatch_by_column = {column: 0 for column in OUTPUT_COLUMNS}
    unexpected_code_rows = 0
    rows = 0

    old_reader = pd.read_csv(existing, dtype=str, chunksize=100_000)
    new_reader = pd.read_csv(regenerated, dtype=str, chunksize=100_000)
    for old, new in zip(old_reader, new_reader, strict=True):
        if list(old.columns) != OUTPUT_COLUMNS or list(new.columns) != OUTPUT_COLUMNS:
            raise ValueError("Existing or regenerated output has an unexpected schema")
        if len(old) != len(new):
            raise ValueError("Existing and regenerated chunks have different row counts")
        rows += len(old)

        for column in OUTPUT_COLUMNS:
            if column in numeric_columns:
                left = pd.to_numeric(old[column], errors="coerce")
                right = pd.to_numeric(new[column], errors="coerce")
                equal = (left.isna() & right.isna()) | (
                    (left - right).abs() <= 1e-9 * (1 + left.abs())
                )
            else:
                equal = old[column].fillna("<NA>").eq(new[column].fillna("<NA>"))
            mismatch_by_column[column] += int((~equal).sum())

        expected = old["occupation_code_raw"].map(normalise_cno_code).astype("string")
        legacy = old["occupation_code_raw"].map(legacy_right_pad).astype("string")
        old_code = old["occupation_code_4d"].astype("string")
        new_code = new["occupation_code_4d"].astype("string")
        expected_new = new_code.eq(expected).fillna(new_code.isna() & expected.isna())
        expected_old = (old_code.eq(expected) | old_code.eq(legacy)).fillna(
            old_code.isna() & expected.isna()
        )
        unexpected_code_rows += int((~(expected_new & expected_old)).sum())

    non_code_mismatches = {
        column: count
        for column, count in mismatch_by_column.items()
        if column != "occupation_code_4d" and count
    }
    result = {
        "existing": portable_path(existing),
        "existing_sha256": sha256(existing),
        "rows_compared": rows,
        "mismatch_by_column": {
            column: count for column, count in mismatch_by_column.items() if count
        },
        "non_code_mismatches": non_code_mismatches,
        "unexpected_code_rows": unexpected_code_rows,
    }
    if non_code_mismatches or unexpected_code_rows:
        raise ValueError(f"Regenerated data differs unexpectedly: {result}")
    return result


def build_dataset(
    raw_root: Path,
    output: Path,
    years: list[int],
    compare_to: Path | None = None,
) -> dict[str, object]:
    inputs = discover_zips(raw_root, years)
    output.parent.mkdir(parents=True, exist_ok=True)
    year_audits = []

    with output.open("wb") as raw_output:
        with gzip.GzipFile(fileobj=raw_output, mode="wb", compresslevel=9, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text_output:
                first = True
                for expected_year, path in inputs:
                    raw = read_zip(path)
                    built, audit = build_occupied(raw)
                    observed_years = set(built["year"].dropna().astype(int).unique())
                    if observed_years != {expected_year}:
                        raise ValueError(
                            f"{path} contains years {sorted(observed_years)}, expected {expected_year}"
                        )
                    built.to_csv(text_output, index=False, header=first)
                    first = False
                    year_audits.append(
                        {
                            "year": expected_year,
                            "input": portable_path(path),
                            "input_sha256": sha256(path),
                            **audit,
                        }
                    )

    manifest = {
        "generator": portable_path(Path(__file__)),
        "output": portable_path(output),
        "output_sha256": sha256(output),
        "years": year_audits,
        "total_occupied_rows": sum(item["occupied_rows"] for item in year_audits),
        "total_codes_changed_from_legacy_right_padding": sum(
            item["codes_changed_from_legacy_right_padding"] for item in year_audits
        ),
    }
    if compare_to is not None:
        manifest["comparison"] = compare_datasets(compare_to, output)
    manifest_path = output.with_suffix(output.suffix + ".build.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the occupied-person annual EPEN departments dataset from official ZIPs."
    )
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--years", type=int, nargs="+", default=[2022, 2023, 2024, 2025])
    parser.add_argument(
        "--compare-to",
        type=Path,
        help="Existing processed file; fail if anything except corrected CNO codes changes.",
    )
    args = parser.parse_args()

    manifest = build_dataset(args.raw_root, args.output, args.years, args.compare_to)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
