# ardia-recorder

[Español](README.es.md)

Agent skill that records a walkthrough performed with [Ardia](https://ardia.dev) (`ardia browse`) and exports it as a 1920 × 1080 MP4. A sidebar shows the task's goals, which one is in progress, which ones are done and how long each took. The page appears inside an Ardia-style window (vertical tabs, the real host in the address field), and a virtual pointer marks each element before acting on it.

Use it to keep evidence of e2e tests, or to show step by step how a task is completed on a website.

[![Demo: goals sidebar on the left, TodoMVC on the right](assets/demo.gif)](assets/demo.mp4)

Full video: [assets/demo.mp4](assets/demo.mp4) (38 s, 1920 × 1080).

## Install

With [APM](https://microsoft.github.io/apm/):

```sh
apm install --global 'skapxd/ardia-recorder#^1.0.0' --target claude,codex
```

- **Source:** APM downloads it straight from this GitHub repository. `skapxd/ardia-recorder` is short for `https://github.com/skapxd/ardia-recorder`, and either form works.
- **Version:** `#^1.0.0` installs the latest 1.x release, and `apm update` moves to newer ones. Use a tag such as `#v1.2.0` to stay on one version. Without a version, APM installs the latest commit on `main`.
- **Agents:** `--target` sets which agents get the skill (`claude`, `codex` or any other APM supports). Without it, APM uses the `targets` in `~/.apm/apm.yml`.

Without APM, clone the repository into your agent's skills folder. For Claude Code:

```sh
git clone --branch v1.2.0 https://github.com/skapxd/ardia-recorder ~/.claude/skills/ardia-recorder
```

### Verifying provenance

Every release includes `ardia-recorder-<version>.tar.gz`, built by GitHub Actions from the tag, with a signed build provenance attestation (SLSA, Sigstore). To check it and install from that package:

```sh
gh release download v1.2.0 -R skapxd/ardia-recorder -p 'ardia-recorder-*.tar.gz'
gh attestation verify ardia-recorder-v1.2.0.tar.gz -R skapxd/ardia-recorder
tar -xzf ardia-recorder-v1.2.0.tar.gz
apm install --global "$PWD/ardia-recorder"
```

## Requirements

- macOS with Ardia open and **Settings → Advanced → Command line and automation → Let programs control Ardia** turned on.
- Python 3, FFmpeg with `libx264`, and Google Chrome.

Optional: screen recording permission for the terminal and Xcode's command line tools (`swiftc`) give a smooth window capture; without them the page is captured with screenshots. Tested with the Ardia app 0.2.48 and the `ardia` CLI 0.6.0.

## Usage

Ask your agent something like *"record a video of creating and deleting a task on this site, with the goals on the left"*. The skill tells it how to turn the request into goals, write the scenario, dry-run it, record it, export it and review the result.

A scenario is a short Python file:

```python
from recorder import Recording

GOALS = [
    ('Create a task', 'Type the text and confirm with Enter'),
    ('Delete the task', 'Remove it from the list with the ✕'),
]

with Recording('Task lifecycle', 'E2E test on TodoMVC', GOALS,
               'https://demo.playwright.dev/todomvc/#/active') as r:
    with r.goal(0):
        r.point('.new-todo', 'Type a new task')
        r.act('type', r.ref('textbox'), 'Buy bread')
        r.act('press', 'Enter')
        r.check('Buy bread' in r.cli('get', 'text', '.todo-list'), 'The task was not created')
    ...
```

The sidebar texts can be in English or Spanish (`lang='es'`).

- The API and framing adjustments are in [references/framework.md](references/framework.md).
- Complete example tasks: [examples/todomvc/](examples/todomvc/) (one tab) and [examples/todomvc-tabs/](examples/todomvc-tabs/) (two tabs, with `r.tab()`).

## Layout

| Path | Contents |
|---|---|
| `SKILL.md` | Instructions for the agent (Spanish: `SKILL.es.md`) |
| `scripts/` | Recording (`recorder.py`), highlights (`overlay.js`), frame (`frame.html`) and export (`render.py`) |
| `references/` | Scenario API, adjustments and review (`framework.md`, `framework.es.md`) |
| `examples/` | Example tasks and scenarios: one tab and two tabs |

## License

MIT
