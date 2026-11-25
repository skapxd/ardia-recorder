"""Compone <toma>.mov + <toma>.json en un MP4 1920×1080 con sidebar de objetivos.

    python3 renderizar.py outputs/nombre.mp4 [work/toma]
"""
import copy, json, sys, subprocess as sp
from pathlib import Path
from urllib.parse import quote

ASSETS = Path(__file__).resolve().parent
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else 'outputs/recorrido.mp4')
TOMA = Path(sys.argv[2] if len(sys.argv) > 2 else 'work/toma').resolve()
W = TOMA.parent
OUT.parent.mkdir(parents=True, exist_ok=True)
DESFASE = .45            # la captura arranca unas décimas después del reloj del script
CROP = '1340:908:120:0'   # ancho:alto:x:y en píxeles del MOV, a escala 1:1 con el hueco del marco
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

toma = json.loads(TOMA.with_suffix('.json').read_text())
estado = {'titulo': toma['titulo'], 'descripcion': toma['descripcion'], 'pestana': toma.get('pestana'), 'url': None,
          'objetivos': [{**o, 'estado': 'pendiente'} for o in toma['objetivos']]}
inicio, estados = {}, []
for e in toma['eventos']:
    if e['tipo'] == 'url':
        estado['url'] = e['url']
    else:
        o = estado['objetivos'][e['i']]
        o['estado'] = e['estado']
        if e['estado'] == 'activo':
            inicio[e['i']] = e['t']
        else:
            o['dur'] = f"{e['t'] - inicio[e['i']]:.1f} s".replace('.', ',')
    t = 0 if not estados else max(0, e['t'] - DESFASE)
    if estados and abs(estados[-1][0] - t) < .05:
        estados.pop()
    estados.append((t, copy.deepcopy(estado)))

FIN = toma['eventos'][-1]['t'] - DESFASE + 3
ins, f = ['-i', str(TOMA.with_suffix('.mov'))], [
    'color=0x121524:s=1920x1080:r=30[bg]',
    f'[0:v]fps=30:eof_action=pass,crop={CROP},setsar=1,tpad=stop_mode=clone:stop_duration=10,trim=duration={FIN:.2f}[app]',
    '[bg][app]overlay=540:132:shortest=1[v0]']
for i, (t, s) in enumerate(estados):
    png = W / f'marco-{i:02d}.png'
    sp.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--default-background-color=00000000',
            '--window-size=1920,1080', f'--screenshot={png}',
            f'file://{ASSETS}/marco.html?s=' + quote(json.dumps(s, ensure_ascii=False))], check=True, capture_output=True)
    ins += ['-framerate', '30', '-loop', '1', '-i', str(png)]
    fade = f',fade=in:st={t:.3f}:d=0.18:alpha=1' if i else ''
    f.append(f'[{i + 1}:v]format=rgba{fade}[m{i}]')
    f.append(f"[v{i}][m{i}]overlay=0:0:shortest=1:enable='gte(t,{t:.3f})'[v{i + 1}]")
f.append(f'[v{len(estados)}]format=yuv420p[out]')

sp.run(['ffmpeg', '-y', '-loglevel', 'error', *ins, '-filter_complex', ';'.join(f), '-map', '[out]', '-r', '30',
        '-c:v', 'libx264', '-crf', '17', '-preset', 'slow', '-movflags', '+faststart', str(OUT)], check=True)
print(OUT, len(estados), 'estados')
