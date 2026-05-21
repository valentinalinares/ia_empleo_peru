from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd


KEY_COLS = [
    "AÑO",
    "MES",
    "CONGLOME",
    "VIVIENDA",
    "HOGAR",
    "CODPERSO",
    "UBIGEO",
    "DOMINIO",
    "ESTRATO",
]

M200_COLS = KEY_COLS + ["P207", "P208A"]
M300_COLS = KEY_COLS + ["P301A", "P314B$2", "P314D"]
M500_COLS = KEY_COLS + ["OCU500", "P505R4", "P506R4", "P507", "P510", "P511A", "P512A", "FAC500A"]

VALUE_MAPPINGS = {
    "categoría ocupacional": {
        "values": [1, 2, 3, 4, 5, 6, 7],
        "labels": [
            "empleador o patrono",
            "trabajador independiente",
            "empleado",
            "obrero",
            "trabajador familiar no remunerado",
            "trabajador del hogar",
            "otro",
        ],
        "missing": None,
    },
    "sector institucional empleador": {
        "values": [1, 2, 3, 5, 6, 7],
        "labels": [
            "FFAA/PNP",
            "administracion publica",
            "empresa publica",
            "empresas especiales de servicios",
            "empresa o patrono privado",
            "otra",
        ],
        "missing": None,
    },
    "formalidad laboral (contrato)": {
        "values": [1, 2, 3, 4, 5, 6, 7, 8],
        "labels": [
            "indefinido",
            "plazo fijo",
            "periodo de prueba",
            "practicas preprof",
            "locacion de servicios",
            "CAS",
            "sin contrato",
            "otro",
        ],
        "missing": None,
    },
    "formalidad laboral (tamaño empresa)": {
        "values": [1, 2, 3, 4, 5, 9],
        "labels": ["<20 pp", "de 21 a 50", "de 51 a 100", "de 101 a 500", ">500", np.nan],
        "missing": 9,
    },
    "sexo del trabajador": {
        "values": [1, 2],
        "labels": ["hombre", "mujer"],
        "missing": None,
    },
    "nivel educativo": {
        "values": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "labels": [
            "sin nivel",
            "educación inicial",
            "primaria incompleta",
            "primaria completa",
            "secundaria incompleta",
            "secundaria completa",
            "superior no universitaria incompleta",
            "superior no universitaria completa",
            "superior universitaria incompleta",
            "superior universitaria completa",
            "maestría/doctorado",
            "básica especial",
        ],
        "missing": 99,
    },
    "uso de internet en trabajo": {
        "values": [0, 2],
        "labels": ["pase", "el trabajo"],
        "missing": None,
    },
    "frecuencia uso internet": {
        "values": [1, 2, 3, 4, 9],
        "labels": [
            "una vez al día",
            "una vez a la semana",
            "una vez al mes",
            "cada 2 meses o más",
            np.nan,
        ],
        "missing": 9,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Construye ENAHO_complete por año con módulos 02+03+05.")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--start-year", type=int, default=2019)
    parser.add_argument("--end-year", type=int, default=2024)
    return parser.parse_args()


def find_zip(year_dir: Path, module: str) -> Path:
    matches = list(year_dir.glob(f"*Modulo{module}.zip"))
    if not matches:
        raise FileNotFoundError(f"No se encontró ZIP para Modulo{module} en {year_dir}")
    return matches[0]


def find_csv_name(zip_path: Path, suffixes: list[str]) -> str:
    with ZipFile(zip_path) as zf:
        names = zf.namelist()
    lower_map = {name.lower(): name for name in names}
    for suffix in suffixes:
        for lower_name, original_name in lower_map.items():
            if lower_name.endswith(suffix.lower()):
                return original_name
    raise FileNotFoundError(f"No se encontró CSV con sufijos {suffixes} en {zip_path}")


def read_csv_from_zip(zip_path: Path, inner_name: str, usecols: list[str]) -> pd.DataFrame:
    with ZipFile(zip_path) as zf:
        with zf.open(inner_name) as handle:
            return pd.read_csv(handle, encoding="latin-1", usecols=lambda c: c in set(usecols), low_memory=False)


def build_codigo_unico(df: pd.DataFrame) -> pd.Series:
    return (
        df["AÑO"].astype("Int64").astype(str).str.zfill(4)
        + df["MES"].astype("Int64").astype(str).str.zfill(2)
        + df["CONGLOME"].astype("Int64").astype(str).str.zfill(5)
        + df["VIVIENDA"].astype("Int64").astype(str).str.zfill(2)
        + df["HOGAR"].astype("Int64").astype(str).str.zfill(2)
        + df["CODPERSO"].astype("Int64").astype(str).str.zfill(2)
        + df["UBIGEO"].astype(str).str.zfill(6)
        + df["DOMINIO"].astype("Int64").astype(str).str.zfill(2)
        + df["ESTRATO"].astype("Int64").astype(str).str.zfill(2)
    )


def rama6(div: int) -> str:
    if 1 <= div <= 3:
        return "Agri/Silvi/Pesca"
    if 5 <= div <= 9:
        return "Minería"
    if 10 <= div <= 33:
        return "Manufactura"
    if 41 <= div <= 43:
        return "Construcción"
    if 45 <= div <= 47:
        return "Comercio"
    if (35 <= div <= 39) or (49 <= div <= 53) or (55 <= div <= 56) or (58 <= div <= 66) or div == 68 or (69 <= div <= 75) or (77 <= div <= 82) or div == 84 or div == 85 or (86 <= div <= 88) or (90 <= div <= 96) or (97 <= div <= 99):
        return "Servicios/Otros"
    return "Servicios/Otros"


def extract_div(val) -> int | pd.NA:
    if pd.isna(val):
        return pd.NA
    s = str(val).strip()
    if not s.isdigit():
        return pd.NA
    if len(s) == 3:
        return int(s[0])
    if len(s) >= 4:
        return int(s[:2])
    return int(s)


def apply_value_labels(df: pd.DataFrame) -> pd.DataFrame:
    for col, mapping in VALUE_MAPPINGS.items():
        if col not in df.columns:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if mapping["missing"] is not None:
            df[col] = df[col].replace(mapping["missing"], np.nan)
        label_dict = dict(zip(mapping["values"], mapping["labels"]))
        df[col] = df[col].map(label_dict)
        df[col] = pd.Categorical(
            df[col],
            categories=[label for label in mapping["labels"] if not pd.isna(label)],
            ordered=True,
        )
    return df


def build_year_dataframe(raw_root: Path, year: int) -> pd.DataFrame:
    year_dir = raw_root / str(year) / "Anual - (Ene-Dic)"
    if not year_dir.exists():
        raise FileNotFoundError(f"No existe carpeta raw para {year}: {year_dir}")

    zip_02 = find_zip(year_dir, "02")
    zip_03 = find_zip(year_dir, "03")
    zip_05 = find_zip(year_dir, "05")

    csv_02 = find_csv_name(zip_02, ["-200.csv"])
    csv_03 = find_csv_name(zip_03, ["-300.csv"])
    csv_05 = find_csv_name(zip_05, ["-500.csv"])

    m200 = read_csv_from_zip(zip_02, csv_02, M200_COLS)
    m300 = read_csv_from_zip(zip_03, csv_03, M300_COLS)
    m500 = read_csv_from_zip(zip_05, csv_05, M500_COLS)

    for frame in (m200, m300, m500):
        frame["codigo_unico"] = build_codigo_unico(frame)

    m200 = m200.add_prefix("m200_").rename(columns={"m200_codigo_unico": "codigo_unico"})
    m300 = m300.add_prefix("m300_").rename(columns={"m300_codigo_unico": "codigo_unico"})
    m500 = m500.add_prefix("m500_").rename(columns={"m500_codigo_unico": "codigo_unico"})

    complete_df = m200.merge(m300, on="codigo_unico", how="inner")
    complete_df = complete_df.merge(m500, on="codigo_unico", how="inner")

    selected_df = complete_df[
        [
            "codigo_unico",
            "m500_OCU500",
            "m500_P505R4",
            "m500_P507",
            "m500_P510",
            "m500_P511A",
            "m500_P512A",
            "m200_P207",
            "m200_P208A",
            "m300_P301A",
            "m300_P314B$2",
            "m300_P314D",
            "m500_FAC500A",
            "m200_ESTRATO",
            "m500_P506R4",
        ]
    ].copy()

    column_mapping = {
        "m500_OCU500": "ocu500",
        "m500_P505R4": "ocupación del trabajador",
        "m500_P507": "categoría ocupacional",
        "m500_P510": "sector institucional empleador",
        "m500_P511A": "formalidad laboral (contrato)",
        "m500_P512A": "formalidad laboral (tamaño empresa)",
        "m200_P207": "sexo del trabajador",
        "m200_P208A": "edad del trabajador",
        "m300_P301A": "nivel educativo",
        "m300_P314B$2": "uso de internet en trabajo",
        "m300_P314D": "frecuencia uso internet",
        "m500_FAC500A": "factor",
        "m200_ESTRATO": "estrato",
        "m500_P506R4": "rama",
    }
    selected_df = selected_df.rename(columns=column_mapping)
    selected_df = selected_df.replace(r"^\s*$", np.nan, regex=True).replace("", np.nan)
    selected_df = apply_value_labels(selected_df)

    selected_df["rama_div"] = selected_df["rama"].apply(extract_div).astype("Int64")
    selected_df["rama_clasif"] = selected_df["rama_div"].apply(lambda x: rama6(int(x)) if pd.notna(x) else pd.NA)
    selected_df["year"] = year

    ordered_cols = [
        "year",
        "codigo_unico",
        "ocu500",
        "ocupación del trabajador",
        "categoría ocupacional",
        "sector institucional empleador",
        "formalidad laboral (contrato)",
        "formalidad laboral (tamaño empresa)",
        "sexo del trabajador",
        "edad del trabajador",
        "nivel educativo",
        "uso de internet en trabajo",
        "frecuencia uso internet",
        "factor",
        "estrato",
        "rama",
        "rama_div",
        "rama_clasif",
    ]
    return selected_df[ordered_cols].copy()


def main() -> None:
    args = parse_args()
    internal_root = args.project_root.resolve()
    if internal_root.name != "_interno":
        internal_root = internal_root / "_interno"
    raw_root = internal_root / "bases" / "originales" / "enaho"
    out_dir = internal_root / "bases" / "intermedias" / "enaho_complete_years"
    out_dir.mkdir(parents=True, exist_ok=True)

    frames: list[pd.DataFrame] = []
    for year in range(args.start_year, args.end_year + 1):
        print(f"Procesando ENAHO {year}...")
        frame = build_year_dataframe(raw_root, year)
        year_path = out_dir / f"ENAHO_complete_{year}.csv"
        frame.to_csv(year_path, index=False, encoding="utf-8-sig")
        frames.append(frame)
        print(f"  -> {len(frame):,} filas guardadas en {year_path.name}")

    combined = pd.concat(frames, ignore_index=True)
    combined_path = out_dir / f"ENAHO_complete_{args.start_year}_{args.end_year}.csv"
    combined.to_csv(combined_path, index=False, encoding="utf-8-sig")
    print(f"Combinado: {len(combined):,} filas en {combined_path}")


if __name__ == "__main__":
    main()
