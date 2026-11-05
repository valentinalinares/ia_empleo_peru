# Actualizacion reproducible del reporte 2025

## Alcance

Los productos 2025 se regeneraron desde la base intermedia completa
`_interno/bases/intermedias/enaho_complete_years/ENAHO_complete_2025.csv`, usando
el generador anual del proyecto sobre `main` actualizado. Ninguno de estos cambios
proviene de la correccion de codigos de ocupacion EPEN: corresponden a completar la
ejecucion ENAHO 2025 y a propagar sus resultados al reporte maestro.

## Archivos y motivo del cambio

| Archivo | Cambio | Motivo |
| --- | --- | --- |
| `annual_tables/audit_2025.csv` | Se incorporan los casos auditados de ingresos altos. | La ejecucion completa detecta seis observaciones sobre S/ 20 000; la salida anterior estaba vacia. |
| `annual_tables/audit_summary_2025.json` | Se actualizan los conteos del control de auditoria. | Resume los seis casos encontrados por la ejecucion completa. |
| `annual_tables/income_scatter_2025.csv` | Se generan 69 filas de ocupaciones. | La salida anterior solo contenia la cabecera. |
| `annual_tables/personas_2025.csv` | Se regeneran los perfiles de personas. | Propaga la base ENAHO 2025 completa a los cortes demograficos. |
| `annual_tables/regional_2025.csv` | Se regeneran los resultados regionales. | Propaga la base ENAHO 2025 completa al corte territorial. |
| `annual_tables/stats_spearman_2025.csv` | Se recalculan las correlaciones. | Usa ingresos y exposicion disponibles en la ejecucion completa. |
| `notebooks/ia_empleo_peru_2025.ipynb` | Se vuelve a ejecutar el cuaderno anual. | Deja celdas, tablas y graficos sincronizados con las salidas regeneradas. |
| `notebooks/htmls/2025.html` | Se vuelve a exportar el cuaderno ejecutado. | Publica la version legible del analisis anual actualizado. |
| `reporte_ia_empleo_peru_2019_2025.html` | Se regenera el reporte maestro y se agrega la advertencia EPEN. | Incorpora 2025 completo y comunica que la tendencia EPEN 2023-2025 debe mostrarse como rango por la sensibilidad a factores faltantes. |

## Separacion de procedencia

- **Correccion de codigos EPEN:** no genera ninguno de los cambios enumerados en
  este documento.
- **Generador ENAHO 2025 mas completo:** genera las seis tablas auxiliares, el
  cuaderno anual y su HTML.
- **Analisis de sensibilidad EPEN:** solo agrega la advertencia metodologica al
  reporte maestro; no modifica bases ni tablas 2025.

El reporte maestro aclara que la advertencia afecta al contraste EPEN 2023-2025 y
no a la serie ENAHO 2019-2025.
