---
name: ardia-recorder
description: Records a walkthrough an agent performs with `ardia browse` (e2e tests or personal tasks in the browser) and exports it as a 1920×1080 MP4 with a goals sidebar showing what was asked, which sub-goal is in progress, which ones are done and how long each took. The page appears inside a modern browser window with its real URL, and a red box with an arrow marks each element before acting on it. Use it to record evidence of an Ardia test, to show step by step how a task is completed on a website, or when asked to "record the walkthrough", "video with goals" or "e2e evidence with Ardia".
---

# ardia-recorder

Produces a 1920 × 1080, 30 fps MP4 from a **scenario**: a Python file listing the goals of the task and the `ardia browse` steps that complete them. The left sidebar tells the progress in plain language. It never shows commands.

The scripts live in `scripts/`, inside this skill's base directory (`$SKILL` below). The full API, framing adjustments and how to review the result are in [references/framework.md](references/framework.md). A complete example is in [examples/todomvc/](examples/todomvc/). Spanish versions: [SKILL.es.md](SKILL.es.md), [references/framework.es.md](references/framework.es.md).

Tested with the Ardia app 0.2.48 and the `ardia` CLI 0.6.0. Check yours with `ardia --version` and `defaults read /Applications/Ardia.app/Contents/Info.plist CFBundleShortVersionString`.

## Workflow

1. **Goals.** Turn the user's request into 3 to 7 verifiable goals, written for whoever watches the video: "Create a task", "Delete the task". Each one has a one-line detail of what happens. No goal mentions commands or selectors. Write them in the user's language and pass `lang='es'` to `Recording` if it is Spanish.
2. **Scenario.** Write it in the user's project, for example `work/scenario.py`, following [examples/todomvc/scenario.py](examples/todomvc/scenario.py). In each goal: `r.point(...)` before the action, `r.act(...)` to act and `r.check(...)` with a real reading of the page. Get `@eN` references with `r.ref(...)` on every run: they change between sessions.
3. **Dry run.** From the project:

   ```sh
   RECORD=0 PYTHONPATH="$SKILL/scripts" python3 work/scenario.py
   ```

   Fix it until it exits without errors.
4. **Record.** Run the same command without `RECORD=0`. The page is captured from Ardia itself with `ardia browse screenshot` (about 8 fps), so it needs no screen recording permission and nothing on screen can cover it.
5. **Export.**

   ```sh
   python3 "$SKILL/scripts/render.py" outputs/<name>.mp4
   ```

6. **Review.** Make a contact sheet and grab the last frame, as described in [references/framework.md](references/framework.md#reviewing-the-result). A zero exit code is not enough. Check that the sidebar advances in order, that the box lands on the right element and that the video ends with **All goals completed**.

## Delivery

State the duration, resolution, which goals were completed and any visible difference. If a goal failed, the sidebar shows it in red: say which one and what the check returned.
