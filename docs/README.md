# Documento de Centinela 503

`main.tex` es la fuente de la propuesta académica para CONINFO 2026. El documento
se compila en tamaño carta y actualmente ocupa tres páginas. `main.pdf` es el
resultado de la compilación y `Propuesta.pdf` es una copia para compartir.

## Colores de identidad

La composición del documento debe utilizar exclusivamente esta paleta:

| Color | Código hexadecimal | Uso |
| --- | --- | --- |
| Azul marino | `#173864` | Títulos, encabezados y separadores principales |
| Cian | `#1C88A8` | Iconos, acentos, bordes de recuadros y pies de página |
| Blanco | `#FFFFFF` | Fondo de páginas y recuadros |
| Negro | `#000000` | Texto del contenido |

En `main.tex`, `navy` y `cyan` definen los colores de marca; `ink` es un alias de
`black` y `line` es un alias de `cyan`. No agregar grises ni otros colores a la
composición. Los logos institucionales se insertan desde sus archivos originales.

## Imagotipo y encabezados

- Original editable: [`img/Imagotipo - Centinela 503.svg`](img/Imagotipo%20-%20Centinela%20503.svg).
- Versión vectorial para LaTeX: [`img/logo-centinela.pdf`](img/logo-centinela.pdf).
- `img/logo-centinela.png` es una versión rasterizada disponible, pero el documento
  utiliza el PDF vectorial para mantener la nitidez al ampliar o imprimir.
- El imagotipo sustituye el texto grande «CENTINELA 503» en los encabezados de las
  tres páginas. Está centrado entre los logos de UNAB y de la Facultad.
- La macro `\centinelalogo` conserva la proporción original de `435 × 91`.
  El ancho es de `7.6 cm` en la primera página y `6.2 cm` en las siguientes,
  con `1.5 mm` de separación respecto a los textos contiguos.
- Se conservan los colores originales del SVG. El texto «CENTINELA 503» de los
  pies de página permanece como identificador del documento.

### Regenerar el PDF del imagotipo

Este paso solo es necesario cuando cambia el SVG. La compilación utiliza el PDF
ya generado y no necesita procesar el SVG en cada ejecución.

La conversión se realizó con Python 3, PyGObject, librsvg 2 y Pycairo. Con esas
dependencias disponibles, ejecutar lo siguiente **desde `docs/`**:

```bash
python3 - <<'PY'
import gi
import cairo

gi.require_version('Rsvg', '2.0')
from gi.repository import Rsvg

logo = Rsvg.Handle.new_from_file('img/Imagotipo - Centinela 503.svg')
surface = cairo.PDFSurface('img/logo-centinela.pdf', 435, 91)
surface.restrict_to_version(cairo.PDF_VERSION_1_5)
viewport = Rsvg.Rectangle()
viewport.x, viewport.y = 0, 0
viewport.width, viewport.height = 435, 91
logo.render_document(cairo.Context(surface), viewport)
surface.finish()
PY
```

El resultado mantiene los trazados vectoriales y el fondo transparente. Se limita
a PDF 1.5 para coincidir con la versión del PDF producido por el compilador.
Si cambian las dimensiones del SVG, actualizar las dimensiones de la conversión
para conservar su proporción.

## Compilar `main.tex`

Se utilizó **Tectonic 0.17.0**, que ejecuta XeTeX y genera el PDF mediante
`xdvipdfmx`. Tectonic resuelve las pasadas necesarias del documento. En la primera
compilación puede necesitar acceso a internet para descargar los paquetes y las
fuentes de LaTeX que falten en su caché.

Con `tectonic` instalado y disponible en `PATH`, ejecutar desde la raíz del
repositorio:

```bash
cd docs
tectonic --keep-logs main.tex
cp main.pdf Propuesta.pdf
```

Ejecutar la copia solo si la compilación termina correctamente. Las rutas de las
imágenes son relativas a `docs/`; conservar la carpeta `img/` junto a `main.tex`.
`--keep-logs` conserva `main.log` para consultar errores y advertencias.

### Comando utilizado en este entorno

El ejecutable está en `/tmp/centinela-tectonic/tectonic` y la caché se guarda en
`/tmp/centinela-tectonic/cache`. Desde `docs/`:

```bash
XDG_CACHE_HOME=/tmp/centinela-tectonic/cache /tmp/centinela-tectonic/tectonic --only-cached --keep-logs main.tex
cp main.pdf Propuesta.pdf
```

`--only-cached` permite compilar sin red cuando todos los recursos necesarios ya
están en caché. Si aparece un error por un paquete o una fuente faltante, repetir
con acceso a internet y sin esa opción:

```bash
XDG_CACHE_HOME=/tmp/centinela-tectonic/cache /tmp/centinela-tectonic/tectonic --keep-logs main.tex
```

Las rutas bajo `/tmp` son temporales y no forman parte del repositorio. En otro
equipo, o si se limpia esa carpeta, instalar Tectonic y usar el comando general.

## Verificación del resultado

Con las herramientas de Poppler disponibles, desde `docs/`:

```bash
pdfinfo main.pdf
pdftoppm -scale-to 1100 -png main.pdf /tmp/centinela-revision
```

Comprobar que el PDF conserve tres páginas tamaño carta y revisar las imágenes
generadas para verificar proporciones del imagotipo, alineación de los encabezados,
colores y ausencia de contenido cortado. Revisar también `main.log` por errores
y avisos de desbordamiento (`Overfull`).
