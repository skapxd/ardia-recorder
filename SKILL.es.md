# ardia-recorder

> Versión en español de [SKILL.md](SKILL.md). La que carga el agente es la versión en inglés.

Genera un MP4 a 30 fps, del tamaño necesario para mostrar la página capturada 1:1, a partir de un **escenario**: un archivo Python que lista los objetivos del encargo y los pasos de `ardia browse` que los cumplen. El panel izquierdo del video cuenta el avance en lenguaje humano. No muestra comandos.

Los scripts están en `scripts/`, dentro del directorio base de esta skill (en adelante `$SKILL`). La referencia completa de la API, los ajustes de encuadre y la revisión del resultado está en [references/framework.es.md](references/framework.es.md). Hay un ejemplo completo en [examples/todomvc/](examples/todomvc/).

Probada con la app Ardia 0.2.48 y la CLI `ardia` 0.6.0. Para ver las tuyas: `ardia --version` y `defaults read /Applications/Ardia.app/Contents/Info.plist CFBundleShortVersionString`.

## Flujo

1. **Objetivos.** Convierte lo que pidió el usuario en 3 a 7 objetivos verificables, redactados para quien ve el video: «Crear una tarea», «Borrar la tarea». Cada uno lleva un detalle de una línea con lo que se hace. Ningún objetivo menciona comandos ni selectores. Escríbelos en el idioma del usuario. Si es español, pasa `lang='es'` a `Recording`.
2. **Escenario.** Escríbelo en el proyecto del usuario, por ejemplo `work/scenario.py`, siguiendo [examples/todomvc/scenario.py](examples/todomvc/scenario.py). En cada objetivo: `r.point(...)` antes de la acción, `r.act(...)` para actuar y `r.check(...)` con una lectura real de la página. Obtén las referencias `@eN` con `r.ref(...)` en cada ejecución: cambian entre sesiones. Si el encargo usa varias pestañas (un formulario en una y la bandeja de entrada en otra), cambia con `r.tab(label, url)` y vuelve con `r.tab(label)`; ver [examples/todomvc-tabs/](examples/todomvc-tabs/).
3. **Prueba sin grabar.** Ejecuta desde el proyecto:

   ```sh
   RECORD=0 PYTHONPATH="$SKILL/scripts" python3 work/scenario.py
   ```

   Corrige hasta que termine sin error.
4. **Grabar.** Ejecuta lo mismo sin `RECORD=0`. Hay tres métodos de captura, en este orden: el video del propio Ardia (`ardia browse record`, cuando Ardia lo permita); la ventana de Ardia con ScreenCaptureKit, fluida y sin que otras ventanas la tapen, si la terminal tiene permiso de grabación de pantalla; y `ardia browse screenshot` (unos 8 fps), donde el puntero se anima al renderizar. No se configura nada de la pantalla ni de la posición de la ventana: el área de la página se detecta sola. `work/take.json` indica cuál se usó (`capture`). Para la captura fluida de la ventana, da permiso de grabación de pantalla a la terminal; sin él, la toma igual funciona.
5. **Exportar.**

   ```sh
   python3 "$SKILL/scripts/render.py" outputs/<nombre>.mp4
   ```

6. **Revisar.** Saca una hoja de contactos y el último fotograma, como indica [references/framework.es.md](references/framework.es.md#revisar-el-resultado). Un código de salida correcto no basta. Comprueba que el panel avanza en orden, que el recuadro cae sobre el elemento correcto y que el video cierra con **Todos los objetivos cumplidos**.

## Al entregar

Indica duración, resolución, qué objetivos se cumplieron y cualquier diferencia visible. Si un objetivo falló, el panel lo muestra en rojo: di cuál fue y qué devolvió la comprobación.
