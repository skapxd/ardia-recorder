---
name: ardia-recorder
description: Graba en video un recorrido que un agente hace con `ardia browse` (pruebas e2e o tareas personales en el navegador) y lo exporta como MP4 1920×1080, con un panel lateral de objetivos que muestra qué se pidió, qué sub-meta está en curso, cuáles se cumplieron y cuánto tardó cada una. La página se ve dentro de una ventana de navegador moderna con su URL real, y un recuadro rojo con flecha marca cada elemento antes de actuar. Úsala cuando haya que grabar evidencia de una prueba con Ardia, mostrar paso a paso cómo se cumple un encargo en una web, o cuando pidan "graba el recorrido", "video con objetivos", "evidencia e2e con Ardia".
---

# ardia-recorder

Genera un MP4 de 1920 × 1080 a 30 fps a partir de un **escenario**: un archivo Python que lista los objetivos del encargo y los pasos de `ardia browse` que los cumplen. El panel izquierdo del video cuenta el avance en lenguaje humano. No muestra comandos.

Los scripts están en `scripts/`, dentro del directorio base de esta skill (en adelante `$SKILL`). La referencia completa de la API, los ajustes de encuadre y la revisión del resultado está en [references/framework.md](references/framework.md). Hay un ejemplo completo en [examples/todomvc/](examples/todomvc/).

## Flujo

1. **Objetivos.** Convierte lo que pidió el usuario en 3 a 7 objetivos verificables, redactados para quien ve el video: «Crear una tarea», «Borrar la tarea». Cada uno lleva un detalle de una línea con lo que se hace. Ningún objetivo menciona comandos ni selectores.
2. **Escenario.** Escríbelo en el proyecto del usuario, por ejemplo `work/escenario.py`, siguiendo [examples/todomvc/escenario.py](examples/todomvc/escenario.py). En cada objetivo: `g.guiar(...)` antes de la acción, `g.accion(...)` para actuar y `g.comprobar(...)` con una lectura real de la página. Obtén las referencias `@eN` con `g.ref(...)` en cada ejecución: cambian entre sesiones.
3. **Prueba sin grabar.** Ejecuta desde el proyecto:

   ```sh
   GRABAR=0 PYTHONPATH="$SKILL/scripts" python3 work/escenario.py
   ```

   Corrige hasta que termine sin error.
4. **Grabar.** Ejecuta lo mismo sin `GRABAR=0`. La captura necesita permiso de grabación de pantalla. Si tu shell no lo tiene (`screencapture -x /tmp/p.png` falla con *could not create image*), ejecuta el comando en la terminal del usuario. La ventana de Ardia debe estar visible y sin nada encima durante la toma.
5. **Exportar.**

   ```sh
   python3 "$SKILL/scripts/renderizar.py" outputs/<nombre>.mp4
   ```

6. **Revisar.** Saca una hoja de contactos y el último fotograma, como indica [references/framework.md](references/framework.md#revisar-el-resultado). Un código de salida correcto no basta. Comprueba que el panel avanza en orden, que el recuadro cae sobre el elemento correcto y que el video cierra con **Todos los objetivos cumplidos**.

## Al entregar

Indica duración, resolución, qué objetivos se cumplieron y cualquier diferencia visible. Si un objetivo falló, el panel lo muestra en rojo: di cuál fue y qué devolvió la comprobación.
