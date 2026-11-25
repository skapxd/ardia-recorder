# Task: the lifecycle of a to-do in TodoMVC

Deliver a 30 fps MP4 in which an agent, using `ardia browse`, creates a task in the [public TodoMVC demo](https://demo.playwright.dev/todomvc/#/active), edits it, marks it as completed, finds it under the **Completed** filter and deletes it. The scenario is [scenario.py](scenario.py).

The reference take lasted about **38 seconds**.

## Setup

Use an Ardia profile with few TodoMVC tasks, so the list fits in the frame. Existing tasks are kept. The test deletes the task it creates, so the profile ends as it started.

## Goals

| # | Goal | What happens | How it is checked |
|---|---|---|---|
| 1 | Create a task | Type **Buy bread** in the input and press Enter | The last row of the list has that text |
| 2 | Edit the task | Double-click the text, change it to **Buy whole wheat bread** and press Enter | The last row has the new text |
| 3 | Mark it as completed | Tick that row's checkbox | — |
| 4 | Find it in Completed | Open the **Completed** filter | The URL ends in `#/completed` and the last completed row has the edited text |
| 5 | Delete the task | Hover the row and click the ✕ | The edited text is no longer in the list |

## Run

From your working folder, with `$SKILL` pointing to the installed skill:

```sh
RECORD=0 PYTHONPATH="$SKILL/scripts" python3 "$SKILL/examples/todomvc/scenario.py"
PYTHONPATH="$SKILL/scripts" python3 "$SKILL/examples/todomvc/scenario.py"
python3 "$SKILL/scripts/render.py" outputs/todomvc-goals.mp4
```

## Acceptance

- The sidebar shows the five goals in order; each one goes through *in progress* and ends *done* with its duration, and the video closes with **All goals completed**.
- The address bar shows `demo.playwright.dev`, first with `#/active` and then with `#/completed`.
- Before each action, the red box surrounds the right element: the input, the row being edited, its checkbox, the **Completed** filter and the ✕.
- In **Completed** the edited task is crossed out, and in the last frame it is no longer in the list.
- The scenario exits without errors. If a goal fails, the sidebar shows it in red, and the delivery states which goal failed and what the check returned.
