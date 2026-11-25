# Framework: videos de recorridos con objetivos en Ardia

> Versión en español de [framework.md](framework.md).

Graba un recorrido que un agente hace con `ardia browse` y lo exporta como MP4 de 1920 × 1080 a 30 fps. A la izquierda hay un panel con los objetivos del encargo, su avance y el tiempo de cada uno. A la derecha se ve la página real dentro de una ventana de navegador, con su URL. Dentro de la página, un puntero virtual va a cada elemento y un recuadro rojo con flecha y etiqueta lo marca antes de cada acción.

En los comandos, `$SKILL` es la carpeta donde está instalada esta skill.

## Requisitos

- macOS con Ardia abierto y **Settings → Advanced → Command line and automation → Let programs control Ardia** activado.
- Python 3 (solo biblioteca estándar), FFmpeg con `libx264` y Google Chrome, que convierte el marco HTML a imagen.

Probado con la app Ardia 0.2.48 y la CLI `ardia` 0.6.0. Ardia todavía no permite grabar video desde el navegador (`ardia browse record` falla con `policy_refused`), así que el grabador toma capturas de la página. Intenta el video primero en cada toma, así que pasa solo a video cuando una versión de Ardia lo permita.

```sh
command -v ardia ffmpeg ffprobe python3
ardia --version
defaults read /Applications/Ardia.app/Contents/Info.plist CFBundleShortVersionString
ffmpeg -hide_banner -encoders | grep libx264
ls "/Applications/Google Chrome.app"
```

## Archivos

| Archivo | Qué hace |
|---|---|
| `scripts/recorder.py` | Clase `Recording`: abre la página, la captura con `ardia browse record` o, mientras Ardia lo rechace, con `ardia browse screenshot` mientras corren los pasos, y guarda la toma en `work/take.mov` y la línea de tiempo en `work/take.json`. |
| `scripts/overlay.js` | Capa que se inyecta en la página: puntero virtual, recuadro, flecha, etiqueta y pulso del clic. No intercepta clics y se retira al terminar. |
| `scripts/frame.html` | Fondo, panel de objetivos y ventana del navegador. El área de la página queda transparente. |
| `scripts/render.py` | Une `work/take.mov` y `work/take.json` en el MP4 final. |

La toma (`work/take.mov`, `work/take.json`) y el video quedan en la carpeta desde donde se ejecuta, no en la skill.

## Escribir un escenario

```python
from recorder import Recording

OBJETIVOS = [
    ('Título del objetivo', 'Qué se hace, en una línea'),
    ...
]

with Recording('Título', 'Descripción', OBJETIVOS, 'https://…', tab='Título de la pestaña', lang='es') as r:
    with r.goal(0):
        r.point('#selector', 'Etiqueta en pantalla')
        r.act('click', '#selector')
        r.check(condición, 'Mensaje si no se cumple')
```

| Llamada | Efecto en el video |
|---|---|
| `Recording(title, description, goals, url, tab=None, lang='en', output='work/take')` | Título y descripción encabezan el panel. `goals` es la lista de `(título, detalle)`. `tab` es el texto de la pestaña; sin él se usa el dominio. `lang` (`'en'` o `'es'`) es el idioma de los textos propios del panel. |
| `with r.goal(i):` | El objetivo `i` pasa a *en curso* y muestra su detalle. Al salir del bloque queda *cumplido*, con su duración, y se oculta el recuadro. Si algo falla dentro, queda *fallido* y el escenario termina con error. |
| `r.point(selector, label)` | Mueve el puntero virtual al elemento y lo marca con recuadro, flecha y etiqueta. Va antes de la acción. |
| `r.act(*args)` | Ejecuta `ardia browse <args>` con una pausa antes y después para que se vea la respuesta. Devuelve la salida. Si la URL cambia, la barra de direcciones se actualiza. |
| `r.ref(role, selector=None)` | Devuelve la referencia de accesibilidad (`@e123`) del primer elemento cuyo rol y nombre coinciden con `role` (expresión regular sobre `snapshot -i --full`). Con `selector`, busca solo dentro de él. |
| `r.cli(*args)` | Ejecuta `ardia browse <args>` sin pausas. Para lecturas y comprobaciones. |
| `r.check(condition, detail)` | Si la condición es falsa, el objetivo en curso queda *fallido*. |

Para un elemento que solo aparece con el puntero encima, ejecuta `r.act('hover', …)` antes de `r.point`. Si el sitio recarga la página completa al navegar, vuelve a inyectar la capa con `r.cli('eval', OVERLAY.read_text())`, importando `OVERLAY` desde `recorder`.

## Grabar y exportar

1. Abre en Ardia el perfil donde se ejecuta el encargo. La captura sale de la propia página, así que la ventana puede estar en cualquier sitio y otras ventanas pueden taparla.
2. Prueba el flujo sin grabar:

   ```sh
   RECORD=0 PYTHONPATH="$SKILL/scripts" python3 work/scenario.py
   ```

3. Graba. Deja `work/take.mov` y `work/take.json`:

   ```sh
   PYTHONPATH="$SKILL/scripts" python3 work/scenario.py
   ```

4. Exporta con un nombre nuevo por versión. El segundo argumento, opcional, es la ruta de la toma sin extensión:

   ```sh
   python3 "$SKILL/scripts/render.py" outputs/<nombre>.mp4 work/take
   ```

## Captura y encuadre

El grabador inicia primero `ardia browse record`. Si Ardia lo acepta, la toma es video real. Si Ardia responde `policy_refused`, como hoy, la página se captura tan rápido como Ardia devuelve las capturas (unos 8 fps en un Mac reciente); cualquier otro error cae al mismo respaldo y se imprime. En los dos casos la toma se codifica a 30 fps constantes, al tamaño CSS de la página, y `work/take.json` guarda el método en `capture` (`video` o `screenshots`). Cada captura conserva el momento en que se tomó, así que el panel queda sincronizado con la página.

El marco muestra un área de 1340 × 908 de la página, centrada en horizontal y alineada arriba. Una página más grande se recorta; una más chica se rellena de blanco. Si la aplicación queda fuera de esa área, cambia el tamaño de la ventana de Ardia antes de grabar.

Comprueba el tamaño de la toma antes de exportar:

```sh
ffprobe -v error -show_entries stream=width,height -of csv=p=0 work/take.mov
```

## Revisar el resultado

```sh
ffprobe -v error -show_entries stream=width,height,r_frame_rate:format=duration -of compact outputs/<nombre>.mp4
ffmpeg -loglevel error -i outputs/<nombre>.mp4 -vf 'fps=0.5,scale=640:-2,tile=4x5' -frames:v 1 work/revision.png
ffmpeg -loglevel error -sseof -0.5 -i outputs/<nombre>.mp4 -frames:v 1 work/final.png
```

En la hoja de contactos, cada objetivo debe pasar por *en curso* y *cumplido* en orden, con el recuadro sobre el elemento correcto antes de cada acción. El último fotograma muestra **Todos los objetivos cumplidos** y la página sin recuadro.
