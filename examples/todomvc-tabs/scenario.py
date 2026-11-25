from recorder import Recording

TASK = 'Call the bank'
LAST = '.todo-list li:last-child'
URL = 'https://demo.playwright.dev/todomvc/'

GOALS = [
    ('Create a task', f'Type “{TASK}” in the first tab and confirm with Enter'),
    ('Find it in a second tab', 'Open the list in a new tab; the first one stays open'),
    ('Complete it there', 'Tick the task in the second tab'),
    ('Check the first tab', 'Go back and reload: it leaves the Active list'),
    ('Delete the task', 'Remove it from the second tab with the ✕'),
]

with Recording('Two tabs, one list', 'E2E test across tabs on the public TodoMVC demo',
               GOALS, URL + '#/active', tab='TodoMVC · Active') as r:

    with r.goal(0):
        r.point('.new-todo', 'Type a new task')
        r.act('type', r.ref('textbox'), TASK)
        r.act('press', 'Enter')
        r.check(TASK in r.cli('get', 'text', f'{LAST} label'), 'The task was not created')

    with r.goal(1):
        r.tab('all', URL + '#/', title='TodoMVC · All')
        r.point(f'{LAST} label', 'Same task, new tab')
        r.check(TASK in r.cli('get', 'text', f'{LAST} label'), 'The task is not in the second tab')

    with r.goal(2):
        r.point(f'{LAST} .toggle', 'Complete it here')
        r.act('click', r.ref('checkbox', LAST))
        r.check(TASK in r.cli('get', 'text', '.todo-list li.completed:last-child label'), 'The task is not completed')

    with r.goal(3):
        r.tab('main')
        r.act('reload')
        r.point('.new-todo', 'Gone from Active after reloading')
        r.check(TASK not in r.cli('get', 'text', '.todoapp'), 'The first tab still lists the task as active')

    with r.goal(4):
        r.tab('all')
        r.act('hover', LAST)
        r.point(f'{LAST} .destroy', 'Delete the task')
        r.act('click', f'{LAST} .destroy')
        r.check(TASK not in r.cli('get', 'text', '.todoapp'), 'The task is still in the list')
