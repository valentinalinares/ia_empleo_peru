# Identificadores y variables laborales de EPEN departamentos

## Alcance

Esta reconstrucción usa exclusivamente variables presentes en los ZIP
oficiales del módulo 76 y las contrasta con los diccionarios EPEN de cada año.
No decodifica claves opacas ni asigna a una columna un concepto distinto del
descrito por el INEI.

## Mapeo auditado

| Columna procesada | Variable original | 2022 | 2023 | 2024 | 2025 | Decisión |
|---|---|---:|---:|---:|---:|---|
| `sample_id` | `MUESTRA` | p. 2 | p. 2 | p. 2 | p. 2 | Identificador de muestra. Se exporta de forma explícita para distinguir claves reutilizadas; no se interpreta como dominio estadístico. |
| `strata_code` | `ESTRATO` | p. 2 | p. 2 | p. 2 | p. 2 | Se conserva el estrato poblacional publicado. No constituye por sí solo la especificación completa del diseño muestral. |
| `person_id` | `C201` | p. 2* | p. 2 | p. 2 | p. 2 | Número de orden de la persona. En 2022 el diccionario lo rotula `PERS_NRO`, mientras el CSV lo entrega como `C201`; coincide exactamente con `c300n` en las 192.416 filas ocupadas. |
| `relationship_code` | `C203` | p. 2 | p. 2 | p. 2 | p. 2 | Relación de parentesco con el jefe del hogar. |
| `occupational_category_code` | `C310` | p. 3 | p. 4 | p. 4 | p. 4 | Categoría en la ocupación principal. |
| `firm_size_code` | `C317` | p. 4 | p. 5 | p. 5 | p. 5 | Intervalo de personas que laboran en el negocio o empresa, incluyendo al informante. |
| `income_periodicity_code` | `C338` | p. 4 | p. 6 | p. 6 | p. 6 | Periodicidad del pago en la ocupación principal dependiente. Es esperable que quede vacía para independientes y otros casos fuera de ese bloque. |
| `ubigeo` | No disponible | - | - | - | - | Los CSV contienen `CCDD`, pero no provincia y distrito. `CODCIUDAD` figura en algunos diccionarios, no está en los CSV usados y no equivale a un ubigeo de seis dígitos. Se mantiene en `NA`. |
| `domain_code` | No disponible | - | - | - | - | `MUESTRA` es un identificador de muestra, no un dominio estadístico. Se mantiene en `NA`. |

Los números de página corresponden a los archivos `Diccionario.pdf` de la
operación 156 guardados en
`data/raw/inei_docs/epen_departamentos/<año>/156/`.

## Completitud observada entre ocupados

| Año | Filas | `strata_code` NA | `firm_size_code` NA | `income_periodicity_code` NA |
|---:|---:|---:|---:|---:|
| 2022 | 192.416 | 0 | 1.692 | 94.736 |
| 2023 | 196.595 | 0 | 1.726 | 97.461 |
| 2024 | 200.630 | 0 | 0 | 98.759 |
| 2025 | 207.407 | 261 | 0 | 100.279 |

`sample_id`, `person_id`, `relationship_code` y
`occupational_category_code` no tienen
faltantes entre los ocupados. No se imputan los valores ausentes de las otras
variables.

## Unicidad y dependencias

- `C201` coincide con `c300n`/`C300n` en las 797.048 filas ocupadas.
- La clave persona formada por año, mes, `MUESTRA`, conglomerado, vivienda,
  hogar y `C201` no tiene duplicados. En la salida, `MUESTRA` se conserva como
  `sample_id`, y la clave procesada equivalente también es única.
- Si se omite `MUESTRA`, 690 filas de los datos originales participan en
  colisiones de clave: 100 en 2022, 174 en 2023, 170 en 2024 y 246 en 2025.
  En la base procesada anterior, la clave normalizada sin `sample_id` producía
  700 filas en colisión. La diferencia se debe a que la normalización numérica
  reúne algunas representaciones distintas de los identificadores originales.
- Cada combinación de año, mes, `MUESTRA` y conglomerado tiene un solo valor
  de `ESTRATO`. En 2025 existen 39 códigos de conglomerado que cambian de
  estrato entre meses; el control no debe aplicarse globalmente sin periodo.
- No se puede comprobar un ubigeo de seis dígitos porque el módulo entregado
  no contiene los componentes de provincia y distrito.

Estas comprobaciones son controles de integridad de identificadores. No
sustituyen la especificación oficial de estratos, UPM, factores y dominios que
se necesita para estimar errores estándar.
