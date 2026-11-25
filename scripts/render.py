"""Compose <take>.mov + <take>.json into an MP4 with a goals sidebar, sized to show the page 1:1.

    python3 render.py outputs/name.mp4 [work/take]
"""
import copy, json, sys, tempfile, subprocess as sp
from pathlib import Path
from urllib.parse import quote

ASSETS = Path(__file__).resolve().parent
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else 'outputs/walkthrough.mp4')
TAKE = Path(sys.argv[2] if len(sys.argv) > 2 else 'work/take').resolve()
W = TAKE.parent
OUT.parent.mkdir(parents=True, exist_ok=True)
OFFSET = 0               # seconds the sidebar changes are moved earlier; the capture shares the script clock
# The page area of frame.html (keep both in sync). It grows with the captured viewport so the page
# is shown 1:1, never cropped or scaled; the video grows with it. A page smaller than the minimum
# area is centered and padded with white. MARGIN is the space right and below the window.
PAGE_X, PAGE_Y, MIN_W, MIN_H, MARGIN = 740, 89, 1131, 982, 49   # PAGE_Y leaves room for the address bar
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

POINTER_HTML = ('data:text/html,<body style="margin:0"><svg width="22" height="30" viewBox="0 0 22 30" '
                'style="position:absolute;left:2px;top:2px;filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))">'
                '<path d="M2 2v22l5.5-5.2 3.6 8.4 3.7-1.6-3.6-8.2H19z" fill="%23111" stroke="%23fff" '
                'stroke-width="2" stroke-linejoin="round"/></svg>')
TIP = 4      # the pointer's tip inside pointer.png
# Sidebar targets in frame.html (keep in sync): the "New Tab" row and the first tab row, then one row every TABS_STEP.
NEW_TAB = (600, 151)
TABS_X, TABS_Y, TABS_STEP = 610, 193, 37
RING = ('data:text/html,' + quote('<body style="margin:0"><div style="margin:4px;width:40px;height:40px;border-radius:50%;'
        'background:rgba(37,99,235,.3);border:3px solid rgba(37,99,235,.95);box-sizing:border-box"></div>'))
MOVE = .8    # seconds the pointer takes to reach a target, as in overlay.js


def snap(png, url, size=None, tries=3):
    size = size or f'{VIDEO_W},{VIDEO_H}'
    """Render a page to a transparent PNG. Headless Chrome fails now and then: retry."""
    cmd = [CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--default-background-color=00000000',
           f'--user-data-dir={tempfile.mkdtemp(prefix="ardia-recorder-chrome-")}',
           f'--window-size={size}', f'--screenshot={png}', url]
    for n in range(tries):
        png.unlink(missing_ok=True)
        r = sp.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and png.exists():
            return
    raise RuntimeError(f'Chrome could not render {png.name}: {r.stderr[-500:]}')


TOAST = {'en': ('New tab', 'Back to'), 'es': ('Nueva pestaña', 'De vuelta a')}
SLIDE, FLASH, TOAST_FOR = .5, 1.4, 1.8   # seconds: old page slides out, new tab glows, notice stays

take = json.loads(TAKE.with_suffix('.json').read_text())
W_PAGE, H_PAGE = take.get('page') or (MIN_W, MIN_H)
# Even sizes: libx264 with yuv420p needs them.
PAGE_W, PAGE_H = max(MIN_W, W_PAGE + W_PAGE % 2), max(MIN_H, H_PAGE + H_PAGE % 2)
VIDEO_W, VIDEO_H = PAGE_X + PAGE_W + MARGIN, PAGE_Y + PAGE_H + MARGIN
VIDEO_W, VIDEO_H = VIDEO_W + VIDEO_W % 2, VIDEO_H + VIDEO_H % 2
FIT = f'pad={PAGE_W}:{PAGE_H}:(ow-iw)/2:0:color=white'
lang = take.get('lang', 'en')
dec = ',' if lang == 'es' else '.'
state = {'title': take['title'], 'description': take['description'], 'tab': take.get('tab'), 'lang': lang,
         'url': None, 'page': [PAGE_W, PAGE_H], 'video': [VIDEO_W, VIDEO_H], 'goals': [{**g, 'state': 'pending'} for g in take['goals']]}
