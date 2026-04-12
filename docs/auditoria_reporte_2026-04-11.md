# Auditoria del reporte IA empleo Peru

Fecha de auditoria: `2026-04-11`

## Hallazgos corregidos

1. `P301A` (`nivel educativo`) estaba mal mapeado en `build_enaho_complete_multiyear.py`.
   El diccionario ENAHO 2024 usa `5 = secundaria incompleta`, `6 = secundaria completa`, `7 = superior no universitaria incompleta`, `8 = superior no universitaria completa`, `9 = superior universitaria incompleta`, `10 = superior universitaria completa`, `11 = maestria/doctorado`, `12 = basica especial`, `99 = missing`.
   En el script faltaba el codigo `5`, por lo que toda la escala quedaba corrida desde secundaria.
   Se corrigio el mapping y se regeneraron las bases `ENAHO_complete_2019_2024`.

2. Los reportes anuales ENAHO usados por el HTML estaban calculando exposicion sobre la base fusionada `02 + 03 + 05`, pero sin filtrar a `ocupados`.
   Eso hacia que el denominador de cobertura y varios agregados mezclaran personas sin empleo actual con ocupacion reportada.
   Se incorporo `OCU500` a la capa intermedia y el notebook ahora filtra a `ocu500 == 1` antes de calcular coberturas y perfiles.

3. El bloque de `personas` en `generar_reporte_html.py` tenia invertido `P507` para `1` y `6`.
   ENAHO define `1 = empleador o patrono` y `6 = trabajador del hogar`.
   Se corrigio el mapping de categorias en ese bloque.

## Impacto de las correcciones

- Exposicion media 2024: paso de `26.5%` a `27.2%`.
- Alta exposicion 2024: paso de `14.5%` a `14.9%`.
- Cobertura 2024 del cruce CNO x indice: paso de `69.8%` a `96.9%` del empleo ocupado.
- Trabajadores cubiertos 2024: `17.66 millones`.
- Ocupaciones observadas / emparejadas 2024: `401 / 379`.

## Variables auditadas

### Demografia

- `P207` (`sexo`): consistente con ENAHO.
  Valores observados: `1 = Hombre`, `2 = Mujer`.
- `P208A` (`edad`): consistente con ENAHO.
  En la base ocupada 2024 auditada, el rango observado va de `14` a `98` anos.
- `P301A` (`educacion`): tenia error y fue corregido.

### Categoria ocupacional

- `P507`: consistente en la capa anual y corregido en el HTML para perfiles de persona.
  Valores oficiales: `1 Empleador o patrono`, `2 Trabajador independiente`, `3 Empleado`, `4 Obrero`, `5 Trabajador familiar no remunerado`, `6 Trabajador del hogar`, `7 Otro`.

### Ingresos

- La estandarizacion `P523 -> ingreso mensual` es correcta:
  `1 diario x 30`, `2 semanal x 4.33`, `3 quincenal x 2`, `4 mensual`.
- No aparecieron atipicos graves por conversion:
  en 2024 no hay casos por encima de `S/ 50,000` mensuales;
  solo hay `3` casos por encima de `S/ 20,000`, con peso agregado muy bajo (`0.022%` del empleo con ingreso reportado).
- No se aplico winsorizacion porque la cola extrema es pequena y no parece un error sistematico de conversion.

### Pesos muestrales

- La capa ocupada ENAHO usa `FAC500A`.
- En la base procesada `2019-2024` no se encontraron pesos faltantes ni no positivos para los ocupados.
- Los totales ponderados de ocupados por ano quedan en el orden esperado:
  `2019: 17.32M`, `2020: 15.07M`, `2021: 17.31M`, `2022: 18.00M`, `2023: 18.02M`, `2024: 18.23M`.

## Cobertura del cruce CNO

- El problema principal ya no es falta de codigo ocupacional, sino ocupaciones observadas en ENAHO que todavia no tienen score en el indice IA.
- En 2024 quedan `22` codigos CNO observados fuera del indice.
- Los mas grandes por empleo ponderado son:
  `4419 Otro personal de apoyo administrativo` (`~305 mil`)
  `0220 Suboficiales de la Policia Nacional` (`~73 mil`)
  `7399 Otros artesanos y trabajadores... de madera/papel/textiles/cuero` (`~51 mil`)
  `3439 Otros profesionales tecnicos en actividades culturales y artisticas` (`~44 mil`)
