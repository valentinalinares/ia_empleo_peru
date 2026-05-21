"""
Genera un reporte HTML interactivo: Exposición a IA en el Mercado Laboral Peruano
Fuentes: ENAHO 2019-2025 + EPEN departamental 2022-2025 + Índice Claude Sonnet
"""

import pandas as pd
import json
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

INTERNAL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = INTERNAL_ROOT.parent
OUTPUTS = INTERNAL_ROOT / "outputs"
DATA = INTERNAL_ROOT / "bases" / "procesadas"
YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
CURRENT_YEAR = 2025
INCOME_YEAR = 2024
REGIONAL_YEARS = [2022, 2023, 2024, 2025]

DEPT_NAMES = {
    1:"Amazonas", 2:"Ancash", 3:"Apurímac", 4:"Arequipa", 5:"Ayacucho",
    6:"Cajamarca", 7:"Callao", 8:"Cusco", 9:"Huancavelica", 10:"Huánuco",
    11:"Ica", 12:"Junín", 13:"La Libertad", 14:"Lambayeque", 15:"Lima",
    16:"Loreto", 17:"Madre de Dios", 18:"Moquegua", 19:"Pasco", 20:"Piura",
    21:"Puno", 22:"San Martín", 23:"Tacna", 24:"Tumbes", 25:"Ucayali",
}

# ─── LOAD EXPOSURE INDEX ──────────────────────────────────────────────────────
print("Cargando indice de exposicion...")
idx = pd.read_excel(INTERNAL_ROOT / "referencias" / "indices" / "anthropic-claude-sonnet-4-6_exposure_index.xlsx")
idx["code"] = idx["code"].astype(str).str.zfill(4)
idx_cols = ["code","mean_exposure_score","%_alta_exposicion","%_sustitucion","%_aumento"]

# ─── LOAD ANNUAL ENAHO EXPOSURE REPORTS ──────────────────────────────────────
print("Cargando reportes anuales ENAHO...")

def load_year(year):
    path = OUTPUTS / f"enaho_exposure_{year}" / f"enaho_exposure_{year}_occupation_report.xlsx"
    xl = pd.ExcelFile(path)
    return {s: xl.parse(s) for s in xl.sheet_names}

data = {y: load_year(y) for y in YEARS}

# ─── SERIE EVOLUTIVA ──────────────────────────────────────────────────────────
evolution = []
for y in YEARS:
    cov = data[y]["coverage"].iloc[0]
    evolution.append({
        "year": y,
        "mean_exposure":   round(float(cov["media_exposicion_ponderada"]), 4),
        "pct_alta":        round(float(cov["media_pct_alta_ponderada"]), 4),
        "pct_sustitucion": round(float(cov["media_pct_sustitucion_ponderada"]), 4),
        "pct_aumento":     round(float(cov["media_pct_aumento_ponderada"]), 4),
        "cobertura":       round(float(cov["cobertura_ponderada"]), 4),
        "trabajadores_cubiertos": int(cov["peso_con_indice"]),
        "ocupaciones_emparejadas": int(cov["ocupaciones_emparejadas"]),
    })

# ─── TOP OCUPACIONES POR AÑO ──────────────────────────────────────────────────
def top_occs(year, n=20):
    df = data[year]["occupation_summary"].copy()
    df = df[df["weighted_population"] > 50000].nlargest(n, "mean_exposure_score")
    return [{
        "code":       str(r["code"]),
        "occupation": (r["occupation_group"][:70] if isinstance(r["occupation_group"], str) else "N/D"),
        "mean_exposure": round(float(r["mean_exposure_score"]), 4),
        "pct_alta":      round(float(r["pct_alta_exposicion"]), 4),
        "pct_sustitucion": round(float(r["pct_sustitucion"]), 4),
        "pct_aumento":   round(float(r["pct_aumento"]), 4),
        "workers":       int(r["weighted_population"]),
        "share_women":   round(float(r["share_women"]), 3),
        "mean_age":      round(float(r["mean_age"]), 1),
    } for _, r in df.iterrows()]

top_occ_by_year = {str(y): top_occs(y) for y in YEARS}

# ─── BUBBLE DATA AÑO ACTUAL ───────────────────────────────────────────────────
def bubble_data(year, min_pop=80000):
    df = data[year]["occupation_summary"].copy()
    df = df[df["weighted_population"] >= min_pop]
    return [{
        "code":       str(r["code"]),
        "occupation": (r["occupation_group"][:60] if isinstance(r["occupation_group"], str) else "N/D"),
        "mean_exposure": round(float(r["mean_exposure_score"]), 4),
        "workers":    int(r["weighted_population"]),
        "share_women": round(float(r["share_women"]), 3),
        "mean_age":   round(float(r["mean_age"]), 1),
        "pct_alta":   round(float(r["pct_alta_exposicion"]), 4),
    } for _, r in df.iterrows()]

bubble_current = bubble_data(CURRENT_YEAR)

# ─── PERFILES DEMOGRÁFICOS ────────────────────────────────────────────────────
def demo_profile(year, sheet):
    df = data[year].get(sheet)
    if df is None:
        return []
    return sorted([{
        "group":        str(r["group"]),
        "mean_exposure": round(float(r["mean_exposure_score"]), 4),
        "pct_alta":     round(float(r["pct_alta_exposicion"]), 4),
        "workers":      int(r["weighted_population"]),
        "pop_share":    round(float(r["population_share"]), 4),
    } for _, r in df.iterrows()], key=lambda x: x["mean_exposure"], reverse=True)

profiles_current = {s: demo_profile(CURRENT_YEAR, s)
                 for s in ["educacion","sexo","categoria_agregada","rama","grupo_edad","formalidad_contrato","formalidad_tamano"]}

profiles_evol = {}
for sheet in ["educacion", "rama", "categoria_agregada"]:
    profiles_evol[sheet] = {str(y): demo_profile(y, sheet) for y in YEARS}

# ─── INGRESOS POR OCUPACIÓN (ENAHO + EPEN) ───────────────────────────────────
print("Cargando datos de ingresos...")
resumen = pd.read_csv(DATA / "resumen_ocupacion_anio.csv.gz")
resumen["occupation_code_4d"] = resumen["occupation_code_4d"].astype(str).str.zfill(4)

# Merge con índice de exposición
resumen_merged = resumen.merge(
    idx[["code","mean_exposure_score","%_alta_exposicion","%_sustitucion","%_aumento"]],
    left_on="occupation_code_4d", right_on="code", how="inner"
)

# Scatter ingreso vs exposición (último año con insumo de ingresos procesado)
income_scatter_rows = []
for _, r in resumen_merged[
    (resumen_merged["source"] == "ENAHO") &
    (resumen_merged["year"] == INCOME_YEAR) &
    (resumen_merged["weighted_population"] > 50000) &
    (resumen_merged["income_monthly_weighted_mean"].notna())
].iterrows():
    income_scatter_rows.append({
        "occupation": (r["occupation_name_cno"][:65] if isinstance(r["occupation_name_cno"], str) else "N/D"),
        "code":       str(r["occupation_code_4d"]),
        "mean_exposure": round(float(r["mean_exposure_score"]), 4),
        "income_mean":   round(float(r["income_monthly_weighted_mean"]), 0),
        "income_median": round(float(r["income_monthly_median_weighted"]), 0) if pd.notna(r["income_monthly_median_weighted"]) else None,
        "workers":       int(r["weighted_population"]),
        "women_share":   round(float(r["women_share_weighted"]), 3) if pd.notna(r.get("women_share_weighted")) else 0.5,
    })

# Evolución ingreso medio (nacional) por año — ENAHO
income_evolution = []
for y in YEARS:
    sub = resumen_merged[(resumen_merged["source"] == "ENAHO") & (resumen_merged["year"] == y)]
    if len(sub) == 0:
        continue
    # Ingreso medio ponderado por población
    total_pop = sub["weighted_population"].sum()
    if total_pop > 0 and sub["income_monthly_weighted_mean"].notna().any():
        sub2 = sub[sub["income_monthly_weighted_mean"].notna()]
        income_mean = (sub2["income_monthly_weighted_mean"] * sub2["weighted_population"]).sum() / sub2["weighted_population"].sum()
    else:
        income_mean = None
    # Correlación ingreso-exposición
    merged_valid = sub[sub["income_monthly_weighted_mean"].notna()]
    corr = merged_valid["mean_exposure_score"].corr(merged_valid["income_monthly_weighted_mean"]) if len(merged_valid) > 5 else None
    income_evolution.append({
        "year": y,
        "income_mean_national": round(income_mean, 0) if income_mean else None,
        "corr_income_exposure": round(corr, 3) if corr is not None else None,
    })

