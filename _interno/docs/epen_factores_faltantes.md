# Diagnóstico de `FAC300_ANUAL` faltante en EPEN 2022-2025

## Alcance

Este diagnóstico es descriptivo. No imputa factores, no excluye observaciones,
no cambia el universo y no modifica la base procesada. La base conserva la
huella SHA-256
`b71df3ff8fa2e2702dd11eed511aa9dd36ac5d3066c5d7b0735bd958229a7800`
antes y después de ejecutar el análisis.

El script reproducible es
`_interno/scripts/diagnosticar_factores_faltantes.py`. Las tablas completas se
guardan en `_interno/outputs/diagnostico_factores/`.

## Fuentes oficiales revisadas

| Año | Documento | Páginas utilizadas |
|---:|---|---|
| 2022 | `data/raw/inei_docs/epen_departamentos/2022/156/Diccionario.pdf` | 2: área, estrato, llave panel y muestra; 7: residencia; 8: `DIVISION_LIMA` y `FAC300_ANUAL` |
| 2022 | `data/raw/inei_docs/epen_departamentos/2022/156/Ficha_Tecnica.pdf` | 4: población objetivo; 6: diseño y panel; 16: ajuste mensual de la transición |
| 2023 | `data/raw/inei_docs/epen_departamentos/2023/156/Diccionario.pdf` | 2: identificadores; 13: residencia y `FAC_T300` |
| 2023 | `data/raw/inei_docs/epen_departamentos/2023/156/Ficha_Tecnica.pdf` | 4: población objetivo; 6: diseño y panel |
| 2024 | `data/raw/inei_docs/epen_departamentos/2024/156/Diccionario.pdf` | 2: identificadores; 13: residencia, `DIVISION_LIMA`, `FAC_T300` y `FAC300_ANUAL` |
| 2024 | `data/raw/inei_docs/epen_departamentos/2024/156/Ficha_Tecnica.pdf` | 4: población objetivo; 6: diseño y panel |
| 2025 | `data/raw/inei_docs/epen_departamentos/2025/156/Diccionario.pdf` | 2: identificadores; 13: residencia, `DIVISION_LIMA` y `FAC_T300` |
| 2025 | `data/raw/inei_docs/epen_departamentos/2025/156/Ficha_Tecnica.pdf` | 4: población objetivo; 6: diseño y panel |

El diccionario disponible para 2025 está rotulado “4to. trimestre
Oct-Nov-Dic 2025”; no se lo presenta como diccionario anual.

## Resultado principal

Los 23.290 ocupados sin `FAC300_ANUAL` ya vienen sin factor en los ZIP
originales del módulo 76. El procesamiento reproduce exactamente los conteos
originales:

| Año | Ocupados | Sin factor | Porcentaje |
|---:|---:|---:|---:|
| 2022 | 192.416 | 0 | 0,00% |
| 2023 | 196.595 | 1.113 | 0,57% |
| 2024 | 200.630 | 7.778 | 3,88% |
| 2025 | 207.407 | 14.399 | 6,94% |
| **Total** | **797.048** | **23.290** | **2,92%** |

La falta no es exclusiva de los ocupados. En toda la población del módulo hay
620.495 filas sin factor. Una parte grande corresponde a personas sin código
`OCUP300`, pero desde 2023 también hay faltantes entre ocupados, desempleados
abiertos, desempleados ocultos e inactivos. Véanse
`resumen_origen.csv` y `faltantes_condicion_actividad.csv`.

## Patrón temporal

- En 2022 no hay ocupados sin factor.
- En 2023 los faltantes se concentran en julio-septiembre: 319, 372 y 422.
- En 2024 aparecen de abril a diciembre y aumentan desde 571 en abril hasta
  1.148 en diciembre.
- En 2025 aparecen en todos los meses, entre 1.047 y 1.295 por mes.

El patrón es progresivo por año y periodo, no una pérdida aleatoria introducida
al construir la base. Los detalles y denominadores están en
`faltantes_anio_mes.csv`.

## Territorio, muestra y estrato

Los faltantes aparecen en 24 códigos departamentales; `CCDD=07` no existe en
estos archivos. `CCDD=15` contiene 514 casos en 2023, 2.790 en 2024 y 5.923 en
2025. La cifra previa de 2.790 se reconcilia exactamente con 2024,
`CCDD=15` y `DIVISION_LIMA=1`.

