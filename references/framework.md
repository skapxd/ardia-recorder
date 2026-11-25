# Framework: goal-driven walkthrough videos with Ardia

> Spanish version: [framework.es.md](framework.es.md).

Records a walkthrough an agent performs with `ardia browse` and exports it as a 1920 × 1080, 30 fps MP4. On the left, a sidebar shows the task's goals, their progress and how long each one took. On the right, the real page appears inside a browser window with its URL. Inside the page, a virtual pointer moves to each element, and a red box with an arrow and a label marks it before every action.

In the commands below, `$SKILL` is the folder where this skill is installed.

## Requirements

- macOS with Ardia open and **Settings → Advanced → Command line and automation → Let programs control Ardia** turned on.
- Python 3 (standard library only), FFmpeg with `libx264`, and Google Chrome, which turns the HTML frame into images.

Tested with the Ardia app 0.2.48 and the `ardia` CLI 0.6.0. Ardia does not allow in-browser video recording yet (`ardia browse record` fails with `policy_refused`), so the recorder takes page screenshots instead. It tries video first on every take, so it switches to video by itself once an Ardia version allows it.

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
| `scripts/recorder.py` | `Recording` class: opens the page, captures it with `ardia browse record` or, while Ardia refuses that, `ardia browse screenshot` while the steps run, and saves the take to `work/take.mov` and the timeline to `work/take.json`. |
| `scripts/overlay.js` | Layer injected into the page: virtual pointer, box, arrow, label and click pulse. It never intercepts clicks and removes itself at the end. |
| `scripts/frame.html` | Background, goals sidebar and browser window. The page area stays transparent. |
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
| `r.ref(role, selector=None)` | Returns the accessibility reference (`@e123`) of the first element whose role and name match `role` (a regular expression over `snapshot -i --full`). With `selector`, it searches only inside it. |
| `r.cli(*args)` | Runs `ardia browse <args>` without pauses. For readings and checks. |
| `r.check(condition, detail)` | If the condition is false, the goal in progress becomes *failed*. |

For an element that only appears on hover, run `r.act('hover', …)` before `r.point`. If the site reloads the whole page when navigating, inject the layer again with `r.cli('eval', OVERLAY.read_text())`, importing `OVERLAY` from `recorder`.

## Recording and exporting

1. Open the Ardia profile the task runs in. The capture comes from the page itself, so the window can be anywhere and other windows can cover it.
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

The recorder starts `ardia browse record` first. If Ardia accepts it, the take is real video. If Ardia answers `policy_refused`, as it does today, the page is captured as fast as Ardia returns screenshots (about 8 fps on a recent Mac); any other error falls back the same way and is printed. Either way, the take is encoded at a constant 30 fps at the page's CSS size, and `work/take.json` records the method in `capture` (`video` or `screenshots`). Each screenshot keeps the time it was taken, so the sidebar stays in sync with the page.

The frame shows a 1340 × 908 area of the page: centered horizontally and aligned to the top. A larger page is cropped; a smaller one is padded with white. If the app sits outside that area, resize the Ardia window before recording.

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
