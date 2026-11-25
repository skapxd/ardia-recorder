# Task: one to-do list across two tabs

Deliver a 1920 × 1080, 30 fps MP4 in which an agent, using `ardia browse`, creates a task in the [public TodoMVC demo](https://demo.playwright.dev/todomvc/#/active), opens the same list in a second tab without closing the first, completes the task there, goes back to the first tab to check the change, and deletes the task. The scenario is [scenario.py](scenario.py).

TodoMVC keeps its tasks in the browser's `localStorage`, so both tabs read the same list. A tab only picks up changes made in the other one when it reloads.

## Setup

Use an Ardia profile with few TodoMVC tasks, so the list fits in the frame. Existing tasks are kept. The test deletes the task it creates and closes the second tab.

## Goals

| # | Goal | What happens | How it is checked |
|---|---|---|---|
| 1 | Create a task | In the first tab (Active filter), type **Call the bank** and press Enter | The last row has that text |
| 2 | Find it in a second tab | `r.tab('all', …)` opens the list (All filter) in a new tab; the first one stays open | The last row of the second tab has the task |
| 3 | Complete it there | Tick its checkbox in the second tab | The last completed row has the task |
| 4 | Check the first tab | `r.tab('main')` goes back; it still shows the task as active until a reload | After reloading, the task is no longer in the Active list |
| 5 | Delete the task | Back in the second tab, hover the row and click the ✕ | The task is no longer in the list |

## Run

From your working folder, with `$SKILL` pointing to the installed skill:

```sh
RECORD=0 PYTHONPATH="$SKILL/scripts" python3 "$SKILL/examples/todomvc-tabs/scenario.py"
PYTHONPATH="$SKILL/scripts" python3 "$SKILL/examples/todomvc-tabs/scenario.py"
python3 "$SKILL/scripts/render.py" outputs/todomvc-tabs.mp4
```

## Acceptance

- The window's sidebar lists **TodoMVC · Active** first and adds **TodoMVC · All** when the second tab opens; the highlighted tab always matches the one being used.
- The video shows the page of the active tab: the full list in the second tab, the Active list in the first.
- In goal 4, the first tab shows the task as active before the reload and drops it after.
- The video closes with **All goals completed**, and after the run the second tab is closed and the task is gone.
