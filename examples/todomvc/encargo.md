# Encargo: ciclo de vida de una tarea en TodoMVC

Entrega un MP4 de 1920 × 1080 a 30 fps donde un agente, con `ardia browse`, crea una tarea en la [demo pública de TodoMVC](https://demo.playwright.dev/todomvc/#/active), la edita, la marca como completada, la encuentra en el filtro **Completed** y la borra. El escenario es [escenario.py](escenario.py).

La toma de referencia duró **37 segundos**.

## Preparación

Usa un perfil de Ardia con pocas tareas en TodoMVC, para que la lista quepa en el encuadre. Las tareas que ya existen se conservan. La prueba borra la que crea, así que el perfil queda como estaba.

## Objetivos

| # | Objetivo | Qué se hace | Cómo se comprueba |
|---|---|---|---|
| 1 | Crear una tarea | Escribir **Validar la demo con Vercel** en el campo y confirmar con Enter | La última fila de la lista tiene ese texto |
| 2 | Editar la tarea | Doble clic sobre el texto, cambiarlo a **Validar la demo con Vercel y Ardia** y confirmar con Enter | La última fila tiene el texto nuevo |
| 3 | Marcarla como completada | Activar la casilla de esa fila | — |
| 4 | Verla en Completadas | Abrir el filtro **Completed** | La URL termina en `#/completed` y la última fila completada tiene el texto editado |
| 5 | Borrar la tarea | Pasar el puntero por la fila y pulsar la ✕ | El texto editado ya no está en la lista |

## Ejecutar

Desde la carpeta de trabajo, con `$SKILL` apuntando a la skill instalada:

```sh
GRABAR=0 PYTHONPATH="$SKILL/scripts" python3 "$SKILL/examples/todomvc/escenario.py"
PYTHONPATH="$SKILL/scripts" python3 "$SKILL/examples/todomvc/escenario.py"
python3 "$SKILL/scripts/renderizar.py" outputs/todomvc-objetivos.mp4
```

## Cómo aceptar la entrega

- El panel muestra los cinco objetivos en orden, cada uno pasa por *en curso* y termina *cumplido* con su duración, y el video cierra con **Todos los objetivos cumplidos**.
- La barra de direcciones muestra `demo.playwright.dev`, primero con `#/active` y después con `#/completed`.
- Antes de cada acción, el recuadro rojo rodea el elemento correcto: el campo de texto, la fila que se edita, su casilla, el filtro **Completed** y la ✕.
- En **Completed** la tarea editada se ve tachada, y en el último fotograma ya no está en la lista.
- El escenario termina sin error. Si un objetivo falla, el panel lo muestra en rojo y la entrega indica cuál fue y qué devolvió la comprobación.
