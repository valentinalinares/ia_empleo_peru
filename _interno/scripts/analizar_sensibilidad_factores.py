from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE = REPO_ROOT / "_interno/bases/procesadas/epen_persona_departamentos_anual_2022_2025.csv.gz"
DEFAULT_INDEX = REPO_ROOT / "_interno/referencias/indices/anthropic-claude-sonnet-4-6_exposure_index.xlsx"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "_interno/outputs/sensibilidad_factores"
DEFAULT_REPORT = REPO_ROOT / "_interno/docs/epen_sensibilidad_factores.md"
BASELINE_BASE_SHA256 = "b71df3ff8fa2e2702dd11eed511aa9dd36ac5d3066c5d7b0735bd958229a7800"
YEARS_WITH_MISSING = (2023, 2024, 2025)
MATCH_KEYS = ["year", "month", "region_code", "area_raw"]
ADJUSTMENT_KEYS = ["year", "month", "region_code", "strata_code", "area_raw"]

REGION_LABELS = {
    "01": "Amazonas", "02": "Ancash", "03": "Apurimac", "04": "Arequipa",
    "05": "Ayacucho", "06": "Cajamarca", "08": "Cusco", "09": "Huancavelica",
    "10": "Huanuco", "11": "Ica", "12": "Junin", "13": "La Libertad",
    "14": "Lambayeque", "15": "Lima (incluye Lima Metropolitana y Callao)",
    "16": "Loreto", "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco",
    "20": "Piura", "21": "Puno", "22": "San Martin", "23": "Tacna",
    "24": "Tumbes", "25": "Ucayali",
}

OFFICIAL_NATIONAL = [
    {
        "year": 2022, "official_occupied": 17_336_500,
        "document": "Peru: Indicadores del Mercado Laboral a nivel departamental y de principales ciudades, 2022",
        "page": 42, "table": "Cuadro 3.1",
        "url": "https://www.inei.gob.pe/media/MenuRecursivo/publicaciones_digitales/Est/Lib1905/libro.pdf",
    },
    {
        "year": 2023, "official_occupied": 17_179_800,
        "document": "Peru: Comportamiento de los Indicadores del Mercado Laboral a Nivel Nacional y en 26 Ciudades",
        "page": 13, "table": "Cuadro 1.6A",
        "url": "https://www.inei.gob.pe/media/MenuRecursivo/boletines/epen-nacional-ivt2023.pdf",
    },
    {
        "year": 2024, "official_occupied": 17_322_900,
        "document": "Peru: Comportamiento de los Indicadores del Mercado Laboral a Nivel Nacional y en 27 Ciudades",
        "page": 13, "table": "Cuadro 1.6A",
        "url": "https://www.inei.gob.pe/media/MenuRecursivo/boletines/informe-tecnico_empleonacional.pdf",
    },
    {
        "year": 2025, "official_occupied": 17_575_200,
        "document": "Peru: Comportamiento de los Indicadores del Mercado Laboral a Nivel Nacional y en 27 Ciudades",
        "page": 10, "table": "Cuadro 1.7A",
        "url": "https://www.inei.gob.pe/media/MenuRecursivo/boletines/01-informe-tecnico-empleo-nacional.pdf",
    },
]

