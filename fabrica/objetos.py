"""Objetos de papel dibujados en código para las escenas collage.

Cada función recibe los campos del guion y devuelve Obj(html, tipo, w, h):
  tipo "doc"  → cae desde arriba (papeles grandes)
  tipo "prop" → aparece con un pop, como un sticker (objetos chicos)
w/h es el tamaño aproximado en px, para que el armado de escena lo ubique sin pisar textos.
Los colores salen de la paleta de la escena (variables CSS --acc, --acc2, --ink).
"""
import math
import re
from dataclasses import dataclass
from html import escape as _e


@dataclass
class Obj:
    html: str
    tipo: str
    w: int
    h: int


def e(x):
    return _e(str(x), quote=False)


# ── SVG ────────────────────────────────────────────────────────────────────
def pelota(tam=300, uid="b"):
    c, r = 150, 128

    def pent(cx, cy, rr, a0):
        return " ".join(f"{cx + rr * math.cos(a0 + i * 2 * math.pi / 5):.1f},{cy + rr * math.sin(a0 + i * 2 * math.pi / 5):.1f}" for i in range(5))

    parts = [f'<polygon points="{pent(c, c, 38, -math.pi / 2)}" fill="#1E1B18"/>']
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        ox, oy = c + math.cos(a) * 112, c + math.sin(a) * 112
        parts.append(f'<polygon points="{pent(ox, oy, 34, a + math.pi)}" fill="#1E1B18"/>')
        parts.append(f'<line x1="{c + math.cos(a) * 38:.1f}" y1="{c + math.sin(a) * 38:.1f}" x2="{c + math.cos(a) * 80:.1f}" '
                     f'y2="{c + math.sin(a) * 80:.1f}" stroke="#1E1B18" stroke-width="5"/>')
    svg = (f'<svg viewBox="0 0 300 300" width="{tam}" height="{tam}" aria-hidden="true"><defs><clipPath id="bc-{uid}">'
           f'<circle cx="{c}" cy="{c}" r="{r}"/></clipPath></defs><circle cx="{c}" cy="{c}" r="{r + 12}" fill="#FFFFFF"/>'
           f'<circle cx="{c}" cy="{c}" r="{r}" fill="#FBFAF5" stroke="#1E1B18" stroke-width="5"/>'
           f'<g clip-path="url(#bc-{uid})">{"".join(parts)}</g></svg>')
    return Obj(svg, "prop", tam, tam)


SHIRT = "M120,20 Q200,62 280,20 L360,50 L400,150 L330,180 L320,140 L320,430 L80,430 L80,140 L70,180 L0,150 L40,50 Z"


def camiseta(base="#FBFAF5", color="#7FB8E6", estilo="rayas", nombre="", numero="", letra="#F6F3EC", uid="j"):
    """estilo: rayas (verticales), banda (horizontal), mitad, lisa."""
    if estilo == "rayas":
        deco = "".join(f'<rect x="{x}" y="0" width="40" height="440" fill="{color}"/>' for x in range(40, 400, 80))
    elif estilo == "banda":
        deco = f'<rect x="0" y="150" width="400" height="64" fill="{color}"/>'
    elif estilo == "mitad":
        deco = f'<rect x="200" y="0" width="200" height="440" fill="{color}"/>'
    else:
        deco = ""
    txt = ""
    if nombre:
        fs = min(48, int(300 / max(1, len(nombre)) * 1.5))
        txt += f'<text x="200" y="128" text-anchor="middle" font-family="Archivo Black" font-size="{fs}" fill="{letra}" letter-spacing="2">{e(nombre.upper())}</text>'
    if numero != "":
        txt += f'<text x="200" y="380" text-anchor="middle" font-family="Archivo Black" font-size="170" fill="{letra}">{e(numero)}</text>'
    svg = (f'<svg viewBox="-20 -20 440 480" width="400" height="440" aria-hidden="true"><defs><clipPath id="jc-{uid}"><path d="{SHIRT}"/></clipPath></defs>'
           f'<path d="{SHIRT}" fill="#FFFFFF" stroke="#FFFFFF" stroke-width="32" stroke-linejoin="round"/>'
           f'<g clip-path="url(#jc-{uid})"><rect x="0" y="0" width="400" height="440" fill="{base}"/>{deco}</g>'
           f'<path d="{SHIRT}" fill="none" stroke="#1E1B18" stroke-width="6" stroke-linejoin="round"/>'
           f'<path d="M150,28 Q200,66 250,28" fill="none" stroke="#1E1B18" stroke-width="6"/>{txt}</svg>')
    return Obj(svg, "prop", 400, 440)


