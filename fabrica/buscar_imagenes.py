"""Busca fotos con licencia en Wikimedia Commons y arma una hoja de miniaturas numeradas para elegir.

uso: python fabrica/buscar_imagenes.py investigacion/<slug>/consultas.json
consultas.json = {"busquedas": ["Boca Juniors 1931", ...], "categorias": ["El Gráfico, 1931", ...], "archivos": ["File:…"], "max": 12}
Escribe al lado: resultados.json (url directa, página, autor, licencia, fecha, descripción) y hoja.jpg.
Solo biblioteca estándar + Pillow.
"""
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
UA = "FabricaShorts/1.0 (https://github.com/ccesano/fabrica-shorts)"
LIBRES = re.compile(r"public domain|pd|cc0|cc[- ]by(?![- ]nc)(?![- ]nd)", re.I)


def api(**p):
    p.update(format="json", formatversion="2")
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(p), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def limpiar(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def info(titulos):
    out = []
    for i in range(0, len(titulos), 40):
        d = api(action="query", titles="|".join(titulos[i:i + 40]), prop="imageinfo",
                iiprop="url|size|extmetadata|mime", iiurlwidth=400)
        for pg in d["query"]["pages"]:
            ii = (pg.get("imageinfo") or [None])[0]
            if not ii or not ii.get("mime", "").startswith("image/") or ii["mime"] == "image/svg+xml":
                continue
            m = ii.get("extmetadata", {})
            lic = limpiar(m.get("LicenseShortName", {}).get("value", ""))
            out.append(dict(titulo=pg["title"], url=ii["url"], miniatura=ii.get("thumburl"), pagina=ii["descriptionurl"],
                            ancho=ii.get("width"), alto=ii.get("height"), licencia=lic,
                            libre=bool(LIBRES.search(lic)),
                            autor=limpiar(m.get("Artist", {}).get("value", ""))[:120],
                            fecha=limpiar(m.get("DateTimeOriginal", {}).get("value", ""))[:40],
                            descripcion=limpiar(m.get("ImageDescription", {}).get("value", ""))[:300]))
    return out


def buscar(c):
    maxn = int(c.get("max", 12))
    titulos = list(c.get("archivos", []))
    for q in c.get("busquedas", []):
        d = api(action="query", list="search", srsearch=q, srnamespace=6, srlimit=maxn)
        titulos += [x["title"] for x in d["query"]["search"]]
    for cat in c.get("categorias", []):
        d = api(action="query", list="categorymembers", cmtitle="Category:" + cat, cmtype="file", cmlimit=maxn * 3)
        titulos += [x["title"] for x in d["query"]["categorymembers"]]
    if c.get("solo_archivos"):
        titulos = list(c.get("archivos", []))
    vistos, uniq = set(), []
    for t in titulos:
        if t not in vistos:
            vistos.add(t)
            uniq.append(t)
    return info(uniq)


def hoja(res, out, cols=6, w=240, h=240):
    from PIL import Image, ImageDraw, ImageFont
    if not res:
        return
    rows = (len(res) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + 30)), "#1a1a1a")
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
    except OSError:
        f = ImageFont.load_default()
    for i, r in enumerate(res):
        x, y = (i % cols) * w, (i // cols) * (h + 30)
        try:
            im = None
            for intento in range(4):
                try:
                    time.sleep(1.0 + 3 * intento)   # Wikimedia corta con 429 si se piden muy rápido
                    req = urllib.request.Request(r["miniatura"], headers={"User-Agent": UA})
                    im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=60).read())).convert("RGB")
                    break
                except urllib.error.HTTPError as e:
                    if e.code != 429 or intento == 3:
                        raise
            im.thumbnail((w - 8, h - 8))
            sheet.paste(im, (x + (w - im.width) // 2, y + (h - im.height) // 2))
        except Exception as e:  # noqa: BLE001
            d.text((x + 10, y + 100), "error", fill="red", font=f)
            print("miniatura", r["titulo"], e, file=sys.stderr)
        color = "#7CFC00" if r["libre"] else "#FF6B6B"
        d.text((x + 8, y + h + 4), f"{i + 1}. {r['licencia'][:18]}", fill=color, font=f)
    sheet.save(out, quality=85)


if __name__ == "__main__":
    p = Path(sys.argv[1])
    c = json.loads(p.read_text())
    res = buscar(c)
    (p.parent / "resultados.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    hoja(res, p.parent / "hoja.jpg")
    print(f"{len(res)} imágenes ({sum(r['libre'] for r in res)} con licencia libre)")
