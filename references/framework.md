# Framework: videos de recorridos con objetivos en Ardia

Graba un recorrido que un agente hace con `ardia browse` y lo exporta como MP4 de 1920 × 1080 a 30 fps. A la izquierda hay un panel con los objetivos del encargo, su avance y el tiempo de cada uno. A la derecha se ve la página real dentro de una ventana de navegador, con su URL. Dentro de la página, un recuadro rojo con flecha y etiqueta marca el elemento antes de cada acción.

En los comandos, `$SKILL` es la carpeta donde está instalada esta skill.

## Requisitos

- macOS con Ardia abierto y **Settings → Advanced → Command line and automation → Let programs control Ardia** activado.
- Permiso de grabación de pantalla para la terminal desde la que se ejecuta el escenario.
- Python 3 (solo biblioteca estándar), FFmpeg con `libx264` y Google Chrome, que convierte el marco HTML a imagen.

```sh
command -v ardia ffmpeg ffprobe python3 screencapture
ardia --version
ffmpeg -hide_banner -encoders | grep libx264
ls "/Applications/Google Chrome.app"
```

## Archivos

| Archivo | Qué hace |
|---|---|
| `scripts/ardia_video.py` | Clase `Grabacion`: abre la página, graba la pantalla, ejecuta los pasos y guarda la línea de tiempo en `work/toma.json`. |
| `scripts/guia-visual-ardia.js` | Capa que se inyecta en la página: puntero, recuadro, flecha, etiqueta y pulso del clic. No intercepta clics y se retira al terminar. |
| `scripts/marco.html` | Fondo, panel de objetivos y ventana del navegador. El área de la página queda transparente. |
| `scripts/renderizar.py` | Une `work/toma.mov` y `work/toma.json` en el MP4 final. |

La toma (`work/toma.mov`, `work/toma.json`) y el video quedan en la carpeta desde donde se ejecuta, no en la skill.

## Escribir un escenario

```python
from ardia_video import Grabacion

OBJETIVOS = [
    ('Título del objetivo', 'Qué se hace, en una línea'),
    ...
]

with Grabacion('Título', 'Descripción', OBJETIVOS, 'https://…', pestana='Título de la pestaña') as g:
    with g.objetivo(0):
        g.guiar('#selector', 'Etiqueta en pantalla')
        g.accion('click', '#selector')
        g.comprobar(condición, 'Mensaje si no se cumple')
```

| Llamada | Efecto en el video |
|---|---|
| `Grabacion(titulo, descripcion, objetivos, url, pestana=None, rect=…, salida='work/toma')` | Título y descripción encabezan el panel. `objetivos` es la lista de `(título, detalle)`. `pestana` es el texto de la pestaña; sin él se usa el dominio. |
| `with g.objetivo(i):` | El objetivo `i` pasa a *en curso* y muestra su detalle. Al salir del bloque queda *cumplido*, con su duración, y se oculta el recuadro. Si algo falla dentro, queda *fallido* y el escenario termina con error. |
| `g.guiar(selector, texto)` | Mueve el puntero al elemento y lo marca con recuadro, flecha y etiqueta. Va antes de la acción. |
| `g.accion(*args)` | Ejecuta `ardia browse <args>` con una pausa antes y después para que se vea la respuesta. Devuelve la salida. Si la URL cambia, la barra de direcciones se actualiza. |
| `g.ref(rol, selector=None)` | Devuelve la referencia de accesibilidad (`@e123`) del primer elemento cuyo rol y nombre coinciden con `rol` (expresión regular sobre `snapshot -i --full`). Con `selector`, busca solo dentro de él. |
| `g.cli(*args)` | Ejecuta `ardia browse <args>` sin pausas. Para lecturas y comprobaciones. |
| `g.comprobar(condicion, detalle)` | Si la condición es falsa, el objetivo en curso queda *fallido*. |

Para un elemento que solo aparece con el puntero encima, ejecuta `g.accion('hover', …)` antes de `g.guiar`. Si el sitio recarga la página completa al navegar, vuelve a inyectar la capa con `g.cli('eval', GUIA.read_text())`, importando `GUIA` desde `ardia_video`.

## Grabar y exportar

1. Abre en Ardia el perfil donde se ejecuta el encargo y deja la ventana visible, sin nada encima. La captura toma un rectángulo fijo de la pantalla: lo que pase por encima de esa zona sale en el video.
2. Prueba el flujo sin grabar:

   ```sh
   GRABAR=0 PYTHONPATH="$SKILL/scripts" python3 work/escenario.py
   ```

3. Graba desde la terminal con permiso de grabación de pantalla. Deja `work/toma.mov` y `work/toma.json`:

   ```sh
   PYTHONPATH="$SKILL/scripts" python3 work/escenario.py
   ```

4. Exporta con un nombre nuevo por versión. El segundo argumento, opcional, es la ruta de la toma sin extensión:

   ```sh
   python3 "$SKILL/scripts/renderizar.py" outputs/<nombre>.mp4 work/toma
   ```

## Ajustes según el equipo

| Valor | Dónde | Cómo medirlo |
|---|---|---|
| `rect` | `Grabacion(…, rect='x,y,ancho,alto')` | Área de la página en puntos de pantalla. Toma una captura completa con `screencapture -x pantalla.png` y mide dónde empieza y termina la página, sin barra lateral ni barra de direcciones. El valor por defecto, `397,39,1514,1032`, corresponde a Ardia maximizado con la barra lateral abierta en una pantalla de 1920 × 1080 puntos. |
| `CROP` | `scripts/renderizar.py` | Recorte de 1340 × 908 píxeles sobre `toma.mov`, en formato `ancho:alto:x:y`. Ajusta `x` para centrar la aplicación y deja `y` en 0. Si la página no llena 908 píxeles de alto, el resto se ve vacío. |
| `DESFASE` | `scripts/renderizar.py` | Segundos que se adelantan los cambios del panel. Si el panel cambia antes o después que la página, mide el desfase en el video y ajústalo. |

Comprueba el tamaño de la toma antes de exportar:

```sh
ffprobe -v error -show_entries stream=width,height -of csv=p=0 work/toma.mov
```

## Revisar el resultado

```sh
ffprobe -v error -show_entries stream=width,height,r_frame_rate:format=duration -of compact outputs/<nombre>.mp4
ffmpeg -loglevel error -i outputs/<nombre>.mp4 -vf 'fps=0.5,scale=640:-2,tile=4x5' -frames:v 1 work/revision.png
ffmpeg -loglevel error -sseof -0.5 -i outputs/<nombre>.mp4 -frames:v 1 work/final.png
```

En la hoja de contactos, cada objetivo debe pasar por *en curso* y *cumplido* en orden, con el recuadro sobre el elemento correcto antes de cada acción. El último fotograma muestra **Todos los objetivos cumplidos** y la página sin recuadro.
