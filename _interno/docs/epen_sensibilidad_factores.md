# Sensibilidad a factores de expansión faltantes en la EPEN

## Alcance y reproducibilidad

Este análisis usa la base de personas ocupadas EPEN 2022-2025 sin modificarla. Su SHA-256 al inicio y al final fue `b71df3ff8fa2e2702dd11eed511aa9dd36ac5d3066c5d7b0735bd958229a7800`. Los indicadores de exposición se enlazan por `occupation_code_4d` con el índice Sonnet del proyecto.

## 1. Contraste con cifras oficiales

| Año | Oficial | Suma FAC300_ANUAL | Diferencia | Diferencia % |
| --- | --- | --- | --- | --- |
| 2022 | 17 336 500 | 17 336 509.7 | 9.7 | 0.000056 |
| 2023 | 17 179 800 | 17 179 796.2 | -3.8 | -0.000022 |
| 2024 | 17 322 900 | 17 322 935.8 | 35.8 | 0.000206 |
| 2025 | 17 575 200 | 17 575 150.0 | -50.0 | -0.000284 |

Las diferencias son solo de redondeo. La suma de los factores válidos ya reproduce el total oficial incluso en 2023-2025, cuando existen filas sin `FAC300_ANUAL`.

Fuentes oficiales verificadas:

- 2022: [Peru: Indicadores del Mercado Laboral a nivel departamental y de principales ciudades, 2022](https://www.inei.gob.pe/media/MenuRecursivo/publicaciones_digitales/Est/Lib1905/libro.pdf), p. 42, Cuadro 3.1: 17 336 500 personas ocupadas.
- 2023: [Peru: Comportamiento de los Indicadores del Mercado Laboral a Nivel Nacional y en 26 Ciudades](https://www.inei.gob.pe/media/MenuRecursivo/boletines/epen-nacional-ivt2023.pdf), p. 13, Cuadro 1.6A: 17 179 800 personas ocupadas.
- 2024: [Peru: Comportamiento de los Indicadores del Mercado Laboral a Nivel Nacional y en 27 Ciudades](https://www.inei.gob.pe/media/MenuRecursivo/boletines/informe-tecnico_empleonacional.pdf), p. 13, Cuadro 1.6A: 17 322 900 personas ocupadas.
- 2025: [Peru: Comportamiento de los Indicadores del Mercado Laboral a Nivel Nacional y en 27 Ciudades](https://www.inei.gob.pe/media/MenuRecursivo/boletines/01-informe-tecnico-empleo-nacional.pdf), p. 10, Cuadro 1.7A: 17 575 200 personas ocupadas.

Los cuatro años cuentan con publicación oficial. El informe 2022 también presenta departamentos (p. 42); los informes anuales 2023-2025 publican el total nacional y ciudades, no una tabla departamental. La comparación departamental 2022 está en `comparacion_cifras_oficiales_departamento_2022.csv`. Para alinear la geografía con `region_code=15`, se sumaron los dominios oficiales Lima Metropolitana y Callao, y provincias de Lima.

## 2. Comparación sin pesos dentro de celdas comparables

Se comparan personas sin y con factor dentro de celdas exactas año × mes × región × área. Las diferencias se combinan con pesos de solapamiento `n0*n1/(n0+n1)`. La prueba es bilateral, con aproximación normal, y la diferencia estandarizada usa la varianza intra-celda combinada. Son pruebas descriptivas: no incorporan el diseño muestral ni corrección por comparaciones múltiples.

| Año | Variable | Media con factor | Media sin factor | DME | p |
| --- | --- | --- | --- | --- | --- |
| 2023 | indice_ia | 0.312 | 0.258 | -0.265 | 0.0000 |
| 2023 | ingreso_mensual | 1 661.949 | 1 492.688 | -0.107 | 0.0000 |
| 2023 | horas_semanales | 39.727 | 44.576 | 0.249 | 0.0000 |
| 2023 | edad | 41.480 | 35.189 | -0.426 | 0.0000 |
| 2024 | indice_ia | 0.309 | 0.264 | -0.222 | 0.0000 |
| 2024 | ingreso_mensual | 1 706.023 | 1 563.408 | -0.091 | 0.0000 |
| 2024 | horas_semanales | 40.260 | 45.565 | 0.279 | 0.0000 |
| 2024 | edad | 41.858 | 36.356 | -0.376 | 0.0000 |
| 2025 | indice_ia | 0.313 | 0.269 | -0.218 | 0.0000 |
| 2025 | ingreso_mensual | 1 813.964 | 1 708.621 | -0.063 | 0.0000 |
| 2025 | horas_semanales | 41.054 | 46.324 | 0.282 | 0.0000 |
| 2025 | edad | 42.134 | 36.668 | -0.373 | 0.0000 |

Mayor diferencia estandarizada por variable categórica:

| Año | Variable | Categoría | DME máxima |
| --- | --- | --- | --- |
| 2023 | gran_grupo_ocupacional | 2 | -0.197 |
| 2023 | nivel_educativo | 6 | 0.174 |
| 2023 | sexo | Hombre | 0.034 |
| 2024 | gran_grupo_ocupacional | 2 | -0.206 |
| 2024 | nivel_educativo | 3 | -0.129 |
| 2024 | sexo | Hombre | 0.023 |
| 2025 | gran_grupo_ocupacional | 2 | -0.200 |
| 2025 | nivel_educativo | 12 | -0.128 |
| 2025 | sexo | Mujer | -0.038 |

El detalle de todos los niveles de gran grupo ocupacional, educación y sexo se conserva en `comparacion_sin_pesos.csv`.

## 3. Sensibilidad de los indicadores

La versión (a) usa únicamente factores válidos. La versión (b) multiplica cada factor válido por `personas totales / personas con factor` dentro de año × mes × región × estrato × área. No se asigna factor a las filas faltantes. `% alta exposición` es la media ponderada de `%_alta_exposicion` del índice ocupacional y se expresa en puntos porcentuales.

| Año | Indicador | Exclusión | Ajuste | Diferencia |
| --- | --- | --- | --- | --- |
| 2023 | exposicion_ia_media | 0.2799 | 0.2803 | 0.0003 |
| 2023 | porcentaje_alta_exposicion | 15.7083 | 15.7482 | 0.0399 |
| 2023 | ingreso_mensual_medio | 1 361.3075 | 1 364.8914 | 3.5839 |
| 2024 | exposicion_ia_media | 0.2794 | 0.2815 | 0.0020 |
| 2024 | porcentaje_alta_exposicion | 15.6523 | 15.8916 | 0.2393 |
| 2024 | ingreso_mensual_medio | 1 448.6322 | 1 471.6660 | 23.0338 |
| 2025 | exposicion_ia_media | 0.2824 | 0.2867 | 0.0043 |
| 2025 | porcentaje_alta_exposicion | 16.0096 | 16.5213 | 0.5117 |
| 2025 | ingreso_mensual_medio | 1 550.4698 | 1 599.0266 | 48.5568 |

Efecto del ajuste sobre la suma de pesos:

| Año | Pesos originales | Pesos ajustados | Aumento % |
| --- | --- | --- | --- |
| 2023 | 17 179 796.2 | 17 309 560.2 | 0.755 |
| 2024 | 17 322 935.8 | 18 214 759.4 | 5.148 |
| 2025 | 17 575 150.0 | 19 438 352.0 | 10.601 |

No hay celdas sin ningún factor válido: quedan 0 personas sin cubrir. El multiplicador máximo es 1.2803. Los resultados completos por región y sexo están en `sensibilidad_indicadores.csv`; las celdas y sus multiplicadores, en `celdas_ajuste_no_respuesta.csv`.

## Limitaciones

- La prueba simple no sustituye inferencia con el diseño muestral completo.
- El ajuste solicitado supone que, condicionando por la celda, las filas con factor representan también a las filas sin factor. Las comparaciones descriptivas pueden cuestionar esa hipótesis, pero no demostrarla.
- Las cifras oficiales están publicadas en centenas; las diferencias pequeñas con la suma de factores reflejan redondeo.

## Recomendación

**Usar la exclusión de filas sin factor como especificación principal y conservar el ajuste solo como sensibilidad.** Los factores válidos ya están calibrados: sus sumas reproducen los totales oficiales de población ocupada. Inflarlos de nuevo con la tasa de respuesta muestral eleva artificialmente la población ponderada y descansa en una hipótesis de representatividad intra-celda que no está documentada por el INEI. Para transparencia, el reporte final puede mostrar el intervalo entre ambas estimaciones, pero no debe presentar la versión ajustada como estimación central.