El diccionario define `DIVISION_LIMA=1` como “Provincia de Lima - Incluye la
Provincia Constitucional del Callao” y `2` como “Región de Lima”. Por ello no
es posible separar Lima Metropolitana de Callao con estas variables. No se
presenta una desagregación inventada.

Los faltantes están presentes en varias muestras. La muestra 1 reúne 12.247
casos (52,6% del total), pero no es el único grupo afectado. Por estrato, los
códigos 1, 2 y 3 reúnen 23.147 casos; hay 93 en el estrato 4 y 50 con estrato
vacío en 2025. No aparecen faltantes en los estratos 5-8.

Las tablas de respaldo son `faltantes_region.csv`,
`faltantes_lima_callao.csv`, `faltantes_muestra.csv` y
`faltantes_estrato.csv`.

## Área y perfil demográfico

Todos los 23.290 ocupados sin factor son urbanos (`AREA=1`) y residentes
habituales (`RESIDENT=1`). Todos tienen `LLAVE_PANEL` informada.

Por sexo hay 12.692 hombres (54,5%) y 10.598 mujeres (45,5%). Por edad, 14.219
casos tienen 25-44 años, 4.938 tienen 45-64, 3.588 tienen 14-24 y 545 tienen 65
o más. Estos conteos describen los faltantes; no deben interpretarse como
estimaciones poblacionales porque precisamente carecen de peso.

Véanse `faltantes_area.csv`, `faltantes_sexo.csv`, `faltantes_edad.csv` y
`residencia_panel.csv`.

## Nivel al que ocurre el faltante

El faltante no afecta a personas sueltas dentro de hogares o viviendas con
factor:

| Nivel | Unidades completas sin factor | Personas sin factor en ellas | Unidades mixtas | Personas sin factor en unidades mixtas |
|---|---:|---:|---:|---:|
| Hogar | 13.666 | 23.290 | 0 | 0 |
| Vivienda | 13.478 | 23.290 | 0 | 0 |
| Conglomerado | 73 | 147 | 9.716 | 23.143 |

Por tanto, todos los ocupados faltantes pertenecen a hogares y viviendas
completos sin factor. La mayoría está en conglomerados que también contienen
otras viviendas con factor. Véase `integridad_unidades.csv`.

## Residencia, panel y visita

Los diccionarios documentan:

- `LLAVE_PANEL`, “Llave panel”, en la página 2 de los cuatro diccionarios.
- `RESIDENT`, “Residente habitual”, en la página 7 del diccionario 2022 y la
  página 13 de los diccionarios 2023-2025.
- `MUESTRA`, “Muestra”, en la página 2 de los cuatro diccionarios.

Las fichas técnicas definen como población objetivo a los residentes habituales
de viviendas particulares (página 4) y señalan que hay UPM de panel y no panel
(página 6). No se encontró una variable explícita de rotación, número de visita
o condición panel/no panel en los CSV. `LLAVE_PANEL` no se decodifica porque el
diccionario no documenta su estructura.

Todos los ocupados sin factor tienen `RESIDENT=1` y una `LLAVE_PANEL` no vacía.
Esto descarta que el faltante se explique simplemente por no residencia o por
ausencia de llave, pero no permite atribuirlo a una ronda o rotación concreta.

## Visitas repetidas del panel dentro del año

Para enlazar hogares sin interpretar la estructura interna de `LLAVE_PANEL`, se
definió cada visita mediante año, mes, muestra, región, conglomerado, vivienda
y hogar, todos con sus códigos originales. Luego se usó como identificador
longitudinal la `LLAVE_PANEL` de la persona marcada como jefe del hogar
(`C203=1`). Todos los hogares con ocupados tuvieron exactamente un jefe y una
llave de jefe en cada visita.

El universo continúa siendo el de ocupados. “Personas” cuenta llaves de persona
únicas; “filas persona” cuenta observaciones mensuales, por lo que una misma
persona puede aparecer dos veces.

| Año | Hogares con alguna visita sin factor | Con otra visita con factor | Sin otra visita con factor | Personas únicas sin factor | Filas persona sin factor |
|---:|---:|---:|---:|---:|---:|
| 2022 | 0 | 0 | 0 | 0 | 0 |
| 2023 | 617 | 0 | 617 | 1.113 | 1.113 |
| 2024 | 3.405 | 0 | 3.405 | 6.087 | 7.778 |
| 2025 | 5.701 | 0 | 5.701 | 10.203 | 14.399 |

