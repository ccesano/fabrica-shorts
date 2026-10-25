"""Guion + tiempos de la voz → escenas del collage (HTML por escena, cues de efectos, subtítulos).

Tipos de escena (campo "escena.tipo" de cada línea del guion):
  golpe    tipografía cinética gigante sobre fondo liso          {"palabras": [...], "kicker"?}
  collage  etiqueta + objeto de papel + 1-2 palabras recortadas    {"etiqueta", "objeto"?, "palabras"?, "sello"?}
  cifra    número que cuenta + palabra                            {"etiqueta"?, "numero", "prefijo"?, "sufijo"?, "palabra"?, "en"?}
  lista    nombres que se apilan en tiras de papel                 {"etiqueta"?, "items": [...], "remate"?}
  cita     frase textual palabra por palabra                       {"texto", "autor"?, "kicker"?}
  cierre   título + llamado a comentar                             {"titulo": [...], "cta", "objeto"?}
Palabras con *asteriscos* van en color de acento. Cualquier palabra puede ser {"texto": "...", "en": "fragmento del say"}
para sincronizarla con un momento distinto de la narración.
"""
import hashlib
import math
import random
import re
import unicodedata
from html import escape

from objetos import crear

PUSH = 0.4          # duración de la transición entre escenas
LEAD = 0.25         # la escena entra un poco antes de que empiece su línea
TAIL = 1.8          # cola después de la última palabra

PALETAS = {
    "bombonera": dict(bgs=["#F3DF9E", "#C9CCF2", "#BEE5D2", "#F7CDB8", "#CFE6F3"], deep="#10214D", acc="#F2C230", acc2="#1F3F8F", ink="#1E1B18"),
    "atardecer": dict(bgs=["#F7CDB8", "#F3DF9E", "#E8D5F0", "#FBE3C5", "#D8E8F0"], deep="#3B1F2B", acc="#FF8A3D", acc2="#B23A48", ink="#1E1B18"),
    "bosque":    dict(bgs=["#D8E8C8", "#F1E3C2", "#C8E0D8", "#E6EFD0", "#F3D9C8"], deep="#1F3A2E", acc="#E9C46A", acc2="#2A6F4E", ink="#1E1B18"),
    "diario":    dict(bgs=["#E9E4D8", "#D9D6CE", "#F1ECDD", "#E3DED2", "#EDE6D6"], deep="#1E1B18", acc="#E63B2E", acc2="#2B2B2B", ink="#1E1B18"),
    "oceano":    dict(bgs=["#CFE6F3", "#D7F0EC", "#E0E4F7", "#F3EED9", "#DDEFE3"], deep="#0E2F44", acc="#4FD1C5", acc2="#1D5C8C", ink="#1E1B18"),
    "neon":      dict(bgs=["#F2D4E6", "#D9E4FF", "#FFF2C2", "#D6F5E3", "#FFE0CC"], deep="#1A1033", acc="#FF4FA3", acc2="#5B3CC4", ink="#1E1B18"),
}

TRANS = ["up", "left", "right", "zoom"]


def semilla(texto):
    return int(hashlib.sha1(texto.encode()).hexdigest()[:8], 16)


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ ]+", " ", s).replace("  ", " ")


def limpio(t):
    return t.replace("*", "")


def es_acento(t):
    return t.startswith("*") and t.endswith("*")


# ── medidas aproximadas de texto (px por carácter / tamaño de fuente) ──
ANCHO = {"league": 0.40, "gloock": 0.68, "news": 0.47, "tag": 0.66, "oswald": 0.56}


def cabe(texto, fuente, ancho, maximo, minimo=40, padding=0):
    n = max(1, len(texto))
    return int(max(minimo, min(maximo, (ancho - padding) / (ANCHO[fuente] * n))))


