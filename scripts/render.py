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

def snap(png, s, tries=3):
    """Render frame.html with this state to a transparent PNG. Headless Chrome fails now and then: retry."""
    cmd = [CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--default-background-color=00000000',
           f'--user-data-dir={tempfile.mkdtemp(prefix="ardia-recorder-chrome-")}',
           '--window-size=1920,1080', f'--screenshot={png}',
           f'file://{ASSETS}/frame.html?s=' + quote(json.dumps(s, ensure_ascii=False))]
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

END = take['events'][-1]['t'] - OFFSET + 3
ins, f = ['-i', str(TAKE.with_suffix('.mov'))], [
    'color=0x121524:s=1920x1080:r=30[bg]',
    f'[0:v]fps=30:eof_action=pass,{FIT},setsar=1,tpad=stop_mode=clone:stop_duration=10,trim=duration={END:.2f}[app]',
    '[bg][app]overlay=540:132:shortest=1[v0]']
for i, (t, s) in enumerate(states):
    png = W / f'frame-{i:02d}.png'
    snap(png, s)
    ins += ['-framerate', '30', '-loop', '1', '-i', str(png)]
    fade = f',fade=in:st={t:.3f}:d=0.18:alpha=1' if i else ''
    f.append(f'[{i + 1}:v]format=rgba{fade}[m{i}]')
    f.append(f"[v{i}][m{i}]overlay=0:0:shortest=1:enable='gte(t,{t:.3f})'[v{i + 1}]")
f.append(f'[v{len(states)}]format=yuv420p[out]')

sp.run(['ffmpeg', '-y', '-loglevel', 'error', *ins, '-filter_complex', ';'.join(f), '-map', '[out]', '-r', '30',
        '-c:v', 'libx264', '-crf', '17', '-preset', 'slow', '-movflags', '+faststart', str(OUT)], check=True)
print(OUT, len(states), 'states')
