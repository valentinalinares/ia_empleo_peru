from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

import nbformat as nbf


def md(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(text)


def code(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(text)


def src(text: str) -> str:
    return textwrap.dedent(text).strip()


def build_enaho_exposure_notebook(
    project_root: Path,
    base_csv: Path,
    analysis_year: int,
    index_path: Path | None = None,
) -> nbf.NotebookNode:
    workspace_root = project_root.parent
    resolved_index = (
        index_path.resolve()
        if index_path
        else (workspace_root / "abril2026" / "anthropic-claude-sonnet-4-6_exposure_index.xlsx")
    )
    output_dir = project_root / "outputs" / f"enaho_exposure_{analysis_year}"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"enaho_exposure_{analysis_year}_occupation_report.xlsx"

    setup_source = (
        src(
            """
            from pathlib import Path
            import json

            import numpy as np
            import pandas as pd
            import matplotlib.pyplot as plt
            from matplotlib.ticker import PercentFormatter, StrMethodFormatter
            from IPython.display import HTML, display

            try:
                import plotly.express as px
                import plotly.graph_objects as go
                HAS_PLOTLY = True
            except ModuleNotFoundError:
                px = None
                go = None
                HAS_PLOTLY = False

            PROJECT_ROOT = Path(r"__PROJECT_ROOT__")
            WORKSPACE_ROOT = Path(r"__WORKSPACE_ROOT__")
            BASE_CSV_PATH = Path(r"__BASE_CSV__")
            INDEX_PATH = Path(r"__INDEX_PATH__")
            REPORT_PATH = Path(r"__REPORT_PATH__")
            PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
            OUTPUT_DIR = Path(r"__OUTPUT_DIR__")
            OUTPUT_TABLES = OUTPUT_DIR / "annual_tables"
            OUTPUT_TABLES.mkdir(parents=True, exist_ok=True)
            ANALYSIS_YEAR = __ANALYSIS_YEAR__

            PROFILE_SHEETS = [
                "sexo",
                "educacion",
                "categoria",
                "categoria_agregada",
                "grupo_edad",
                "formalidad_contrato",
                "formalidad_tamano",
                "rama",
                "estrato",
            ]
            PERSONA_REGIONS = [(15, "Lima"), (4, "Arequipa"), (13, "La Libertad"), (7, "Callao")]
            DEPT_NAMES = {
                1: "Amazonas",
                2: "Ancash",
                3: "Apurímac",
                4: "Arequipa",
                5: "Ayacucho",
                6: "Cajamarca",
                7: "Callao",
                8: "Cusco",
                9: "Huancavelica",
                10: "Huánuco",
                11: "Ica",
                12: "Junín",
                13: "La Libertad",
                14: "Lambayeque",
                15: "Lima",
                16: "Loreto",
                17: "Madre de Dios",
                18: "Moquegua",
                19: "Pasco",
                20: "Piura",
                21: "Puno",
                22: "San Martín",
                23: "Tacna",
                24: "Tumbes",
                25: "Ucayali",
            }
            CAT_MAP = {
                1: "Empleador/a",
                2: "Independiente",
                3: "Empleado/a",
                4: "Obrero/a",
                5: "Familiar no remunerado/a",
                6: "Trab. del hogar",
                7: "Otro",
            }
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
            COLORS = {
                "accent": "#c25b2a",
                "accent2": "#2563eb",
                "accent3": "#059669",
                "yellow": "#d97706",
                "text": "#1a1a1a",
                "muted": "#6b7280",
                "border": "#e5e7eb",
                "bg": "#f8f8f6",
                "card": "#ffffff",
            }

            pd.set_option("display.max_columns", 160)
            pd.set_option("display.max_rows", 120)
            if HAS_PLOTLY:
                px.defaults.template = "plotly_white"

            CSS = f\"\"\"
            <style>
            body {{ background:{COLORS["bg"]}; }}
            .audit-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin:8px 0 20px 0; }}
            .audit-card {{ background:{COLORS["card"]}; border:1px solid {COLORS["border"]}; border-radius:14px; padding:14px 16px; }}
            .audit-card .eyebrow {{ font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:{COLORS["muted"]}; }}
            .audit-card .value {{ font-size:30px; font-weight:700; color:{COLORS["accent"]}; margin-top:4px; }}
            .audit-card .sub {{ font-size:12px; color:{COLORS["muted"]}; margin-top:3px; }}
            .audit-note {{ background:#fffbf5; border-left:4px solid {COLORS["yellow"]}; border-radius:0 10px 10px 0; padding:12px 16px; margin:14px 0; color:#78350f; }}
            .audit-note.blue {{ background:#eff6ff; border-left-color:{COLORS["accent2"]}; color:#1e3a8a; }}
            .audit-note.green {{ background:#f0fdf4; border-left-color:{COLORS["accent3"]}; color:#14532d; }}
            .mini-tag {{ display:inline-block; padding:2px 8px; border-radius:999px; background:#f3f4f6; color:{COLORS["muted"]}; font-size:11px; margin-right:6px; }}
            </style>
            \"\"\"
            display(HTML(CSS))

            def safe_zfill(series):
                return pd.to_numeric(series, errors="coerce").astype("Int64").astype("string").str.zfill(4)

            def weighted_mean(values, weights):
                v = pd.to_numeric(values, errors="coerce")
                w = pd.to_numeric(weights, errors="coerce")
                mask = v.notna() & w.notna() & (w > 0)
                if not mask.any():
                    return np.nan
                return float(np.average(v[mask], weights=w[mask]))

            def weighted_share(mask, weights):
                return weighted_mean(pd.Series(mask).astype(float), weights)

            def weighted_median(values, weights):
                v = pd.to_numeric(values, errors="coerce")
                w = pd.to_numeric(weights, errors="coerce")
                mask = v.notna() & w.notna() & (w > 0)
                if not mask.any():
                    return np.nan
                ordered = pd.DataFrame({"value": v[mask], "weight": w[mask]}).sort_values("value")
                cutoff = ordered["weight"].sum() / 2
                return float(ordered.loc[ordered["weight"].cumsum() >= cutoff, "value"].iloc[0])

            def fmt_pct(value, digits=1):
                if pd.isna(value):
                    return "N/D"
                return f"{value * 100:.{digits}f}%"

            def fmt_num(value):
                if pd.isna(value):
                    return "N/D"
                return f"{value:,.0f}"

            def fmt_sol(value):
                if pd.isna(value):
                    return "N/D"
                return f"S/ {value:,.0f}"

            def render_cards(cards):
                html = ['<div class="audit-grid">']
                for card in cards:
                    html.append(
                        "<div class='audit-card'>"
                        f"<div class='eyebrow'>{card['label']}</div>"
                        f"<div class='value'>{card['value']}</div>"
                        f"<div class='sub'>{card['sub']}</div>"
                        "</div>"
                    )
                html.append("</div>")
                display(HTML("".join(html)))

            def render_note(text, tone="amber"):
                klass = "audit-note"
                if tone == "blue":
                    klass += " blue"
                elif tone == "green":
                    klass += " green"
                display(HTML(f"<div class='{klass}'>{text}</div>"))

            def show_plotly(fig, include_js=False):
                if HAS_PLOTLY and fig is not None:
                    display(HTML(fig.to_html(full_html=False, include_plotlyjs="cdn" if include_js else False)))
            """
        )
        .replace("__PROJECT_ROOT__", str(project_root))
        .replace("__WORKSPACE_ROOT__", str(workspace_root))
        .replace("__BASE_CSV__", str(base_csv.resolve()))
        .replace("__INDEX_PATH__", str(resolved_index))
        .replace("__REPORT_PATH__", str(report_path))
        .replace("__OUTPUT_DIR__", str(output_dir))
        .replace("__ANALYSIS_YEAR__", str(analysis_year))
    )
    load_source = src(
        """
        report_xl = pd.ExcelFile(REPORT_PATH)
        report = {sheet: report_xl.parse(sheet) for sheet in report_xl.sheet_names}
        occupation_summary = report["occupation_summary"].copy()
        occupation_summary["code"] = occupation_summary["code"].astype(str).str.zfill(4)
        occupation_summary = occupation_summary.sort_values("weighted_population", ascending=False).reset_index(drop=True)
        coverage = report["coverage"].iloc[0].to_dict()
        profiles = {sheet: report[sheet].copy() for sheet in PROFILE_SHEETS if sheet in report}

        top_occ = (
            occupation_summary[occupation_summary["weighted_population"] > 50000]
            .nlargest(20, "mean_exposure_score")
            .copy()
        )
        bubble_df = occupation_summary[occupation_summary["weighted_population"] >= 80000].copy()
        bubble_df["workers_millions"] = bubble_df["weighted_population"] / 1_000_000
        bubble_df["women_pct"] = bubble_df["share_women"] * 100

        comparison_rows = []
        for sheet_name, df in profiles.items():
            clean = df.dropna(subset=["mean_exposure_score"]).sort_values("mean_exposure_score", ascending=False).copy()
            if clean.empty:
                continue
            top_row = clean.iloc[0]
            bottom_row = clean.iloc[-1]
            comparison_rows.append(
                {
                    "dimension": sheet_name,
                    "top_group": str(top_row["group"]),
                    "top_exposure": float(top_row["mean_exposure_score"]),
                    "top_share": float(top_row["population_share"]),
                    "bottom_group": str(bottom_row["group"]),
                    "bottom_exposure": float(bottom_row["mean_exposure_score"]),
                    "bottom_share": float(bottom_row["population_share"]),
                    "gap_exposure": float(top_row["mean_exposure_score"] - bottom_row["mean_exposure_score"]),
                }
            )
        comparison_df = pd.DataFrame(comparison_rows).sort_values("gap_exposure", ascending=False).reset_index(drop=True)

        idx = pd.read_excel(INDEX_PATH)
        idx["code"] = safe_zfill(idx["code"])
        idx = idx[
            [
                "code",
                "occupation_group",
                "mean_exposure_score",
                "median_exposure_score",
                "%_alta_exposicion",
                "%_media_alta_exp",
                "%_sustitucion",
                "%_aumento",
            ]
        ].copy()

        base = pd.read_csv(BASE_CSV_PATH, low_memory=False)
        if "year" in base.columns:
            base = base[base["year"] == ANALYSIS_YEAR].copy()
        if "ocu500" in base.columns:
            base["ocu500"] = pd.to_numeric(base["ocu500"], errors="coerce")
            base = base[base["ocu500"] == 1].copy()
        base["factor"] = pd.to_numeric(base["factor"], errors="coerce").fillna(0)
        base = base[base["factor"] > 0].copy()
        base["occupation_code_4d"] = safe_zfill(base["ocupación del trabajador"])
        base["age"] = pd.to_numeric(base["edad del trabajador"], errors="coerce")
        base_merged = base.merge(idx, how="left", left_on="occupation_code_4d", right_on="code")
        matched_base = base_merged[base_merged["mean_exposure_score"].notna()].copy()

        enaho_micro = pd.read_csv(PROCESSED_DIR / "enaho_persona_anual_2019_2024.csv.gz")
        enaho_micro = enaho_micro[enaho_micro["year"] == ANALYSIS_YEAR].copy()
        enaho_micro["weight"] = pd.to_numeric(enaho_micro["weight"], errors="coerce")
        enaho_micro["labor_income_monthly"] = pd.to_numeric(enaho_micro["labor_income_monthly"], errors="coerce")
        enaho_micro["age"] = pd.to_numeric(enaho_micro["age"], errors="coerce")
        enaho_micro["is_urban"] = pd.to_numeric(enaho_micro["is_urban"], errors="coerce")
        enaho_micro = enaho_micro[enaho_micro["weight"] > 0].copy()
        enaho_micro["occupation_code_4d"] = safe_zfill(enaho_micro["occupation_code_4d"])
        enaho_micro["education_label"] = pd.to_numeric(enaho_micro["education_code"], errors="coerce").map(EDU_MAP)
        enaho_micro["category_label"] = pd.to_numeric(enaho_micro["occupational_category_code"], errors="coerce").map(CAT_MAP).fillna("Otro")
        enaho_micro["region_name"] = pd.to_numeric(enaho_micro["region_code"], errors="coerce").map(DEPT_NAMES)
        enaho_micro = enaho_micro.merge(idx, how="inner", left_on="occupation_code_4d", right_on="code")

        q25 = enaho_micro["mean_exposure_score"].quantile(0.25)
        q75 = enaho_micro["mean_exposure_score"].quantile(0.75)
        persona_q1 = enaho_micro[enaho_micro["mean_exposure_score"] <= q25].copy()
        persona_q4 = enaho_micro[enaho_micro["mean_exposure_score"] >= q75].copy()

        resumen = pd.read_csv(PROCESSED_DIR / "resumen_ocupacion_anio.csv.gz")
        resumen["occupation_code_4d"] = safe_zfill(resumen["occupation_code_4d"])
        income_df = resumen[
            (resumen["source"] == "ENAHO") &
            (resumen["year"] == ANALYSIS_YEAR) &
            (resumen["weighted_population"] > 50000) &
            (resumen["income_monthly_weighted_mean"].notna())
        ].copy()
        income_df = income_df.merge(
            idx[["code", "occupation_group", "mean_exposure_score", "%_alta_exposicion"]],
            how="inner",
            left_on="occupation_code_4d",
            right_on="code",
        )
        income_df["income_gap_vs_median"] = income_df["income_monthly_weighted_mean"] - income_df["income_monthly_median_weighted"]
        income_corr = income_df["mean_exposure_score"].corr(income_df["income_monthly_weighted_mean"]) if len(income_df) >= 3 else np.nan

        epen = pd.read_csv(PROCESSED_DIR / "epen_persona_departamentos_anual_2022_2025.csv.gz")
        epen["occupation_code_4d"] = safe_zfill(epen["occupation_code_4d"])
        epen["weight"] = pd.to_numeric(epen["weight"], errors="coerce")
        epen["labor_income_monthly"] = pd.to_numeric(epen["labor_income_monthly"], errors="coerce")
        epen = epen[(epen["year"] == ANALYSIS_YEAR) & (epen["weight"] > 0)].copy()
        if not epen.empty:
            epen = epen.merge(
                idx[["code", "occupation_group", "mean_exposure_score", "%_alta_exposicion", "%_aumento", "%_sustitucion"]],
                how="inner",
                left_on="occupation_code_4d",
                right_on="code",
            )
            regional_df = (
                epen.groupby("region_code", dropna=False)
                .apply(
                    lambda g: pd.Series(
                        {
                            "region_name": DEPT_NAMES.get(int(g.name), f"Región {int(g.name)}") if pd.notna(g.name) else "N/D",
                            "workers": g["weight"].sum(),
                            "mean_exposure": weighted_mean(g["mean_exposure_score"], g["weight"]),
                            "pct_alta": weighted_mean(g["%_alta_exposicion"], g["weight"]),
                            "pct_aumento": weighted_mean(g["%_aumento"], g["weight"]),
                            "pct_sustitucion": weighted_mean(g["%_sustitucion"], g["weight"]),
                            "income_mean": weighted_mean(g["labor_income_monthly"], g["weight"]),
                        }
                    ),
                    include_groups=False,
                )
                .reset_index()
                .sort_values("mean_exposure", ascending=False)
                .reset_index(drop=True)
            )
            regional_top_occ = (
                epen.groupby(["region_code", "occupation_code_4d", "occupation_group"], dropna=False)
                .apply(
                    lambda g: pd.Series(
                        {
                            "workers": g["weight"].sum(),
                            "mean_exposure": weighted_mean(g["mean_exposure_score"], g["weight"]),
                        }
                    ),
                    include_groups=False,
                )
                .reset_index()
            )
            regional_top_occ = regional_top_occ[regional_top_occ["workers"] > 10000].copy()
        else:
            regional_df = pd.DataFrame(columns=["region_code", "region_name", "workers", "mean_exposure", "pct_alta", "pct_aumento", "pct_sustitucion", "income_mean"])
            regional_top_occ = pd.DataFrame(columns=["region_code", "occupation_code_4d", "occupation_group", "workers", "mean_exposure"])

        crosswalk = pd.read_csv(PROCESSED_DIR / "ocupacion_crosswalk_4d.csv")
        crosswalk["occupation_code_4d"] = crosswalk["occupation_code_4d"].astype(str).str.zfill(4)

        unmatched_occ = (
            base_merged[base_merged["mean_exposure_score"].isna() & base_merged["occupation_code_4d"].notna()]
            .groupby("occupation_code_4d", dropna=False)
            .agg(weighted_population=("factor", "sum"))
            .reset_index()
            .sort_values("weighted_population", ascending=False)
        )
        unmatched_occ = unmatched_occ.merge(crosswalk[["occupation_code_4d", "occupation_name_cno"]], how="left", on="occupation_code_4d")
        unmatched_occ["reason"] = np.where(unmatched_occ["occupation_name_cno"].notna(), "Sin score en índice IA", "Sin nombre en crosswalk")

        income_outliers = enaho_micro[enaho_micro["labor_income_monthly"].notna()].copy()
        outliers_over_20k = int((income_outliers["labor_income_monthly"] > 20000).sum())
        outliers_over_50k = int((income_outliers["labor_income_monthly"] > 50000).sum())

        audit_summary = {
            "report_rows": int(len(base)),
            "report_weight_total": float(base["factor"].sum()),
            "coverage_weighted": float(coverage["cobertura_ponderada"]),
            "covered_workers": float(coverage["peso_con_indice"]),
            "mean_exposure": float(coverage["media_exposicion_ponderada"]),
            "pct_alta": float(coverage["media_pct_alta_ponderada"]),
            "pct_sustitucion": float(coverage["media_pct_sustitucion_ponderada"]),
            "pct_aumento": float(coverage["media_pct_aumento_ponderada"]),
            "matched_occupations": int(coverage["ocupaciones_emparejadas"]),
            "observed_occupations": int(coverage["ocupaciones_observadas"]),
            "unmatched_occupations": int(len(unmatched_occ)),
            "income_outliers_over_20k": outliers_over_20k,
            "income_outliers_over_50k": outliers_over_50k,
        }

        print(f"Año analizado: {ANALYSIS_YEAR}")
        print(f"Ocupaciones en reporte anual: {len(occupation_summary)}")
        print(f"Cobertura ponderada: {coverage['cobertura_ponderada']:.4f}")
        print(f"Ocupaciones sin score IA: {len(unmatched_occ)}")
        """
    )
    kpi_source = src(
        """
        render_cards(
            [
                {
                    "label": "Cobertura del índice",
                    "value": fmt_pct(coverage["cobertura_ponderada"]),
                    "sub": f"{fmt_num(coverage['peso_con_indice'])} ocupados ponderados con match",
                },
                {
                    "label": "Exposición media",
                    "value": fmt_pct(coverage["media_exposicion_ponderada"]),
                    "sub": "Promedio ponderado del score ocupacional",
                },
                {
                    "label": "Alta exposición",
                    "value": fmt_pct(coverage["media_pct_alta_ponderada"]),
                    "sub": "Participación ponderada de tareas altamente expuestas",
                },
                {
                    "label": "Augmentation / sustitución",
                    "value": f"{fmt_pct(coverage['media_pct_aumento_ponderada'])} / {fmt_pct(coverage['media_pct_sustitucion_ponderada'])}",
                    "sub": "Promedios ponderados del índice ocupacional",
                },
            ]
        )

        render_note(
            "Este cuaderno usa exactamente el reporte anual ya consolidado en Excel y lo cruza con los microdatos armonizados para abrir cada componente por año. "
            "La redacción y las salidas corresponden a una versión final, trazable y replicable.",
            tone="green",
        )

        pd.DataFrame([coverage]).T.rename(columns={0: "valor"})
        """
    )
    top_occ_source = src(
        """
        display(
            top_occ[
                [
                    "code",
                    "occupation_group",
                    "weighted_population",
                    "mean_exposure_score",
                    "pct_alta_exposicion",
                    "pct_aumento",
                    "share_women",
                ]
            ].rename(
                columns={
                    "code": "cno_4d",
                    "occupation_group": "ocupacion",
                    "weighted_population": "trabajadores",
                    "mean_exposure_score": "exposicion_media",
                    "pct_alta_exposicion": "pct_alta_exposicion",
                    "pct_aumento": "pct_aumento",
                    "share_women": "pct_mujeres",
                }
            )
        )

        if HAS_PLOTLY:
            fig = px.bar(
                top_occ.sort_values("mean_exposure_score"),
                x="mean_exposure_score",
                y="occupation_group",
                orientation="h",
                color="weighted_population",
                color_continuous_scale=["#fde68a", "#c25b2a"],
                hover_data={
                    "code": True,
                    "weighted_population": ":,.0f",
                    "pct_alta_exposicion": ":.1%",
                    "pct_aumento": ":.1%",
                    "share_women": ":.1%",
                },
                labels={
                    "mean_exposure_score": "Exposición media",
                    "occupation_group": "Ocupación",
                    "weighted_population": "Trabajadores",
                },
            )
            fig.update_layout(
                title=f"Top 20 ocupaciones con mayor exposición media ({ANALYSIS_YEAR})",
                height=720,
                coloraxis_colorbar_title="Trabajadores",
                margin=dict(l=10, r=10, t=60, b=20),
            )
            show_plotly(fig, include_js=True)
        else:
            ordered = top_occ.sort_values("mean_exposure_score")
            fig, ax = plt.subplots(figsize=(10, 7))
            ax.barh(ordered["occupation_group"], ordered["mean_exposure_score"], color=COLORS["accent"])
            ax.set_xlabel("Exposición media")
            ax.set_ylabel("")
            ax.set_title(f"Top 20 ocupaciones con mayor exposición media ({ANALYSIS_YEAR})")
            plt.tight_layout()
            plt.show()
        """
    )
    bubble_source = src(
        """
        render_note(
            "El gráfico feo de ocupaciones contra sustitución se eliminó. En la versión final, el mapa ocupacional replica el producto del HTML maestro: "
            "exposición media, tamaño del empleo y composición por sexo.",
            tone="blue",
        )

        if HAS_PLOTLY:
            fig = px.scatter(
                bubble_df,
                x="mean_exposure_score",
                y="weighted_population",
                size="weighted_population",
                color="share_women",
                color_continuous_scale=["#2563eb", "#f59e0b", "#c25b2a"],
                hover_name="occupation_group",
                hover_data={
                    "code": True,
                    "weighted_population": ":,.0f",
                    "pct_alta_exposicion": ":.1%",
                    "pct_aumento": ":.1%",
                    "share_women": ":.1%",
                    "mean_age": ":.1f",
                },
                labels={
                    "mean_exposure_score": "Exposición media",
                    "weighted_population": "Trabajadores",
                    "share_women": "Proporción de mujeres",
                },
                size_max=48,
                log_y=True,
            )
            fig.update_layout(
                title=f"Exposición vs tamaño del empleo ({ANALYSIS_YEAR})",
                height=640,
                margin=dict(l=10, r=10, t=60, b=30),
            )
            show_plotly(fig)
        else:
            fig, ax = plt.subplots(figsize=(10, 7))
            sizes = np.sqrt(bubble_df["weighted_population"] / bubble_df["weighted_population"].max()) * 1600
            scatter = ax.scatter(
                bubble_df["mean_exposure_score"],
                bubble_df["weighted_population"],
                s=sizes,
                c=bubble_df["share_women"],
                cmap="cividis",
                alpha=0.72,
                edgecolors="white",
                linewidth=0.6,
            )
            ax.set_yscale("log")
            ax.set_xlabel("Exposición media")
            ax.set_ylabel("Trabajadores (escala log)")
            ax.set_title(f"Exposición vs tamaño del empleo ({ANALYSIS_YEAR})")
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label("Proporción de mujeres")
            plt.tight_layout()
            plt.show()

        bubble_df[
            [
                "code",
                "occupation_group",
                "weighted_population",
                "mean_exposure_score",
                "share_women",
                "pct_alta_exposicion",
            ]
        ].sort_values("weighted_population", ascending=False).head(15)
        """
    )
    profiles_source = src(
        """
        SHEET_LABELS = {
            "sexo": "Sexo",
            "educacion": "Educación",
            "categoria": "Categoría ocupacional",
            "categoria_agregada": "Categoría agregada",
            "grupo_edad": "Grupo de edad",
            "formalidad_contrato": "Contrato",
            "formalidad_tamano": "Tamaño de empresa",
            "rama": "Rama de actividad",
            "estrato": "Estrato",
        }

        primary_sheets = ["sexo", "educacion", "categoria_agregada", "rama", "grupo_edad", "formalidad_tamano"]
        fig, axes = plt.subplots(3, 2, figsize=(14, 14))
        axes = axes.flatten()

        for ax, sheet_name in zip(axes, primary_sheets):
            df = profiles[sheet_name].sort_values("mean_exposure_score", ascending=True).copy()
            ax.barh(df["group"], df["mean_exposure_score"], color=COLORS["accent"])
            ax.set_title(SHEET_LABELS[sheet_name], fontsize=11, loc="left")
            ax.set_xlabel("Exposición media")
            ax.xaxis.set_major_formatter(PercentFormatter(1.0))
            ax.tick_params(axis="y", labelsize=8)

        for ax in axes[len(primary_sheets):]:
            ax.axis("off")

        fig.suptitle(f"Perfiles demográficos y laborales con mayor exposición ({ANALYSIS_YEAR})", fontsize=15, y=1.01)
        plt.tight_layout()
        plt.show()

        for sheet_name in PROFILE_SHEETS:
            display(
                profiles[sheet_name]
                .sort_values("mean_exposure_score", ascending=False)
                .rename(columns={"group": SHEET_LABELS.get(sheet_name, sheet_name.lower())})
            )
        """
    )
    comparative_source = src(
        """
        comparison_df["dimension_label"] = comparison_df["dimension"].map(SHEET_LABELS).fillna(comparison_df["dimension"])
        comparison_view = comparison_df[
            [
                "dimension_label",
                "top_group",
                "top_exposure",
                "bottom_group",
                "bottom_exposure",
                "gap_exposure",
            ]
        ].rename(
            columns={
                "dimension_label": "dimension",
                "top_group": "mayor_exposicion",
                "top_exposure": "score_mayor",
                "bottom_group": "menor_exposicion",
                "bottom_exposure": "score_menor",
                "gap_exposure": "brecha",
            }
        )
        display(comparison_view)

        if HAS_PLOTLY:
            fig = px.bar(
                comparison_df.sort_values("gap_exposure"),
                x="gap_exposure",
                y="dimension_label",
                orientation="h",
                color="gap_exposure",
                color_continuous_scale=["#93c5fd", "#c25b2a"],
                custom_data=["top_group", "bottom_group", "top_exposure", "bottom_exposure"],
                labels={"gap_exposure": "Brecha de exposición", "dimension_label": "Dimensión"},
            )
            fig.update_traces(
                hovertemplate="<b>%{y}</b><br>Mayor exposición: %{customdata[0]} (%{customdata[2]:.1%})<br>"
                "Menor exposición: %{customdata[1]} (%{customdata[3]:.1%})<br>"
                "Brecha: %{x:.1%}<extra></extra>"
            )
            fig.update_layout(title=f"Mayor brecha interna de exposición por dimensión ({ANALYSIS_YEAR})", height=520)
            show_plotly(fig)
        else:
            ordered = comparison_df.sort_values("gap_exposure")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.barh(ordered["dimension_label"], ordered["gap_exposure"], color=COLORS["accent2"])
            ax.set_xlabel("Brecha de exposición")
            ax.xaxis.set_major_formatter(PercentFormatter(1.0))
            ax.set_ylabel("")
            ax.set_title(f"Mayor brecha interna de exposición por dimensión ({ANALYSIS_YEAR})")
            plt.tight_layout()
            plt.show()

        top_gap = comparison_df.iloc[0]
        render_note(
            f"La mayor brecha interna del año aparece en <strong>{top_gap['dimension_label']}</strong>: "
            f"{top_gap['top_group']} alcanza {fmt_pct(top_gap['top_exposure'])} frente a {fmt_pct(top_gap['bottom_exposure'])} en {top_gap['bottom_group']}.",
            tone="blue",
        )
        """
    )
    income_source = src(
        """
        render_cards(
            [
                {
                    "label": "Correlación ingreso-exposición",
                    "value": f"{income_corr:.2f}" if pd.notna(income_corr) else "N/D",
                    "sub": "Correlación entre ingreso mensual medio y score ocupacional",
                },
                {
                    "label": "Ocupaciones en scatter",
                    "value": fmt_num(len(income_df)),
                    "sub": "Solo ocupaciones ENAHO con más de 50 mil ocupados e ingreso reportado",
                },
                {
                    "label": "Ingreso medio máximo",
                    "value": fmt_sol(income_df['income_monthly_weighted_mean'].max()),
                    "sub": "Máximo ingreso promedio ocupacional del corte anual",
                },
            ]
        )

        if HAS_PLOTLY:
            fig = px.scatter(
                income_df,
                x="mean_exposure_score",
                y="income_monthly_weighted_mean",
                size="weighted_population",
                color="women_share_weighted",
                color_continuous_scale=["#2563eb", "#f59e0b", "#c25b2a"],
                hover_name="occupation_name_cno",
                hover_data={
                    "occupation_code_4d": True,
                    "income_monthly_weighted_mean": ":,.0f",
                    "income_monthly_median_weighted": ":,.0f",
                    "weighted_population": ":,.0f",
                    "women_share_weighted": ":.1%",
                },
                labels={
                    "mean_exposure_score": "Exposición media",
                    "income_monthly_weighted_mean": "Ingreso mensual medio",
                    "women_share_weighted": "Proporción de mujeres",
                },
                size_max=44,
            )
            fig.update_layout(
                title=f"Ingreso laboral mensual y exposición a IA ({ANALYSIS_YEAR})",
                height=620,
                margin=dict(l=10, r=10, t=60, b=20),
            )
            show_plotly(fig)
        else:
            fig, ax = plt.subplots(figsize=(10, 7))
            sizes = np.sqrt(income_df["weighted_population"] / income_df["weighted_population"].max()) * 1400
            scatter = ax.scatter(
                income_df["mean_exposure_score"],
                income_df["income_monthly_weighted_mean"],
                s=sizes,
                c=income_df["women_share_weighted"],
                cmap="plasma",
                alpha=0.75,
                edgecolors="white",
                linewidth=0.6,
            )
            ax.set_xlabel("Exposición media")
            ax.set_ylabel("Ingreso mensual medio")
            ax.yaxis.set_major_formatter(StrMethodFormatter("S/ {x:,.0f}"))
            ax.set_title(f"Ingreso laboral mensual y exposición a IA ({ANALYSIS_YEAR})")
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label("Proporción de mujeres")
            plt.tight_layout()
            plt.show()

        display(
            income_df[
                [
                    "occupation_code_4d",
                    "occupation_name_cno",
                    "weighted_population",
                    "income_monthly_weighted_mean",
                    "income_monthly_median_weighted",
                    "mean_exposure_score",
                ]
            ]
            .sort_values(["mean_exposure_score", "income_monthly_weighted_mean"], ascending=[False, False])
            .head(20)
        )

        render_note(
            f"Chequeo de ingresos extremos en microdatos armonizados del año: {outliers_over_20k} casos por encima de S/ 20 mil y {outliers_over_50k} por encima de S/ 50 mil.",
            tone="green",
        )
        """
    )
    personas_source = src(
        """
        def weighted_mode(series, weights):
            valid = pd.DataFrame({"value": series, "weight": weights}).dropna()
            if valid.empty:
                return "N/D"
            return valid.groupby("value")["weight"].sum().sort_values(ascending=False).index[0]

        def build_persona(df, label, tier):
            if df.empty:
                return None
            weights = df["weight"]
            total = weights.sum()
            occ_top = (
                df.groupby(["occupation_code_4d", "occupation_group"], dropna=False)["weight"]
                .sum()
                .sort_values(ascending=False)
                .head(3)
            )
            top_occupations = [
                {
                    "code": code,
                    "name": str(name)[:62] if pd.notna(name) else "N/D",
                    "workers": float(workers),
                }
                for (code, name), workers in occ_top.items()
            ]
            income_valid = df[df["labor_income_monthly"].notna()].copy()
            return {
                "label": label,
                "tier": tier,
                "total_workers": float(total),
                "mean_exposure": weighted_mean(df["mean_exposure_score"], weights),
                "pct_aumento": weighted_mean(df["%_aumento"], weights),
                "pct_sustitucion": weighted_mean(df["%_sustitucion"], weights),
                "pct_women": weighted_share(df["sex"].astype(str).eq("Mujer"), weights),
                "pct_urban": weighted_mean(df["is_urban"], weights),
                "mean_age": weighted_mean(df["age"], weights),
                "income_mean": weighted_mean(income_valid["labor_income_monthly"], income_valid["weight"]),
                "top_category": weighted_mode(df["category_label"], weights),
                "top_education": weighted_mode(df["education_label"], weights),
                "top_occupations": top_occupations,
            }

        persona_records = [
            build_persona(persona_q4, f"Perú {ANALYSIS_YEAR} — alta exposición (Q4)", "alta"),
            build_persona(persona_q1, f"Perú {ANALYSIS_YEAR} — baja exposición (Q1)", "baja"),
        ]

        for region_code, region_name in PERSONA_REGIONS:
            sub = enaho_micro[pd.to_numeric(enaho_micro["region_code"], errors="coerce") == region_code].copy()
            if len(sub) < 40:
                continue
            q75_region = sub["mean_exposure_score"].quantile(0.75)
            persona_records.append(
                build_persona(sub[sub["mean_exposure_score"] >= q75_region], f"{region_name} {ANALYSIS_YEAR} — alta exposición (Q4)", "alta")
            )

        persona_records = [p for p in persona_records if p is not None]
        persona_export = pd.DataFrame(
            [
                {
                    k: json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v
                    for k, v in persona.items()
                }
                for persona in persona_records
            ]
        )

        cards = []
        for persona in persona_records:
            occ_html = "".join(
                [
                    f"<li><span class='mini-tag'>{o['code']}</span>{o['name']} ({fmt_num(o['workers'])})</li>"
                    for o in persona["top_occupations"]
                ]
            )
            cards.append(
                f'''
                <div class="audit-card">
                  <div class="eyebrow">{persona['label']}</div>
                  <div class="value">{fmt_pct(persona['mean_exposure'])}</div>
                  <div class="sub">{persona['top_category']} · {persona['top_education']}</div>
                  <div style="margin-top:10px;font-size:12px;color:{COLORS['muted']};">
                    Mujeres: {fmt_pct(persona['pct_women'])} · Urbano: {fmt_pct(persona['pct_urban'])} · Edad media: {persona['mean_age']:.1f}
                  </div>
                  <div style="margin-top:6px;font-size:12px;color:{COLORS['muted']};">
                    Ingreso mensual: {fmt_sol(persona['income_mean'])} · Augmentation: {fmt_pct(persona['pct_aumento'])}
                  </div>
                  <ul style="margin:10px 0 0 18px;padding:0;font-size:12px;color:{COLORS['text']};">{occ_html}</ul>
                </div>
                '''
            )
        display(HTML("<div class='audit-grid'>" + "".join(cards) + "</div>"))

        persona_compare = pd.DataFrame(
            [
                {"metric": "Mujeres", "Q4": persona_records[0]["pct_women"], "Q1": persona_records[1]["pct_women"]},
                {"metric": "Urbano", "Q4": persona_records[0]["pct_urban"], "Q1": persona_records[1]["pct_urban"]},
                {"metric": "Augmentation", "Q4": persona_records[0]["pct_aumento"], "Q1": persona_records[1]["pct_aumento"]},
                {"metric": "Sustitución", "Q4": persona_records[0]["pct_sustitucion"], "Q1": persona_records[1]["pct_sustitucion"]},
            ]
        )

        if HAS_PLOTLY:
            fig = go.Figure()
            fig.add_bar(name="Q4 alta exposición", x=persona_compare["metric"], y=persona_compare["Q4"], marker_color=COLORS["accent"])
            fig.add_bar(name="Q1 baja exposición", x=persona_compare["metric"], y=persona_compare["Q1"], marker_color=COLORS["accent2"])
            fig.update_layout(
                title=f"Comparación de perfiles del trabajador expuesto ({ANALYSIS_YEAR})",
                barmode="group",
                yaxis_tickformat=".0%",
                height=460,
            )
            show_plotly(fig)
        else:
            fig, ax = plt.subplots(figsize=(9, 5))
            x = np.arange(len(persona_compare))
            width = 0.35
            ax.bar(x - width / 2, persona_compare["Q4"], width, label="Q4 alta exposición", color=COLORS["accent"])
            ax.bar(x + width / 2, persona_compare["Q1"], width, label="Q1 baja exposición", color=COLORS["accent2"])
            ax.set_xticks(x)
            ax.set_xticklabels(persona_compare["metric"])
            ax.yaxis.set_major_formatter(PercentFormatter(1.0))
            ax.set_title(f"Comparación de perfiles del trabajador expuesto ({ANALYSIS_YEAR})")
            ax.legend()
            plt.tight_layout()
            plt.show()

        persona_export
        """
    )
    regional_source = src(
        """
        if regional_df.empty:
            render_note(
                f"No hay corte EPEN anual disponible para {ANALYSIS_YEAR}. El bloque departamental solo puede replicarse desde 2022 en adelante.",
                tone="blue",
            )
        else:
            render_cards(
                [
                    {
                        "label": "Departamentos con dato",
                        "value": fmt_num(len(regional_df)),
                        "sub": "EPEN anual con match ocupacional e ingreso mensual",
                    },
                    {
                        "label": "Mayor exposición departamental",
                        "value": fmt_pct(regional_df['mean_exposure'].max()),
                        "sub": str(regional_df.iloc[0]["region_name"]),
                    },
                    {
                        "label": "Ingreso departamental más alto",
                        "value": fmt_sol(regional_df['income_mean'].max()),
                        "sub": str(regional_df.sort_values('income_mean', ascending=False).iloc[0]["region_name"]),
                    },
                ]
            )

            if HAS_PLOTLY:
                fig = px.bar(
                    regional_df.sort_values("mean_exposure"),
                    x="mean_exposure",
                    y="region_name",
                    orientation="h",
                    color="income_mean",
                    color_continuous_scale=["#bfdbfe", "#2563eb"],
                    hover_data={"workers": ":,.0f", "pct_alta": ":.1%", "pct_aumento": ":.1%"},
                    labels={"mean_exposure": "Exposición media", "region_name": "Departamento", "income_mean": "Ingreso medio"},
                )
                fig.update_layout(title=f"Exposición a IA por departamento ({ANALYSIS_YEAR})", height=700)
                show_plotly(fig)
            else:
                ordered = regional_df.sort_values("mean_exposure")
                fig, ax = plt.subplots(figsize=(10, 8))
                ax.barh(ordered["region_name"], ordered["mean_exposure"], color=COLORS["accent2"])
                ax.xaxis.set_major_formatter(PercentFormatter(1.0))
                ax.set_title(f"Exposición a IA por departamento ({ANALYSIS_YEAR})")
                ax.set_xlabel("Exposición media")
                plt.tight_layout()
                plt.show()

            regional_occ_view = (
                regional_top_occ.sort_values(["region_code", "mean_exposure"], ascending=[True, False])
                .groupby("region_code")
                .head(3)
                .merge(regional_df[["region_code", "region_name"]], how="left", on="region_code")
            )
            display(
                regional_occ_view[
                    ["region_name", "occupation_code_4d", "occupation_group", "workers", "mean_exposure"]
                ].rename(
                    columns={
                        "region_name": "departamento",
                        "occupation_code_4d": "cno_4d",
                        "occupation_group": "ocupacion",
                        "workers": "trabajadores",
                        "mean_exposure": "exposicion_media",
                    }
                )
            )
        """
    )
    audit_source = src(
        """
        calc_coverage = matched_base["factor"].sum() / base["factor"].sum()
        calc_mean_exposure = weighted_mean(matched_base["mean_exposure_score"], matched_base["factor"])
        calc_pct_alta = weighted_mean(matched_base["%_alta_exposicion"], matched_base["factor"])
        calc_pct_aumento = weighted_mean(matched_base["%_aumento"], matched_base["factor"])
        calc_pct_sustitucion = weighted_mean(matched_base["%_sustitucion"], matched_base["factor"])

        audit_frame = pd.DataFrame(
            [
                {
                    "analysis_year": ANALYSIS_YEAR,
                    "coverage_report": coverage["cobertura_ponderada"],
                    "coverage_rebuilt": calc_coverage,
                    "coverage_diff": abs(calc_coverage - coverage["cobertura_ponderada"]),
                    "mean_exposure_report": coverage["media_exposicion_ponderada"],
                    "mean_exposure_rebuilt": calc_mean_exposure,
                    "mean_exposure_diff": abs(calc_mean_exposure - coverage["media_exposicion_ponderada"]),
                    "pct_alta_report": coverage["media_pct_alta_ponderada"],
                    "pct_alta_rebuilt": calc_pct_alta,
                    "pct_aumento_report": coverage["media_pct_aumento_ponderada"],
                    "pct_aumento_rebuilt": calc_pct_aumento,
                    "pct_sustitucion_report": coverage["media_pct_sustitucion_ponderada"],
                    "pct_sustitucion_rebuilt": calc_pct_sustitucion,
                    "unmatched_occupations": len(unmatched_occ),
                    "outliers_over_20k": outliers_over_20k,
                    "outliers_over_50k": outliers_over_50k,
                }
            ]
        )

        render_cards(
            [
                {
                    "label": "Diferencia cobertura",
                    "value": f"{audit_frame.iloc[0]['coverage_diff']:.6f}",
                    "sub": "Reporte anual vs reconstrucción desde microdatos",
                },
                {
                    "label": "Diferencia exposición media",
                    "value": f"{audit_frame.iloc[0]['mean_exposure_diff']:.6f}",
                    "sub": "Debe tender a cero si no hay contradicción interna",
                },
                {
                    "label": "Ocupaciones fuera del índice",
                    "value": fmt_num(len(unmatched_occ)),
                    "sub": f"{fmt_num(unmatched_occ['weighted_population'].sum())} ocupados ponderados sin score",
                },
                {
                    "label": "Atípicos de ingreso >50k",
                    "value": fmt_num(outliers_over_50k),
                    "sub": f"{fmt_num(outliers_over_20k)} casos por encima de 20k",
                },
            ]
        )

        if audit_frame.iloc[0]["coverage_diff"] < 1e-9 and audit_frame.iloc[0]["mean_exposure_diff"] < 1e-9:
            render_note("La reconstrucción desde microdatos replica exactamente los indicadores de cobertura y exposición media del reporte anual. No se detectaron contradicciones internas en estas métricas.", tone="green")
        else:
            render_note("La auditoría encontró diferencias no triviales entre el reporte anual y la reconstrucción desde microdatos. Este caso requiere revisar el pipeline antes de usar resultados externos.", tone="amber")

        display(
            unmatched_occ.head(15).rename(
                columns={
                    "occupation_code_4d": "cno_4d",
                    "weighted_population": "trabajadores",
                    "occupation_name_cno": "ocupacion",
                    "reason": "motivo",
                }
            )
        )

        audit_frame
        """
    )
    export_source = src(
        """
        export_map = {
            f"coverage_{ANALYSIS_YEAR}.csv": pd.DataFrame([coverage]),
            f"occupation_summary_{ANALYSIS_YEAR}.csv": occupation_summary,
            f"top_occupations_{ANALYSIS_YEAR}.csv": top_occ,
            f"bubble_occupations_{ANALYSIS_YEAR}.csv": bubble_df,
            f"comparison_{ANALYSIS_YEAR}.csv": comparison_df,
            f"income_scatter_{ANALYSIS_YEAR}.csv": income_df,
            f"personas_{ANALYSIS_YEAR}.csv": persona_export,
            f"regional_{ANALYSIS_YEAR}.csv": regional_df,
            f"regional_top_occ_{ANALYSIS_YEAR}.csv": regional_top_occ,
            f"unmatched_occupations_{ANALYSIS_YEAR}.csv": unmatched_occ,
            f"audit_{ANALYSIS_YEAR}.csv": audit_frame,
        }

        for sheet_name, df in profiles.items():
            export_map[f"profile_{sheet_name}_{ANALYSIS_YEAR}.csv"] = df

        for filename, df in export_map.items():
            df.to_csv(OUTPUT_TABLES / filename, index=False)

        with (OUTPUT_TABLES / f"audit_summary_{ANALYSIS_YEAR}.json").open("w", encoding="utf-8") as fh:
            json.dump(audit_summary, fh, ensure_ascii=False, indent=2)

        exported_files = sorted(p.name for p in OUTPUT_TABLES.iterdir())
        print(f"Tablas exportadas en: {OUTPUT_TABLES}")
        pd.DataFrame({"archivo": exported_files})
        """
    )

    nb = nbf.v4.new_notebook()
    nb.cells = [
        md(
            f"# IA y empleo en Perú: ENAHO {analysis_year}\n\n"
            "Versión anual final del cruce entre ENAHO y el índice ocupacional de exposición a IA. "
            "Este cuaderno replica la lógica del HTML maestro, pero concentrada en un solo año y con salidas desagregadas para auditoría y revisión."
        ),
        md(
            "## Alcance\n\n"
            f"- Año analizado: **{analysis_year}**\n"
            "- Base laboral: **ENAHO anual, ocupados**\n"
            "- Índice: **Claude Sonnet 4-6 / abril 2026**\n"
            "- Clasificación ocupacional: **CNO-2015 a 4 dígitos**\n"
            "- Este cuaderno está pensado como versión final reproducible del corte anual, alineada con el HTML maestro."
        ),
        code(setup_source),
        code(load_source),
        md("## Panorama anual"),
        code(kpi_source),
        md("## 1. Ocupaciones más expuestas"),
        code(top_occ_source),
        md(
            "## 2. Mapa ocupacional\n\n"
            "Se replica el producto principal del HTML para el año seleccionado: exposición media por ocupación, tamaño del empleo y composición por sexo."
        ),
        code(bubble_source),
        md("## 3. Perfiles demográficos y laborales"),
        code(profiles_source),
        md("## 4. Extremos de exposición dentro de cada dimensión"),
        code(comparative_source),
        md("## 5. Ingresos y exposición"),
        code(income_source),
        md("## 6. Perfiles del trabajador expuesto"),
        code(personas_source),
        md("## 7. Análisis departamental"),
        code(regional_source),
        md("## 8. Auditoría anual de coherencia"),
        code(audit_source),
        md("## 9. Exportación de tablas auxiliares"),
        code(export_source),
    ]
    nb.metadata.kernelspec = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    nb.metadata.language_info = {
        "name": "python",
        "version": "3.11",
    }
    return nb


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Construye un notebook anual final ENAHO Exposure por año.")
    parser.add_argument("--project-root", type=Path, default=project_root)
    parser.add_argument("--base-csv", type=Path, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--index-path", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    nb = build_enaho_exposure_notebook(
        project_root=args.project_root.resolve(),
        base_csv=args.base_csv.resolve(),
        analysis_year=args.year,
        index_path=args.index_path.resolve() if args.index_path else None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print(f"Notebook ENAHO Exposure generado en: {args.output}")


if __name__ == "__main__":
    main()