class Escena:
    def __init__(self, idx, linea, tl, inicio, dur, pal, rnd, fondo):
        self.idx, self.linea, self.tl, self.S, self.dur = idx, linea, tl, inicio, dur
        self.pal, self.r, self.fondo = pal, rnd, fondo
        self.world, self.sfx = [], []
        self.zoom = None
        self.n = 0

    # momento local (s, relativo a la escena) en que la narración dice `clave`
    def cuando(self, clave, defecto):
        say = norm(self.linea["say"])
        k = norm(limpio(clave)).strip()
        pos = say.find(k) if k else -1
        if pos < 0:
            for w in sorted(k.split(), key=len, reverse=True):
                if len(w) > 2 and say.find(w) >= 0:
                    pos = say.find(w)
                    break
        if pos < 0:
            return defecto
        frac = pos / max(1, len(say))
        t_abs = self.tl["t0"] + frac * (self.tl["t1"] - self.tl["t0"])
        return max(PUSH + 0.05, round(t_abs - self.S - 0.08, 3))

    def reparto(self, k, n, desde=None):
        """Momento por defecto de la k-ésima de n piezas, repartidas a lo largo de la línea."""
        a = self.tl["t0"] - self.S + 0.1 if desde is None else desde
        b = self.tl["t1"] - self.S - 0.3
        return round(max(PUSH + 0.05, a + (b - a) * (k / max(1, n))), 3)

    def uid(self):
        self.n += 1
        return f"e{self.idx}-{self.n}"

    def fx(self, kind, t, g=0.3, **kw):
        if 0 <= t < self.dur:
            self.sfx.append(dict(k=kind, t=round(self.S + t, 3), g=g, **kw))

    # ── piezas ──
    def tira(self, kind, texto, t, style, size, rot=None):
        rot_attr = f' data-rot="{rot}"' if rot else ""
        self.world.append(f'<div class="cg-strip cg-{kind}" data-t="{t}"{rot_attr} style="{style}"><div class="cg-paper"></div>'
                          f'<div class="cg-text" style="font-size: {size}px">{escape(texto, quote=False)}</div></div>')
        if kind == "word":
            for i in range(len(texto)):
                self.fx("tecla", t + 0.1 + i * 0.045, 0.08, pan=(i / max(1, len(texto)) - 0.5) * 0.6)
        else:
            self.fx("papel", t, 0.18)

    def kin(self, texto, t, x, y, size, desde="zoom", clase=""):
        cls = ("acc " if es_acento(texto) else "") + clase
        self.world.append(f'<div class="cg-kin {cls.strip()}" data-t="{t}" data-from="{desde}" '
                          f'style="left: {x}px; top: {y}px; font-size: {size}px">{escape(limpio(texto), quote=False)}</div>')
        self.fx("golpe", t + 0.1, 0.42)

    def objeto(self, spec, t, cx, top, rot, max_h=560, max_w=900):
        if spec.get("tipo") == "foto" and "caja" not in spec:
            spec = dict(spec, caja=(min(max_w, 640), max_h))
        o, cls = crear(spec, self.uid())
        z = min(1.0, max_h / o.h, max_w / o.w)
        w, h = o.w * z, o.h * z
        left = int(min(1080 - 40 - w, max(40, cx - w / 2)))
        zoom = f"zoom: {z:.3f}; " if z < 0.999 else ""
        if o.tipo == "doc":
            self.world.append(f'<div class="cg-doc {cls}" data-t="{t}" data-rot="{rot}" style="{zoom}left: {left / z:.0f}px; top: {top / z:.0f}px">{o.html}</div>')
            self.fx("papel", t + 0.25, 0.3)
        else:
            self.world.append(f'<div class="cg-prop {cls}" data-t="{t}" data-rot="{rot}" style="{zoom}left: {left / z:.0f}px; top: {top / z:.0f}px; width: {o.w}px; height: {o.h}px">{o.html}</div>')
            self.fx("pop", t, 0.32)
        return left, top, w, h

    def sello(self, texto, t, style, rot=-8):
        size = min(64, int(560 / (0.72 * max(1, len(texto)))))
        self.world.append(f'<div class="cg-pop" data-t="{t}" data-rot="{rot}" data-anim="stamp" style="{style}">'
                          f'<div class="stamp" data-layout-allow-occlusion style="font-size: {size}px">{escape(texto, quote=False)}</div></div>')
        self.fx("sello", t + 0.12, 0.4)


def item_txt(p):
    return p["texto"] if isinstance(p, dict) else p


def item_en(p):
    return p.get("en", p["texto"]) if isinstance(p, dict) else p