def reloj(minuto=45, hora=None, uid="r"):
    """Reloj; con minuto dibuja la porción jugada (fútbol), con hora "HH:MM" marca la hora."""
    ticks = "".join(
        f'<line x1="{150 + 104 * math.cos(a):.1f}" y1="{150 + 104 * math.sin(a):.1f}" x2="{150 + 118 * math.cos(a):.1f}" '
        f'y2="{150 + 118 * math.sin(a):.1f}" stroke="#1E1B18" stroke-width="{6 if i % 3 == 0 else 3}"/>'
        for i, a in ((i, -math.pi / 2 + i * math.pi / 6) for i in range(12)))
    if hora:
        h, m = (int(x) for x in str(hora).split(":"))
        am, ah = -math.pi / 2 + m / 60 * 2 * math.pi, -math.pi / 2 + ((h % 12) + m / 60) / 12 * 2 * math.pi
        hands = (f'<line x1="150" y1="150" x2="{150 + 70 * math.cos(ah):.1f}" y2="{150 + 70 * math.sin(ah):.1f}" stroke="#1E1B18" stroke-width="11" stroke-linecap="round"/>'
                 f'<line x1="150" y1="150" x2="{150 + 100 * math.cos(am):.1f}" y2="{150 + 100 * math.sin(am):.1f}" stroke="#D2402E" stroke-width="6" stroke-linecap="round"/>')
        wedge, label = "", e(hora)
    else:
        frac = (minuto % 90) / 60 if minuto <= 60 else 1
        a1 = -math.pi / 2 + frac * 2 * math.pi
        large = 1 if frac > 0.5 else 0
        wedge = (f'<path d="M150,150 L150,26 A124,124 0 {large},1 {150 + 124 * math.cos(a1):.1f},{150 + 124 * math.sin(a1):.1f} Z" fill="var(--acc)" opacity=".6"/>'
                 if frac < 1 else '<circle cx="150" cy="150" r="124" fill="var(--acc)" opacity=".6"/>')
        hands = (f'<line x1="150" y1="150" x2="150" y2="56" stroke="#1E1B18" stroke-width="9" stroke-linecap="round"/>'
                 f'<line x1="150" y1="150" x2="{150 + 90 * math.cos(a1):.1f}" y2="{150 + 90 * math.sin(a1):.1f}" stroke="#D2402E" stroke-width="6" stroke-linecap="round"/>')
        label = f"{minuto}'"
    svg = ('<svg viewBox="0 0 300 300" width="300" height="300" aria-hidden="true">'
           '<circle cx="150" cy="150" r="146" fill="#FFFFFF"/><circle cx="150" cy="150" r="132" fill="#FFFDF7" stroke="#1E1B18" stroke-width="7"/>'
           f'{wedge}{ticks}{hands}<circle cx="150" cy="150" r="10" fill="#1E1B18"/>'
           f'<text x="150" y="{214 if hora else 118}" text-anchor="middle" font-family="Archivo Black" font-size="34" fill="#1E1B18">{label}</text></svg>')
    return Obj(svg, "prop", 300, 300)


def vinilo(titulo="", uid="v"):
    grooves = "".join(f'<circle cx="150" cy="150" r="{r}" fill="none" stroke="#2c2a28" stroke-width="2"/>' for r in range(60, 140, 9))
    svg = ('<svg viewBox="0 0 300 300" width="320" height="320" aria-hidden="true"><circle cx="150" cy="150" r="148" fill="#FFFFFF"/>'
           f'<circle cx="150" cy="150" r="140" fill="#161412"/>{grooves}<circle cx="150" cy="150" r="52" fill="var(--acc)"/>'
           f'<text x="150" y="146" text-anchor="middle" font-family="Archivo Black" font-size="15" fill="#1E1B18">{e(titulo.upper()[:16])}</text>'
           '<circle cx="150" cy="150" r="6" fill="#FFFDF7"/></svg>')
    return Obj(svg, "prop", 320, 320)


def tele(texto="", uid="t"):
    """Televisor de tubo con una placa de texto en pantalla."""
    svg = ('<svg viewBox="0 0 420 380" width="420" height="380" aria-hidden="true">'
           '<line x1="170" y1="70" x2="110" y2="6" stroke="#1E1B18" stroke-width="6"/><line x1="250" y1="70" x2="320" y2="10" stroke="#1E1B18" stroke-width="6"/>'
           '<rect x="8" y="64" width="404" height="290" rx="34" fill="#FFFFFF"/><rect x="20" y="76" width="380" height="266" rx="26" fill="#8B6B47" stroke="#1E1B18" stroke-width="6"/>'
           '<rect x="44" y="100" width="260" height="200" rx="30" fill="var(--acc2)" stroke="#1E1B18" stroke-width="6"/>'
           f'<text x="174" y="214" text-anchor="middle" font-family="Archivo Black" font-size="30" fill="#F6F3EC">{e(texto.upper()[:12])}</text>'
           '<circle cx="352" cy="140" r="18" fill="#F3C33B" stroke="#1E1B18" stroke-width="5"/><circle cx="352" cy="200" r="18" fill="#F3C33B" stroke="#1E1B18" stroke-width="5"/>'
           '<rect x="70" y="342" width="40" height="26" fill="#1E1B18"/><rect x="310" y="342" width="40" height="26" fill="#1E1B18"/></svg>')
    return Obj(svg, "prop", 420, 380)


