"""Mapa de papel: países de Natural Earth (world-atlas, 1:50m) proyectados en Mercator y recortados a la zona del viaje.
Devuelve el SVG de los países y una función para ubicar puntos (lat, lon) en ese SVG."""
import json
import math
from functools import lru_cache
from pathlib import Path

DATOS = Path(__file__).resolve().parent / "datos/paises-50m.json"

# nombres en castellano → nombre en world-atlas (los que más vamos a usar)
ALIAS = {"inglaterra": "United Kingdom", "reino unido": "United Kingdom", "escocia": "United Kingdom", "egipto": "Egypt",
         "españa": "Spain", "italia": "Italy", "francia": "France", "alemania": "Germany", "brasil": "Brazil",
         "estados unidos": "United States of America", "méxico": "Mexico", "mexico": "Mexico", "uruguay": "Uruguay",
         "argentina": "Argentina", "chile": "Chile", "perú": "Peru", "peru": "Peru", "colombia": "Colombia",
         "paraguay": "Paraguay", "bolivia": "Bolivia", "japón": "Japan", "japon": "Japan", "rusia": "Russia",
         "australia": "Australia", "portugal": "Portugal", "holanda": "Netherlands", "países bajos": "Netherlands",
         "bélgica": "Belgium", "suiza": "Switzerland", "grecia": "Greece", "turquía": "Turkey", "china": "China",
         "india": "India", "sudáfrica": "South Africa", "nueva zelanda": "New Zealand", "irlanda": "Ireland",
         "malvinas": "Falkland Is.", "islas malvinas": "Falkland Is.", "cuba": "Cuba", "venezuela": "Venezuela",
         "ecuador": "Ecuador", "canadá": "Canada", "suecia": "Sweden", "noruega": "Norway", "polonia": "Poland",
         "austria": "Austria", "hungría": "Hungary", "croacia": "Croatia", "serbia": "Serbia", "israel": "Israel",
         "marruecos": "Morocco", "nigeria": "Nigeria", "camerún": "Cameroon", "corea del sur": "South Korea"}


@lru_cache(1)
def _paises():
    topo = json.loads(DATOS.read_text())
    (sx, sy), (tx, ty) = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def anillo(idx):
        pts = []
        for i in idx:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(a if not pts else a[1:])
        return pts

    out = []
    for g in topo["objects"]["countries"]["geometries"]:
        polys = g.get("arcs", [])
        if g["type"] == "Polygon":
            polys = [polys]
        elif g["type"] != "MultiPolygon":
            continue
        out.append((g.get("properties", {}).get("name", ""), [[anillo(r) for r in p] for p in polys]))
    return out


def _merc(lat, lon):
    lat = max(-85.0, min(85.0, lat))
    return lon, math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def armar(puntos, ancho, alto, resaltar=(), margen=0.55):
    """puntos: [(lat, lon), …]. Devuelve (svg_paths, proyectar). El encuadre incluye todos los puntos con margen
    (fracción del tamaño del recorrido, mínimo 6°) y respeta la proporción ancho/alto."""
    xs, ys = zip(*[_merc(la, lo) for la, lo in puntos])
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w, h = max(x1 - x0, 6), max(y1 - y0, 6)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = w * (1 + 2 * margen), h * (1 + 2 * margen)
    if w / h > ancho / alto:
        h = w * alto / ancho
    else:
        w = h * ancho / alto
    bx0, by1 = cx - w / 2, cy + h / 2
    k = ancho / w

    def proyectar(lat, lon):
        x, y = _merc(lat, lon)
        return (x - bx0) * k, (by1 - y) * k

    resaltar = {ALIAS.get(r.lower(), r) for r in resaltar}
    normales, destacados = [], []
    for nombre, polys in _paises():
        d = []
        for p in polys:
            for ring in p:
                q = [proyectar(la, lo) for lo, la in ring]
                qx, qy = [a for a, _ in q], [b for _, b in q]
                if max(qx) < -20 or min(qx) > ancho + 20 or max(qy) < -20 or min(qy) > alto + 20:
                    continue
                # saltear puntos muy pegados (menos peso en el render)
                lim, last, pts = 1.6, None, []
                for x, y in q:
                    if last is None or abs(x - last[0]) + abs(y - last[1]) > lim:
                        pts.append((x, y))
                        last = (x, y)
                if len(pts) > 2:
                    d.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")
        if d:
            (destacados if nombre in resaltar else normales).append("".join(d))
    return normales, destacados, proyectar
