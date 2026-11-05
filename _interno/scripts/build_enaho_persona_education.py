from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path

import pandas as pd


EDU_MAP = {
    1: "sin nivel",
    2: "educación inicial",
    3: "primaria incompleta",
    4: "primaria completa",
    5: "secundaria incompleta",
    6: "secundaria completa",
    7: "superior no universitaria incompleta",
    8: "superior no universitaria completa",
    9: "superior universitaria incompleta",
    10: "superior universitaria completa",
    11: "maestría/doctorado",
    12: "básica especial",
}

KEY_WIDTHS = {
    "year": 4,
    "month": 2,
    "cluster_id": 5,
    "dwelling_id": 2,
    "household_id": 2,
    "person_id": 2,
    "ubigeo": 6,
    "domain_code": 2,
    "strata_code": 2,
}


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Reconstruye education_code de ENAHO desde P301A preservado en las bases completas."
    )
    parser.add_argument("--project-root", type=Path, default=project_root)
    parser.add_argument("--start-year", type=int, default=2019)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_lf(path: Path) -> str:
    """SHA-256 con finales de linea normalizados a LF.

    Las bases completas son CSV de texto: en Windows Git puede escribirlas con
    CRLF. Normalizar evita que la huella dependa del sistema operativo.
    """
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def normalise_label(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = unicodedata.normalize("NFKD", str(value).strip().casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return re.sub(r"\s+", " ", text)


def education_label_to_code(value: object) -> int | pd.NA:
    label = normalise_label(value)
    if label is None:
        return pd.NA
    if label == "sin nivel":
        return 1
    if label.endswith("inicial"):
        return 2
    if label.startswith("primaria "):
        return 3 if label.endswith("incompleta") else 4
    if label.startswith("secundaria "):
        return 5 if label.endswith("incompleta") else 6
    if label.startswith("superior no universitaria "):
        return 7 if label.endswith("incompleta") else 8
    if label.startswith("superior universitaria "):
        return 9 if label.endswith("incompleta") else 10
    if label.startswith("maestr") and label.endswith("doctorado"):
        return 11
    if label.endswith("especial"):
        return 12
    raise ValueError(f"Etiqueta educativa no reconocida: {value!r}")


def read_as_text(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)


def integer_identifier(series: pd.Series, width: int) -> pd.Series:
    values = pd.to_numeric(series, errors="raise").astype("Int64")
    if values.isna().any():
        raise ValueError(f"La llave contiene {int(values.isna().sum())} valores faltantes.")
    return values.astype(str).str.zfill(width)


def build_person_key(frame: pd.DataFrame) -> pd.Series:
    missing = set(KEY_WIDTHS).difference(frame.columns)
    if missing:
        raise ValueError(f"Faltan columnas para la llave ENAHO: {sorted(missing)}")
    parts = [integer_identifier(frame[column], width) for column, width in KEY_WIDTHS.items()]
    result = parts[0]
    for part in parts[1:]:
        result = result + part
    return result


def education_lookup(complete_dir: Path, start_year: int, end_year: int) -> tuple[pd.Series, dict]:
    pieces: list[pd.Series] = []
    audit: dict[str, dict] = {}
    for year in range(start_year, end_year + 1):
        path = complete_dir / f"ENAHO_complete_{year}.csv"
        complete = pd.read_csv(path, dtype={"codigo_unico": "string"}, low_memory=False)
        if "education_code" in complete.columns:
            code = pd.to_numeric(complete["education_code"], errors="coerce").astype("Int64")
            source_column = "education_code (P301A preservado)"
        elif "nivel educativo" in complete.columns:
            code = complete["nivel educativo"].map(education_label_to_code).astype("Int64")
            source_column = "nivel educativo (P301A etiquetado)"
        else:
            raise ValueError(f"{path.name} no contiene P301A ni nivel educativo.")

        invalid = sorted(set(code.dropna().astype(int)).difference(EDU_MAP))
        if invalid:
            raise ValueError(f"{path.name} contiene códigos educativos fuera de EDU_MAP: {invalid}")

        keys = complete["codigo_unico"].astype("string").str.replace(r"\.0$", "", regex=True)
        if keys.isna().any() or keys.duplicated().any():
            raise ValueError(f"La llave codigo_unico no es completa y única en {path.name}.")
        pieces.append(pd.Series(code.array, index=keys, name="education_code"))
        audit[str(year)] = {
            "source": source_column,
            "rows": int(len(complete)),
            "non_missing": int(code.notna().sum()),
            "missing": int(code.isna().sum()),
            "codes": {str(k): int(v) for k, v in code.value_counts().sort_index().items()},
            "source_sha256_lf": sha256_lf(path),
        }

    lookup = pd.concat(pieces)
    if lookup.index.duplicated().any():
        raise ValueError("codigo_unico se repite entre las bases anuales.")
    return lookup, audit


def rebuild_education(
    input_path: Path,
    output_path: Path,
    complete_dir: Path,
    start_year: int,
    end_year: int,
    manifest_path: Path | None = None,
) -> dict:
    before_hash = sha256(input_path)
    # Leer todo como texto: asi se conservan ceros a la izquierda (region_code,
    # occupation_code_4d) y la representacion exacta de los decimales.
    before = read_as_text(input_path)
    if "education_code" not in before.columns:
        raise ValueError("La base procesada no contiene education_code.")
    original_other = before.drop(columns="education_code").copy(deep=True)

    lookup, source_audit = education_lookup(complete_dir, start_year, end_year)
    keys = build_person_key(before)
    if keys.duplicated().any():
        raise ValueError("La llave de persona no es única en la base procesada.")
    education = keys.map(lookup).astype("Int64")
    year = pd.to_numeric(before["year"], errors="raise").astype(int)
    missing_by_year = education.isna().groupby(year).sum()
    if (missing_by_year == year.groupby(year).size()).any():
        raise ValueError("education_code quedó completamente vacío en al menos un año.")
    before["education_code"] = education.astype("string").fillna("")

    pd.testing.assert_frame_equal(
        original_other,
        before.drop(columns="education_code"),
        check_dtype=True,
        check_exact=True,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output_path.parent, suffix=".csv.gz", delete=False) as temp:
        temp_path = Path(temp.name)
    try:
        # Salida determinista e igual en cualquier sistema: CRLF como la base
        # original, gzip sin nombre de archivo ni fecha en la cabecera.
        payload = before.to_csv(index=False, lineterminator="\r\n").encode("utf-8")
        with temp_path.open("wb") as raw, gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0
        ) as compressed:
            compressed.write(payload)
        serialized = read_as_text(temp_path)
        if list(serialized.columns) != list(before.columns):
            raise ValueError("El orden de columnas cambio al escribir la base.")
        pd.testing.assert_frame_equal(
            original_other.reset_index(drop=True),
            serialized.drop(columns="education_code").reset_index(drop=True),
            check_exact=True,
        )
        os.replace(temp_path, output_path)
    finally:
        temp_path.unlink(missing_ok=True)

    result = {
        "input": input_path.name,
        "output": output_path.name,
        "sha256_before": before_hash,
        "sha256_after": sha256(output_path),
        "rows": int(len(before)),
        "row_order_unchanged": True,
        "other_columns_unchanged": True,
        "education": {
            str(y): {
                "rows": int((year == y).sum()),
                "non_missing": int(education[year == y].notna().sum()),
                "missing": int(education[year == y].isna().sum()),
            }
            for y in range(start_year, end_year + 1)
        },
        "sources": source_audit,
        "edu_map": {str(key): value for key, value in EDU_MAP.items()},
    }
    if manifest_path is not None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    args = parse_args()
    internal_root = args.project_root.resolve()
    if internal_root.name != "_interno":
        internal_root = internal_root / "_interno"
    processed = internal_root / "bases" / "procesadas" / "enaho_persona_anual_2019_2025.csv.gz"
    input_path = (args.input or processed).resolve()
    output_path = (args.output or processed).resolve()
    manifest_path = (
        args.manifest
        or processed.with_name("enaho_persona_anual_2019_2025.education.build.json")
    ).resolve()
    result = rebuild_education(
        input_path=input_path,
        output_path=output_path,
        complete_dir=internal_root / "bases" / "intermedias" / "enaho_complete_years",
        start_year=args.start_year,
        end_year=args.end_year,
        manifest_path=manifest_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