# ── tipos de escena ──────────────────────────────────────────────────────────
def golpe(E, esc):
    palabras = esc.get("palabras") or [E.linea.get("sub", "")]
    sizes = []
    for p in palabras:
        txt = limpio(item_txt(p)).upper()
        sizes.append(cabe(txt, "league", 940, 380 if es_acento(item_txt(p)) else 300, 90))
    alto = sum(s * 0.86 + 14 for s in sizes)
    k = min(1.0, 1060 / alto)
    sizes = [int(s * k) for s in sizes]
    alto = sum(s * 0.86 + 14 for s in sizes)
    y = 280 + (1120 - alto) / 2
    if esc.get("kicker"):
        E.world.append(f'<div class="kick cg-fade" data-t="{PUSH + 0.05}" style="left: 76px; top: {y - 110:.0f}px">{escape(esc["kicker"], quote=False)}</div>')
    desdes = ["zoom", "left", "up", "right", "zoom", "down"]
    E.r.shuffle(desdes)
    desdes = ["zoom"] + desdes
    for i, (p, s) in enumerate(zip(palabras, sizes)):
        t = E.cuando(item_en(p), E.reparto(i, len(palabras)))
        clase = "box" if es_acento(item_txt(p)) and E.r.random() < 0.35 else ""
        txt = item_txt(p)
        txt = ("*" + limpio(txt).upper() + "*") if es_acento(txt) else txt.upper()
        E.kin(txt, t, 70, int(y), s, desdes[i % len(desdes)], clase)
        y += s * 0.86 + 14


def collage(E, esc):
    lado = E.r.choice(["izq", "der"])
    rot = E.r.choice([-9, -6, -4, 4, 6, 9])
    if esc.get("etiqueta"):
        et = esc["etiqueta"]
        size = cabe(et, "news", 980, 92, 58, 68)
        E.tira("label", et, PUSH + 0.05, f"left: 50px; top: {E.r.choice([250, 270, 290])}px; width: 980px", size)
    palabras = esc.get("palabras", [])[:2]
    y_obj = 420
    if esc.get("objeto"):
        cx = 540 + (-150 if lado == "izq" else 150) * (0.5 if esc["objeto"].get("tipo") in ("marcador", "postal") else 1)
        t = E.cuando(esc["objeto"].get("en", ""), PUSH + 0.25) if esc["objeto"].get("en") else PUSH + 0.25
        spec = {k: v for k, v in esc["objeto"].items() if k != "en"}
        _, _, _, h = E.objeto(spec, t, cx, y_obj, rot, max_h=560 if palabras else 760)
    if esc.get("objeto2"):
        spec = {k: v for k, v in esc["objeto2"].items() if k != "en"}
        t2 = E.cuando(esc["objeto2"].get("en", ""), E.reparto(1, 2)) if esc["objeto2"].get("en") else E.reparto(1, 2)
        E.objeto(spec, t2, 540 + (220 if lado == "izq" else -220), 520, -rot, max_h=420, max_w=420)
    ys = [1010, 1190]
    for i, p in enumerate(palabras):
        txt = limpio(item_txt(p)).upper()
        size = cabe(txt, "gloock", 990, 128, 64, 68)
        t = E.cuando(item_en(p), E.reparto(i + 1, len(palabras) + 1))
        izq = (i % 2 == 0) == (lado == "izq")
        style = f"left: {E.r.choice([46, 60, 70])}px; top: {ys[i]}px" if izq else f"right: {E.r.choice([40, 50, 64])}px; top: {ys[i]}px"
        E.tira("word", txt, t, style, size)
    if esc.get("sello"):
        t = E.cuando(esc.get("sello_en", esc["sello"]), E.reparto(2, 3))
        E.sello(esc["sello"].upper(), t, f"left: {E.r.choice([240, 300, 360])}px; top: 840px", E.r.choice([-9, -6, 6]))