started, states, switches, count = {}, [], [], 1
for e in take['events']:
    if e['type'] in ('point', 'tab_click'):
        continue
    t = 0 if not states else max(0, e['t'] - OFFSET)
    fade = .18
    if e['type'] == 'url':
        state['url'] = e['url']
    elif e['type'] == 'tabs':
        state['tabs'], state['active'] = e['tabs'], e['active']
        if 'switch' in e:
            # A tab change: remember it for the page transition and make the new tab glow for a moment.
            t0, t1 = (x - OFFSET for x in e['switch'])
            switches.append({'t0': t0, 't1': t1, 'new': len(e['tabs']) > count, 'title': e['tabs'][e['active']]})
            state['flash'], fade = e['active'], .4
        count = len(e['tabs'])
    else:
        g = state['goals'][e['i']]
        g['state'] = e['state']
        if e['state'] == 'active':
            started[e['i']] = e['t']
        else:
            g['dur'] = f"{e['t'] - started[e['i']]:.1f} s".replace('.', dec)
    if 'flash' in state and switches and t >= switches[-1]['t1'] + FLASH:
        del state['flash']
    if states and abs(states[-1][0] - t) < .05:
        states.pop()
    states.append((t, copy.deepcopy(state), fade))
for sw in switches:  # end each glow on its own, even if nothing else happens
    te = sw['t1'] + FLASH
    before = [x for x in states if x[0] <= te]
    if before and 'flash' in before[-1][1]:
        calm = copy.deepcopy(before[-1][1]); del calm['flash']
        states.append((te, calm, .4))
states.sort(key=lambda x: x[0])


def eased(axis, points, start):
    """ffmpeg expression for the pointer position: eased moves from one target to the next."""
    expr, prev = [f'{start:.1f}'], start
    for p in points:
        s = f'clip((t-{p["t"] - OFFSET:.3f})/{MOVE},0,1)'
        expr.append(f'{p[axis] - prev:.1f}*{s}*{s}*(3-2*{s})')
        prev = p[axis]
    return '+'.join(expr) + f'-{TIP}'


def toast_html(text):
    return ('data:text/html,' + quote(
        '<meta charset="utf-8"><body style="margin:0;display:flex;justify-content:center;padding-top:6px">'
        '<div style="background:#17130f;color:#f1ece2;font:600 19px/1 -apple-system,system-ui;padding:14px 20px;'
        'border-radius:8px;box-shadow:0 1px 2px rgba(22,19,15,.2),0 10px 24px -6px rgba(22,19,15,.45)">'
        f'<span style="color:#fbb927">{text[0]}</span> · {text[1]}</div>'))


END = take['events'][-1]['t'] - OFFSET + 3
# Pointer targets in video coordinates: point() targets inside the page, and tab clicks in the sidebar.
dx = PAGE_X + (PAGE_W - W_PAGE) // 2
points, clicks = [], []
for e in take['events']:
    if e['type'] == 'point':
        points.append({'t': e['t'], 'x': dx + e['x'], 'y': PAGE_Y + e['y']})
    elif e['type'] == 'tab_click':
        x, y = NEW_TAB if e['target'] == 'new' else (TABS_X, TABS_Y + TABS_STEP * e['target'])
        points.append({'t': e['t'], 'x': x, 'y': y})
        clicks.append((e['t'] - OFFSET + MOVE, x, y))
