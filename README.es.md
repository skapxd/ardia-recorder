# ardia-recorder

[English](README.md)

Skill para agentes que graba en video un recorrido hecho con [Ardia](https://ardia.dev) (`ardia browse`) y lo exporta como MP4 del tamaño del viewport capturado, con la página 1:1. Un panel lateral muestra los objetivos del encargo, cuál está en curso, cuáles se cumplieron y cuánto tardó cada uno. La página se ve dentro de una ventana con el estilo de Ardia (pestañas verticales y, sobre la página, una barra de direcciones con el dominio y el path actuales), y un puntero virtual marca cada elemento antes de actuar sobre él.

Sirve para dejar evidencia de pruebas e2e y para mostrar paso a paso cómo se cumple una tarea en una web.

[![Demo: panel de objetivos a la izquierda y TodoMVC a la derecha](assets/demo.gif)](assets/demo.mp4)

Video completo: [assets/demo.mp4](assets/demo.mp4) (39 s, 2304 × 1170).

## Instalación

Con [APM](https://microsoft.github.io/apm/):

```sh
apm install --global 'skapxd/ardia-recorder#^1.0.0' --target claude,codex
```

- **Origen:** APM la descarga directamente de este repositorio de GitHub. `skapxd/ardia-recorder` es la forma corta de `https://github.com/skapxd/ardia-recorder`, y las dos funcionan.
- **Versión:** `#^1.0.0` instala el release 1.x más reciente, y `apm update` pasa a los siguientes. Usa un tag como `#v1.3.0` para quedarte en una versión. Sin versión, APM instala el último commit de `main`.
- **Agentes:** `--target` indica qué agentes reciben la skill (`claude`, `codex` u otro de los que admite APM). Sin él, APM usa los `targets` de `~/.apm/apm.yml`.

Sin APM, clona el repositorio en la carpeta de skills de tu agente. Para Claude Code:

```sh
git clone --branch v1.3.0 https://github.com/skapxd/ardia-recorder ~/.claude/skills/ardia-recorder
```

### Verificar la procedencia

Cada release incluye `ardia-recorder-<versión>.tar.gz`, generado por GitHub Actions a partir del tag, con una atestación de procedencia firmada (SLSA, Sigstore). Para comprobarla e instalar desde ese paquete:

```sh
gh release download v1.3.0 -R skapxd/ardia-recorder -p 'ardia-recorder-*.tar.gz'
gh attestation verify ardia-recorder-v1.3.0.tar.gz -R skapxd/ardia-recorder
tar -xzf ardia-recorder-v1.3.0.tar.gz
apm install --global "$PWD/ardia-recorder"
```

## Requisitos

- macOS con Ardia abierto y **Settings → Advanced → Command line and automation → Let programs control Ardia** activado.
- Python 3, FFmpeg con `libx264` y Google Chrome.

Opcional: con permiso de grabación de pantalla para la terminal y las herramientas de línea de comandos de Xcode (`swiftc`), la ventana se graba de forma fluida; sin ellos, la página se captura con screenshots. Probada con la app Ardia 0.2.48 y la CLI `ardia` 0.6.0.

## Uso

Pídele al agente algo como *«graba en video cómo se crea y se borra una tarea en esta web, con los objetivos a la izquierda»*. La skill le indica cómo convertir el pedido en objetivos, escribir el escenario, probarlo sin grabar, grabarlo, exportarlo y revisar el resultado.

Un escenario es un archivo Python corto:

```python
from recorder import Recording

OBJETIVOS = [
    ('Crear una tarea', 'Escribir el texto y confirmarlo con Enter'),
    ('Borrar la tarea', 'Quitarla de la lista con la ✕'),
]

with Recording('Ciclo de una tarea', 'Prueba e2e de TodoMVC', OBJETIVOS,
               'https://demo.playwright.dev/todomvc/#/active', lang='es') as r:
    with r.goal(0):
        r.point('.new-todo', 'Escribir una tarea nueva')
        r.act('type', r.ref('textbox'), 'Comprar pan')
        r.act('press', 'Enter')
        r.check('Comprar pan' in r.cli('get', 'text', '.todo-list'), 'La tarea no se creó')
    ...
```

Con `lang='es'`, los textos propios del panel salen en español.

- La API y los ajustes de encuadre están en [references/framework.es.md](references/framework.es.md).
- Encargos completos de ejemplo, en inglés: [examples/todomvc/](examples/todomvc/) (una pestaña) y [examples/todomvc-tabs/](examples/todomvc-tabs/) (dos pestañas, con `r.tab()`).

## Estructura

| Ruta | Contenido |
|---|---|
| `SKILL.md` | Instrucciones para el agente (en español: `SKILL.es.md`) |
| `scripts/` | Grabación (`recorder.py`), marcas en la página (`overlay.js`), marco (`frame.html`) y exportación (`render.py`) |
| `references/` | API del escenario, ajustes y revisión (`framework.md`, `framework.es.md`) |
| `examples/` | Encargos y escenarios de ejemplo: una pestaña y dos pestañas |

## Licencia

MIT
