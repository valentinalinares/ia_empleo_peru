from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_ROOT = REPO_ROOT.parent / "data/raw/inei_data_core/epen_departamentos"
DEFAULT_BASE = (
    REPO_ROOT
    / "_interno/bases/procesadas/epen_persona_departamentos_anual_2022_2025.csv.gz"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "_interno/outputs/diagnostico_factores"
YEARS = (2022, 2023, 2024, 2025)

REGION_LABELS = {
    "01": "Amazonas",
    "02": "Ancash",
    "03": "Apurimac",
    "04": "Arequipa",
    "05": "Ayacucho",
    "06": "Cajamarca",
    "07": "Callao",
    "08": "Cusco",
    "09": "Huancavelica",
    "10": "Huanuco",
    "11": "Ica",
    "12": "Junin",
    "13": "La Libertad",
    "14": "Lambayeque",
    "15": "Lima",
    "16": "Loreto",
    "17": "Madre de Dios",
    "18": "Moquegua",
    "19": "Pasco",
    "20": "Piura",
    "21": "Puno",
    "22": "San Martin",
    "23": "Tacna",
    "24": "Tumbes",
    "25": "Ucayali",
}

RAW_COLUMNS = {
    "ANIO",
    "MES",
    "CCDD",
    "MUESTRA",
    "ESTRATO",
    "AREA",
    "LLAVE_PANEL",
    "CONGLOMERADO",
    "SELVIV",
    "HOGAR",
    "C201",
    "C207",
    "C208",
    "OCUP300",
    "RESIDENT",
    "FAC300_ANUAL",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def portable_path(path: Path) -> str:
    resolved = path.resolve()
    for root in (REPO_ROOT, REPO_ROOT.parent):
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            continue
    return str(resolved)


def clean_code(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0+$", "", regex=True)
        .replace("", pd.NA)
    )


def clean_value(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().replace("", pd.NA)


def find_zip(raw_root: Path, year: int) -> Path:
    matches = sorted((raw_root / str(year)).glob("*/csv/*-Modulo76.zip"))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected one module 76 ZIP for {year}, found {len(matches)}"
        )
    return matches[0]


def read_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        csv_files = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_files) != 1:
            raise ValueError(f"Expected one CSV inside {path}, found {len(csv_files)}")
        with archive.open(csv_files[0]) as stream:
            return pd.read_csv(
                stream,
                dtype=str,
                encoding="utf-8-sig",
                low_memory=False,
            )


def grouped_missing(
    occupied: pd.DataFrame,
    columns: list[str],
    labels: dict[str, dict[str, str]] | None = None,
) -> pd.DataFrame:
    grouped = (
        occupied.groupby(columns, dropna=False)["factor_missing"]
        .agg(group_rows="size", missing_rows="sum")
        .reset_index()
    )
    grouped["missing_pct_of_group"] = (
        100 * grouped["missing_rows"] / grouped["group_rows"]
    )
    if labels:
        for column, mapping in labels.items():
            grouped[f"{column}_label"] = grouped[column].map(mapping).fillna(
                "No identificado"
            )
    return grouped


def unit_integrity(occupied: pd.DataFrame) -> pd.DataFrame:
    common = ["year", "month", "sample_id", "region_code", "cluster_id"]
    levels = {
        "conglomerado": common,
        "vivienda": [*common, "dwelling_id"],
        "hogar": [*common, "dwelling_id", "household_id"],
    }
    records: list[dict[str, object]] = []
    for level, keys in levels.items():
        units = (
            occupied.groupby(keys, dropna=False)["factor_missing"]
            .agg(occupied_rows="size", missing_rows="sum")
            .reset_index()
        )
        units["status"] = "sin_faltantes"
        units.loc[
            units["missing_rows"].eq(units["occupied_rows"]), "status"
        ] = "unidad_completa_sin_factor"
        mixed = units["missing_rows"].gt(0) & units["missing_rows"].lt(
            units["occupied_rows"]
        )
        units.loc[mixed, "status"] = "unidad_mixta"
        summary = (
            units.groupby("status", dropna=False)
            .agg(
                units=("status", "size"),
                occupied_rows=("occupied_rows", "sum"),
                missing_rows=("missing_rows", "sum"),
            )
            .reset_index()
        )
        summary.insert(0, "level", level)
        records.extend(summary.to_dict(orient="records"))
    result = pd.DataFrame.from_records(records)
    result["missing_pct_within_status"] = (
        100 * result["missing_rows"] / result["occupied_rows"]
    )
    return result


def discover_factor_columns(columns: list[str]) -> list[str]:
    return [
        column
        for column in columns
        if re.search(r"fac|factor|peso", column, flags=re.IGNORECASE)
    ]


def build_diagnostic(raw_root: Path, processed_base: Path) -> dict[str, pd.DataFrame]:
    processed = pd.read_csv(
        processed_base,
        dtype=str,
        usecols=["year", "weight"],
        low_memory=False,
    )
    processed["year"] = pd.to_numeric(processed["year"], errors="raise").astype(int)
    processed["weight_missing"] = clean_value(processed["weight"]).isna()
    processed_summary = (
        processed.groupby("year", dropna=False)["weight_missing"]
        .agg(processed_occupied_rows="size", processed_missing_rows="sum")
        .reset_index()
    )

    occupied_frames: list[pd.DataFrame] = []
    activity_frames: list[pd.DataFrame] = []
    source_rows: list[dict[str, object]] = []
    factor_rows: list[dict[str, object]] = []

    for year in YEARS:
        zip_path = find_zip(raw_root, year)
        raw = read_zip(zip_path)
        missing_columns = sorted(RAW_COLUMNS - set(raw.columns))
        if missing_columns:
            raise ValueError(f"Missing raw columns for {year}: {missing_columns}")

        factor_columns = discover_factor_columns(list(raw.columns))
        annual = clean_value(raw["FAC300_ANUAL"])
        occupied_mask = clean_code(raw["OCUP300"]).eq("1")
        annual_missing = annual.isna()

        source_rows.append(
            {
                "year": year,
                "zip_path": portable_path(zip_path),
                "zip_sha256": sha256(zip_path),
                "raw_population_rows": len(raw),
                "raw_population_missing_rows": int(annual_missing.sum()),
                "raw_population_missing_pct": 100 * annual_missing.mean(),
                "raw_occupied_rows": int(occupied_mask.sum()),
                "raw_occupied_missing_rows": int(
                    (occupied_mask & annual_missing).sum()
                ),
                "raw_occupied_missing_pct": (
                    100 * (occupied_mask & annual_missing).sum() / occupied_mask.sum()
                ),
            }
        )

        for factor in factor_columns:
            present = clean_value(raw[factor]).notna()
            factor_rows.append(
                {
                    "year": year,
                    "factor_variable": factor,
                    "present_in_csv": True,
                    "nonmissing_population_rows": int(present.sum()),
                    "nonmissing_occupied_rows": int((present & occupied_mask).sum()),
                    "nonmissing_among_occupied_without_annual_factor": int(
                        (present & occupied_mask & annual_missing).sum()
                    ),
                }
            )

        activity_frames.append(
            pd.DataFrame(
                {
                    "year": year,
                    "labor_status_code": clean_code(raw["OCUP300"]),
                    "factor_missing": annual_missing,
                }
            )
        )
        occupied = raw.loc[occupied_mask].copy()
        occupied_frame = pd.DataFrame(
            {
                "year": year,
                "month": clean_code(occupied["MES"]),
                "region_code": clean_code(occupied["CCDD"]).str.zfill(2),
                "sample_id": clean_code(occupied["MUESTRA"]),
                "strata_code": clean_code(occupied["ESTRATO"]),
                "area_code": clean_code(occupied["AREA"]),
                "panel_key_present": clean_value(occupied["LLAVE_PANEL"]).notna(),
                "resident_code": clean_code(occupied["RESIDENT"]),
                "sex_code": clean_code(occupied["C207"]),
                "age": pd.to_numeric(clean_code(occupied["C208"]), errors="coerce"),
                "cluster_id": occupied["CONGLOMERADO"].astype("string"),
                "dwelling_id": occupied["SELVIV"].astype("string"),
                "household_id": occupied["HOGAR"].astype("string"),
                "person_id": clean_code(occupied["C201"]),
                "division_lima": (
                    clean_code(occupied["DIVISION_LIMA"])
                    if "DIVISION_LIMA" in occupied.columns
                    else pd.Series(pd.NA, index=occupied.index, dtype="string")
                ),
                "factor_missing": annual_missing.loc[occupied.index].to_numpy(),
            }
        )
        occupied_frames.append(occupied_frame.reset_index(drop=True))

    occupied_all = pd.concat(occupied_frames, ignore_index=True)
    activity_all = pd.concat(activity_frames, ignore_index=True)
    occupied_all["age_group"] = pd.cut(
        occupied_all["age"],
        bins=[13, 24, 44, 64, float("inf")],
        labels=["14-24", "25-44", "45-64", "65+"],
    ).astype("string")

    source = pd.DataFrame(source_rows).merge(processed_summary, on="year", how="left")
    source["raw_processed_rows_match"] = source["raw_occupied_rows"].eq(
        source["processed_occupied_rows"]
    )
    source["raw_processed_missing_match"] = source["raw_occupied_missing_rows"].eq(
        source["processed_missing_rows"]
    )

    region = grouped_missing(
        occupied_all,
        ["year", "region_code"],
        labels={"region_code": REGION_LABELS},
    )
    lima = occupied_all.loc[occupied_all["region_code"].eq("15")].copy()
    lima_labels = {
        "1": "Provincia de Lima, incluida Provincia Constitucional del Callao",
        "2": "Region Lima",
    }
    lima_table = grouped_missing(lima, ["year", "division_lima"])
    lima_table["division_lima_label"] = (
        lima_table["division_lima"].map(lima_labels).fillna("No identificado")
    )

    residence_panel = grouped_missing(
        occupied_all,
        ["year", "resident_code", "panel_key_present"],
    )
    residence_panel["resident_label"] = residence_panel["resident_code"].map(
        {"0": "No residente habitual", "1": "Residente habitual", "9": "Omision"}
    ).fillna("No identificado")

    tables = {
        "resumen_origen.csv": source,
        "faltantes_condicion_actividad.csv": grouped_missing(
            activity_all, ["year", "labor_status_code"]
        ),
        "faltantes_anio_mes.csv": grouped_missing(occupied_all, ["year", "month"]),
        "faltantes_region.csv": region,
        "faltantes_lima_callao.csv": lima_table,
        "faltantes_muestra.csv": grouped_missing(
            occupied_all, ["year", "sample_id"]
        ),
        "faltantes_estrato.csv": grouped_missing(
            occupied_all, ["year", "strata_code"]
        ),
        "faltantes_area.csv": grouped_missing(
            occupied_all,
            ["year", "area_code"],
            labels={"area_code": {"1": "Urbana", "2": "Rural"}},
        ),
        "faltantes_sexo.csv": grouped_missing(
            occupied_all,
            ["year", "sex_code"],
            labels={"sex_code": {"1": "Hombre", "2": "Mujer"}},
        ),
        "faltantes_edad.csv": grouped_missing(
            occupied_all, ["year", "age_group"]
        ),
        "integridad_unidades.csv": unit_integrity(occupied_all),
        "residencia_panel.csv": residence_panel,
        "variables_factor.csv": pd.DataFrame(factor_rows),
    }
    return tables


def write_diagnostic(
    raw_root: Path,
    processed_base: Path,
    output_dir: Path,
) -> dict[str, object]:
    before_sha = sha256(processed_base)
    tables = build_diagnostic(raw_root, processed_base)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(output_dir / name, index=False, encoding="utf-8")
    after_sha = sha256(processed_base)
    if before_sha != after_sha:
        raise RuntimeError("The processed EPEN base changed during the diagnostic")
    summary = {
        "processed_base": processed_base.as_posix(),
        "processed_base_sha256_before": before_sha,
        "processed_base_sha256_after": after_sha,
        "base_unchanged": before_sha == after_sha,
        "output_dir": output_dir.as_posix(),
        "tables": sorted(tables),
    }
    print(json.dumps(summary, indent=2))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose missing FAC300_ANUAL values without changing EPEN data."
    )
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--processed-base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    write_diagnostic(args.raw_root, args.processed_base, args.output_dir)


if __name__ == "__main__":
    main()
