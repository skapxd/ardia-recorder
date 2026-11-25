"""Record an Ardia walkthrough with visible goals.

Usage from a scenario:

    with Recording('Title', 'Description', GOALS, url, tab='Tab title') as r:
        with r.goal(0):
            r.point('.selector', 'On-screen label')
            r.act('click', '.selector')

The page is captured from Ardia itself with `ardia browse screenshot`, so it does not depend
on the screen, the window position or screen recording permission. Writes the take to
work/take.mov and the timeline to work/take.json, relative to the current directory.
With RECORD=0 in the environment, runs the flow without capturing.
"""
import json, os, re, shutil, threading, time, subprocess as sp
from contextlib import contextmanager
from pathlib import Path

OVERLAY = Path(__file__).resolve().parent / 'overlay.js'


class Recording:
    def __init__(self, title, description, goals, url, tab=None, lang='en', output='work/take'):
        self.meta = {'title': title, 'description': description, 'tab': tab, 'lang': lang,
                     'goals': [{'title': g[0], 'detail': g[1]} for g in goals]}
        self.url, self.output = url, output
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        self.events, self.record = [], os.environ.get('RECORD', '1') != '0'
        self._url = None

    def cli(self, *args):
        r = sp.run(['ardia', 'browse', *args], text=True, capture_output=True)
        if r.returncode:
            raise RuntimeError(r.stderr + r.stdout)
        return r.stdout

    def t(self):
        return time.monotonic() - self.start

    def _event(self, **kw):
        self.events.append({'t': round(self.t(), 3), **kw})

    def _watch_url(self):
        url = self.cli('get', 'url').strip()
        if url != self._url:
            self._url = url
            self._event(type='url', url=url)

    def _capture(self):
        """Take page screenshots as fast as Ardia returns them, each stamped with its time."""
        while not self._stop.is_set():
            t, path = self.t(), self.frames_dir / f'{len(self.frames):05d}.png'
            r = sp.run(['ardia', 'browse', 'screenshot', str(path)], capture_output=True)
            if r.returncode == 0 and path.exists():
                self.frames.append((t, path.name))

    def _encode(self):
        """Turn the stamped screenshots into a constant 30 fps take at the page's CSS size."""
        if not self.frames:
            raise RuntimeError('No screenshots were captured')
        lines = ['ffconcat version 1.0']
        times = [0] + [t for t, _ in self.frames[1:]] + [self.t()]
        for (_, name), a, b in zip(self.frames, times, times[1:]):
            lines += [f'file {name}', f'duration {max(b - a, 0.001):.3f}']
        lines.append(f'file {self.frames[-1][1]}')
        (self.frames_dir / 'frames.txt').write_text('\n'.join(lines) + '\n')
        w, h = json.loads(self.cli('eval', '[innerWidth, innerHeight]'))
        sp.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
                '-i', str(self.frames_dir / 'frames.txt'), '-vf', f'scale={w}:{h}:flags=lanczos,fps=30',
                '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', self.output + '.mov'], check=True)

    def __enter__(self):
        self.cli('open', self.url, '--show')
        self.start = time.monotonic()
        self._watch_url()
        self.cli('eval', OVERLAY.read_text())
        if self.record:
            self.frames_dir = Path(self.output + '-frames')
            shutil.rmtree(self.frames_dir, ignore_errors=True)
            self.frames_dir.mkdir(parents=True)
            self.frames, self._stop = [], threading.Event()
            self._thread = threading.Thread(target=self._capture, daemon=True)
            self._thread.start()
        time.sleep(1.5)
        return self

    def __exit__(self, *exc):
        time.sleep(3)  # hold the final state
        if self.record:
            self._stop.set()
            self._thread.join(timeout=10)
            self._encode()
        Path(self.output + '.json').write_text(json.dumps(
            {**self.meta, 'events': self.events, 'fps': round(len(self.frames) / self.t(), 1) if self.record else None},
            ensure_ascii=False, indent=1))
        self.cli('eval', 'window.ardiaOverlay?.remove()')

    @contextmanager
    def goal(self, i):
        self._event(type='goal', i=i, state='active')
        time.sleep(.8)
        try:
            yield
        except Exception:
            self._event(type='goal', i=i, state='failed')
            raise
        self.cli('eval', 'ardiaOverlay.hide()')
        self._event(type='goal', i=i, state='done')
        time.sleep(.9)

    def point(self, selector, label):
        self.cli('eval', f'ardiaOverlay.point({json.dumps(selector)},{json.dumps(label, ensure_ascii=False)})')
        time.sleep(1.2)

    def act(self, *args):
        time.sleep(.4)
        out = self.cli(*args)
        time.sleep(.9)
        self._watch_url()
        return out

    def ref(self, role, selector=None):
        args = ['snapshot', '-i', '--full'] + (['-s', selector] if selector else [])
        snap = self.cli(*args)
        m = re.search(r'^.*?' + role + r'.*?\bref=(e\d+)\]', snap, re.M)
        if not m:
            raise RuntimeError(snap)
        return '@' + m.group(1)

    def check(self, condition, detail):
        if not condition:
            raise AssertionError(detail)