# ─── ANÁLISIS POR DEPARTAMENTO (EPEN 2022-2025) ───────────────────────────────
print("Calculando exposicion por departamento...")
epen = pd.read_csv(DATA / "epen_persona_departamentos_anual_2022_2025.csv.gz")
epen["occupation_code_4d"] = epen["occupation_code_4d"].astype(str).str.zfill(4)

epen_merged = epen.merge(
    idx[["code","mean_exposure_score","%_alta_exposicion","%_sustitucion","%_aumento"]],
    left_on="occupation_code_4d", right_on="code", how="inner"
)
epen_merged = epen_merged[epen_merged["year"].isin(REGIONAL_YEARS)]

def weighted_mean(g, val_col, wt_col="weight"):
    valid = g[[val_col, wt_col]].dropna()
    if len(valid) == 0 or valid[wt_col].sum() == 0:
        return None
    return (valid[val_col] * valid[wt_col]).sum() / valid[wt_col].sum()

regional_rows = []
for (region, year), g in epen_merged.groupby(["region_code", "year"]):
    wt_sum = g["weight"].sum()
    income_valid = g[g["labor_income_monthly"].notna()]
    income_wt_sum = income_valid["weight"].sum()
    regional_rows.append({
        "region_code":    int(region),
        "region_name":    DEPT_NAMES.get(int(region), f"Región {region}"),
        "year":           int(year),
        "mean_exposure":  round((g["mean_exposure_score"] * g["weight"]).sum() / wt_sum, 4),
        "pct_alta":       round((g["%_alta_exposicion"]   * g["weight"]).sum() / wt_sum, 4),
        "pct_sustitucion":round((g["%_sustitucion"]       * g["weight"]).sum() / wt_sum, 4),
        "pct_aumento":    round((g["%_aumento"]           * g["weight"]).sum() / wt_sum, 4),
        "trabajadores":   round(wt_sum, 0),
        "income_mean":    round((income_valid["labor_income_monthly"] * income_valid["weight"]).sum() / income_wt_sum, 0) if income_wt_sum > 0 else None,
    })

regional_data = regional_rows

# Top occupations por departamento (año actual, top 5 por región)
top_occ_by_region = {}
for region, g_region in epen_merged[epen_merged["year"] == CURRENT_YEAR].groupby("region_code"):
    occ_agg = g_region.groupby("occupation_code_4d").apply(
        lambda g: pd.Series({
            "mean_exposure": (g["mean_exposure_score"] * g["weight"]).sum() / g["weight"].sum(),
            "workers": g["weight"].sum(),
        }), include_groups=False
    ).reset_index()
    occ_agg = occ_agg[occ_agg["workers"] > 10000].nlargest(5, "mean_exposure")
    # Add names
    occ_agg = occ_agg.merge(idx[["code","occupation_group"]], left_on="occupation_code_4d", right_on="code", how="left")
    top_occ_by_region[str(int(region))] = [{
        "code":       str(r["occupation_code_4d"]),
        "occupation": (r["occupation_group"][:55] if isinstance(r["occupation_group"], str) else "N/D"),
        "mean_exposure": round(float(r["mean_exposure"]), 4),
        "workers":    int(r["workers"]),
    } for _, r in occ_agg.iterrows()]

