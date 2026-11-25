# Framework: goal-driven walkthrough videos with Ardia

> Spanish version: [framework.es.md](framework.es.md).

Records a walkthrough an agent performs with `ardia browse` and exports it as a 30 fps MP4 sized to the captured viewport. On the left, a sidebar shows the task's goals, their progress and how long each one took. On the right, the real page appears inside an Ardia-style window, with an address bar over the page that shows the current host and path. Inside the page, a virtual pointer moves to each element, and a red box with an arrow and a label marks it before every action.

In the commands below, `$SKILL` is the folder where this skill is installed.

## Requirements

- macOS with Ardia open and **Settings → Advanced → Command line and automation → Let programs control Ardia** turned on.
- Python 3 (standard library only), FFmpeg with `libx264`, and Google Chrome, which turns the HTML frame into images.

Optional, for smooth capture: screen recording permission for the terminal that runs the scenario, and Xcode's command line tools (`swiftc`) to build the window capture helper. Tested with the Ardia app 0.2.48 and the `ardia` CLI 0.6.0.

```sh
command -v ardia ffmpeg ffprobe python3
ardia --version
defaults read /Applications/Ardia.app/Contents/Info.plist CFBundleShortVersionString
ffmpeg -hide_banner -encoders | grep libx264
ls "/Applications/Google Chrome.app"
```

## Files

| File | What it does |
|---|---|
| `scripts/recorder.py` | `Recording` class: opens the page, captures it while the steps run (see [Capture and framing](#capture-and-framing)), and saves the take to `work/take.mov` and the timeline to `work/take.json`. |
| `scripts/window_capture.swift` | Records the Ardia window with ScreenCaptureKit and finds the page in it. Built once with `swiftc` into `~/Library/Caches/ardia-recorder/`. |
| `scripts/overlay.js` | Layer injected into the page: box, arrow, label and click pulse. It never intercepts clicks and removes itself at the end. The pointer is drawn by `render.py`, so it can also reach the window's tabs. |
| `scripts/frame.html` | Background, goals sidebar and an Ardia-style window. The page area stays transparent; keep it in sync with `PAGE_*` in `render.py`. |
| `scripts/render.py` | Combines `work/take.mov` and `work/take.json` into the final MP4. |

The take (`work/take.mov`, `work/take.json`) and the video are written to the folder you run from, not to the skill.

## Writing a scenario

```python
from recorder import Recording

GOALS = [
    ('Goal title', 'What happens, in one line'),
    ...
]

with Recording('Title', 'Description', GOALS, 'https://…', tab='Tab title') as r:
    with r.goal(0):
        r.point('#selector', 'On-screen label')
        r.act('click', '#selector')
        r.check(condition, 'Message if it fails')
```

| Call | Effect on the video |
|---|---|
| `Recording(title, description, goals, url, tab=None, lang='en', output='work/take')` | Title and description head the sidebar. `goals` is the list of `(title, detail)`. `tab` is the tab text; without it, the domain is used. `lang` (`'en'` or `'es'`) sets the language of the sidebar's own texts. |
| `with r.goal(i):` | Goal `i` becomes *in progress* and shows its detail. When the block ends it becomes *done*, with its duration, and the box is hidden. If anything fails inside, it becomes *failed* and the scenario exits with an error. |
| `r.point(selector, label)` | Moves the virtual pointer to the element and marks it with a box, arrow and label. Goes before the action. |
| `r.act(*args)` | Runs `ardia browse <args>` with a pause before and after so the response is visible. Returns its output. If the URL changes, the address bar updates. |
| `r.tab(label, url=None, title=None)` | With `url`, opens a new tab and shows it; without it, goes back to a tab already open. In the video, the pointer clicks "New Tab" or the tab in the sidebar, the old page slides out, a short notice names the tab now in front, and that tab glows for a moment; this adds about a second per change. The sidebar lists every tab opened so far and highlights the active one. `title` is the tab text (default: the page title); the first tab is `'main'`. The tabs it opened are closed at the end. |
| `r.ref(role, selector=None)` | Returns the accessibility reference (`@e123`) of the first element whose role and name match `role` (a regular expression over `snapshot -i --full`). With `selector`, it searches only inside it. |
| `r.cli(*args)` | Runs `ardia browse <args>` without pauses. For readings and checks. |
| `r.check(condition, detail)` | If the condition is false, the goal in progress becomes *failed*. |

For an element that only appears on hover, run `r.act('hover', …)` before `r.point`. The overlay is injected again on its own after a reload, a navigation or a tab change. [examples/todomvc-tabs/](../examples/todomvc-tabs/) shows a task across two tabs.

## Recording and exporting

1. Open the Ardia profile the task runs in. The window can be anywhere on any display, and other windows can cover it.
2. Dry run:

   ```sh
   RECORD=0 PYTHONPATH="$SKILL/scripts" python3 work/scenario.py
   ```

3. Record. It writes `work/take.mov` and `work/take.json`:

   ```sh
   PYTHONPATH="$SKILL/scripts" python3 work/scenario.py
   ```

4. Export with a new name per version. The second, optional argument is the take path without extension:

   ```sh
   python3 "$SKILL/scripts/render.py" outputs/<name>.mp4 work/take
   ```

## Capture and framing

The recorder tries three methods in order and records the one it used in `work/take.json` (`capture`):

| `capture` | How | Smoothness | Needs |
|---|---|---|---|
| `video` | `ardia browse record` | Real video | An Ardia version that allows it (today it answers `policy_refused`) |
| `window` | `window_capture.swift` records the Ardia window with ScreenCaptureKit | 30 fps, native resolution; other windows on top don't matter | Screen recording permission for the terminal, and `swiftc` |
| `screenshots` | `ardia browse screenshot` in a loop | Page at about 8 fps (the pointer is always drawn at 30 fps by `render.py`) | Nothing |

For `window`, the overlay briefly paints magenta marks in the page corners; the helper finds them in a capture of each Ardia window, which gives the window and the exact page area for any display, scale or window layout. When a method is not available, the recorder prints why and uses the next one. Every take is encoded at a constant 30 fps at the page's CSS size, aligned with the goals timeline.

The video grows with the captured viewport so the page is shown 1:1, never cropped or scaled: the page area is the viewport (at least 1131 × 982) and the video is that plus the goals sidebar and margins (1920 × 1120 for a 1131 × 982 viewport). A smaller page is centered and padded with white.

Check the take size before exporting:

```sh
ffprobe -v error -show_entries stream=width,height -of csv=p=0 work/take.mov
```

## Reviewing the result

```sh
ffprobe -v error -show_entries stream=width,height,r_frame_rate:format=duration -of compact outputs/<name>.mp4
ffmpeg -loglevel error -i outputs/<name>.mp4 -vf 'fps=0.5,scale=640:-2,tile=4x5' -frames:v 1 work/review.png
ffmpeg -loglevel error -sseof -0.5 -i outputs/<name>.mp4 -frames:v 1 work/last.png
```

In the contact sheet, every goal must go through *in progress* and *done* in order, with the box on the right element before each action. The last frame shows **All goals completed** and the page without the box.
