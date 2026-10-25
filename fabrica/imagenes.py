"""Imágenes del guion: descarga, tratamiento de color, recorte de fondo y créditos.

En el guion, una foto es un objeto {"tipo": "foto", ...} (dentro de una escena collage/cierre/cifra) o una escena
{"tipo": "foto", "foto": {...}}. Campos:
  url | src      URL directa al archivo (Wikimedia Commons, Openverse…) o archivo en videos/<slug>/
  credito        autor / fuente, tal como debe aparecer
  licencia       "dominio público", "CC BY 4.0", "CC BY-SA 3.0", "uso autorizado (ONG)", etc.
  pagina         página de la imagen (para el registro de derechos)
  tratamiento    color (por defecto, apenas desaturado) | byn | sepia
  recorte        true → se le quita el fondo y queda como figura recortada con borde blanco (personas, objetos)
  epigrafe       texto al pie del marco (solo sin recorte)
"""
import hashlib
import json
import os
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

RAIZ = Path(__file__).resolve().parent.parent
MODELOS = Path(os.environ.get("FABRICA_MODELOS", RAIZ / "modelos"))
CACHE = RAIZ / ".cache/img"
UA = "FabricaShorts/1.0 (https://github.com/ccesano/fabrica-shorts)"
MAX_LADO = 1400


def _bajar(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    dst = CACHE / (hashlib.sha1(url.encode()).hexdigest()[:16] + Path(url.split("?")[0]).suffix.lower()[:5])
    if not dst.exists():
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=90) as r:
            dst.write_bytes(r.read())
    return dst


_SES = None


def _mascara(img):
    """Máscara de primer plano con IS-Net (modelo de rembg, onnx)."""
    global _SES
    import onnxruntime as ort
    if _SES is None:
        _SES = ort.InferenceSession(str(MODELOS / "isnet-general-use.onnx"), providers=["CPUExecutionProvider"])
    x = np.asarray(img.convert("RGB").resize((1024, 1024), Image.LANCZOS), dtype=np.float32)
    x = x / max(x.max(), 1e-6)
    x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([1.0, 1.0, 1.0], np.float32)
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    pred = _SES.run(None, {_SES.get_inputs()[0].name: x})[0][:, 0]
    pred = (pred - pred.min()) / (pred.max() - pred.min() + 1e-9)
    m = Image.fromarray((np.squeeze(pred) * 255).astype("uint8"), "L").resize(img.size, Image.LANCZOS)
    return m


def _tratar(img, modo):
    if modo == "byn":
        g = ImageOps.grayscale(img)
        g = ImageOps.autocontrast(g, cutoff=1)
        return Image.merge("RGB", (g, g, g))
    if modo == "sepia":
        g = ImageOps.autocontrast(ImageOps.grayscale(img), cutoff=1)
        return ImageOps.colorize(g, black="#2b1d10", white="#f3e6cc", mid="#9c7a52")
    img = ImageEnhance.Color(img).enhance(0.85)       # un poco menos saturada para que conviva con el papel
    return ImageEnhance.Contrast(img).enhance(1.05)