- Este gap no se corrigio aqui porque no es un error de codigo ni de merge: faltan scores ocupacionales en el indice fuente.

## Auditoria de notebooks anuales finales

- Los notebooks anuales `2019-2024` fueron reconstruidos con un generador final (`build_enaho_exposure_notebook.py`) que lee directamente:
  `enaho_exposure_YYYY_occupation_report.xlsx`,
  `enaho_persona_anual_2019_2024.csv.gz`,
  `resumen_ocupacion_anio.csv.gz`,
  `epen_persona_departamentos_anual_2022_2025.csv.gz`,
  `ocupacion_crosswalk_4d.csv`.
- Se elimino el grafico antiguo `ocupaciones, exposicion IA y sustitucion`.
  El mapa ocupacional anual ahora usa:
  `X = exposicion media`,
  `Y = tamano del empleo`,
  `color = proporcion de mujeres`,
  igual que el HTML maestro.
- Se retiraron referencias a `piloto`, lecturas exploratorias y bloques de recomendaciones dentro de los notebooks y sus exportaciones HTML.
- Cada notebook anual exporta `21` tablas auxiliares en `outputs/enaho_exposure_YYYY/annual_tables/`.
- Los `6` notebooks ejecutan sin errores en `nbconvert`.

## Coherencia entre HTML maestro, notebooks y tablas

- Se compararon los KPIs anuales del bloque `EVOLUTION` del HTML maestro contra:
  la hoja `coverage` de cada reporte anual y
  los `audit_summary_YYYY.json` exportados por los notebooks.
- Resultado:
  `media_exposicion`, `cobertura` y `pct_alta` coinciden exactamente en los `6` anos auditados (`diferencia absoluta = 0.0000` en todos los casos).
- Conteo de ocupaciones sin score IA por ano:
  `2019: 24`, `2020: 20`, `2021: 21`, `2022: 23`, `2023: 22`, `2024: 22`.
- Casos con ingreso mensual mayor a `S/ 50,000` en los microdatos armonizados:
  `0` en todos los anos `2019-2024`.
- El bloque departamental queda activo para `2022-2024` y muestra nota metodologica de no disponibilidad para `2019-2021`, consistente con la cobertura temporal de EPEN usada en este proyecto.

## Archivos corregidos

- `Proyecto_IA_Empleo_2026/scripts/build_enaho_complete_multiyear.py`
- `Proyecto_IA_Empleo_2026/scripts/build_enaho_exposure_notebook.py`
- `Proyecto_IA_Empleo_2026/scripts/generate_enaho_exposure_year_reports.py`
- `generar_reporte_html.py`
- `reporte_ia_empleo_peru_2019_2024.html`

## Salidas regeneradas

- `Proyecto_IA_Empleo_2026/data/intermediate/enaho_complete_years/ENAHO_complete_2019_2024.csv`
- `Proyecto_IA_Empleo_2026/outputs/enaho_exposure_2019/` a `.../enaho_exposure_2024/`
- `Proyecto_IA_Empleo_2026/notebooks/enaho_exposure/03_enaho_exposure_2019.ipynb` a `...2024.ipynb`
- `Proyecto_IA_Empleo_2026/outputs/html/enaho_exposure/03_enaho_exposure_2019.html` a `...2024.html`
- `reporte_ia_empleo_peru_2019_2024.html`

## Fuentes oficiales consultadas

- INEI, `Diccionario_2024.pdf`:
  `P301A` en modulo 300 y 500.
  URL: `https://proyectos.inei.gob.pe/iinei/srienaho/Descarga/DocumentosMetodologicos/2024-55/20_Diccionario_2024.pdf`
- INEI, `Diccionario_2024.pdf`:
  `P507`, `P510`, `P523`, `P524A1`.
  URL: `https://proyectos.inei.gob.pe/iinei/srienaho/Descarga/DocumentosMetodologicos/2024-55/20_Diccionario_2024.pdf`
- INEI, `16_Relaciones-Logicas-Enaho01A.pdf`:
  validaciones de `P301`.
  URL: `https://proyectos.inei.gob.pe/iinei/srienaho/Descarga/DocumentosMetodologicos/2024-55/16_Relaciones-Logicas-Enaho01A.pdf`