def cifra(E, esc):
    if esc.get("etiqueta"):
        et = esc["etiqueta"]
        E.tira("label", et, PUSH + 0.05, "left: 50px; top: 270px; width: 980px", cabe(et, "news", 980, 92, 58, 68))
    num = float(esc["numero"])
    dec = int(esc.get("decimales", 0))
    pre, suf = esc.get("prefijo", ""), esc.get("sufijo", "")
    shown = f"{pre}{num:,.{dec}f}{suf}"
    size = cabe(shown, "league", 960, 470, 160)
    t = E.cuando(esc.get("en", ""), PUSH + 0.35) if esc.get("en") else PUSH + 0.35
    dur = min(1.6, max(0.8, (E.tl["t1"] - E.S) - t - 0.6))
    top = 470 if esc.get("etiqueta") else 380
    E.world.append(f'<div class="cg-count" data-t="{t}" data-dur="{dur:.2f}" data-to="{num}" data-dec="{dec}" '
                   f'data-pre="{escape(pre)}" data-suf="{escape(suf)}" style="left: 40px; width: 1000px; top: {top}px; text-align: center">'
                   f'<span class="cg-num" style="font-size: {size}px">0</span></div>')
    for i in range(int(dur / 0.07)):
        E.fx("tic", t + i * 0.07, 0.06 + 0.06 * i / max(1, dur / 0.07))
    E.fx("ding", t + dur, 0.28)
    y = top + size * 0.86 + 70
    if esc.get("palabra"):
        txt = esc["palabra"].upper()
        E.tira("word", txt, max(t + dur * 0.6, E.cuando(esc.get("palabra_en", esc["palabra"]), t + dur)),
               f"right: 56px; top: {min(1240, y):.0f}px", cabe(txt, "gloock", 990, 120, 64, 68))
    if esc.get("objeto"):
        spec = {k: v for k, v in esc["objeto"].items() if k != "en"}
        E.objeto(spec, t + dur + 0.2, 280, min(1080, y + 150), E.r.choice([-8, 8]), max_h=320, max_w=420)


def lista(E, esc):
    items = esc["items"][:6]
    y0 = 270
    if esc.get("etiqueta"):
        et = esc["etiqueta"]
        E.tira("label", et, PUSH + 0.05, "left: 50px; top: 260px; width: 980px", cabe(et, "news", 980, 90, 58, 68))
        y0 = 420
    remate = esc.get("remate")
    hueco = 1300 - y0 - (190 if remate else 0)
    paso = min(150, hueco / max(1, len(items)))
    size = min(int(paso * 0.62), 76)
    for i, it in enumerate(items):
        txt = item_txt(it)
        sz = min(size, cabe(txt.upper(), "tag", 900, 76, 40, 48))
        t = E.cuando(item_en(it), E.reparto(i, len(items) + (1 if remate else 0)))
        x = 70 + (110 if i % 2 else 0) + E.r.randint(-12, 12)
        prefijo = f"{i + 1}. " if esc.get("numerada") else ""
        E.tira("tag", prefijo + txt.upper(), t, f"left: {x}px; top: {y0 + i * paso:.0f}px", sz, rot=E.r.choice([-2, -1, 1, 2]))
    if remate:
        txt = limpio(item_txt(remate)).upper()
        t = E.cuando(item_en(remate), E.reparto(len(items), len(items) + 1))
        E.tira("word", txt, t, f"right: 46px; top: {min(1210, y0 + len(items) * paso + 40):.0f}px", cabe(txt, "gloock", 990, 120, 64, 68))


def cita(E, esc):
    texto = esc.get("texto") or E.linea["say"]
    palabras = texto.split()
    n = len(limpio(texto))
    size = 118 if n <= 60 else 100 if n <= 100 else 82 if n <= 150 else 66
    if esc.get("kicker"):
        E.world.append(f'<div class="kick cg-fade" data-t="{PUSH + 0.05}" style="left: 76px; top: 300px">{escape(esc["kicker"], quote=False)}</div>')
    E.world.append(f'<div class="qmark cg-fade" data-t="{PUSH + 0.1}" style="left: 48px; top: 250px">“</div>')
    a = E.tl["t0"] - E.S - 0.05
    b = E.tl["t1"] - E.S - 0.35
    acum, total = 0, sum(len(limpio(w)) + 1 for w in palabras)
    spans = []
    for w in palabras:
        t = round(max(PUSH, a + (b - a) * acum / total), 3)
        acum += len(limpio(w)) + 1
        cls = "cg-fade em" if es_acento(w.strip(".,;:!?¡¿«»\"")) or ("*" in w) else "cg-fade"
        spans.append(f'<span class="{cls}" data-t="{t}">{escape(limpio(w), quote=False)}</span>')
    lineas_q = math.ceil(n * 0.5 * size / 940) + 1
    top = int(max(470, 820 - lineas_q * size * 1.12 / 2))
    E.world.append(f'<div class="quote" style="top: {top}px; font-size: {size}px">{"".join(spans)}</div>')
    if esc.get("autor"):
        E.world.append(f'<div class="author cg-fade" data-t="{round(b + 0.25, 3)}" style="right: 70px; top: 1290px">— {escape(esc["autor"], quote=False)}</div>')
        E.fx("papel", b + 0.25, 0.2)


