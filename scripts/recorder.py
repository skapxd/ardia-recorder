"""Record an Ardia walkthrough with visible goals.

Usage from a scenario:

    with Recording('Title', 'Description', GOALS, url, tab='Tab title') as r:
        with r.goal(0):
            r.point('.selector', 'On-screen label')
            r.act('click', '.selector')
        with r.goal(1):
            r.tab('inbox', 'https://mail.example/inbox')   # open a second tab and show it
            ...
            r.tab('main')                                  # back to the first one

Capture methods, in order (take.json records the one used in `capture`):
  video        Ardia's own recorder (`ardia browse record`), once Ardia allows it.
  window       The Ardia window via ScreenCaptureKit (window_capture.swift), smooth and unaffected
               by other windows. The page area is found with calibration marks, so nothing about
               the screen or window position is configured. Needs screen recording permission.
  screenshots  `ardia browse screenshot` in a loop (about 8 fps). The renderer animates the
               pointer so it still moves smoothly. Needs nothing.
Writes the take to work/take.mov and the timeline to work/take.json, relative to the current directory.
With RECORD=0 in the environment, runs the flow without capturing.
"""
import hashlib, json, os, re, select, shutil, signal, threading, time, subprocess as sp
from contextlib import contextmanager
from pathlib import Path

OVERLAY = Path(__file__).resolve().parent / 'overlay.js'
HELPER_SRC = Path(__file__).resolve().parent / 'window_capture.swift'


def helper():
    """Compile window_capture.swift once per version into the user cache. None if it can't be built."""
    digest = hashlib.sha256(HELPER_SRC.read_bytes()).hexdigest()[:12]
    binary = Path.home() / 'Library/Caches/ardia-recorder' / f'window_capture-{digest}'
    if not binary.exists():
        if not shutil.which('swiftc'):
            return None
        binary.parent.mkdir(parents=True, exist_ok=True)
        r = sp.run(['swiftc', '-O', str(HELPER_SRC), '-o', str(binary)], capture_output=True, text=True)
        if r.returncode:
            print('ardia-recorder: could not build window_capture:', r.stderr.strip()[-300:])
            return None
    return binary