# El cuadro oficial separa Lima Metropolitana + Callao de las provincias de Lima.
# La base usa CCDD=15 para ambas, por eso se suman 5 019 400 y 1 030 100.
OFFICIAL_REGIONS_2022 = {
    "01": 228_500, "02": 632_800, "03": 245_600, "04": 749_900,
    "05": 369_200, "06": 812_500, "08": 783_200, "09": 198_400,
    "10": 392_800, "11": 485_500, "12": 705_400, "13": 1_098_800,
    "14": 674_800, "15": 5_019_400 + 1_030_100, "16": 512_900,
    "17": 101_400, "18": 97_900, "19": 149_100, "20": 1_171_600,
    "21": 718_300, "22": 506_400, "23": 204_600, "24": 131_700,
    "25": 315_700,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def portable_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def clean_code(series: pd.Series, width: int | None = None) -> pd.Series:
    result = series.astype("string").str.strip().str.replace(r"\.0+$", "", regex=True).replace("", pd.NA)
    return result.str.zfill(width) if width is not None else result


def read_inputs(base_path: Path, index_path: Path) -> pd.DataFrame:
    code_columns = {name: "string" for name in (
        "region_code", "strata_code", "area_raw", "occupation_code_4d",
        "education_code", "sex_code",
    )}
    base = pd.read_csv(base_path, dtype=code_columns, low_memory=False)
    base["region_code"] = clean_code(base["region_code"], 2)
    base["occupation_code_4d"] = clean_code(base["occupation_code_4d"], 4)
    for column in ("strata_code", "area_raw", "education_code", "sex_code"):
        base[column] = clean_code(base[column])
    for column in ("weight", "labor_income_monthly", "hours_week", "age"):
        base[column] = pd.to_numeric(base[column], errors="coerce")

    index = pd.read_excel(index_path, dtype={"code": "string"})
    index["code"] = clean_code(index["code"], 4)
    if index["code"].duplicated().any():
        duplicated = index.loc[index["code"].duplicated(), "code"].tolist()
        raise ValueError(f"Duplicated occupation codes in exposure index: {duplicated}")
    return base.merge(
        index[["code", "mean_exposure_score", "%_alta_exposicion"]],
        left_on="occupation_code_4d", right_on="code", how="left",
        validate="many_to_one",
    ).drop(columns="code")


def compare_official_figures(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    official = pd.DataFrame(OFFICIAL_NATIONAL)
    weighted = base.groupby("year", as_index=False)["weight"].sum(min_count=1).rename(columns={"weight": "base_weight_sum"})
    missing = (base.assign(factor_missing=base["weight"].isna()).groupby("year", as_index=False)
               .agg(sample_rows=("weight", "size"), missing_factor_rows=("factor_missing", "sum")))
    national = official.merge(weighted, on="year").merge(missing, on="year")
    national["absolute_difference"] = national["base_weight_sum"] - national["official_occupied"]
    national["percentage_difference"] = 100 * national["absolute_difference"] / national["official_occupied"]
    national["publication_status"] = "published"

    regions = pd.DataFrame([{
        "year": 2022, "region_code": code, "region_label": REGION_LABELS[code],
        "official_occupied": value,
    } for code, value in OFFICIAL_REGIONS_2022.items()])
    base_regions = (base.loc[base["year"].eq(2022)].groupby("region_code", as_index=False)["weight"]
                    .sum(min_count=1).rename(columns={"weight": "base_weight_sum"}))
    regions = regions.merge(base_regions, on="region_code", how="left")
    regions["absolute_difference"] = regions["base_weight_sum"] - regions["official_occupied"]
    regions["percentage_difference"] = 100 * regions["absolute_difference"] / regions["official_occupied"]
    regions["document"] = OFFICIAL_NATIONAL[0]["document"]
    regions["page"] = 42
    regions["table"] = "Cuadro 3.1"
    regions["url"] = OFFICIAL_NATIONAL[0]["url"]
    regions["alignment_note"] = "Transcripcion directa del dominio publicado."
    regions.loc[regions["region_code"].eq("15"), "alignment_note"] = (
        "Suma de Lima Metropolitana y Callao (5 019 400) y provincias de Lima "
        "(1 030 100), porque la base las conserva juntas en region_code=15."
    )
    return national, regions


def normal_two_sided_p(z_value: float) -> float:
    return math.erfc(abs(z_value) / math.sqrt(2.0)) if math.isfinite(z_value) else math.nan


def overlap_difference(frame: pd.DataFrame, value_column: str, keys: list[str]) -> dict[str, float | int]:
    valid = frame[keys + ["factor_missing", value_column]].dropna(subset=[value_column])
    grouped = (valid.groupby(keys + ["factor_missing"], dropna=False)[value_column]
               .agg(["size", "mean", "var"]).reset_index())
    with_factor = grouped.loc[~grouped["factor_missing"]].drop(columns="factor_missing")
    without_factor = grouped.loc[grouped["factor_missing"]].drop(columns="factor_missing")
    paired = with_factor.merge(without_factor, on=keys, suffixes=("_with", "_without"), how="inner")
    if paired.empty:
        return {"mean_with_factor": math.nan, "mean_without_factor": math.nan,
                "difference_without_minus_with": math.nan, "standardized_difference": math.nan,
                "z_statistic": math.nan, "p_value": math.nan, "matched_cells": 0,
                "n_with_factor": 0, "n_without_factor": 0}
    paired["overlap_weight"] = paired["size_with"] * paired["size_without"] / (paired["size_with"] + paired["size_without"])
    weights = paired["overlap_weight"].to_numpy(dtype=float)
    normalized = weights / weights.sum()
    mean_with = float(np.average(paired["mean_with"], weights=weights))
    mean_without = float(np.average(paired["mean_without"], weights=weights))
    difference = mean_without - mean_with
    degrees = paired["size_with"] + paired["size_without"] - 2
    pooled_cell_variance = (((paired["size_with"] - 1) * paired["var_with"].fillna(0)
                             + (paired["size_without"] - 1) * paired["var_without"].fillna(0))
                            / degrees.replace(0, np.nan))
    variance_mask = pooled_cell_variance.notna()
    pooled_variance = float(np.average(pooled_cell_variance.loc[variance_mask],
                                       weights=paired.loc[variance_mask, "overlap_weight"]))
    standardized = difference / math.sqrt(pooled_variance) if pooled_variance > 0 else math.nan
    sampling_variance = (paired["var_with"].fillna(0) / paired["size_with"]
                         + paired["var_without"].fillna(0) / paired["size_without"])
    standard_error = math.sqrt(float(np.sum(normalized**2 * sampling_variance)))
    z_statistic = difference / standard_error if standard_error > 0 else math.nan
    return {"mean_with_factor": mean_with, "mean_without_factor": mean_without,
            "difference_without_minus_with": difference, "standardized_difference": standardized,
            "z_statistic": z_statistic, "p_value": normal_two_sided_p(z_statistic),
            "matched_cells": int(len(paired)), "n_with_factor": int(paired["size_with"].sum()),
            "n_without_factor": int(paired["size_without"].sum())}


def compare_unweighted(base: pd.DataFrame) -> pd.DataFrame:
    working = base.loc[base["year"].isin(YEARS_WITH_MISSING)].copy()
    working["factor_missing"] = working["weight"].isna()
    working["major_occupation_group"] = working["occupation_code_4d"].str[0]
    continuous = {"indice_ia": "mean_exposure_score", "ingreso_mensual": "labor_income_monthly",
                  "horas_semanales": "hours_week", "edad": "age"}
    categorical = {"gran_grupo_ocupacional": "major_occupation_group",
                   "nivel_educativo": "education_code", "sexo": "sex"}
    records: list[dict[str, object]] = []
    for year in YEARS_WITH_MISSING:
        year_frame = working.loc[working["year"].eq(year)].copy()
        for outcome, column in continuous.items():
            records.append({"year": year, "outcome": outcome, "level": "mean",
                            "outcome_type": "continuous",
                            **overlap_difference(year_frame, column, MATCH_KEYS)})
        for outcome, column in categorical.items():
            category = year_frame[column].astype("string").fillna("Sin dato")
            for level in sorted(category.unique()):
                indicator = f"__indicator_{column}"
                year_frame[indicator] = category.eq(level).astype(float)
                records.append({"year": year, "outcome": outcome, "level": level,
                                "outcome_type": "binary_indicator",
                                **overlap_difference(year_frame, indicator, MATCH_KEYS)})
    result = pd.DataFrame.from_records(records)
    result["comparison_design"] = "Overlap-weighted within exact year-month-region-area cells; without factor minus with factor"
    result["test"] = "Normal approximation for overlap-weighted mean difference"
    return result


def build_adjusted_weights(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    working = base.copy()
    # "Con factor" significa FAC300_ANUAL observado. Los cuatro factores con
    # valor cero de 2023 cuentan como observados, aunque no aporten peso.
    working["factor_valid"] = working["weight"].notna()
    cells = (working.groupby(ADJUSTMENT_KEYS, dropna=False)
             .agg(total_persons=("factor_valid", "size"),
                  persons_with_factor=("factor_valid", "sum"),
                  original_weight_sum=("weight", "sum"))
             .reset_index())
    cells["persons_without_factor"] = cells["total_persons"] - cells["persons_with_factor"]
    cells["adjustment_multiplier"] = np.where(cells["persons_with_factor"].gt(0),
                                               cells["total_persons"] / cells["persons_with_factor"], np.nan)
    cells["valid_weight_mean"] = np.where(cells["persons_with_factor"].gt(0),
                                           cells["original_weight_sum"] / cells["persons_with_factor"], np.nan)
    cells["calibration_multiplier_c"] = np.where(cells["persons_with_factor"].gt(0),
                                                  cells["persons_with_factor"] / cells["total_persons"], np.nan)
    cells["uncovered_persons"] = np.where(cells["persons_with_factor"].eq(0),
                                           cells["total_persons"], 0).astype(int)
    working = working.merge(cells[ADJUSTMENT_KEYS + ["adjustment_multiplier", "valid_weight_mean",
                                                      "calibration_multiplier_c", "uncovered_persons"]],
                            on=ADJUSTMENT_KEYS, how="left", validate="many_to_one")
    working["adjusted_weight"] = np.where(working["factor_valid"],
                                           working["weight"] * working["adjustment_multiplier"], np.nan)
    provisional_c = np.where(working["factor_valid"], working["weight"],
                             working["valid_weight_mean"])
    working["imputed_calibrated_weight"] = provisional_c * working["calibration_multiplier_c"]
    version_c_sums = (working.groupby(ADJUSTMENT_KEYS, dropna=False)["imputed_calibrated_weight"]
                      .sum(min_count=1).rename("version_c_weight_sum").reset_index())
    cells = cells.merge(version_c_sums, on=ADJUSTMENT_KEYS, how="left", validate="one_to_one")
    cells["version_c_minus_original"] = cells["version_c_weight_sum"] - cells["original_weight_sum"]
    return working, cells


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    mask = values.notna() & weights.notna() & weights.gt(0)
    return float(np.average(values.loc[mask], weights=weights.loc[mask])) if mask.any() else math.nan


def sensitivity_indicators(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    adjusted, cells = build_adjusted_weights(base)
    adjusted = adjusted.loc[adjusted["year"].isin(YEARS_WITH_MISSING)].copy()
    indicators = {"exposicion_ia_media": ("mean_exposure_score", "proportion"),
                  "porcentaje_alta_exposicion": ("%_alta_exposicion", "percentage_points"),
                  "ingreso_mensual_medio": ("labor_income_monthly", "soles")}
    levels = [("national", None, None), ("region", "region_code", REGION_LABELS), ("sex", "sex", None)]
    records: list[dict[str, object]] = []
    for year in YEARS_WITH_MISSING:
        year_frame = adjusted.loc[adjusted["year"].eq(year)]
        for aggregation, group_column, labels in levels:
            grouped = [("Total", year_frame)] if group_column is None else [
                (str(group), frame) for group, frame in year_frame.groupby(group_column, dropna=False)]
            for group, frame in grouped:
                group_label = labels.get(group, group) if labels else group
                for indicator, (column, unit) in indicators.items():
                    original = weighted_mean(frame[column], frame["weight"])
                    adjusted_estimate = weighted_mean(frame[column], frame["adjusted_weight"])
                    imputed_estimate = weighted_mean(frame[column], frame["imputed_calibrated_weight"])
                    scale = 100.0 if unit == "percentage_points" else 1.0
                    original, adjusted_estimate, imputed_estimate = (
                        original * scale, adjusted_estimate * scale, imputed_estimate * scale)
                    difference_b = adjusted_estimate - original
                    difference_c = imputed_estimate - original
                    records.append({
                        "year": year, "aggregation": aggregation, "group_code": group,
                        "group_label": group_label, "indicator": indicator, "unit": unit,
                        "estimate_excluding_missing_factor": original,
                        "estimate_adjusted_nonresponse": adjusted_estimate,
                        "estimate_imputed_cell_mean_calibrated": imputed_estimate,
                        "absolute_difference": difference_b,
                        "percentage_difference": 100 * difference_b / original if original != 0 else math.nan,
                        "absolute_difference_c_minus_a": difference_c,
                        "percentage_difference_c_minus_a": 100 * difference_c / original if original != 0 else math.nan,
                        "sample_persons_total": int(len(frame)),
                        "sample_persons_with_factor": int(frame["factor_valid"].sum()),
                        "sample_persons_with_outcome_and_factor": int((frame[column].notna() & frame["factor_valid"]).sum()),
                    })
    totals = (adjusted.groupby("year", as_index=False)
              .agg(original_weight_sum=("weight", "sum"), adjusted_weight_sum=("adjusted_weight", "sum"),
                   imputed_calibrated_weight_sum=("imputed_calibrated_weight", "sum"),
                   sample_persons=("weight", "size"), sample_persons_with_factor=("factor_valid", "sum")))
    totals["absolute_increase"] = totals["adjusted_weight_sum"] - totals["original_weight_sum"]
    totals["percentage_increase"] = 100 * totals["absolute_increase"] / totals["original_weight_sum"]
    totals["version_c_minus_original"] = totals["imputed_calibrated_weight_sum"] - totals["original_weight_sum"]
    return pd.DataFrame.from_records(records), cells, totals


def indicator_trends(sensitivity: pd.DataFrame) -> pd.DataFrame:
    versions = {
        "a_exclusion": "estimate_excluding_missing_factor",
        "b_nonresponse_adjustment": "estimate_adjusted_nonresponse",
        "c_imputed_calibrated": "estimate_imputed_cell_mean_calibrated",
    }
    periods = ((2023, 2024), (2024, 2025), (2023, 2025))
    keys = ["aggregation", "group_code", "group_label", "indicator", "unit"]
    records: list[dict[str, object]] = []
    for key, group in sensitivity.groupby(keys, dropna=False):
        by_year = group.set_index("year")
        for start, end in periods:
            if start not in by_year.index or end not in by_year.index:
                continue
            for version, column in versions.items():
                start_value = float(by_year.loc[start, column])
                end_value = float(by_year.loc[end, column])
                change = end_value - start_value
                records.append({
                    **dict(zip(keys, key, strict=True)),
                    "year_start": start,
                    "year_end": end,
                    "version": version,
                    "estimate_start": start_value,
                    "estimate_end": end_value,
                    "absolute_change": change,
                    "percentage_change": 100 * change / start_value if start_value != 0 else math.nan,
                })
    return pd.DataFrame.from_records(records)


def format_number(value: float, digits: int = 2) -> str:
    return "NA" if pd.isna(value) else f"{value:,.{digits}f}".replace(",", " ")


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = ["| " + " | ".join(str(row[column]) for column in columns) + " |"
            for _, row in frame[columns].iterrows()]
    return "\n".join([header, separator, *rows])


def write_report(path: Path, national: pd.DataFrame, regions: pd.DataFrame,
                 unweighted: pd.DataFrame, sensitivity: pd.DataFrame,
                 cells: pd.DataFrame, totals: pd.DataFrame,
                 trends: pd.DataFrame, base_hash: str) -> None:
    national_display = national.copy()
    national_display["Año"] = national_display["year"]
    national_display["Oficial"] = national_display["official_occupied"].map(lambda x: format_number(x, 0))
    national_display["Suma FAC300_ANUAL"] = national_display["base_weight_sum"].map(lambda x: format_number(x, 1))
    national_display["Diferencia"] = national_display["absolute_difference"].map(lambda x: format_number(x, 1))
    national_display["Diferencia %"] = national_display["percentage_difference"].map(lambda x: format_number(x, 6))
    national_sensitivity = sensitivity.loc[sensitivity["aggregation"].eq("national")].copy()
    national_sensitivity["Año"] = national_sensitivity["year"]
    national_sensitivity["Indicador"] = national_sensitivity["indicator"]
    national_sensitivity["(a) Exclusión"] = national_sensitivity["estimate_excluding_missing_factor"].map(lambda x: format_number(x, 4))
    national_sensitivity["(b) Ajuste"] = national_sensitivity["estimate_adjusted_nonresponse"].map(lambda x: format_number(x, 4))
    national_sensitivity["(c) Imputación calibrada"] = national_sensitivity["estimate_imputed_cell_mean_calibrated"].map(lambda x: format_number(x, 4))
    national_sensitivity["(b)-(a)"] = national_sensitivity["absolute_difference"].map(lambda x: format_number(x, 4))
    national_sensitivity["(c)-(a)"] = national_sensitivity["absolute_difference_c_minus_a"].map(lambda x: format_number(x, 4))
    continuous = unweighted.loc[unweighted["outcome_type"].eq("continuous")].copy()
    continuous["Año"], continuous["Variable"] = continuous["year"], continuous["outcome"]
    continuous["Media con factor"] = continuous["mean_with_factor"].map(lambda x: format_number(x, 3))
    continuous["Media sin factor"] = continuous["mean_without_factor"].map(lambda x: format_number(x, 3))
    continuous["DME"] = continuous["standardized_difference"].map(lambda x: format_number(x, 3))
    continuous["p"] = continuous["p_value"].map(lambda x: format_number(x, 4))
    largest = (unweighted.loc[unweighted["outcome_type"].eq("binary_indicator")]
               .assign(abs_smd=lambda x: x["standardized_difference"].abs())
               .sort_values(["year", "outcome", "abs_smd"], ascending=[True, True, False])
               .groupby(["year", "outcome"], as_index=False).first())
    largest["Año"], largest["Variable"], largest["Categoría"] = largest["year"], largest["outcome"], largest["level"]
    largest["DME máxima"] = largest["standardized_difference"].map(lambda x: format_number(x, 3))
    zero_cells = cells.loc[cells["year"].isin(YEARS_WITH_MISSING) & cells["persons_with_factor"].eq(0)]
    uncovered = int(zero_cells["uncovered_persons"].sum())
    max_multiplier = cells.loc[cells["year"].isin(YEARS_WITH_MISSING), "adjustment_multiplier"].max()
    total_display = totals.copy()
    total_display["Año"] = total_display["year"]
    total_display["Pesos originales"] = total_display["original_weight_sum"].map(lambda x: format_number(x, 1))
    total_display["Pesos (b)"] = total_display["adjusted_weight_sum"].map(lambda x: format_number(x, 1))
    total_display["Aumento (b) %"] = total_display["percentage_increase"].map(lambda x: format_number(x, 3))
    total_display["Pesos (c)"] = total_display["imputed_calibrated_weight_sum"].map(lambda x: format_number(x, 1))
    total_display["Diferencia (c)"] = total_display["version_c_minus_original"].map(lambda x: format_number(x, 8))

    national_trends = trends.loc[trends["aggregation"].eq("national")].copy()
    version_labels = {
        "a_exclusion": "(a) Exclusión",
        "b_nonresponse_adjustment": "(b) Ajuste",
        "c_imputed_calibrated": "(c) Imputación calibrada",
    }
    national_trends["Versión"] = national_trends["version"].map(version_labels)
    national_trends["period"] = national_trends["year_start"].astype(str) + "-" + national_trends["year_end"].astype(str)
    trend_display = (national_trends.pivot(index=["indicator", "Versión"], columns="period",
                                           values="absolute_change").reset_index())
    trend_display = trend_display.rename(columns={"indicator": "Indicador"})
    for period in ("2023-2024", "2024-2025", "2023-2025"):
        trend_display[period] = trend_display[period].map(lambda x: format_number(x, 4))
    trend_2023_2025 = national_trends.loc[
        national_trends["year_start"].eq(2023) & national_trends["year_end"].eq(2025)
    ].set_index(["indicator", "version"])["absolute_change"]
    exposure_change_a = trend_2023_2025.loc[("exposicion_ia_media", "a_exclusion")]
    exposure_change_c = trend_2023_2025.loc[("exposicion_ia_media", "c_imputed_calibrated")]
    high_change_a = trend_2023_2025.loc[("porcentaje_alta_exposicion", "a_exclusion")]
    high_change_c = trend_2023_2025.loc[("porcentaje_alta_exposicion", "c_imputed_calibrated")]

    lines = [
        "# Sensibilidad a factores de expansión faltantes en la EPEN", "",
        "## Alcance y reproducibilidad", "",
        f"Este análisis usa la base de personas ocupadas EPEN 2022-2025 sin modificarla. Su SHA-256 al inicio y al final fue `{base_hash}`. Los indicadores de exposición se enlazan por `occupation_code_4d` con el índice Sonnet del proyecto.", "",
        "## 1. Contraste con cifras oficiales", "",
        markdown_table(national_display, ["Año", "Oficial", "Suma FAC300_ANUAL", "Diferencia", "Diferencia %"]), "",
        "Las diferencias son solo de redondeo. La suma de los factores válidos ya reproduce el total oficial incluso en 2023-2025, cuando existen filas sin `FAC300_ANUAL`.", "",
        "Fuentes oficiales verificadas:", "",
    ]
    for row in OFFICIAL_NATIONAL:
        lines.append(f"- {row['year']}: [{row['document']}]({row['url']}), p. {row['page']}, {row['table']}: {format_number(row['official_occupied'], 0)} personas ocupadas.")
    lines.extend([
        "",
        "Los cuatro años cuentan con publicación oficial. El informe 2022 también presenta departamentos (p. 42); los informes anuales 2023-2025 publican el total nacional y ciudades, no una tabla departamental. La comparación departamental 2022 está en `comparacion_cifras_oficiales_departamento_2022.csv`. Para alinear la geografía con `region_code=15`, se sumaron los dominios oficiales Lima Metropolitana y Callao, y provincias de Lima.", "",
        "## 2. Comparación sin pesos dentro de celdas comparables", "",
        "Se comparan personas sin y con factor dentro de celdas exactas año × mes × región × área. Las diferencias se combinan con pesos de solapamiento `n0*n1/(n0+n1)`. La prueba es bilateral, con aproximación normal, y la diferencia estandarizada usa la varianza intra-celda combinada. Son pruebas descriptivas: no incorporan el diseño muestral ni corrección por comparaciones múltiples.", "",
        markdown_table(continuous, ["Año", "Variable", "Media con factor", "Media sin factor", "DME", "p"]), "",
        "Mayor diferencia estandarizada por variable categórica:", "",
        markdown_table(largest, ["Año", "Variable", "Categoría", "DME máxima"]), "",
        "El detalle de todos los niveles de gran grupo ocupacional, educación y sexo se conserva en `comparacion_sin_pesos.csv`.", "",
        "## 3. Sensibilidad de los indicadores", "",
        "La versión (a) usa únicamente factores válidos. La versión (b) multiplica cada factor válido por `personas totales / personas con factor` dentro de año × mes × región × estrato × área y no incorpora las filas sin factor. La versión (c) asigna a cada persona sin factor el factor medio válido de su celda y luego reescala todos los factores de la celda para conservar exactamente la suma original. `% alta exposición` es la media ponderada de `%_alta_exposicion` del índice ocupacional y se expresa en puntos porcentuales.", "",
        markdown_table(national_sensitivity, ["Año", "Indicador", "(a) Exclusión", "(b) Ajuste", "(c) Imputación calibrada", "(b)-(a)", "(c)-(a)"]), "",
        "Efecto de las versiones sobre la suma de pesos:", "",
        markdown_table(total_display, ["Año", "Pesos originales", "Pesos (b)", "Aumento (b) %", "Pesos (c)", "Diferencia (c)"]), "",
        f"No hay celdas sin ningún factor válido: quedan {uncovered} personas sin cubrir. El multiplicador máximo de (b) es {max_multiplier:.4f}. La versión (c) conserva la suma original en cada celda, dentro de precisión numérica. Los resultados completos por región y sexo están en `sensibilidad_indicadores.csv`; las celdas y sus controles, en `celdas_ajuste_no_respuesta.csv`.", "",
        "## Tendencia 2023–2025", "",
        "La tabla muestra cambios absolutos. En exposición media son proporciones; en alta exposición, puntos porcentuales; y en ingreso, soles.", "",
        markdown_table(trend_display, ["Indicador", "Versión", "2023-2024", "2024-2025", "2023-2025"]), "",
        "La versión (b) eleva la exposición porque aumenta el peso de los respondentes de las celdas urbanas afectadas, pero no incorpora a las personas sin factor, cuya exposición observada es menor. La versión (c) sí incorpora a esas personas y preserva los totales calibrados, por lo que separa ese efecto de composición del aumento artificial de población de (b). El detalle nacional, regional y por sexo está en `tendencia_indicadores.csv`.", "",
        f"La tendencia de exposición **no es robusta al tratamiento de los factores faltantes**. Entre 2023 y 2025, (a) muestra un cambio de {exposure_change_a:+.4f} en exposición media y {high_change_a:+.4f} puntos porcentuales en alta exposición, mientras (c) muestra {exposure_change_c:+.4f} y {high_change_c:+.4f}, respectivamente. La imputación calibrada cambia el signo de ambos resultados; por tanto, no corresponde concluir que la exposición aumentó sin reportar esta sensibilidad.", "",
        "## Limitaciones", "",
        "- La prueba simple no sustituye inferencia con el diseño muestral completo.",
        "- Las versiones (b) y (c) suponen que la celda define un grupo adecuado para tratar la falta de factor. La versión (c), además, asigna el promedio de factor a cada caso faltante; es una sensibilidad, no un factor oficial reconstruido.",
        "- Las cifras oficiales están publicadas en centenas; las diferencias pequeñas con la suma de factores reflejan redondeo.", "",
        "## Recomendación", "",
        "**Usar la versión (a), exclusión de filas sin factor, como especificación principal; presentar (c) como sensibilidad conservadora de totales y no usar (b) como estimación central.** Los factores válidos ya reproducen los totales oficiales. La versión (b) los infla nuevamente. La versión (c) corrige ese problema, pero sigue dependiendo de una imputación no oficial, por lo que no desplaza a (a) como estimación central. Sin embargo, (c) sí contradice la dirección ascendente de la exposición entre 2023 y 2025 observada con (a). En consecuencia, los niveles deben reportarse con (a) como referencia, mientras la tendencia debe presentarse como no robusta y acompañada por el rango (a)-(c).",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_analysis(base_path: Path, index_path: Path, output_dir: Path, report_path: Path) -> dict[str, object]:
    initial_hash = sha256(base_path)
    base = read_inputs(base_path, index_path)
    national, regions = compare_official_figures(base)
    unweighted = compare_unweighted(base)
    sensitivity, cells, totals = sensitivity_indicators(base)
    trends = indicator_trends(sensitivity)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "comparacion_cifras_oficiales_nacional.csv": national,
        "comparacion_cifras_oficiales_departamento_2022.csv": regions,
        "comparacion_sin_pesos.csv": unweighted,
        "sensibilidad_indicadores.csv": sensitivity,
        "celdas_ajuste_no_respuesta.csv": cells,
        "totales_peso_sensibilidad.csv": totals,
        "tendencia_indicadores.csv": trends,
    }
    for filename, frame in outputs.items():
        frame.to_csv(output_dir / filename, index=False, encoding="utf-8-sig")
    final_hash = sha256(base_path)
    if final_hash != initial_hash:
        raise RuntimeError("The processed EPEN base changed during the analysis")
    if initial_hash != BASELINE_BASE_SHA256:
        raise RuntimeError(f"Unexpected processed EPEN base hash: {initial_hash}; expected {BASELINE_BASE_SHA256}")
    write_report(report_path, national, regions, unweighted, sensitivity, cells, totals, trends, initial_hash)
    metadata = {
        "base_path": portable_path(base_path), "base_sha256_before": initial_hash,
        "base_sha256_after": final_hash, "index_path": portable_path(index_path),
        "index_sha256": sha256(index_path), "rows": int(len(base)),
        "missing_factor_rows": int(base["weight"].isna().sum()),
        "years": sorted(int(year) for year in base["year"].unique()),
        "official_reports_available": [2022, 2023, 2024, 2025],
        "official_reports_unavailable": [],
        "uncovered_persons_in_adjustment_cells_2023_2025": int(cells.loc[cells["year"].isin(YEARS_WITH_MISSING), "uncovered_persons"].sum()),
        "max_abs_version_c_cell_difference": float(cells["version_c_minus_original"].abs().max()),
        "outputs": sorted(outputs), "report": portable_path(report_path),
    }
    (output_dir / "resumen_ejecucion.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze sensitivity to missing EPEN annual expansion factors.")
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(json.dumps(run_analysis(args.base, args.index, args.output_dir, args.report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
