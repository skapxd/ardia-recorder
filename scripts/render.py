"""Compose <take>.mov + <take>.json into a 1920x1080 MP4 with a goals sidebar.

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
# The frame's page area is 1340x908: center the page horizontally, keep its top, pad if it is smaller.
FIT = 'crop=min(iw\\,1340):min(ih\\,908):(iw-min(iw\\,1340))/2:0,pad=1340:908:(ow-iw)/2:0:color=white'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

POINTER_HTML = ('data:text/html,<body style="margin:0"><svg width="22" height="30" viewBox="0 0 22 30" '
                'style="position:absolute;left:2px;top:2px;filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))">'
                '<path d="M2 2v22l5.5-5.2 3.6 8.4 3.7-1.6-3.6-8.2H19z" fill="%23111" stroke="%23fff" '
                'stroke-width="2" stroke-linejoin="round"/></svg>')
TIP = 4      # the pointer's tip inside pointer.png
MOVE = .8    # seconds the pointer takes to reach a target, as in overlay.js


def snap(png, url, size='1920,1080', tries=3):
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


take = json.loads(TAKE.with_suffix('.json').read_text())
lang = take.get('lang', 'en')
dec = ',' if lang == 'es' else '.'
state = {'title': take['title'], 'description': take['description'], 'tab': take.get('tab'), 'lang': lang,
         'url': None, 'goals': [{**g, 'state': 'pending'} for g in take['goals']]}
started, states = {}, []
for e in take['events']:
    if e['type'] == 'point':
        continue
    if e['type'] == 'url':
        state['url'] = e['url']
    else:
        g = state['goals'][e['i']]
        g['state'] = e['state']
        if e['state'] == 'active':
            started[e['i']] = e['t']
        else:
            g['dur'] = f"{e['t'] - started[e['i']]:.1f} s".replace('.', dec)
    t = 0 if not states else max(0, e['t'] - OFFSET)
    if states and abs(states[-1][0] - t) < .05:
        states.pop()
    states.append((t, copy.deepcopy(state)))

def eased(axis, points, start):
    """ffmpeg expression for the pointer position: eased moves from one point() target to the next."""
    expr, prev = [str(start)], start
    for p in points:
        s = f'clip((t-{p["t"] - OFFSET:.3f})/{MOVE},0,1)'
        expr.append(f'{p[axis] - prev:.1f}*{s}*{s}*(3-2*{s})')
        prev = p[axis]
    return '+'.join(expr) + f'-{TIP}'


END = take['events'][-1]['t'] - OFFSET + 3
points = [e for e in take['events'] if e['type'] == 'point']
ins, f = ['-i', str(TAKE.with_suffix('.mov'))], ['color=0x121524:s=1920x1080:r=30[bg]']
page = f'[0:v]fps=30:eof_action=pass,setsar=1,tpad=stop_mode=clone:stop_duration=10,trim=duration={END:.2f}'
if take.get('capture') == 'screenshots' and points:
    # The page was captured at ~8 fps: draw the pointer here so it moves at the video's frame rate.
    snap(W / 'pointer.png', POINTER_HTML, size='200,200')
    ins += ['-loop', '1', '-framerate', '30', '-i', str(W / 'pointer.png')]
    f.append(f'[1:v]crop=30:38:0:0,format=rgba[ptr]')
    f.append(f"{page}[pg];[pg][ptr]overlay=x='{eased('x', points, 0)}':y='{eased('y', points, 0)}':shortest=1,{FIT}[app]")
else:
    f.append(f'{page},{FIT}[app]')
f.append('[bg][app]overlay=540:132:shortest=1[v0]')
first = ins.count('-i')  # index of the first frame input
for i, (t, s) in enumerate(states):
    png = W / f'frame-{i:02d}.png'
    snap(png, f'file://{ASSETS}/frame.html?s=' + quote(json.dumps(s, ensure_ascii=False)))
    ins += ['-framerate', '30', '-loop', '1', '-i', str(png)]
    fade = f',fade=in:st={t:.3f}:d=0.18:alpha=1' if i else ''
    f.append(f'[{first + i}:v]format=rgba{fade}[m{i}]')
    f.append(f"[v{i}][m{i}]overlay=0:0:shortest=1:enable='gte(t,{t:.3f})'[v{i + 1}]")
f.append(f'[v{len(states)}]format=yuv420p[out]')

sp.run(['ffmpeg', '-y', '-loglevel', 'error', *ins, '-filter_complex', ';'.join(f), '-map', '[out]', '-r', '30',
        '-c:v', 'libx264', '-crf', '17', '-preset', 'slow', '-movflags', '+faststart', str(OUT)], check=True)
print(OUT, len(states), 'states')