def cierre(E, esc):
    titulo = esc.get("titulo") or ["GRACIAS"]
    y = 300
    for i, p in enumerate(titulo):
        txt = item_txt(p)
        size = cabe(limpio(txt).upper(), "league", 900, 300 if i else 200, 90)
        t = E.cuando(item_en(p), E.reparto(i, len(titulo) + 2))
        up = ("*" + limpio(txt).upper() + "*") if es_acento(txt) else txt.upper()
        E.kin(up, t, 70, y, size, "zoom" if i == 0 else "left", "" if es_acento(txt) else "ink")
        y += size * 0.86 + 16
    if esc.get("objeto"):
        spec = {k: v for k, v in esc["objeto"].items() if k != "en"}
        E.objeto(spec, E.reparto(1, 3), 790, y + 10, E.r.choice([-10, 10]), max_h=300, max_w=340)
        y += 330
    cta = esc.get("cta")
    if cta:
        partes = [p.strip() for p in re.split(r"(?<=[?.!])\s+", cta) if p.strip()]
        primera, resto = partes[0], " ".join(partes[1:])
        yc = max(y + 60, 990)
        E.tira("label", primera, E.cuando(primera, E.reparto(1, 2)), f"left: 50px; top: {yc:.0f}px; width: 980px", cabe(primera, "news", 980, 84, 54, 68))
        if resto:
            E.tira("tag", resto.upper(), E.cuando(resto, E.reparto(2, 3)), f"left: 60px; top: {yc + 150:.0f}px", cabe(resto.upper(), "tag", 960, 58, 36, 48))


def foto(E, esc):
    """Una foto grande (con marco o recortada) como protagonista, con etiqueta arriba y 1-2 palabras abajo."""
    palabras = esc.get("palabras", [])[:2]
    top = 250
    if esc.get("etiqueta"):
        et = esc["etiqueta"]
        E.tira("label", et, PUSH + 0.05, f"left: 50px; top: {E.r.choice([240, 260])}px; width: 980px", cabe(et, "news", 980, 92, 58, 68))
        top = 390
    alto = (1200 if not palabras else 1090 - 130 * len(palabras)) - top
    spec = dict({k: v for k, v in esc["foto"].items() if k != "en"}, tipo="foto")
    spec["caja"] = (900, alto)
    t = E.cuando(esc["foto"].get("en", ""), PUSH + 0.2) if esc["foto"].get("en") else PUSH + 0.2
    E.objeto(spec, t, 540, top, E.r.choice([-3, -2, 2, 3]), max_h=alto + 120, max_w=980)
    ys = [1110, 1250] if len(palabras) == 2 else [1190]
    for i, p in enumerate(palabras):
        txt = limpio(item_txt(p)).upper()
        t = E.cuando(item_en(p), E.reparto(i + 1, len(palabras) + 1))
        style = f"left: {E.r.choice([46, 60])}px; top: {ys[i]}px" if i % 2 == 0 else f"right: {E.r.choice([40, 56])}px; top: {ys[i]}px"
        E.tira("word", txt, t, style, cabe(txt, "gloock", 990, 118, 64, 68))
    if esc.get("sello"):
        t = E.cuando(esc.get("sello_en", esc["sello"]), E.reparto(2, 3))
        E.sello(esc["sello"].upper(), t, f"right: {E.r.choice([80, 120])}px; top: {top + alto - 160}px", E.r.choice([-9, 7]))
    E.zoom = 0.07   # acercamiento lento sobre la foto


