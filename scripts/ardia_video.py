"""Graba un recorrido de Ardia con objetivos visibles.

Uso desde un escenario:

    with Grabacion('Título', 'Descripción', OBJETIVOS, url, pestana='Título de la pestaña') as g:
        with g.objetivo(0):
            g.guiar('.selector', 'Texto en pantalla')
            g.accion('click', '.selector')

Deja la toma en work/toma.mov y la línea de tiempo en work/toma.json, relativas a la
carpeta desde donde se ejecuta. Con GRABAR=0 en el entorno ejecuta el flujo sin capturar pantalla.
"""
import json, os, re, time, signal, subprocess as sp
from contextlib import contextmanager
from pathlib import Path

GUIA = Path(__file__).resolve().parent / 'guia-visual-ardia.js'


class Grabacion:
    # Área de contenido de Ardia en puntos de pantalla (x,y,ancho,alto)
    def __init__(self, titulo, descripcion, objetivos, url, pestana=None, rect='397,39,1514,1032', salida='work/toma'):
        self.meta = {'titulo': titulo, 'descripcion': descripcion, 'pestana': pestana,
                     'objetivos': [{'titulo': o[0], 'detalle': o[1]} for o in objetivos]}
        self.url, self.rect, self.salida = url, rect, salida
        Path(salida).parent.mkdir(parents=True, exist_ok=True)
        self.eventos, self.grabar = [], os.environ.get('GRABAR', '1') != '0'
        self._url = None

    def cli(self, *args):
        r = sp.run(['ardia', 'browse', *args], text=True, capture_output=True)
        if r.returncode:
            raise RuntimeError(r.stderr + r.stdout)
        return r.stdout

    def t(self):
        return time.monotonic() - self.inicio

    def _evento(self, **kw):
        self.eventos.append({'t': round(self.t(), 3), **kw})

    def _mirar_url(self):
        url = self.cli('get', 'url').strip()
        if url != self._url:
            self._url = url
            self._evento(tipo='url', url=url)

    def __enter__(self):
        self.cli('open', self.url, '--show')
        self.proc = None
        if self.grabar:
            self.proc = sp.Popen(['screencapture', '-x', '-v', '-R' + self.rect, self.salida + '.mov'])
        self.inicio = time.monotonic()
        self._mirar_url()
        time.sleep(3)  # margen para que arranque la captura
        if self.proc and self.proc.poll() is not None:
            raise RuntimeError('La captura de pantalla no arrancó')
        self.cli('eval', GUIA.read_text())
        return self

    def __exit__(self, *exc):
        time.sleep(3)  # dejar ver el cierre
        if self.proc:
            self.proc.send_signal(signal.SIGINT)
            self.proc.wait(timeout=15)
        Path(self.salida + '.json').write_text(json.dumps({**self.meta, 'eventos': self.eventos}, ensure_ascii=False, indent=1))
        self.cli('eval', 'window.guiaArdia?.retirar()')

    @contextmanager
    def objetivo(self, i):
        self._evento(tipo='objetivo', i=i, estado='activo')
        time.sleep(.8)
        try:
            yield
        except Exception:
            self._evento(tipo='objetivo', i=i, estado='fallo')
            raise
        self.cli('eval', 'guiaArdia.ocultar()')
        self._evento(tipo='objetivo', i=i, estado='hecho')
        time.sleep(.9)

    def guiar(self, selector, texto):
        self.cli('eval', f'guiaArdia.apuntar({json.dumps(selector)},{json.dumps(texto, ensure_ascii=False)})')
        time.sleep(1.2)

    def accion(self, *args):
        time.sleep(.4)
        salida = self.cli(*args)
        time.sleep(.9)
        self._mirar_url()
        return salida

    def ref(self, rol, selector=None):
        args = ['snapshot', '-i', '--full'] + (['-s', selector] if selector else [])
        snap = self.cli(*args)
        m = re.search(r'^.*?' + rol + r'.*?\bref=(e\d+)\]', snap, re.M)
        if not m:
            raise RuntimeError(snap)
        return '@' + m.group(1)

    def comprobar(self, condicion, detalle):
        if not condicion:
            raise AssertionError(detalle)