class Recording:
    def __init__(self, title, description, goals, url, tab=None, lang='en', output='work/take', label='main'):
        self.meta = {'title': title, 'description': description, 'tab': tab, 'lang': lang,
                     'goals': [{'title': g[0], 'detail': g[1]} for g in goals]}
        self.url, self.output = url, output
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        self.events, self.record = [], os.environ.get('RECORD', '1') != '0'
        self._url = None
        self.first, self.tabs, self.active = label, {}, label  # tabs: label -> {'id', 'title'}
        self._busy = threading.Lock()  # screenshots never run in the middle of an action (they can drop a hover)

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

    def _current_tab_id(self):
        """The t-id of the tab this session is acting on (marked with an arrow in `tab list`)."""
        m = re.search(r'^\s*→\s*\[(t\d+)\]', self.cli('tab', 'list'), re.M)
        if not m:
            raise RuntimeError('Could not find the session tab')
        return m.group(1)

    def _ensure_overlay(self):
        """Inject the overlay into the current page if it is not there (new tab, reload, navigation)."""
        if json.loads(self.cli('eval', 'typeof window.ardiaOverlay')) == 'undefined':
            self.cli('eval', OVERLAY.read_text())
            self.cli('eval', 'ardiaOverlay.pointer(false)')  # render.py draws the pointer

    def _tabs_event(self, switch=None):
        """switch: (start, end) of a tab change, so render.py can cross-fade the page over it."""
        labels = list(self.tabs)
        extra = {'switch': [round(switch[0], 3), round(switch[1], 3)]} if switch else {}
        self._event(type='tabs', tabs=[self.tabs[l]['title'] for l in labels], active=labels.index(self.active), **extra)

    def _capture(self):
        """Take page screenshots as fast as Ardia returns them, each stamped with its time."""
        while not self._stop.is_set():
            with self._busy:
                t, path = self.t(), self.frames_dir / f'{len(self.frames):05d}.png'
                r = sp.run(['ardia', 'browse', 'screenshot', str(path)], capture_output=True)
            if r.returncode == 0 and path.exists():
                self.frames.append((t, path.name))

    def _start_video(self):
        """Try Ardia's own recorder. Returns True if it started; False if Ardia refuses it."""
        self.video = Path(self.output + '.webm').resolve()
        self.video.unlink(missing_ok=True)
        r = sp.run(['ardia', 'browse', '--json', 'record', 'start', str(self.video)], text=True, capture_output=True)
        try:
            res = json.loads(r.stdout)
        except ValueError:
            res = {'success': False, 'code': None, 'error': r.stderr + r.stdout}
        if res.get('success'):
            return True
        if res.get('code') != 'policy_refused':
            print('ardia-recorder: video recording failed, using screenshots:', res.get('error', '').strip()[:200])
        return False

    def _start_window(self):
        """Record the Ardia window with ScreenCaptureKit. Returns False if it is not possible here."""
        binary = helper()
        if not binary:
            return False
        self.cli('eval', 'ardiaOverlay.marks(true)')
        time.sleep(.4)
        r = sp.run([str(binary), 'calibrate'], capture_output=True, text=True, timeout=30)
        self.cli('eval', 'ardiaOverlay.marks(false)')
        if r.returncode:
            reason = 'no screen recording permission' if r.returncode == 3 else r.stderr.strip()[:200]
            print(f'ardia-recorder: window capture unavailable ({reason}), using screenshots')
            return False
        self.area = json.loads(r.stdout)
        self.window_raw = Path(self.output + '-window.mov').resolve()
        start_wall = time.time() - self.t()
        self.window_proc = sp.Popen([str(binary), 'record', str(self.window_raw), str(self.area['window'])],
                                    stdout=sp.PIPE, stderr=sp.PIPE, text=True)
        ready, _, _ = select.select([self.window_proc.stdout], [], [], 10)
        line = self.window_proc.stdout.readline() if ready else ''
        if not line.startswith('FIRST '):
            self.window_proc.kill()
            print('ardia-recorder: window capture did not start, using screenshots')
            return False
        self.window_offset = float(line.split()[1]) - start_wall
        return True

    def _encode_window(self):
        """Crop the window recording to the page, scale it to CSS size and align it to the timeline."""
        a = self.area
        w, h = self.page
        sp.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(self.window_raw), '-vf',
                f"crop={a['w']}:{a['h']}:{a['x']}:{a['y']},scale={w}:{h}:flags=lanczos,fps=30,"
                f"tpad=start_duration={max(self.window_offset, 0):.3f}:start_mode=clone",
                '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', self.output + '.mov'], check=True)

    def _page_size(self):
        return json.loads(self.cli('eval', '[innerWidth, innerHeight]'))

    def _encode_video(self):
        """Convert Ardia's recording to a constant 30 fps take at the page's CSS size."""
        w, h = self.page
        sp.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(self.video), '-vf', f'scale={w}:{h}:flags=lanczos,fps=30',
                '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', self.output + '.mov'], check=True)

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
        w, h = self.page
        sp.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
                '-i', str(self.frames_dir / 'frames.txt'), '-vf', f'scale={w}:{h}:flags=lanczos,fps=30',
                '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', self.output + '.mov'], check=True)

    def __enter__(self):
        self.cli('open', self.url, '--show')
        self.tabs[self.first] = {'id': self._current_tab_id(), 'title': self.meta['tab'] or self.cli('get', 'title').strip()}
        self.capture = None
        self.start = time.monotonic()
        if self.record and self._start_video():
            self.capture = 'video'
        self._tabs_event()
        self._watch_url()
        self.cli('eval', OVERLAY.read_text())
        self.cli('eval', 'ardiaOverlay.pointer(false)')  # render.py draws the pointer, so it can reach the tabs
        if self.record and not self.capture and self._start_window():
            self.capture = 'window'
        if self.record and not self.capture:
            self.capture = 'screenshots'
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
        self.page = self._page_size()
        if self.capture == 'video':
            self.cli('record', 'stop')
            self._encode_video()
        elif self.capture == 'window':
            self.window_proc.send_signal(signal.SIGINT)
            self.window_proc.wait(timeout=30)
            self._encode_window()
        elif self.capture == 'screenshots':
            self._stop.set()
            self._thread.join(timeout=10)
            self._encode()
        fps = round(len(self.frames) / self.t(), 1) if self.capture == 'screenshots' else None
        Path(self.output + '.json').write_text(json.dumps(
            {**self.meta, 'events': self.events, 'capture': self.capture, 'page': self.page, 'screenshot_fps': fps},
            ensure_ascii=False, indent=1))
        for label, tab in self.tabs.items():  # close the tabs r.tab() opened; keep the first one
            if label != self.first:
                self.cli('tab', 'close', tab['id'])
        self.cli('tab', self.tabs[self.first]['id'])
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

    def tab(self, label, url=None, title=None):
        """Open a new tab (with url) or go back to an open one, and show it in Ardia.

        The sidebar of the video lists every tab opened so far and highlights the active one.
        title is the tab text in that sidebar; by default, the page title."""
        if url and label in self.tabs:
            raise ValueError(f'Tab {label!r} is already open')
        if not url and label not in self.tabs:
            raise ValueError(f'Unknown tab {label!r}: open it with r.tab({label!r}, url)')
        # The pointer goes to "New Tab" or to the tab in the sidebar and clicks it before the switch.
        self._event(type='tab_click', target='new' if url else list(self.tabs).index(label))
        time.sleep(1.1)
        start = self.t()
        if url:
            self.cli('tab', 'new', '--label', label, url)
            self.tabs[label] = {'id': self._current_tab_id(), 'title': None}
        with self._busy:
            self.cli('tab', self.tabs[label]['id'], '--show')
        self.active = label
        self._ensure_overlay()
        self.tabs[label]['title'] = title or self.tabs[label]['title'] or self.cli('get', 'title').strip()
        self._tabs_event(switch=(start, self.t()))
        self._watch_url()
        time.sleep(.9)

    def point(self, selector, label):
        self._ensure_overlay()
        pos = json.loads(self.cli('eval', f'ardiaOverlay.point({json.dumps(selector)},{json.dumps(label, ensure_ascii=False)})'))
        self._event(type='point', x=round(pos['x'], 1), y=round(pos['y'], 1))
        time.sleep(1.2)

    def act(self, *args):
        time.sleep(.4)
        with self._busy:
            out = self.cli(*args)
        time.sleep(.9)
        self._ensure_overlay()
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
