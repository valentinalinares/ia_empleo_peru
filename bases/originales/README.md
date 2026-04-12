# Bases originales

Esta carpeta forma parte del bundle local `ia_empleo_peru`, pero en GitHub no se versionan los microdatos crudos completos porque Git sigue los `junctions` como archivos reales y el volumen supera lo razonable para un repo de publicacion.

## Estructura local

- `enaho/`: microdatos originales ENAHO usados en el pipeline.
- `epen/`: microdatos originales EPEN usados en el bloque departamental.

## Estado en el repo Git

- En la carpeta local, `enaho/` y `epen/` siguen disponibles mediante `junctions`.
- En la version para GitHub, esas subcarpetas quedan excluidas del commit.
- La replica publicable conserva:
  - scripts,
  - notebooks,
  - HTML,
  - tablas auxiliares,
  - capas procesadas,
  - capas intermedias,
  - referencias e indice IA.

## Fuente institucional

Los microdatos originales provienen del INEI y deben recuperarse desde las descargas oficiales correspondientes a ENAHO y EPEN o desde la copia local del proyecto fuente.