No se encontró ningún hogar enlazado que tuviera una visita sin factor y otra
con factor en el mismo año. Por tanto, en estos datos no hay casos para
clasificar la visita con factor como primera, última u otra; las tres categorías
quedan en cero. Esto no prueba una regla general de asignación del factor: solo
describe los enlaces observables con una misma llave de jefe dentro de cada año.
Un cambio de jefe puede producir una llave distinta y no se fuerza un enlace
entre esos casos.

La distribución de visitas anuales fue:

| Año | Estado del hogar | 1 visita | 2 visitas |
|---:|---|---:|---:|
| 2022 | Solo con factor | 29.580 | 40.305 |
| 2023 | Solo con factor | 28.534 | 41.625 |
| 2023 | Solo sin factor | 617 | 0 |
| 2024 | Solo con factor | 28.956 | 41.821 |
| 2024 | Solo sin factor | 2.296 | 1.109 |
| 2025 | Solo con factor | 29.652 | 42.321 |
| 2025 | Solo sin factor | 2.867 | 2.834 |

No hubo hogares con más de dos visitas enlazadas en un año ni hogares con una
mezcla de visitas con y sin factor. Los resultados reproducibles, incluidos los
ceros de posición, están en `visitas_panel.csv`.

## Otros factores

La inspección de todas las columnas de los cuatro ZIP encuentra una sola
variable cuyo nombre corresponde a un factor o peso: `FAC300_ANUAL`. Ninguna
fila sin factor anual dispone de otro factor en esos CSV.

Hay una discrepancia documental:

- El diccionario 2022 documenta `FAC300_ANUAL` en la página 8.
- El diccionario 2023 documenta `FAC_T300` en la página 13, pero ese campo no
  está en el CSV; el CSV sí contiene `FAC300_ANUAL`.
- El diccionario 2024 documenta `FAC_T300` y `FAC300_ANUAL` en la página 13,
  pero el CSV solo contiene `FAC300_ANUAL`.
- El diccionario 2025 documenta `FAC_T300` en la página 13, pero ese campo no
  está en el CSV; el CSV sí contiene `FAC300_ANUAL`.

Por ello no existe en los archivos disponibles un factor trimestral, mensual o
alternativo que pueda siquiera evaluarse para estas 23.290 filas.
`variables_factor.csv` deja este resultado reproducible.

## Qué dice la documentación oficial

Se revisaron las fichas técnicas y los diccionarios almacenados en
`data/raw/inei_docs/epen_departamentos/<año>/156/`.

Las fichas 2022-2025 describen la población objetivo en la página 4 y el diseño
estratificado, probabilístico, de áreas, bietápico e independiente en cada
departamento en la página 6. La ficha 2022, página 16, menciona un factor de
ajuste mensual usado para empalmar indicadores durante la transición, pero no
define `FAC300_ANUAL` a nivel de persona.

Ninguna de las cuatro fichas ni de los cuatro diccionarios especifica:

- a qué registros se asigna `FAC300_ANUAL`;
- por qué puede quedar vacío;
- si los vacíos identifican una muestra, panel, visita o etapa de procesamiento;
- qué otro factor debe usarse en su lugar.

El origen administrativo del faltante queda confirmado, pero su motivo no se
puede determinar con la documentación disponible.

## Opciones

Estas alternativas se presentan sin elegir una:

1. **Mantener las filas sin peso.** Preserva todos los registros y hace visible
   el problema. No permite que esas filas contribuyan a estimaciones ponderadas
   y exige reportar su exclusión efectiva de cada estimador.
2. **Excluirlas explícitamente del universo analítico ponderado.** Produce una
   regla clara y evita pesos nulos implícitos. Puede sesgar resultados porque el
   faltante crece en el tiempo, es exclusivamente urbano y se concentra por
   territorio y estrato.
3. **Solicitar al INEI una base o aclaración corregida.** Es la única vía que
   puede establecer si falta un factor válido y cuál corresponde. Depende de
   una respuesta externa y puede retrasar el análisis.
4. **Usar otro factor oficial.** Solo sería defendible si el INEI entrega el
   campo alternativo y documenta su universo y periodicidad. No es aplicable
   con los ZIP actuales, porque no contienen otro factor.
5. **Imputar un factor.** Mantendría las filas en estimaciones, pero introduciría
   supuestos no respaldados y podría alterar totales y varianzas. No se
   recomienda sin una regla oficial y una validación metodológica independiente.

La decisión debe tomarse después de aclarar con el INEI la asignación del factor
y de evaluar sensibilidad por año, mes, territorio y estrato.