print("  Regiones procesadas:", len(regional_rows) // len(REGIONAL_YEARS))

# ─── PERFILES DE TRABAJADOR (PERSONAS) ───────────────────────────────────────
print("Construyendo perfiles de trabajador...")

# Mapping verificado contra el diccionario ENAHO 2024 (P507)
CAT_MAP = {1:"Empleador/a", 2:"Independiente", 3:"Empleado/a",
           4:"Obrero/a", 5:"Familiar no remunerado/a", 6:"Trab. del hogar", 7:"Otro"}

personas_path = OUTPUTS / f"enaho_exposure_{CURRENT_YEAR}" / "annual_tables" / f"personas_{CURRENT_YEAR}.csv"
personas_df = pd.read_csv(personas_path)

def parse_persona_row(r):
    top_occs = json.loads(r["top_occupations"]) if isinstance(r.get("top_occupations"), str) else []
    pct_women = float(r["pct_women"]) if pd.notna(r.get("pct_women")) else 0
    return {
        "label": str(r["label"]),
        "tier": str(r["tier"]),
        "total_workers": int(float(r["total_workers"])),
        "sex": "Mujer" if pct_women >= 0.5 else "Hombre",
        "pct_women": round(pct_women, 3),
        "mean_age": round(float(r["mean_age"]), 1) if pd.notna(r.get("mean_age")) else None,
        "education": str(r.get("top_education", "N/D")),
        "top_category": str(r.get("top_category", "N/D")),
        "top_occupations": top_occs,
        "income_mean": round(float(r["income_mean"]), 0) if pd.notna(r.get("income_mean")) else None,
        "pct_urban": round(float(r["pct_urban"]), 3) if pd.notna(r.get("pct_urban")) else None,
        "mean_exposure": round(float(r["mean_exposure"]), 4),
        "pct_alta": round(float(r["pct_alta"]), 4) if "pct_alta" in r and pd.notna(r.get("pct_alta")) else 0,
        "pct_aumento": round(float(r["pct_aumento"]), 4),
        "pct_sustitucion": round(float(r["pct_sustitucion"]), 4),
    }

persona_list = [parse_persona_row(r) for _, r in personas_df.iterrows()]
print(f"  Perfiles generados: {len(persona_list)}")

# ─── SERIALIZE ────────────────────────────────────────────────────────────────
DATA_JS = f"""
const EVOLUTION = {json.dumps(evolution, ensure_ascii=False)};
const TOP_OCC_BY_YEAR = {json.dumps(top_occ_by_year, ensure_ascii=False)};
const BUBBLE_CURRENT = {json.dumps(bubble_current, ensure_ascii=False)};
const PROFILES_CURRENT = {json.dumps(profiles_current, ensure_ascii=False)};
const PROFILES_EVOL = {json.dumps(profiles_evol, ensure_ascii=False)};
const INCOME_SCATTER = {json.dumps(income_scatter_rows, ensure_ascii=False)};
const INCOME_EVOLUTION = {json.dumps(income_evolution, ensure_ascii=False)};
const REGIONAL_DATA = {json.dumps(regional_data, ensure_ascii=False)};
const TOP_OCC_BY_REGION = {json.dumps(top_occ_by_region, ensure_ascii=False)};
const DEPT_NAMES = {json.dumps(DEPT_NAMES, ensure_ascii=False)};
const PERSONAS = {json.dumps(persona_list, ensure_ascii=False)};
"""

# ─── HTML ─────────────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Exposicion a IA en el Empleo Peruano 2019-2025</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
  :root {
    --bg:#f8f8f6; --card:#ffffff; --accent:#c25b2a; --accent2:#2563eb;
    --accent3:#059669; --text:#1a1a1a; --muted:#6b7280; --border:#e5e7eb;
    --yellow:#d97706; --purple:#7c3aed; --font:'Segoe UI',system-ui,sans-serif;
  }
  *{box-sizing:border-box;margin:0;padding:0;}
  body{background:var(--bg);color:var(--text);font-family:var(--font);font-size:15px;line-height:1.6;}

  /* NAV */
  nav{background:#111;color:#fff;padding:0 32px;display:flex;align-items:center;gap:24px;height:52px;position:sticky;top:0;z-index:100;overflow-x:auto;}
  nav .brand{font-weight:700;font-size:14px;color:#fff;text-decoration:none;white-space:nowrap;}
  nav a{color:#aaa;text-decoration:none;font-size:12px;transition:color .2s;white-space:nowrap;}
  nav a:hover{color:#fff;}
  nav .spacer{flex:1;}
  nav .badge{background:var(--accent);color:#fff;font-size:11px;padding:2px 8px;border-radius:10px;font-weight:600;white-space:nowrap;}

  /* HERO */
  .hero{background:#111;color:#fff;padding:72px 32px 56px;}
  .hero-inner{max-width:860px;margin:0 auto;}
  .hero-eyebrow{font-size:12px;letter-spacing:1.5px;text-transform:uppercase;color:var(--accent);font-weight:600;margin-bottom:16px;}
  .hero h1{font-size:clamp(28px,4vw,46px);font-weight:700;line-height:1.15;letter-spacing:-1px;margin-bottom:20px;}
  .hero h1 span{color:var(--accent);}
  .hero p{font-size:17px;color:#ccc;max-width:620px;margin-bottom:32px;}
  .hero-meta{display:flex;gap:24px;flex-wrap:wrap;font-size:13px;color:#888;}
  .hero-meta strong{color:#ddd;}

  /* KPI STRIP */
  .kpi-strip{background:var(--card);border-bottom:1px solid var(--border);}
  .kpi-inner{max-width:1100px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));}
  .kpi{padding:22px 24px;border-right:1px solid var(--border);}
  .kpi:last-child{border-right:none;}
  .kpi-val{font-size:30px;font-weight:700;letter-spacing:-1px;color:var(--accent);}
  .kpi-label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;margin-top:4px;}
  .kpi-delta{font-size:12px;color:var(--accent3);margin-top:2px;}

  /* LAYOUT */
  .container{max-width:1100px;margin:0 auto;padding:0 24px;}
  .section{padding:52px 0;}
  .section+.section{border-top:1px solid var(--border);}
  .section-label{font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:var(--accent);font-weight:700;margin-bottom:8px;}
  .section-title{font-size:clamp(19px,2.5vw,27px);font-weight:700;letter-spacing:-0.5px;margin-bottom:10px;}
  .section-desc{color:var(--muted);font-size:14px;max-width:680px;margin-bottom:28px;line-height:1.7;}

  /* CARDS */
  .card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:24px;}
  .grid-2{display:grid;grid-template-columns:1fr 1fr;gap:20px;}
  .grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;}
  @media(max-width:720px){.grid-2,.grid-3{grid-template-columns:1fr;}}

  /* YEAR TABS */
  .year-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:24px;}
  .year-tab{padding:6px 14px;border-radius:6px;border:1px solid var(--border);background:var(--card);cursor:pointer;font-size:13px;font-weight:500;color:var(--muted);transition:all .15s;}
  .year-tab.active{background:var(--accent);color:#fff;border-color:var(--accent);}
  .year-tab:hover:not(.active){background:var(--border);color:var(--text);}

  /* BAR ROWS */
  .bar-row{display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid #f0f0f0;}
  .bar-row:last-child{border-bottom:none;}
  .bar-rank{width:20px;text-align:right;font-size:11px;color:var(--muted);font-weight:600;}
  .bar-label{flex:1;font-size:13px;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .bar-track{width:140px;height:6px;background:#eee;border-radius:3px;flex-shrink:0;}
  .bar-fill{height:100%;border-radius:3px;background:var(--accent);}
  .bar-val{width:42px;text-align:right;font-size:12px;font-weight:700;color:var(--accent);}
  .bar-workers{width:56px;text-align:right;font-size:11px;color:var(--muted);}

  /* PROFILE CARDS */
  .profile-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px;}
  .profile-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:18px 20px;}
  .profile-card h4{font-size:13px;font-weight:700;margin-bottom:12px;color:var(--text);}
  .prof-row{display:flex;justify-content:space-between;align-items:center;padding:5px 0;font-size:13px;border-bottom:1px solid #f5f5f5;}
  .prof-row:last-child{border-bottom:none;}
  .prof-score{font-weight:700;color:var(--accent);}
  .prof-share{font-size:11px;color:var(--muted);margin-left:8px;}

  /* REGION SELECTOR */
  .region-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px;margin-bottom:24px;}
  .region-btn{padding:7px 10px;border-radius:6px;border:1px solid var(--border);background:var(--card);cursor:pointer;font-size:12px;font-weight:500;color:var(--muted);transition:all .15s;text-align:center;}
  .region-btn.active{background:var(--accent2);color:#fff;border-color:var(--accent2);}
  .region-btn:hover:not(.active){background:#eff6ff;color:var(--accent2);}

  /* NOTE */
  .note{background:#fffbf5;border-left:3px solid var(--yellow);padding:12px 16px;font-size:13px;color:#78350f;border-radius:0 6px 6px 0;margin-top:16px;}
  .note-blue{background:#eff6ff;border-left:3px solid var(--accent2);padding:12px 16px;font-size:13px;color:#1e3a8a;border-radius:0 6px 6px 0;margin-top:16px;}
  .note-green{background:#f0fdf4;border-left:3px solid var(--accent3);padding:12px 16px;font-size:13px;color:#14532d;border-radius:0 6px 6px 0;margin-top:16px;}
  .metodo{background:#fafafa;border:1px dashed #d1d5db;padding:10px 14px;font-size:12px;color:#6b7280;border-radius:6px;margin-top:12px;}
  .metodo strong{color:#374151;}

  /* PERSONA CARDS */
  .persona-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px;}
  .persona-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:0;overflow:hidden;transition:box-shadow .2s;}
  .persona-card:hover{box-shadow:0 4px 20px rgba(0,0,0,.08);}
  .persona-header{padding:20px 22px 14px;border-bottom:1px solid var(--border);}
  .persona-header.alta{border-top:4px solid var(--accent);}
  .persona-header.baja{border-top:4px solid var(--accent2);}
  .persona-tier{font-size:10px;letter-spacing:1.2px;text-transform:uppercase;font-weight:700;margin-bottom:6px;}
  .persona-tier.alta{color:var(--accent);}
  .persona-tier.baja{color:var(--accent2);}
  .persona-location{font-size:18px;font-weight:700;letter-spacing:-0.3px;color:var(--text);}
  .persona-exp{font-size:28px;font-weight:700;letter-spacing:-1px;margin-top:2px;}
  .persona-exp.alta{color:var(--accent);}
  .persona-exp.baja{color:var(--accent2);}
  .persona-body{padding:16px 22px;}
  .persona-stat-row{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:14px;}
  .persona-stat{flex:1;min-width:80px;}
  .persona-stat-val{font-size:17px;font-weight:700;color:var(--text);}
  .persona-stat-label{font-size:11px;color:var(--muted);margin-top:2px;}
  .persona-occs{margin-top:6px;}
  .persona-occ-item{font-size:12px;color:var(--muted);padding:4px 0;border-bottom:1px solid #f5f5f5;display:flex;justify-content:space-between;align-items:center;}
  .persona-occ-item:last-child{border-bottom:none;}
  .persona-occ-name{flex:1;padding-right:8px;}
  .persona-occ-n{font-size:11px;white-space:nowrap;color:#9ca3af;}
  .persona-aug-bar{height:6px;background:#e5e7eb;border-radius:3px;margin-top:12px;overflow:hidden;}
  .persona-aug-fill{height:100%;border-radius:3px;background:var(--accent3);}

  /* SECTION DIVIDER */
  .section-divider{height:4px;background:linear-gradient(90deg,var(--accent),var(--accent2),var(--accent3));opacity:.3;margin:0;}

  footer{background:#111;color:#666;padding:40px 32px;font-size:13px;margin-top:80px;}
  footer strong{color:#999;}
</style>
</head>
<body>

<nav>
  <a class="brand" href="#">ENAHO x IA Peru</a>
  <a href="#evolucion">Evolucion</a>
  <a href="#ocupaciones">Ocupaciones</a>
  <a href="#mapa">Mapa</a>
  <a href="#perfiles">Perfiles</a>
  <a href="#ingresos">Ingresos</a>
  <a href="#departamentos">Departamentos</a>
  <a href="#personas" style="color:#f9a8d4;font-weight:600;">Quienes son?</a>
  <div class="spacer"></div>
  <span class="badge">2019-2025</span>
</nav>

<div class="hero">
  <div class="hero-inner">
    <div class="hero-eyebrow">Investigacion - Universidad del Pacifico - 2026</div>
    <h1>Exposicion a la Inteligencia Artificial<br>en el <span>Empleo Peruano</span></h1>
    <p>Siete anos de ENAHO cruzados con un indice de exposicion ocupacional construido con Claude Sonnet. Analisis de ocupaciones, perfiles demograficos, ingresos y distribucion regional.</p>
    <div class="hero-meta">
      <span><strong>Fuente:</strong> ENAHO 2019-2025 (INEI) + EPEN Departamental 2022-2025</span>
      <span><strong>Indice:</strong> Claude Sonnet 4-6 / Abril 2026</span>
      <span><strong>Clasificacion:</strong> CNO-2015 4 digitos</span>
    </div>
  </div>
</div>

<div class="kpi-strip">
  <div class="kpi-inner">
    <div class="kpi"><div class="kpi-val">27.0%</div><div class="kpi-label">Exposicion media 2025</div><div class="kpi-delta">+0.2pp vs 2019</div></div>
    <div class="kpi"><div class="kpi-val">14.6%</div><div class="kpi-label">Trabajadores alta exposicion</div><div class="kpi-delta">+0.2pp vs 2019</div></div>
    <div class="kpi"><div class="kpi-val">29.1%</div><div class="kpi-label">Tasa augmentation 2025</div><div class="kpi-delta">vs 0.8% sustitucion</div></div>
    <div class="kpi"><div class="kpi-val">17.9M</div><div class="kpi-label">Trabajadores cubiertos</div><div class="kpi-delta">96.8% del empleo ocupado</div></div>
    <div class="kpi"><div class="kpi-val">377</div><div class="kpi-label">Ocupaciones analizadas</div><div class="kpi-delta">de 397 observadas</div></div>
    <div class="kpi"><div class="kpi-val">25</div><div class="kpi-label">Departamentos (EPEN)</div><div class="kpi-delta">2022-2025</div></div>
  </div>
</div>

<!-- ═══ S1: EVOLUCIÓN ═══ -->
<section class="section" id="evolucion">
  <div class="container">
    <div class="section-label">01 - Serie temporal</div>
    <div class="section-title">Evolucion de la exposicion 2019-2025</div>
    <div class="section-desc">La exposicion media al impacto de la IA se mantiene cerca de 27% entre 2019 y 2025. La caida de 2020 refleja cambios en la composicion sectorial del empleo durante la pandemia. El augmentation domina consistentemente sobre la sustitucion.</div>
    <div class="card">
      <div id="chart-evolution" style="height:360px;"></div>
    </div>
    <div class="metodo">
      <strong>Como se calculo:</strong> Cada ocupado ENAHO (2019-2025) fue emparejado con su ocupacion CNO 4 digitos. A esa ocupacion se le asigno el score del indice construido con Claude Sonnet 4-6 sobre el CNO-2015. La exposicion agregada es la media ponderada por factor de expansion (peso muestral). La cobertura del cruce supera 96% del empleo ocupado y el remanente corresponde sobre todo a ocupaciones observadas en ENAHO que aun no tienen score en el indice. Augmentation = la IA amplifica las capacidades del trabajador. Sustitucion = la IA podria reemplazar la tarea.
    </div>
  </div>
</section>

<!-- ═══ S2: TOP OCUPACIONES ═══ -->
<section class="section" id="ocupaciones">
  <div class="container">
    <div class="section-label">02 - Ranking ocupacional</div>
    <div class="section-title">Ocupaciones mas expuestas a la IA</div>
    <div class="section-desc">Top 20 ocupaciones con mayor exposicion media ponderada (solo ocupaciones con mas de 50,000 trabajadores). Selecciona el ano para ver la evolucion del ranking.</div>
    <div class="year-tabs" id="occ-year-tabs">
      <button class="year-tab" onclick="showTopOcc(2019)">2019</button>
      <button class="year-tab" onclick="showTopOcc(2020)">2020</button>
      <button class="year-tab" onclick="showTopOcc(2021)">2021</button>
      <button class="year-tab" onclick="showTopOcc(2022)">2022</button>
      <button class="year-tab" onclick="showTopOcc(2023)">2023</button>
      <button class="year-tab" onclick="showTopOcc(2024)">2024</button>
      <button class="year-tab active" onclick="showTopOcc(2025)">2025</button>
    </div>
    <div class="grid-2">
      <div class="card" id="top-occ-list" style="overflow-y:auto;max-height:540px;"></div>
      <div class="card"><div id="chart-top-occ" style="height:500px;"></div></div>
    </div>
    <div class="metodo">
      <strong>Como se calculo:</strong> Para cada ano, se agrupan los trabajadores ENAHO por ocupacion CNO 4d y se calcula la media del score de exposicion ponderada por el factor de expansion. Solo se incluyen ocupaciones con al menos 50,000 trabajadores para garantizar representatividad estadistica. El ranking muestra las ocupaciones con mayor score medio.
    </div>
  </div>
</section>

<!-- ═══ S3: MAPA OCUPACIONAL ═══ -->
<section class="section" id="mapa">
  <div class="container">
    <div class="section-label">03 - Mapa ocupacional</div>
    <div class="section-title">Exposicion vs. tamano del empleo (2025)</div>
    <div class="section-desc">Cada burbuja es una ocupacion (>=80,000 trabajadores). Eje X = exposicion media; Eje Y = numero de trabajadores (escala log). Color = proporcion de mujeres. Pasa el cursor para ver detalle.</div>
    <div class="card"><div id="chart-bubble" style="height:500px;"></div></div>
    <div class="metodo">
      <strong>Como se calculo:</strong> Mismo empate CNO x score que en el ranking. Cada burbuja representa una ocupacion con >=80,000 trabajadores en ENAHO 2025. El tamano de la burbuja es proporcional a la poblacion ponderada. El color indica la proporcion de mujeres en esa ocupacion segun ENAHO 2025.
    </div>
  </div>
</section>

<!-- ═══ S4: PERFILES DEMOGRÁFICOS ═══ -->
<section class="section" id="perfiles">
  <div class="container">
    <div class="section-label">04 - Perfil del trabajador expuesto</div>
    <div class="section-title">Quienes trabajan en ocupaciones de alta exposicion?</div>
    <div class="section-desc">Exposicion media ponderada por caracteristica del trabajador (ENAHO 2025). El porcentaje entre parentesis es la participacion de ese grupo en el empleo total.</div>
    <div class="profile-grid">
      <div class="profile-card"><h4>Nivel educativo</h4><div id="prof-educacion"></div></div>
      <div class="profile-card"><h4>Sexo</h4><div id="prof-sexo"></div></div>
      <div class="profile-card"><h4>Categoria de empleo</h4><div id="prof-categoria_agregada"></div></div>
      <div class="profile-card"><h4>Rama de actividad</h4><div id="prof-rama"></div></div>
      <div class="profile-card"><h4>Grupo de edad</h4><div id="prof-grupo_edad"></div></div>
      <div class="profile-card"><h4>Tipo de contrato</h4><div id="prof-formalidad_contrato"></div></div>
    </div>
    <div style="margin-top:28px;" class="card">
      <div id="chart-profiles" style="height:420px;"></div>
    </div>
    <div class="metodo">
      <strong>Como se calculo:</strong> Para cada grupo demografico (ej: "secundaria completa", "empleado"), se identifica a todos los trabajadores ENAHO 2025 que pertenecen a ese grupo y tienen match con el indice. Se calcula la media del score de exposicion ponderada por el factor de expansion. El porcentaje entre parentesis es la participacion de ese grupo en el empleo total cubierto.
    </div>
  </div>
</section>

<!-- ═══ S5: TENDENCIAS ═══ -->
<section class="section" id="tendencias">
  <div class="container">
    <div class="section-label">05 - Tendencias por segmento</div>
    <div class="section-title">Como cambio la exposicion por sector? (2019-2025)</div>
    <div class="section-desc">Evolucion de la exposicion media por rama de actividad y nivel educativo.</div>
    <div class="grid-2">
      <div class="card"><div id="chart-rama-evol" style="height:380px;"></div></div>
      <div class="card"><div id="chart-edu-evol" style="height:380px;"></div></div>
    </div>
  </div>
</section>

<!-- ═══ S6: COMPARATIVO ═══ -->
<section class="section" id="comparativo">
  <div class="container">
    <div class="section-label">06 - Comparativo</div>
    <div class="section-title">Alta exposicion vs. baja exposicion</div>
    <div class="section-desc">Subgrupos con mayor y menor exposicion dentro de cada dimension demografica (2025).</div>
    <div class="card"><div id="chart-comparative" style="height:420px;"></div></div>
    <div class="note" style="margin-top:20px;">
      <strong>Hallazgo:</strong> Los trabajadores de alta exposicion son mas educados, trabajan en comercio y servicios, tienen empleo formal y participacion femenina mas alta. El augmentation domina en todos los grupos.
    </div>
  </div>
</section>

<div class="section-divider"></div>

<!-- ═══ S7: INGRESOS ═══ -->
<section class="section" id="ingresos">
  <div class="container">
    <div class="section-label">07 - Ingresos y exposicion</div>
    <div class="section-title">Relacion entre salario e indice de exposicion a la IA</div>
    <div class="section-desc">Cada punto representa una ocupacion (ENAHO 2024, >50,000 trabajadores con ingreso reportado). El tamano refleja el numero de trabajadores; el color indica proporcion de mujeres. Las ocupaciones de mayor ingreso tienden a tener mayor exposicion. Esta seccion conserva 2024 porque el insumo procesado de ingresos todavia no fue extendido a 2025.</div>
    <div class="card"><div id="chart-income-scatter" style="height:520px;"></div></div>
    <div class="grid-2" style="margin-top:20px;">
      <div class="card"><div id="chart-income-evol" style="height:300px;"></div></div>
      <div class="card"><div id="chart-income-exposure-bar" style="height:300px;"></div></div>
    </div>
    <div class="note-blue" style="margin-top:16px;">
      <strong>Lectura:</strong> La correlacion positiva entre ingreso y exposicion sugiere que las ocupaciones mejor remuneradas son tambien las mas expuestas a la IA. Esto implica que el impacto potencial se concentra en trabajadores con mayor capital humano, no en los mas vulnerables economicamente.
    </div>
    <div class="metodo" style="margin-top:12px;">
      <strong>Como se calculo:</strong> Los ingresos provienen de la variable ingreso laboral mensual de ENAHO, estandarizada a periodicidad mensual (diario x30, semanal x4.33, etc.) y ponderada por el factor de expansion. Solo se incluyen trabajadores con ingreso reportado y match con el indice. El scatter usa ENAHO 2024 con umbral de 50,000 trabajadores por ocupacion.
    </div>
  </div>
</section>

<!-- ═══ S8: DEPARTAMENTOS ═══ -->
<section class="section" id="departamentos">
  <div class="container">
    <div class="section-label">08 - Analisis departamental</div>
    <div class="section-title">Exposicion a la IA por departamento (EPEN 2022-2025)</div>
    <div class="section-desc">Distribucion geografica de la exposicion ocupacional usando EPEN departamental. Lima y Arequipa lideran por su mayor concentracion de empleos formales en servicios y comercio. Selecciona un departamento para ver sus ocupaciones mas expuestas.</div>

    <div class="grid-2" style="margin-bottom:24px;">
      <div class="card"><div id="chart-dept-bar" style="height:480px;"></div></div>
      <div class="card"><div id="chart-dept-income" style="height:480px;"></div></div>
    </div>

    <div class="card" style="margin-bottom:20px;">
      <div id="chart-dept-evol" style="height:360px;"></div>
    </div>

    <!-- Region selector -->
    <div class="section-title" style="font-size:18px;margin-bottom:12px;">Ocupaciones mas expuestas por departamento (2025)</div>
    <div class="region-grid" id="region-selector"></div>
    <div class="card" style="margin-top:16px;">
      <div id="region-occ-list"></div>
    </div>

    <div class="metodo" style="margin-top:12px;">
      <strong>Como se calculo:</strong> Para cada departamento y ano, se toman los microdatos del EPEN departamental anual (INEI). Cada trabajador es emparejado con su ocupacion CNO 4d y el score del indice Sonnet. La exposicion departamental es la media ponderada del score usando el factor de expansion del EPEN. La cobertura del EPEN es mas alta en zonas urbanas — departamentos rurales (ej: Amazonas, Huancavelica) pueden subestimar la exposicion real del sector agricola. Los ingresos usan el ingreso laboral mensual del EPEN, estandarizado de la misma forma que ENAHO.
    </div>
  </div>
</section>

<div class="section-divider"></div>

<!-- ═══ S9: PERSONAS ═══ -->
<section class="section" id="personas">
  <div class="container">
    <div class="section-label">09 - Perfiles del trabajador expuesto</div>
    <div class="section-title">A quien impacta la IA? El rostro de la exposicion</div>
    <div class="section-desc">Perfil tipico del trabajador en el cuartil de mayor exposicion (Q4) segun la ENAHO 2025, a nivel nacional. El perfil muestra las caracteristicas modales y promedio de quienes trabajan en las ocupaciones mas expuestas. Se incluye tambien el perfil de baja exposicion para contraste.</div>

    <div class="persona-grid" id="persona-grid"></div>

    <div style="margin-top:32px;" class="card">
      <div id="chart-persona-compare" style="height:380px;"></div>
    </div>

    <div class="note-green" style="margin-top:20px;">
      <strong>Que nos dice este perfil:</strong> El trabajador de alta exposicion en Peru tiende a concentrarse en ocupaciones urbanas de comercio, servicios y apoyo administrativo, con mayor educacion formal, mas presencia femenina y mejores ingresos que el grupo de baja exposicion. En contraste, la baja exposicion se concentra en agricultura, construccion y ocupaciones elementales, con menor ingreso y menor urbanizacion. En ambos casos domina mas el componente de augmentation que el de sustitucion directa.
    </div>
    <div class="metodo" style="margin-top:12px;">
      <strong>Como se construyo:</strong> Se seleccionan todos los trabajadores ENAHO 2025 con match al indice de exposicion. Se identifica el cuartil superior (Q4, score >= percentil 75) y se calculan: sexo modal, edad media ponderada, categoria de empleo modal, top 3 ocupaciones por numero de trabajadores y porcentaje urbano.
    </div>
  </div>
</section>

<footer>
  <div class="container">
    <strong>Exposicion a IA en el Empleo Peruano 2019-2025</strong><br><br>
    Indice construido con <strong>Claude Sonnet 4-6</strong> (Anthropic, abril 2026) sobre CNO-2015 (INEI).
    Cruce con microdatos ENAHO ponderados por factor de expansion y EPEN departamental anual.
    Universidad del Pacifico - 2026.
  </div>
</footer>

<script>
""" + DATA_JS + """
// ─── HELPERS ──────────────────────────────────────────────────────────────────
const fmtPct  = v => (v*100).toFixed(1)+'%';
const fmtN    = v => v>=1e6?(v/1e6).toFixed(1)+'M':v>=1e3?(v/1e3).toFixed(0)+'K':String(Math.round(v));
const fmtSol  = v => v ? 'S/ '+Math.round(v).toLocaleString('es-PE') : 'N/D';
const COLORS  = ['#c25b2a','#2563eb','#059669','#d97706','#7c3aed','#db2777','#0891b2','#65a30d'];
const PLY_CFG = {responsive:true,displayModeBar:false};
const PLY_LAY = {plot_bgcolor:'#fff',paper_bgcolor:'#fff',font:{family:'Segoe UI,sans-serif',size:12}};

// ─── S1: EVOLUTION ────────────────────────────────────────────────────────────
(()=>{
  const yrs = EVOLUTION.map(d=>d.year);
  Plotly.newPlot('chart-evolution',[
    {name:'Exposicion media',x:yrs,y:EVOLUTION.map(d=>+(d.mean_exposure*100).toFixed(2)),
     type:'scatter',mode:'lines+markers',line:{color:'#c25b2a',width:3},marker:{size:8}},
    {name:'% Alta exposicion',x:yrs,y:EVOLUTION.map(d=>+(d.pct_alta*100).toFixed(2)),
     type:'scatter',mode:'lines+markers',line:{color:'#2563eb',width:3,dash:'dot'},marker:{size:8}},
    {name:'% Augmentation',x:yrs,y:EVOLUTION.map(d=>+(d.pct_aumento*100).toFixed(2)),
     type:'scatter',mode:'lines+markers',line:{color:'#059669',width:2},marker:{size:6}},
    {name:'% Sustitucion',x:yrs,y:EVOLUTION.map(d=>+(d.pct_sustitucion*100).toFixed(2)),
     type:'scatter',mode:'lines+markers',line:{color:'#d97706',width:2,dash:'dash'},marker:{size:6}},
  ],{...PLY_LAY,margin:{t:20,r:20,b:40,l:50},
    xaxis:{tickvals:yrs,tickfont:{size:12}},
    yaxis:{title:'Porcentaje (%)',ticksuffix:'%',range:[0,35]},
    legend:{orientation:'h',y:-0.18,x:0},hovermode:'x unified'},PLY_CFG);
})();

// ─── S2: TOP OCUPACIONES ─────────────────────────────────────────────────────
function showTopOcc(year){
  document.querySelectorAll('.year-tab').forEach((t,i)=>{
    t.classList.toggle('active',[2019,2020,2021,2022,2023,2024,2025][i]===year);
  });
  const occs = TOP_OCC_BY_YEAR[String(year)];
  document.getElementById('top-occ-list').innerHTML = occs.map((o,i)=>`
    <div class="bar-row">
      <div class="bar-rank">${i+1}</div>
      <div class="bar-label" title="${o.occupation}">${o.occupation}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${(o.mean_exposure*100).toFixed(0)}%"></div></div>
      <div class="bar-val">${fmtPct(o.mean_exposure)}</div>
      <div class="bar-workers">${fmtN(o.workers)}</div>
    </div>`).join('');
  const top15 = [...occs].slice(0,15).reverse();
  Plotly.newPlot('chart-top-occ',[{
    type:'bar',orientation:'h',
    x:top15.map(o=>+(o.mean_exposure*100).toFixed(1)),
    y:top15.map(o=>o.occupation.length>42?o.occupation.slice(0,42)+'...':o.occupation),
    marker:{color:top15.map(o=>o.mean_exposure>0.55?'#c25b2a':o.mean_exposure>0.35?'#d97706':'#2563eb'),opacity:0.85},
    text:top15.map(o=>fmtPct(o.mean_exposure)),textposition:'outside',
    hovertemplate:'<b>%{y}</b><br>Exposicion: %{x:.1f}%<extra></extra>',
  }],{...PLY_LAY,margin:{t:20,r:80,b:40,l:10},
    xaxis:{range:[0,100],ticksuffix:'%',title:'Score de exposicion medio'},
    yaxis:{automargin:true,tickfont:{size:11}}},PLY_CFG);
}
showTopOcc(2025);

// ─── S3: BUBBLE ───────────────────────────────────────────────────────────────
(()=>{
  const d = BUBBLE_CURRENT;
  const maxW = Math.max(...d.map(o=>o.workers));
  Plotly.newPlot('chart-bubble',[{
    type:'scatter',mode:'markers',
    x:d.map(o=>+(o.mean_exposure*100).toFixed(1)),
    y:d.map(o=>o.workers),
    marker:{size:d.map(o=>8+28*(o.workers/maxW)),
      color:d.map(o=>o.share_women),
      colorscale:[['0','#2563eb'],['0.5','#d97706'],['1','#db2777']],
      showscale:true,colorbar:{title:'% mujeres',tickformat:'.0%',len:0.6,thickness:12},
      opacity:0.75,line:{width:1,color:'rgba(0,0,0,0.1)'}},
    text:d.map(o=>`<b>${o.occupation}</b><br>Exposicion: ${fmtPct(o.mean_exposure)}<br>Trabajadores: ${fmtN(o.workers)}<br>% Mujeres: ${fmtPct(o.share_women)}<br>Edad media: ${o.mean_age}`),
    hoverinfo:'text',
  }],{...PLY_LAY,margin:{t:20,r:100,b:60,l:70},
    xaxis:{title:'Exposicion media (%)',ticksuffix:'%',range:[-2,100]},
    yaxis:{title:'Trabajadores (ponderado)',type:'log',tickformat:'.2s'}},PLY_CFG);
})();

// ─── S4: PERFILES ─────────────────────────────────────────────────────────────
(()=>{
  ['educacion','sexo','categoria_agregada','rama','grupo_edad','formalidad_contrato'].forEach(s=>{
    const el = document.getElementById('prof-'+s);
    if(!el) return;
    const maxS = 0.55;
    el.innerHTML = (PROFILES_CURRENT[s]||[]).map(r=>{
      const c = r.mean_exposure>0.4?'#c25b2a':r.mean_exposure>0.25?'#d97706':'#059669';
      return `<div class="prof-row">
        <span>${r.group}</span>
        <span><span class="prof-score" style="color:${c}">${fmtPct(r.mean_exposure)}</span>
        <span class="prof-share">(${fmtPct(r.pop_share)})</span></span></div>`;
    }).join('');
  });
  const colorMap={educacion:'#c25b2a',categoria_agregada:'#2563eb',rama:'#059669',grupo_edad:'#d97706',formalidad_contrato:'#7c3aed'};
  const labelMap={educacion:'Educacion',categoria_agregada:'Categoria',rama:'Rama',grupo_edad:'Edad',formalidad_contrato:'Contrato'};
  Plotly.newPlot('chart-profiles',
    Object.keys(colorMap).map(k=>({
      type:'bar',name:labelMap[k],
      x:(PROFILES_CURRENT[k]||[]).sort((a,b)=>b.mean_exposure-a.mean_exposure).map(r=>r.group),
      y:(PROFILES_CURRENT[k]||[]).sort((a,b)=>b.mean_exposure-a.mean_exposure).map(r=>+(r.mean_exposure*100).toFixed(2)),
      marker:{color:colorMap[k],opacity:0.85},
      hovertemplate:'<b>%{x}</b><br>%{y:.1f}%<extra>'+labelMap[k]+'</extra>',
    })),
    {...PLY_LAY,barmode:'group',margin:{t:30,r:20,b:120,l:60},
      xaxis:{tickangle:-35,tickfont:{size:10},automargin:true},
      yaxis:{title:'Exposicion media (%)',ticksuffix:'%'},
      legend:{orientation:'h',y:1.08}},PLY_CFG);
})();

// ─── S5: TENDENCIAS ───────────────────────────────────────────────────────────
(()=>{
  const yrs=[2019,2020,2021,2022,2023,2024,2025];
  const ramaGroups=[...new Set(Object.values(PROFILES_EVOL.rama).flatMap(v=>v.map(r=>r.group)))];
  Plotly.newPlot('chart-rama-evol',
    ramaGroups.map((g,i)=>({
      type:'scatter',mode:'lines+markers',name:g,x:yrs,
      y:yrs.map(y=>{const r=(PROFILES_EVOL.rama[String(y)]||[]).find(x=>x.group===g);return r?+(r.mean_exposure*100).toFixed(2):null;}),
      line:{color:COLORS[i%COLORS.length],width:2},marker:{size:6},connectgaps:true,
    })),
    {...PLY_LAY,title:{text:'Por rama de actividad',font:{size:14}},
      margin:{t:50,r:20,b:40,l:55},xaxis:{tickvals:yrs},
      yaxis:{title:'Exposicion (%)',ticksuffix:'%',range:[0,55]},
      legend:{font:{size:10}},hovermode:'x unified'},PLY_CFG);

  const eduAll=[...new Set(Object.values(PROFILES_EVOL.educacion).flatMap(v=>v.map(r=>r.group)))];
  const eduMeans=eduAll.map(g=>({g,m:yrs.map(y=>{const r=(PROFILES_EVOL.educacion[String(y)]||[]).find(x=>x.group===g);return r?r.mean_exposure:0;}).reduce((a,b)=>a+b,0)/yrs.length})).sort((a,b)=>b.m-a.m).slice(0,6).map(x=>x.g);
  Plotly.newPlot('chart-edu-evol',
    eduMeans.map((g,i)=>({
      type:'scatter',mode:'lines+markers',name:g.length>28?g.slice(0,28)+'...':g,x:yrs,
      y:yrs.map(y=>{const r=(PROFILES_EVOL.educacion[String(y)]||[]).find(x=>x.group===g);return r?+(r.mean_exposure*100).toFixed(2):null;}),
      line:{color:COLORS[i%COLORS.length],width:2},marker:{size:6},connectgaps:true,
    })),
    {...PLY_LAY,title:{text:'Por nivel educativo',font:{size:14}},
      margin:{t:50,r:20,b:40,l:55},xaxis:{tickvals:yrs},
      yaxis:{title:'Exposicion (%)',ticksuffix:'%',range:[0,60]},
      legend:{font:{size:9}},hovermode:'x unified'},PLY_CFG);
})();

// ─── S6: COMPARATIVO ─────────────────────────────────────────────────────────
(()=>{
  const buildPair=(sheet,n=2)=>{
    const r=[...(PROFILES_CURRENT[sheet]||[])].sort((a,b)=>b.mean_exposure-a.mean_exposure);
    return {top:r.slice(0,n),bot:r.slice(-n).reverse()};
  };
  const pairs={Educacion:buildPair('educacion',2),Categoria:buildPair('categoria_agregada',2),Rama:buildPair('rama',2),Contrato:buildPair('formalidad_contrato',2)};
  const hX=[],hY=[],lX=[],lY=[];
  Object.entries(pairs).forEach(([dim,{top,bot}])=>{
    top.forEach(r=>{hX.push(`${dim}: ${r.group.length>16?r.group.slice(0,16)+'...':r.group}`);hY.push(+(r.mean_exposure*100).toFixed(1));});
    bot.forEach(r=>{lX.push(`${dim}: ${r.group.length>16?r.group.slice(0,16)+'...':r.group}`);lY.push(+(r.mean_exposure*100).toFixed(1));});
  });
  Plotly.newPlot('chart-comparative',[
    {type:'bar',name:'Mayor exposicion en grupo',x:hX,y:hY,marker:{color:'#c25b2a',opacity:0.85},hovertemplate:'<b>%{x}</b><br>%{y:.1f}%<extra>Alta</extra>'},
    {type:'bar',name:'Menor exposicion en grupo',x:lX,y:lY,marker:{color:'#2563eb',opacity:0.7},hovertemplate:'<b>%{x}</b><br>%{y:.1f}%<extra>Baja</extra>'},
  ],{...PLY_LAY,barmode:'group',margin:{t:30,r:20,b:120,l:60},
    xaxis:{tickangle:-35,tickfont:{size:10},automargin:true},
    yaxis:{title:'Exposicion media (%)',ticksuffix:'%',range:[0,60]},
    legend:{orientation:'h',y:1.05}},PLY_CFG);
})();

// ─── S7: INGRESOS ─────────────────────────────────────────────────────────────
(()=>{
  // Scatter ingreso vs exposicion
  const d = INCOME_SCATTER;
  const maxW = Math.max(...d.map(o=>o.workers));
  Plotly.newPlot('chart-income-scatter',[{
    type:'scatter',mode:'markers',
    x:d.map(o=>+(o.mean_exposure*100).toFixed(1)),
    y:d.map(o=>o.income_mean),
    marker:{
      size:d.map(o=>7+22*(o.workers/maxW)),
      color:d.map(o=>o.women_share),
      colorscale:[['0','#2563eb'],['0.5','#d97706'],['1','#db2777']],
      showscale:true,colorbar:{title:'% mujeres',tickformat:'.0%',len:0.6,thickness:12},
      opacity:0.78,line:{width:1,color:'rgba(0,0,0,0.1)'},
    },
    text:d.map(o=>`<b>${o.occupation}</b><br>Exposicion: ${fmtPct(o.mean_exposure)}<br>Ingreso medio: ${fmtSol(o.income_mean)}<br>Ingreso mediana: ${fmtSol(o.income_median)}<br>Trabajadores: ${fmtN(o.workers)}<br>% Mujeres: ${fmtPct(o.women_share)}`),
    hoverinfo:'text',
  }],{...PLY_LAY,margin:{t:30,r:100,b:60,l:80},
    xaxis:{title:'Exposicion media a la IA (%)',ticksuffix:'%',range:[-2,100]},
    yaxis:{title:'Ingreso laboral mensual medio (S/)',tickformat:',.0f'},
    annotations:[{
      x:85,y:4500,text:'Mayor ingreso<br>Mayor exposicion',showarrow:false,
      font:{size:11,color:'#888'},bgcolor:'rgba(255,255,255,0.8)',borderpad:4,
    }]},PLY_CFG);

  // Evolucion ingreso nacional
  const yrs = INCOME_EVOLUTION.map(d=>d.year);
  Plotly.newPlot('chart-income-evol',[{
    type:'scatter',mode:'lines+markers',name:'Ingreso medio (S/)',
    x:yrs,y:INCOME_EVOLUTION.map(d=>d.income_mean_national),
    line:{color:'#059669',width:3},marker:{size:8},
    hovertemplate:'%{x}: S/ %{y:,.0f}<extra></extra>',
  }],{...PLY_LAY,title:{text:'Ingreso medio nacional (ENAHO)',font:{size:13}},
    margin:{t:50,r:20,b:40,l:70},
    xaxis:{tickvals:yrs},
    yaxis:{title:'S/ mensuales',tickformat:',.0f'}},PLY_CFG);

  // Correlacion ingreso-exposicion por ocupacion (top/bottom 10 por ingreso)
  const sorted = [...INCOME_SCATTER].filter(o=>o.income_mean).sort((a,b)=>b.income_mean-a.income_mean);
  const top10 = sorted.slice(0,10);
  const bot10 = sorted.slice(-10).reverse();
  const combined = [...top10,...bot10];
  Plotly.newPlot('chart-income-exposure-bar',[{
    type:'bar',orientation:'h',
    x:combined.map(o=>+(o.mean_exposure*100).toFixed(1)).reverse(),
    y:combined.map(o=>(o.occupation.length>35?o.occupation.slice(0,35)+'...':o.occupation)+' ('+fmtSol(o.income_mean)+')').reverse(),
    marker:{color:combined.map(o=>o.income_mean>2000?'#c25b2a':'#2563eb').reverse(),opacity:0.85},
    hovertemplate:'<b>%{y}</b><br>Exposicion: %{x:.1f}%<extra></extra>',
  }],{...PLY_LAY,title:{text:'Exposicion en ocup. de alto/bajo ingreso',font:{size:13}},
    margin:{t:50,r:50,b:40,l:12},
    xaxis:{range:[0,100],ticksuffix:'%'},
    yaxis:{automargin:true,tickfont:{size:10}},
    annotations:[{x:5,y:19,text:'Alto ingreso',showarrow:false,font:{size:10,color:'#c25b2a'},xanchor:'left'},
                 {x:5,y:9,text:'Bajo ingreso',showarrow:false,font:{size:10,color:'#2563eb'},xanchor:'left'}]},PLY_CFG);
})();

// ─── S8: DEPARTAMENTOS ────────────────────────────────────────────────────────
(()=>{
  // Bar chart departamentos 2025
  const reg2025 = REGIONAL_DATA.filter(d=>d.year===2025).sort((a,b)=>b.mean_exposure-a.mean_exposure);
  Plotly.newPlot('chart-dept-bar',[{
    type:'bar',orientation:'h',
    x:reg2025.map(d=>+(d.mean_exposure*100).toFixed(1)).reverse(),
    y:reg2025.map(d=>d.region_name).reverse(),
    marker:{
      color:reg2025.map(d=>+(d.mean_exposure*100).toFixed(1)).reverse(),
      colorscale:[['0','#dbeafe'],['0.5','#f97316'],['1','#c25b2a']],
      cmin:22,cmax:32,
      showscale:false,opacity:0.9,
    },
    text:reg2025.map(d=>fmtPct(d.mean_exposure)).reverse(),
    textposition:'outside',
    hovertemplate:'<b>%{y}</b><br>Exposicion: %{x:.1f}%<extra></extra>',
  }],{...PLY_LAY,title:{text:'Exposicion media por departamento (2025)',font:{size:14}},
    margin:{t:50,r:70,b:40,l:100},
    xaxis:{range:[0,38],ticksuffix:'%',title:'Score exposicion (%)'},
    yaxis:{automargin:true,tickfont:{size:11}}},PLY_CFG);

  // Income by dept 2025
  const regInc = reg2025.filter(d=>d.income_mean).sort((a,b)=>b.income_mean-a.income_mean);
  Plotly.newPlot('chart-dept-income',[
    {type:'bar',orientation:'h',name:'Ingreso medio (S/)',
     x:regInc.map(d=>d.income_mean).reverse(),
     y:regInc.map(d=>d.region_name).reverse(),
     marker:{color:'#059669',opacity:0.8},
     text:regInc.map(d=>fmtSol(d.income_mean)).reverse(),textposition:'outside',
     hovertemplate:'<b>%{y}</b><br>Ingreso: S/ %{x:,.0f}<extra></extra>',
    },
  ],{...PLY_LAY,title:{text:'Ingreso laboral medio por departamento (2025)',font:{size:14}},
    margin:{t:50,r:90,b:40,l:100},
    xaxis:{title:'S/ mensuales',tickformat:',.0f'},
    yaxis:{automargin:true,tickfont:{size:11}}},PLY_CFG);

  // Evolucion exposicion por departamento (2022-2025) — top 8 departamentos
  const top8depts = reg2025.slice(0,8).map(d=>d.region_code);
  const years3 = [2022,2023,2024,2025];
  Plotly.newPlot('chart-dept-evol',
    top8depts.map((rc,i)=>{
      const name = DEPT_NAMES[String(rc)]||`Region ${rc}`;
      return {type:'scatter',mode:'lines+markers',name:name,
        x:years3,
        y:years3.map(y=>{
          const row=REGIONAL_DATA.find(d=>d.region_code===rc&&d.year===y);
          return row?+(row.mean_exposure*100).toFixed(2):null;
        }),
        line:{color:COLORS[i%COLORS.length],width:2},marker:{size:7},connectgaps:true,
      };
    }),
    {...PLY_LAY,title:{text:'Evolucion exposicion - Top 8 departamentos (2022-2025)',font:{size:14}},
      margin:{t:50,r:20,b:40,l:55},xaxis:{tickvals:years3},
      yaxis:{title:'Exposicion (%)',ticksuffix:'%',range:[24,36]},
      legend:{font:{size:10}},hovermode:'x unified'},PLY_CFG);

  // Region selector
  const allRegions = [...new Set(REGIONAL_DATA.filter(d=>d.year===2025).map(d=>d.region_code))].sort((a,b)=>a-b);
  const selDiv = document.getElementById('region-selector');
  allRegions.forEach(rc=>{
    const btn = document.createElement('button');
    btn.className = 'region-btn'+(rc===15?' active':'');
    btn.textContent = DEPT_NAMES[String(rc)]||`Region ${rc}`;
    btn.onclick = ()=>{
      document.querySelectorAll('.region-btn').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      showRegionOcc(rc);
    };
    selDiv.appendChild(btn);
  });
  showRegionOcc(15);
})();

function showRegionOcc(rc){
  const occs = TOP_OCC_BY_REGION[String(rc)]||[];
  const name  = DEPT_NAMES[String(rc)]||`Region ${rc}`;
  const el    = document.getElementById('region-occ-list');
  el.innerHTML = `<div style="font-weight:700;font-size:14px;margin-bottom:12px;color:var(--accent2)">
    Top ocupaciones expuestas en ${name} (2025)</div>` +
    (occs.length ? occs.map((o,i)=>`
    <div class="bar-row">
      <div class="bar-rank">${i+1}</div>
      <div class="bar-label" title="${o.occupation}">${o.occupation}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${(o.mean_exposure*100).toFixed(0)}%;background:var(--accent2)"></div></div>
      <div class="bar-val" style="color:var(--accent2)">${fmtPct(o.mean_exposure)}</div>
      <div class="bar-workers">${fmtN(o.workers)}</div>
    </div>`).join('') : '<div style="color:var(--muted);padding:12px">Sin datos suficientes para este departamento.</div>');
}

// ─── S9: PERSONAS ─────────────────────────────────────────────────────────────
(()=>{
  const grid = document.getElementById('persona-grid');
  const sexIcon = s => s==='Mujer' ? '&#9792;' : '&#9794;';
  const tierLabel = t => t==='alta' ? 'Alta exposicion (Q4)' : 'Baja exposicion (Q1)';

  PERSONAS.forEach(p=>{
    const card = document.createElement('div');
    card.className = 'persona-card';
    const topOcc = p.top_occupations.slice(0,3).map(o=>`
      <div class="persona-occ-item">
        <span class="persona-occ-name">${o.name}</span>
        <span class="persona-occ-n">${fmtN(o.workers)}</span>
      </div>`).join('');
    const augPct = Math.round(p.pct_aumento * 100);
    const sustPct = Math.round(p.pct_sustitucion * 100);
    const incStr = p.income_mean ? fmtSol(p.income_mean) : 'N/D';
    const eduStr = p.education || 'N/D';
    card.innerHTML = `
      <div class="persona-header ${p.tier}">
        <div class="persona-tier ${p.tier}">${tierLabel(p.tier)}</div>
        <div class="persona-location">${p.label}</div>
        <div class="persona-exp ${p.tier}">${fmtPct(p.mean_exposure)} exposicion</div>
      </div>
      <div class="persona-body">
        <div class="persona-stat-row">
          <div class="persona-stat">
            <div class="persona-stat-val">${sexIcon(p.sex)} ${p.sex}</div>
            <div class="persona-stat-label">${fmtPct(p.pct_women)} mujeres</div>
          </div>
          <div class="persona-stat">
            <div class="persona-stat-val">${p.mean_age} anos</div>
            <div class="persona-stat-label">Edad media</div>
          </div>
          <div class="persona-stat">
            <div class="persona-stat-val">${incStr}</div>
            <div class="persona-stat-label">Ingreso mensual</div>
          </div>
        </div>
        <div class="persona-stat-row">
          <div class="persona-stat">
            <div class="persona-stat-val" style="font-size:14px">${p.top_category}</div>
            <div class="persona-stat-label">Categoria laboral</div>
          </div>
          <div class="persona-stat">
            <div class="persona-stat-val" style="font-size:13px">${Math.round(p.pct_urban*100)}%</div>
            <div class="persona-stat-label">Zona urbana</div>
          </div>
        </div>
        <div style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.8px;margin-bottom:6px;">Top ocupaciones</div>
        <div class="persona-occs">${topOcc}</div>
        <div style="margin-top:12px;">
          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:4px;">
            <span>Augmentation: <strong style="color:var(--accent3)">${augPct}%</strong></span>
            <span>Sustitucion: <strong style="color:var(--accent)">${sustPct}%</strong></span>
          </div>
          <div class="persona-aug-bar">
            <div class="persona-aug-fill" style="width:${augPct}%"></div>
          </div>
        </div>
        <div style="font-size:11px;color:var(--muted);margin-top:10px;">${fmtN(p.total_workers)} trabajadores en este cuartil</div>
      </div>`;
    grid.appendChild(card);
  });

  // Comparison chart: alta vs baja
  const alta = PERSONAS.find(p=>p.tier==='alta');
  const baja = PERSONAS.find(p=>p.tier==='baja');
  if(alta && baja){
    const dims = ['Exposicion media','% Alta exp.','% Augmentation','% Urbano','Ingreso (S/ /100)','Edad'];
    const vAlta = [
      +(alta.mean_exposure*100).toFixed(1),
      +(alta.pct_alta*100).toFixed(1),
      +(alta.pct_aumento*100).toFixed(1),
      +(alta.pct_urban*100).toFixed(1),
      alta.income_mean ? +(alta.income_mean/100).toFixed(1) : 0,
      alta.mean_age,
    ];
    const vBaja = [
      +(baja.mean_exposure*100).toFixed(1),
      +(baja.pct_alta*100).toFixed(1),
      +(baja.pct_aumento*100).toFixed(1),
      +(baja.pct_urban*100).toFixed(1),
      baja.income_mean ? +(baja.income_mean/100).toFixed(1) : 0,
      baja.mean_age,
    ];
    Plotly.newPlot('chart-persona-compare',[
      {type:'bar',name:'Alta exposicion (Q4)',x:dims,y:vAlta,
       marker:{color:'#c25b2a',opacity:0.85},
       hovertemplate:'<b>%{x}</b>: %{y}<extra>Alta exp.</extra>'},
      {type:'bar',name:'Baja exposicion (Q1)',x:dims,y:vBaja,
       marker:{color:'#2563eb',opacity:0.7},
       hovertemplate:'<b>%{x}</b>: %{y}<extra>Baja exp.</extra>'},
    ],{...PLY_LAY,barmode:'group',
      title:{text:'Comparativo: trabajador de alta vs. baja exposicion (Peru 2025)',font:{size:14}},
      margin:{t:50,r:20,b:60,l:60},
      xaxis:{tickfont:{size:12}},
      yaxis:{title:'Valor'},
      legend:{orientation:'h',y:1.08}},PLY_CFG);
  }
})();
</script>
</body>
</html>"""

out_path = PROJECT_ROOT / "reporte_ia_empleo_peru_2019_2025.html"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(HTML)

size_kb = out_path.stat().st_size / 1024
print(f"Reporte generado: {out_path}")
print(f"Tamano: {size_kb:.0f} KB")