TIPOS = {"golpe": golpe, "collage": collage, "foto": foto, "cifra": cifra, "lista": lista, "cita": cita, "cierre": cierre}
SOLIDOS = {"golpe", "cita"}


# ── armado ───────────────────────────────────────────────────────────────────
def armar(guion, timings, slug):
    """Devuelve (escenas, duracion_total, sfx, subtitulos)."""
    lineas = guion["lineas"]
    tls = timings["lines"]
    assert len(lineas) == len(tls), "guion y timings no coinciden"
    seed = semilla(slug)
    rnd = random.Random(seed)
    nombre_pal = guion.get("paleta") or sorted(PALETAS)[seed % len(PALETAS)]
    pal = PALETAS[nombre_pal]
    fin = round(tls[-1]["t1"] + TAIL, 3)
    inicios = [0.0] + [round(max(0.0, tl["t0"] - LEAD), 3) for tl in tls[1:]]
    bg_off = rnd.randrange(len(pal["bgs"]))
    trans_prev = None
    escenas, sfx = [], []
    for i, (ln, tl) in enumerate(zip(lineas, tls)):
        esc = ln.get("escena") or {"tipo": "golpe", "palabras": [ln.get("sub", ln["say"])]}
        tipo = esc["tipo"]
        if tipo not in TIPOS:
            raise SystemExit(f"línea {i + 1}: tipo de escena desconocido '{tipo}' (hay: {', '.join(TIPOS)})")
        S = inicios[i]
        dur = round((inicios[i + 1] - S + PUSH) if i + 1 < len(lineas) else fin - S, 3)
        fondo = esc.get("fondo") or ("solido" if tipo in SOLIDOS else "papel")
        E = Escena(i + 1, ln, tl, S, dur, pal, random.Random(seed + i * 7919), fondo)
        TIPOS[tipo](E, esc)
        if i == 0:
            trans = None
        else:
            opciones = ["cut", "zoom"] if tipo == "golpe" else [t for t in TRANS if t != trans_prev]
            trans = rnd.choice(opciones)
        if trans and trans != "cut":
            E.fx("whoosh", 0.0, 0.26, d=0.4, pan=-0.3 if trans == "right" else 0.3 if trans == "left" else 0)
        elif trans == "cut":
            E.fx("corte", 0.0, 0.3)
        bg = pal["bgs"][(bg_off + i) % len(pal["bgs"])]
        escenas.append(dict(id=f"s{i + 1}-{tipo}", start=S, dur=dur, bg=bg, solid=fondo == "solido", trans=trans,
                            world=E.world, seed=seed % 997 + i * 13, pal=pal, zoom=E.zoom))
        sfx += E.sfx
        trans_prev = trans
    for i, s in enumerate(escenas):
        s["push"] = i > 0
        s["pushout"] = round(s["dur"] - PUSH, 3) if i + 1 < len(escenas) else None
        s["outdir"] = escenas[i + 1]["trans"] if i + 1 < len(escenas) else None
        s["exit"] = round(s["dur"] - 0.9, 3) if i + 1 < len(escenas) else None
    return escenas, fin, sfx, subtitulos(lineas, tls), nombre_pal


def subtitulos(lineas, tls):
    """Filas [inicio, fin, texto] de 1-3 palabras, repartidas a lo largo de cada línea según su largo."""
    rows = []
    for ln, tl in zip(lineas, tls):
        words = limpio(ln.get("sub") or ln["say"]).replace("«", "").replace("»", "").split()
        chunks, cur = [], []
        for w in words:
            cur.append(w)
            if re.search(r"[,.?!:;…]$", w) or len(cur) == 3 or len(" ".join(cur)) >= 15:
                chunks.append(cur)
                cur = []
        if cur:
            chunks.append(cur)
        total = sum(len(" ".join(c)) + 2 for c in chunks)
        t, acc = tl["t0"], 0
        span = tl["t1"] - tl["t0"]
        for c in chunks:
            a = tl["t0"] + span * acc / total
            acc += len(" ".join(c)) + 2
            b = tl["t0"] + span * acc / total
            rows.append([round(a, 3), round(b + 0.05, 3), " ".join(c).rstrip(".,;:").upper()])
    return rows
