Estos scripts quedan operativos dentro de `ia_empleo_peru/_interno` y usan rutas relativas al bundle.

## Scripts clave

- `build_enaho_complete_multiyear.py`: arma `ENAHO_complete_YYYY.csv` a partir de las bases crudas ubicadas en `_interno/bases/originales/enaho/`.
- `build_enaho_exposure_notebook.py`: genera el notebook anual final alineado con el HTML maestro y exporta tablas auxiliares por ano.
- `generate_enaho_exposure_year_reports.py`: genera notebooks y reportes anuales por ano.
- `generar_reporte_html.py`: reconstruye `reporte_ia_empleo_peru_2019_2024.html` usando solo insumos dentro de esta carpeta.

## Nota

Para rerun del bundle hacen falta:

- `_interno/bases/intermedias/enaho_complete_years/`
- `_interno/bases/procesadas/`
- `_interno/outputs/enaho_exposure_2019` a `_interno/outputs/enaho_exposure_2024`
- `_interno/referencias/indices/anthropic-claude-sonnet-4-6_exposure_index.xlsx`