# ── Papeles (HTML + CSS de fabrica.css) ───────────────────────────────────
def entrada(titulo="ENTRADA", nombre="", campos=None, talon="GENERAL"):
    campos = campos or {}
    f = "".join(f'<div><span class="k">{e(k).upper()}</span><span class="v">{e(v)}</span></div>' for k, v in list(campos.items())[:3])
    html = (f'<div class="m"><div class="band">{e(titulo).upper()}</div><div class="name">{e(nombre)}</div>'
            f'<div class="fields">{f}</div></div><div class="stub"><span>{e(talon).upper()}</span></div>')
    return Obj(html, "doc", 560, 280)


def recorte(volanta="", titular="", lineas=8):
    lines = "".join(f'<div class="ln{" s" if i % 3 == 2 else ""}"></div>' for i in range(lineas))
    h = 120 + 64 * max(1, math.ceil(len(titular) / 20)) + 27 * lineas
    return Obj(f'<div class="kick2">{e(volanta).upper()}</div><div class="head">{e(titular)}</div>{lines}', "doc", 580, h)


def planilla(volanta="", titulo="", filas=None):
    filas = filas or []
    rows = "".join(f'<div class="row"><span class="n">{e(n)}</span>{e(t)}</div>' for n, t in filas[:7])
    return Obj(f'<div class="kick2">{e(volanta).upper()}</div><div class="t">{e(titulo)}</div>{rows}', "doc", 480, 150 + 66 * len(filas[:7]))


def marcador(filas=None):
    filas = filas or [["LOCAL", 0], ["VISITA", 0]]
    rows = "".join(f'<div class="row"><span class="tm">{e(t).upper()}</span><span class="sc">{e(g)}</span></div>' for t, g in filas[:3])
    return Obj(rows, "doc", 820, 80 + 150 * len(filas[:3]))


MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]


def calendario(dia=1, mes=1, anio=""):
    m = MESES[int(mes) - 1] if str(mes).isdigit() else str(mes).upper()[:10]
    return Obj(f'<div class="mo">{e(m)}</div><div class="d">{e(dia)}</div><div class="y">{e(anio)}</div>', "doc", 380, 470)


def postal(texto="Saludos desde", lugar="", colores=None):
    colores = colores or []
    stripes = "".join(f'<div class="st" style="top: {i * 34}px; background: {c}"></div>' for i, c in enumerate(colores[:10]))
    deco = stripes or '<div class="sun"></div><div class="hill"></div><div class="hill" style="left: 40%; bottom: -170px"></div>'
    return Obj(f'<div class="pic">{deco}</div><div class="say">{e(texto)}<b>{e(lugar)}</b></div>', "doc", 760, 470)


def foto(src, epigrafe="", ancho=800, alto=600, marco=False, caja=(600, 680), **_):
    """Foto ya preparada por imagenes.py: con marco blanco (tipo polaroid) o recortada (sticker)."""
    z = min(caja[0] / ancho, caja[1] / alto)
    w, h = int(ancho * z), int(alto * z)
    if marco:
        cap = f'<div class="cap2">{e(epigrafe)}</div>' if epigrafe else ""
        pie = 64 if epigrafe else 18
        return Obj(f'<img src="{e(src)}" alt="" style="width: {w}px; height: {h}px" />{cap}', "doc", w + 36, h + 18 + pie)
    return Obj(f'<img src="{e(src)}" alt="" style="display: block; width: {w}px; height: {h}px" />', "prop", w, h)


CLASES = {"entrada": "o-ticket", "recorte": "o-clip", "planilla": "o-sheet", "marcador": "o-score",
          "calendario": "o-cal", "postal": "o-post", "foto": "o-photo"}
CATALOGO = {"pelota": pelota, "camiseta": camiseta, "reloj": reloj, "vinilo": vinilo, "tele": tele,
            "entrada": entrada, "recorte": recorte, "planilla": planilla, "marcador": marcador,
            "calendario": calendario, "postal": postal, "foto": foto}


def crear(spec, uid):
    """spec = {"tipo": "camiseta", ...campos} → (Obj, clase_css)."""
    spec = dict(spec)
    tipo = spec.pop("tipo")
    if tipo not in CATALOGO:
        raise ValueError(f"objeto desconocido: {tipo} (hay: {', '.join(CATALOGO)})")
    fn = CATALOGO[tipo]
    if "uid" in fn.__code__.co_varnames:
        spec["uid"] = uid
    if tipo == "foto":
        spec = {k: v for k, v in spec.items() if k in ("src", "epigrafe", "ancho", "alto", "marco", "caja")}
    if tipo == "pelota" and "tam" in spec:
        spec["tam"] = int(spec["tam"])
    o = fn(**spec)
    # var() en atributos de presentación SVG no es fiable: pasarlo a style
    o.html = re.sub(r'fill="var\((--[a-z0-9]+)\)"', r'style="fill: var(\1)"', o.html)
    if tipo == "foto" and o.tipo == "prop":
        return o, "o-cutout"
    return o, CLASES.get(tipo, f"o-{tipo}")
