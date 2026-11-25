from recorder import Recording

TASK, EDITED = 'Buy bread', 'Buy whole wheat bread'
LAST = '.todo-list li:last-child'

GOALS = [
    ('Create a task', f'Type “{TASK}” and confirm with Enter'),
    ('Edit the task', 'Double-click the text and change it'),
    ('Mark it as completed', 'Tick the task checkbox'),
    ('Find it in Completed', 'Open the filter and check it shows crossed out'),
    ('Delete the task', 'Remove it from the list with the ✕'),
]

with Recording('Task lifecycle', 'E2E test on the public TodoMVC demo',
               GOALS, 'https://demo.playwright.dev/todomvc/#/active', tab='React • TodoMVC') as r:

    with r.goal(0):
        r.point('.new-todo', 'Type a new task')
        r.act('type', r.ref('textbox'), TASK)
        r.act('press', 'Enter')
        r.check(TASK in r.cli('get', 'text', f'{LAST} label'), 'The task was not created')

    with r.goal(1):
        r.point(f'{LAST} label', 'Double-click to edit')
        r.act('dblclick', f'{LAST} label')
        r.act('fill', f'{LAST} .edit', EDITED)
        r.act('press', 'Enter')
        r.check(EDITED in r.cli('get', 'text', f'{LAST} label'), 'The edit was not saved')

    with r.goal(2):
        r.point(f'{LAST} .toggle', 'Complete this task')
        r.act('click', r.ref('checkbox', LAST))

    with r.goal(3):
        r.point('a[href="#/completed"]', 'Show completed tasks')
        r.act('click', r.ref('link "Completed"'))
        r.point(f'{LAST} label', 'Shown crossed out in Completed')
        r.check(EDITED in r.cli('get', 'text', '.todo-list li.completed:last-child label'),
                'The task is not in Completed')

    with r.goal(4):
        r.act('hover', LAST)
        r.point(f'{LAST} .destroy', 'Delete the task')
        r.act('click', f'{LAST} .destroy')
        r.check(EDITED not in r.cli('get', 'text', '.todoapp'), 'The task is still in the list')
