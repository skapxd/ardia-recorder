# Framework: videos de recorridos con objetivos en Ardia

> Versión en español de [framework.md](framework.md).

Graba un recorrido que un agente hace con `ardia browse` y lo exporta como MP4 a 30 fps del tamaño del viewport capturado. A la izquierda hay un panel con los objetivos del encargo, su avance y el tiempo de cada uno. A la derecha se ve la página real dentro de una ventana con el estilo de Ardia, con una barra de direcciones sobre la página que muestra el dominio y el path actuales. Dentro de la página, un puntero virtual va a cada elemento y un recuadro rojo con flecha y etiqueta lo marca antes de cada acción.

En los comandos, `$SKILL` es la carpeta donde está instalada esta skill.

## Requisitos

- macOS con Ardia abierto y **Settings → Advanced → Command line and automation → Let programs control Ardia** activado.
- Python 3 (solo biblioteca estándar), FFmpeg con `libx264` y Google Chrome, que convierte el marco HTML a imagen.

Opcional, para una captura fluida: permiso de grabación de pantalla para la terminal que ejecuta el escenario, y las herramientas de línea de comandos de Xcode (`swiftc`) para compilar el helper de captura de la ventana. Probado con la app Ardia 0.2.48 y la CLI `ardia` 0.6.0.

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
| `scripts/recorder.py` | Clase `Recording`: abre la página, la captura mientras corren los pasos (ver [Captura y encuadre](#captura-y-encuadre)) y guarda la toma en `work/take.mov` y la línea de tiempo en `work/take.json`. |
| `scripts/window_capture.swift` | Graba la ventana de Ardia con ScreenCaptureKit y encuentra la página en ella. Se compila una vez con `swiftc` en `~/Library/Caches/ardia-recorder/`. |
| `scripts/overlay.js` | Capa que se inyecta en la página: recuadro, flecha, etiqueta y pulso del clic. No intercepta clics y se retira al terminar. El puntero lo dibuja `render.py`, así también puede llegar a las pestañas de la ventana. |
| `scripts/frame.html` | Fondo, panel de objetivos y una ventana con el estilo de Ardia. El área de la página queda transparente; mantenla igual que `PAGE_*` en `render.py`. |
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
| `Recording(title, description, goals, url, tab=None, lang='en', output='work/take', profile=None)` | Título y descripción encabezan el panel. `goals` es la lista de `(título, detalle)`. `tab` es el texto de la pestaña; sin él se usa el dominio. `lang` (`'en'` o `'es'`) es el idioma de los textos propios del panel. `profile` es el perfil de Ardia (nombre o id) donde corre la toma: usa una ventana de ese perfil o abre una. Sin él, la ventana activa. |
| `with r.goal(i):` | El objetivo `i` pasa a *en curso* y muestra su detalle. Al salir del bloque queda *cumplido*, con su duración, y se oculta el recuadro. Si algo falla dentro, queda *fallido* y el escenario termina con error. |
| `r.point(selector, label)` | Mueve el puntero virtual al elemento y lo marca con recuadro, flecha y etiqueta. Va antes de la acción. |
| `r.act(*args)` | Ejecuta `ardia browse <args>` con una pausa antes y después para que se vea la respuesta. Devuelve la salida. Si la URL cambia, la barra de direcciones se actualiza. |
| `r.tab(label, url=None, title=None)` | Con `url`, abre una pestaña nueva y la muestra; sin ella, vuelve a una pestaña ya abierta. En el video, el puntero hace clic en «New Tab» o en la pestaña de la barra lateral, la página anterior sale deslizándose, un aviso breve nombra la pestaña que queda al frente y esa pestaña se ilumina un momento; cada cambio suma alrededor de un segundo. La barra lateral lista las pestañas abiertas y resalta la activa. `title` es el texto de la pestaña (por defecto, el título de la página); la primera pestaña es `'main'`. Al terminar cierra las pestañas que abrió. |
| `r.ref(role, selector=None)` | Devuelve la referencia de accesibilidad (`@e123`) del primer elemento cuyo rol y nombre coinciden con `role` (expresión regular sobre `snapshot -i --full`). Con `selector`, busca solo dentro de él. |
| `r.cli(*args)` | Ejecuta `ardia browse <args>` sin pausas. Para lecturas y comprobaciones. |
| `r.check(condition, detail)` | Si la condición es falsa, el objetivo en curso queda *fallido*. |

Para un elemento que solo aparece con el puntero encima, ejecuta `r.act('hover', …)` antes de `r.point`. La capa se vuelve a inyectar sola después de recargar, navegar o cambiar de pestaña. [examples/todomvc-tabs/](../examples/todomvc-tabs/) muestra una tarea en dos pestañas.

## Grabar y exportar

1. Pasa en `profile` el perfil de Ardia donde se ejecuta el encargo, el que tiene las sesiones que necesita. La ventana puede estar en cualquier sitio y pantalla, y otras ventanas pueden taparla. No uses esa ventana mientras graba: las pestañas nuevas se abren en la ventana activa, así que el recorder trae la suya al frente antes de cada una, y se detiene con un error si la pestaña grabada sale de esa ventana. Cada toma usa una sesión de Ardia propia, así que nunca reutiliza una pestaña de una corrida anterior.
2. Prueba el flujo sin grabar:

   ```sh
   RECORD=0 PYTHONPATH="$SKILL/scripts" python3 work/scenario.py
   ```

3. Graba. Deja `work/take.mov` y `work/take.json`:

   ```sh
   PYTHONPATH="$SKILL/scripts" python3 work/scenario.py
   ```

   `PACE` escala las pausas alrededor de cada acción (por defecto `1`). `PACE=0.3` va rápido y todavía se sigue con la vista:

   ```sh
   PACE=0.3 PYTHONPATH="$SKILL/scripts" python3 work/scenario.py
   ```

4. Exporta con un nombre nuevo por versión. El segundo argumento, opcional, es la ruta de la toma sin extensión:

   ```sh
   python3 "$SKILL/scripts/render.py" outputs/<nombre>.mp4 work/take
   ```

## Captura y encuadre

El grabador prueba tres métodos en orden y guarda el que usó en `work/take.json` (`capture`):

| `capture` | Cómo | Fluidez | Necesita |
|---|---|---|---|
| `video` | `ardia browse record` | Video real | Una versión de Ardia que lo permita (hoy responde `policy_refused`) |
| `window` | `window_capture.swift` graba la ventana de Ardia con ScreenCaptureKit | 30 fps, resolución nativa; no importa qué ventanas tenga encima | Permiso de grabación de pantalla para la terminal, y `swiftc` |
| `screenshots` | `ardia browse screenshot` en bucle | Página a unos 8 fps (el puntero siempre lo dibuja `render.py` a 30 fps) | Nada |

Para `window`, la capa pinta un instante unas marcas magenta en las esquinas de la página; el helper las busca en una captura de cada ventana de Ardia y así obtiene la ventana y el área exacta de la página, en cualquier pantalla, escala o disposición. Cuando un método no está disponible, el grabador imprime el motivo y usa el siguiente. Toda toma se codifica a 30 fps constantes, al tamaño CSS de la página y alineada con la línea de tiempo de los objetivos.

El video crece con el viewport capturado para mostrar la página 1:1, sin recortarla ni escalarla: el área de la página es el viewport (mínimo 1131 × 982) y el video suma el panel de objetivos y los márgenes (1920 × 1120 con un viewport de 1131 × 982). Una página más chica se centra y se rellena de blanco.

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