def _recortar(img):
    m = _mascara(img)
    m = m.point(lambda v: 255 if v > 128 else int(v * 1.6) if v > 40 else 0)
    from scipy import ndimage
    arr = np.asarray(m)
    a = arr > 128
    lab, n = ndimage.label(a)
    if n >= 1:
        # la figura principal es la pieza más grande; otras piezas solo si son grandes y están pegadas a ella
        # (antes entraban pedazos de pared o de fondo y la figura quedaba chica dentro de un recorte enorme)
        tam = ndimage.sum(a, lab, range(1, n + 1))
        prin = int(np.argmax(tam)) + 1
        sl = ndimage.find_objects(lab)
        y0, y1 = sl[prin - 1][0].start, sl[prin - 1][0].stop
        x0, x1 = sl[prin - 1][1].start, sl[prin - 1][1].stop
        my, mx = 0.15 * (y1 - y0), 0.15 * (x1 - x0)
        ok = [prin]
        for i in range(1, n + 1):
            if i == prin or tam[i - 1] < 0.15 * tam[prin - 1]:
                continue
            cy, cx = ndimage.center_of_mass(a, lab, i)
            if y0 - my <= cy <= y1 + my and x0 - mx <= cx <= x1 + mx:
                ok.append(i)
        keep = ndimage.binary_dilation(np.isin(lab, ok), iterations=6)
        arr = (arr * keep).astype("uint8")
        m = Image.fromarray(arr, "L")
    bbox = Image.fromarray(((arr > 128) * 255).astype("uint8"), "L").getbbox()
    if bbox:
        pad = max(12, int(0.025 * max(img.size)))
        bbox = (max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(img.width, bbox[2] + pad), min(img.height, bbox[3] + pad))
        img, m = img.crop(bbox), m.crop(bbox)
    borde = m.filter(ImageFilter.MaxFilter(max(9, (min(img.size) // 90) * 2 + 1))).filter(ImageFilter.GaussianBlur(1.2))
    out = Image.new("RGBA", img.size, (255, 255, 255, 0))
    blanco = Image.new("RGBA", img.size, (255, 255, 255, 255))
    out.paste(blanco, (0, 0), borde)
    figura = img.convert("RGBA")
    figura.putalpha(m)
    return Image.alpha_composite(out, figura)


def preparar(spec, carpeta_video, assets, n):
    """Deja la imagen lista en assets/img y devuelve el spec con src local, tamaño y crédito."""
    spec = dict(spec)
    origen = spec.pop("url", None)
    if origen:
        f = _bajar(origen)
    else:
        f = Path(carpeta_video) / spec["src"]
        if not f.exists():
            raise SystemExit(f"No encuentro la imagen {f}")
    img = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
    img.thumbnail((MAX_LADO, MAX_LADO), Image.LANCZOS)
    if max(img.size) < 1100:   # imágenes chicas (grabados viejos, portadas): agrandar para que no se vean pixeladas
        z = 1100 / max(img.size)
        img = img.resize((round(img.width * z), round(img.height * z)), Image.LANCZOS)
    img = _tratar(img, spec.pop("tratamiento", "color"))
    destino = Path(assets) / "img"
    destino.mkdir(parents=True, exist_ok=True)
    if spec.pop("recorte", False):
        img = _recortar(img)
        nombre = f"img{n:02d}.png"
        img.save(destino / nombre, optimize=True)
    else:
        nombre = f"img{n:02d}.jpg"
        img.save(destino / nombre, quality=90)
        spec["marco"] = True
    spec["src"] = f"assets/img/{nombre}"
    spec["ancho"], spec["alto"] = img.size
    return spec


def recorrer(guion):
    """Todas las fotos del guion como (dict contenedor, clave)."""
    for ln in guion["lineas"]:
        esc = ln.get("escena") or {}
        for k in ("objeto", "objeto2", "foto"):
            o = esc.get(k)
            if isinstance(o, dict) and (o.get("tipo") == "foto" or k == "foto"):
                yield esc, k


def preparar_todas(guion, carpeta_video, assets):
    """Modifica el guion en memoria (src locales) y devuelve la lista de créditos."""
    creditos = []
    for n, (esc, k) in enumerate(recorrer(guion), 1):
        o = esc[k]
        cred = {x: o.get(x) for x in ("credito", "licencia", "pagina", "url") if o.get(x)}
        esc[k] = preparar(dict(o, tipo="foto"), carpeta_video, assets, n)
        if cred:
            creditos.append(cred)
    return creditos


def linea_creditos(creditos):
    vistos, partes = set(), []
    for c in creditos:
        t = c.get("credito", "autor desconocido") + (f" ({c['licencia']})" if c.get("licencia") else "")
        if t not in vistos:
            vistos.add(t)
            partes.append(t)
    return ("Imágenes: " + "; ".join(partes) + ".") if partes else ""


if __name__ == "__main__":
    import sys
    a = preparar({"src": sys.argv[1], "recorte": len(sys.argv) > 3 and sys.argv[3] == "recorte",
                  "tratamiento": sys.argv[2] if len(sys.argv) > 2 else "color"}, ".", sys.argv[4] if len(sys.argv) > 4 else "/tmp/imgtest", 1)
    print(json.dumps(a))
