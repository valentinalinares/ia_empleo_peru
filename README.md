# ia_empleo_peru

Carpeta de entrega ordenada para presentación y preparada para funcionar desde esta misma carpeta con rutas relativas.

## Qué queda visible

- `reporte_ia_empleo_peru_2019_2025.html`: reporte maestro final para 2019-2025.
- `notebooks/`: notebooks anuales por año.
- `notebooks/htmls/`: versión HTML de cada notebook anual, nombrada solo por año.

## Notebooks

- `ia_empleo_peru_2019.ipynb`
- `ia_empleo_peru_2020.ipynb`
- `ia_empleo_peru_2021.ipynb`
- `ia_empleo_peru_2022.ipynb`
- `ia_empleo_peru_2023.ipynb`
- `ia_empleo_peru_2024.ipynb`
- `ia_empleo_peru_2025.ipynb`

## HTML de notebooks

- `notebooks/htmls/2019.html`
- `notebooks/htmls/2020.html`
- `notebooks/htmls/2021.html`
- `notebooks/htmls/2022.html`
- `notebooks/htmls/2023.html`
- `notebooks/htmls/2024.html`
- `notebooks/htmls/2025.html`

## Sobre el prefijo `03`

El `03_` venía de una convención interna del pipeline por etapas.
No significaba una versión mejor ni peor del archivo.
Para esta carpeta de presentación se quitó porque solo metía ruido.

## Carpeta interna

`_interno/` guarda el soporte técnico y metodológico necesario para rerun del bundle:

- bases
- scripts
- salidas auxiliares
- referencias
- auditoría
- insumos intermedios para los notebooks y el HTML maestro

Eso se dejó fuera de la vista principal para que la carpeta sea más limpia al presentarla.

## Metodología y autoría del índice

El índice y la nueva corrida usada por los reportes fueron desarrollados por
Walter Omar Manky Bonilla, con la asistencia de investigación de Valentina
Linares Herrera, usando Claude Sonnet 4.6. La corrida se realizó en abril de
2026 y su paquete metodológico fue versionado el 15 de junio de 2026. Es una
actualización metodológica del trabajo publicado por Manky (2025), no una
reproducción de los puntajes publicados por el INEI. Conserva un score continuo
y aplica reglas revisadas para empates, ambigüedades y tipo de exposición.

La procedencia del índice, su relación con la publicación oficial y la
documentación pública disponible sobre el diseño EPEN se detallan en
[`_interno/docs/metodologia_indice_y_diseno_epen.md`](_interno/docs/metodologia_indice_y_diseno_epen.md).
