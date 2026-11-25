from ardia_video import Grabacion

TAREA, EDITADA = 'Comprar pan', 'Comprar pan integral'
ULTIMA = '.todo-list li:last-child'

OBJETIVOS = [
    ('Crear una tarea', f'Escribir «{TAREA}» y confirmarla con Enter'),
    ('Editar la tarea', 'Doble clic sobre el texto y cambiarlo'),
    ('Marcarla como completada', 'Activar la casilla de la tarea'),
    ('Verla en Completadas', 'Abrir el filtro y comprobar que aparece tachada'),
    ('Borrar la tarea', 'Quitarla de la lista con la ✕'),
]

with Grabacion('Ciclo de vida de una tarea', 'Prueba e2e sobre la demo pública de TodoMVC',
               OBJETIVOS, 'https://demo.playwright.dev/todomvc/#/active',
               pestana='React • TodoMVC') as g:

    with g.objetivo(0):
        g.guiar('.new-todo', 'Escribir una tarea nueva')
        g.accion('type', g.ref('textbox'), TAREA)
        g.accion('press', 'Enter')
        g.comprobar(TAREA in g.cli('get', 'text', f'{ULTIMA} label'), 'La tarea no se creó')

    with g.objetivo(1):
        g.guiar(f'{ULTIMA} label', 'Doble clic para editar')
        g.accion('dblclick', f'{ULTIMA} label')
        g.accion('fill', f'{ULTIMA} .edit', EDITADA)
        g.accion('press', 'Enter')
        g.comprobar(EDITADA in g.cli('get', 'text', f'{ULTIMA} label'), 'La edición no se guardó')

    with g.objetivo(2):
        g.guiar(f'{ULTIMA} .toggle', 'Completar esta tarea')
        g.accion('click', g.ref('checkbox', ULTIMA))

    with g.objetivo(3):
        g.guiar('a[href="#/completed"]', 'Ver las tareas completadas')
        g.accion('click', g.ref('link "Completed"'))
        g.guiar(f'{ULTIMA} label', 'Aparece tachada en Completadas')
        g.comprobar(EDITADA in g.cli('get', 'text', '.todo-list li.completed:last-child label'),
                    'La tarea no aparece en Completadas')

    with g.objetivo(4):
        g.accion('hover', ULTIMA)
        g.guiar(f'{ULTIMA} .destroy', 'Borrar la tarea')
        g.accion('click', f'{ULTIMA} .destroy')
        g.comprobar(EDITADA not in g.cli('get', 'text', '.todo-list'), 'La tarea sigue en la lista')
