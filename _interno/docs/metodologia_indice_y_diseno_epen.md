# Metodología del índice de exposición y diseño muestral EPEN

## Dos versiones que deben distinguirse

### Antecedente publicado

Manky (2025) construye índices de exposición a automatización tradicional y a
inteligencia artificial generativa a partir de las tareas del Clasificador
Nacional de Ocupaciones 2015 (CNO-2015). El estudio fue publicado por el INEI
y es el antecedente metodológico público de este proyecto:

> Manky, W. O. (2025). *Doble desafío tecnológico: análisis de la exposición
> a la automatización tradicional y a la inteligencia artificial generativa
> en el empleo peruano, utilizando datos de la ENAHO 2024*. Instituto Nacional
> de Estadística e Informática.

- Publicación oficial: <https://www.gob.pe/institucion/inei/informes-publicaciones/7453406-doble-desafio-tecnologico-analisis-de-la-exposicion-a-la-automatizacion-tradicional-y-a-la-inteligencia-artificial-generativa-en-el-empleo-peruano-utilizando-datos-de-la-enaho-2024>
- Ficha bibliográfica del autor: <https://omarmanky.com/publicaciones/2025-doble-desafio-tecnologico/>

El informe publicado utiliza categorías discretas por tarea, cuatro corridas
independientes y una regla conservadora para resolver empates. Sus puntajes no
son intercambiables con los utilizados actualmente por este repositorio.

### Corrida actual del proyecto

Los resultados de este repositorio usan una nueva corrida realizada por
**Valentina Linares Herrera y Walter Omar Manky Bonilla** con **Claude Sonnet
4.6 (Anthropic)** sobre las tareas del CNO-2015. Esta versión:

- conserva un score continuo de exposición por tarea y por ocupación;
- distingue aumento (`A`), sustitución (`S`) e impacto nulo (`N`);
- deja sin asignación las clasificaciones ambiguas o discrepantes;
- marca los empates en vez de resolverlos asignando una categoría;
- agrega los resultados por ocupación mediante
  `mean_exposure_score`, conservando mediana y dispersión para sensibilidad.

Por ello debe describirse como una **actualización del enfoque publicado por
Manky (2025)** y no como “el índice publicado por el INEI”. La fuente de datos
que usa el pipeline es
`_interno/referencias/indices/anthropic-claude-sonnet-4-6_exposure_index.xlsx`.

Descripción recomendada para informes:

> Los puntajes utilizados constituyen una nueva corrida de la clasificación de
> tareas del CNO-2015, realizada por Valentina Linares Herrera y Walter Omar
> Manky Bonilla con Claude Sonnet 4.6. La corrida actualiza el enfoque
> desarrollado por Manky (2025), conserva un score continuo y aplica reglas
> revisadas para empates, ambigüedades y tipo de exposición. En consecuencia,
> sus valores no son idénticos a los publicados originalmente por el INEI.

Referencia de la corrida actual como material de trabajo:

> Linares Herrera, V., y Manky Bonilla, W. O. (2026). *Índice de exposición a
> inteligencia artificial generativa para ocupaciones peruanas: corrida
> Claude Sonnet 4.6*. Material de trabajo no publicado.

## Qué publica el INEI sobre el diseño EPEN

Las fichas técnicas EPEN 2023-2025 documentan un diseño probabilístico,
estratificado, de áreas y bietápico, independiente en cada departamento. La
primera etapa selecciona conglomerados sistemáticamente con probabilidad
proporcional al número de viviendas y la segunda selecciona segmentos o
viviendas sistemáticamente con arranque aleatorio. La encuesta combina
muestras panel y no panel.

Fuentes oficiales:

- EPEN 2023: <https://proyectos.inei.gob.pe/iinei/srienaho/Descarga/DocumentosMetodologicos/2023-156/Ficha_Tecnica.pdf>
- EPEN 2024: <https://proyectos.inei.gob.pe/iinei/srienaho/Descarga/DocumentosMetodologicos/2024-156/Ficha_Tecnica.pdf>
- EPEN 2025: <https://proyectos.inei.gob.pe/iinei/srienaho/Descarga/FichaTecnica/969-Ficha.pdf>
- Diccionario EPEN 2022: <https://www.inei.gob.pe/media/DATOS_ABIERTOS/EPEN_DEP/DICCIONARIO/2022/Diccionario.pdf>
- Diccionario EPEN 2024: <https://proyectos.inei.gob.pe/iinei/srienaho/Descarga/DocumentosMetodologicos/2024-156/Diccionario.pdf>

Los diccionarios identifican `CCDD`, `AREA`, `ESTRATO`, `CONGLOMERADO`,
`MUESTRA`, `LLAVE_PANEL` y `FAC300_ANUAL`. La auditoría de los microdatos del
proyecto muestra además que la UPM no puede identificarse mediante
`cluster_id` solo: los números de conglomerado se reutilizan entre
departamentos. La clave operativa mínima es `sample_id + region_code +
cluster_id`, manteniendo los identificadores como texto para conservar ceros a
la izquierda.

## Qué no está especificado públicamente

La documentación localizada no proporciona una receta completa para
reproducir exactamente las varianzas oficiales de la EPEN anual. En
particular, no confirma:

- la combinación operativa de variables que forma el estrato de varianza;
- el identificador de UPM usado al acumular meses y visitas panel;
- el tratamiento de las visitas repetidas en la estimación anual;
- el estimador de varianza, las UPM de inclusión forzosa, los estratos con una
  sola UPM y las correcciones de población finita;
- las etapas finales de calibración de `FAC300_ANUAL`;
- el tratamiento oficial de los registros sin `FAC300_ANUAL`.

La ficha EPEN de Lima Metropolitana y Callao sí documenta el peso base como el
inverso de las probabilidades de selección y un ajuste por falta de respuesta
en la UPM, pero no describe toda la construcción del factor anual nacional:
<https://proyectos.inei.gob.pe/iinei/srienaho/Descarga/FichaTecnica/787-Ficha.pdf>.

## Uso recomendado sin una especificación adicional del INEI

1. Para estimaciones puntuales, usar `FAC300_ANUAL` y mantener separados los
   análisis de sensibilidad de las filas sin factor.
2. Para inferencia, declarar explícitamente que los errores estándar son una
   aproximación basada en el diseño público, no errores oficiales del INEI.
3. Usar como especificación inicial una UPM compuesta por `sample_id +
   region_code + cluster_id`, peso `FAC300_ANUAL` y estratos candidatos que
   combinen región, área y `strata_code`.
4. Contrastar variantes que agreguen `sample_id` o periodo y validarlas contra
   los errores estándar, coeficientes de variación y efectos de diseño
   publicados por el INEI.
5. Reportar sensibilidad entre especificaciones cuando ninguna reproduzca de
   manera estable los resultados oficiales.

Informes oficiales útiles como puntos de contraste:

- Abril-junio 2023: <https://proyectos.inei.gob.pe/iinei/srienaho/Descarga/DocumentosMetodologicos/2023-39/Error_Muestral_por_Trimestre.pdf>
- Enero-marzo 2024: <https://proyectos.inei.gob.pe/iinei/srienaho/Descarga/DocumentosMetodologicos/2024-36/Error_Muestral_por_Trimestre.pdf>

Esta validación empírica puede producir errores estándar defendibles y
reproducibles, pero no demuestra que la especificación elegida sea idéntica al
algoritmo interno del INEI.
