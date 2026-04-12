# ia_empleo_peru

Carpeta ordenada para el reporte de IA y empleo en Peru.

## Que contiene

- `html/`: reporte maestro `reporte_ia_empleo_peru_2019_2024.html`.
- `notebooks/enaho_exposure/`: notebooks ejecutados por ano con el mismo enfoque del HTML y mas detalle por componente.
- `notebooks_html/enaho_exposure/`: exportaciones HTML de esos notebooks por ano.
- `outputs/`: reportes Excel anuales usados por el HTML y tablas auxiliares exportadas por cada notebook anual.
- `bases/procesadas/`: capas procesadas que alimentan el HTML.
- `bases/intermedias/enaho_complete_years/`: base ENAHO anual por ano usada para los notebooks.
- `bases/originales/enaho/` y `bases/originales/epen/`: microdatos originales INEI.
- `referencias/`: indice IA y referencias CNO/equivalencias.
- `scripts/`: scripts fuente relevantes del pipeline.
- `docs/`: auditoria y notas metodologicas.

## Nota sobre espacio

Para no duplicar gigas de microdatos, estas rutas se dejaron como `junctions`:

- `bases/originales/enaho`
- `bases/originales/epen`
- `bases/intermedias/enaho_complete_years`
- `referencias/cno`
- `referencias/equivalencias`

Eso significa que desde esta carpeta puedes navegar todo en un solo lugar, pero los archivos siguen apuntando a la capa fuente ya existente en `Proyecto_IA_Empleo_2026`.

## Nota para GitHub

La carpeta local mantiene accesos a las bases originales mediante `junctions`. Para una publicacion Git razonable, el repo deja documentadas esas rutas pero no versiona los microdatos crudos completos de `bases/originales/`, porque Git los sigue como archivos reales y el volumen deja de ser manejable.

## Punto de partida recomendado

1. Abre `html/reporte_ia_empleo_peru_2019_2024.html`.
2. Revisa `docs/auditoria_reporte_2026-04-11.md`.
3. Si quieres desagregados por ano, abre `notebooks/enaho_exposure/03_enaho_exposure_YYYY.ipynb` o su version HTML en `notebooks_html/enaho_exposure/`.
