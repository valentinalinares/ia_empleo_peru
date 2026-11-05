Estos scripts quedan operativos dentro de `ia_empleo_peru/_interno` y usan rutas relativas al bundle.

## Scripts clave

- `build_enaho_complete_multiyear.py`: arma `ENAHO_complete_YYYY.csv` a partir de las bases crudas ubicadas en `_interno/bases/originales/enaho/`.
- `build_enaho_persona_education.py`: reconstruye `education_code` en la base
  procesada ENAHO desde `P301A`, preservado como codigo o etiqueta en las bases
  completas. Antes de escribir verifica que las filas y las otras columnas no
  cambien, y genera un manifiesto de auditoria.
- `build_enaho_exposure_notebook.py`: genera el notebook anual final alineado con el HTML maestro y exporta tablas auxiliares por ano.
- `generate_enaho_exposure_year_reports.py`: genera notebooks y reportes anuales por ano.
- `generar_reporte_html.py`: reconstruye `reporte_ia_empleo_peru_2019_2025.html` usando solo insumos dentro de esta carpeta.
- `build_epen_persona_departamentos.py`: reconstruye la base anual de personas
  ocupadas EPEN 2022-2025 desde los ZIP oficiales del modulo 76. Conserva el
  codigo original y genera `occupation_code_4d` completando ceros a la
  izquierda. Escribe tambien un manifiesto con huellas SHA-256 y conteos.
- `analizar_sensibilidad_factores.py`: contrasta la suma de los factores EPEN
  con las cifras oficiales, compara casos con y sin factor dentro de celdas
  homogéneas y calcula la sensibilidad a un ajuste por falta de respuesta. La
  base procesada se abre solo para lectura y su SHA-256 se verifica antes y
  después.
- `diagnosticar_factores_faltantes.py`: describe los ocupados EPEN sin
  `FAC300_ANUAL` (origen en los ZIP, distribución, panel y otros factores). Solo
  lee datos; informe en `_interno/docs/epen_factores_faltantes.md`.

Requiere Python 3.10 o superior (usa `zip(..., strict=True)`) y las
dependencias de `requirements.txt`. Por defecto busca los ZIP en
`../data/raw/inei_data_core/epen_departamentos/<ano>/*/csv/*-Modulo76.zip`,
relativo a la carpeta `ia_empleo_peru`; otra ubicacion se indica con
`--raw-root`.

Ejecutar desde la carpeta `ia_empleo_peru`:

```text
python _interno/scripts/build_epen_persona_departamentos.py
python _interno/scripts/build_enaho_persona_education.py
python -m unittest tests/test_build_epen_persona_departamentos.py
python -m unittest tests/test_build_enaho_persona_education.py
python _interno/scripts/analizar_sensibilidad_factores.py
python -m unittest tests/test_analizar_sensibilidad_factores.py
```

El mapeo auditado de identificadores EPEN, sus fuentes por año y las
limitaciones de `ubigeo`, dominio y `MUESTRA` están documentados en
`_interno/docs/epen_departamentos_identificadores.md`.

La autoría y procedencia del índice Sonnet, su relación con Manky (2025), y la
documentación pública y limitaciones del diseño muestral EPEN se explican en
`_interno/docs/metodologia_indice_y_diseno_epen.md`.

## Nota

Para rerun del bundle hacen falta:

- `_interno/bases/intermedias/enaho_complete_years/`
- `_interno/bases/procesadas/`
- `_interno/outputs/enaho_exposure_2019` a `_interno/outputs/enaho_exposure_2025`
- `_interno/referencias/indices/anthropic-claude-sonnet-4-6_exposure_index.xlsx`