ins, f = ['-i', str(TAKE.with_suffix('.mov'))], [f'color=0x121524:s={VIDEO_W}x{VIDEO_H}:r=30[bg]']
f.append(f'[0:v]fps=30:eof_action=pass,setsar=1,tpad=stop_mode=clone:stop_duration=10,trim=duration={END:.2f}[pg0]')
cur = 'pg0'
for k, sw in enumerate(switches):
    # The old page stays put while Ardia switches, then slides out to the left, revealing the new tab.
    still = W / f'switch-{k}.png'
    sp.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f"{max(sw['t0'] - .05, 0):.3f}", '-i', str(TAKE.with_suffix('.mov')),
            '-frames:v', '1', str(still)], check=True)
    ins += ['-loop', '1', '-framerate', '30', '-i', str(still)]
    s_ = f"clip((t-{sw['t1']:.3f})/{SLIDE},0,1)"
    f.append(f"[{ins.count('-i') - 1}:v]format=rgba[sn{k}]")
    f.append(f"[{cur}][sn{k}]overlay=x='-{W_PAGE}*{s_}*{s_}*(3-2*{s_})':y=0:shortest=1:"
             f"enable='between(t,{sw['t0']:.3f},{sw['t1'] + SLIDE:.3f})'[pa{k}]")
    # A short notice on top of the page says which tab is now in front.
    toast = W / f'toast-{k}.png'
    words = TOAST.get(lang, TOAST['en'])
    snap(toast, toast_html((words[0] if sw['new'] else words[1], sw['title'])), size='900,90')
    ins += ['-loop', '1', '-framerate', '30', '-i', str(toast)]
    f.append(f"[{ins.count('-i') - 1}:v]format=rgba,fade=in:st={sw['t1']:.3f}:d=0.25:alpha=1,"
             f"fade=out:st={sw['t1'] + TOAST_FOR - .35:.3f}:d=0.35:alpha=1[to{k}]")
    f.append(f"[pa{k}][to{k}]overlay=x=(main_w-overlay_w)/2:y=22:shortest=1:"
             f"enable='between(t,{sw['t1']:.3f},{sw['t1'] + TOAST_FOR:.3f})'[pb{k}]")
    cur = f'pb{k}'
f.append(f'[{cur}]{FIT}[app]')
f.append(f'[bg][app]overlay={PAGE_X}:{PAGE_Y}:shortest=1[v0]')
first = ins.count('-i')  # index of the first frame input
for i, (t, s, fade) in enumerate(states):
    png = W / f'frame-{i:02d}.png'
    snap(png, f'file://{ASSETS}/frame.html?s=' + quote(json.dumps(s, ensure_ascii=False)))
    ins += ['-framerate', '30', '-loop', '1', '-i', str(png)]
    fx = f',fade=in:st={t:.3f}:d={fade}:alpha=1' if i else ''
    f.append(f'[{first + i}:v]format=rgba{fx}[m{i}]')
    f.append(f"[v{i}][m{i}]overlay=0:0:shortest=1:enable='gte(t,{t:.3f})'[v{i + 1}]")
last = f'v{len(states)}'
for k, (tc, x, y) in enumerate(clicks):
    # The click on a sidebar tab: a ring that fades out where the pointer lands.
    ring = W / 'ring.png'
    if not ring.exists():
        snap(ring, RING, size='200,200')
    ins += ['-loop', '1', '-framerate', '30', '-i', str(ring)]
    f.append(f"[{ins.count('-i') - 1}:v]crop=48:48:0:0,format=rgba,fade=out:st={tc:.3f}:d=0.6:alpha=1[ring{k}]")
    f.append(f"[{last}][ring{k}]overlay={x - 24:.0f}:{y - 24:.0f}:shortest=1:enable='between(t,{tc:.3f},{tc + .6:.3f})'[c{k}]")
    last = f'c{k}'
if points:
    # One pointer for the whole video, drawn at 30 fps, so it can move from the page to the tabs.
    snap(W / 'pointer.png', POINTER_HTML, size='200,200')
    ins += ['-loop', '1', '-framerate', '30', '-i', str(W / 'pointer.png')]
    f.append(f"[{ins.count('-i') - 1}:v]crop=30:38:0:0,format=rgba[ptr]")
    start = (PAGE_X + PAGE_W / 2, PAGE_Y + PAGE_H / 2)
    f.append(f"[{last}][ptr]overlay=x='{eased('x', points, start[0])}':y='{eased('y', points, start[1])}':shortest=1[pt]")
    last = 'pt'
f.append(f'[{last}]format=yuv420p[out]')

sp.run(['ffmpeg', '-y', '-loglevel', 'error', *ins, '-filter_complex', ';'.join(f), '-map', '[out]', '-r', '30',
        '-c:v', 'libx264', '-crf', '17', '-preset', 'slow', '-movflags', '+faststart', str(OUT)], check=True)
print(OUT, len(states), 'states,', len(switches), 'tab switches')
