"""Un guion = un video.

uso:  python fabrica/make_short.py videos/<slug>/guion.json [--motor kokoro|chatterbox|grabada] [--borrador] [--sin-render]

Pasos: voz (con control por Whisper) → escenas → música/efectos/mezcla → proyecto HyperFrames → chequeo → render
→ audio final → controles (duración, sonoridad, hoja de cuadros) → publicacion.json.
Todo queda en videos/<slug>/salida/ (no se sube al repo, salvo lo que copie el flujo de GitHub).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import escenas as ESC  # noqa: E402
import imagenes  # noqa: E402
import proyecto  # noqa: E402
import voz  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
HF = os.environ.get("HYPERFRAMES", "hyperframes@0.8.190")
TIPOS = set(ESC.TIPOS)


def paso(msg):
    print(f"\n▶ {msg}", flush=True)


def validar(g):
    err = []
    if not g.get("titulo"):
        err.append("falta 'titulo'")
    ls = g.get("lineas") or []
    largo = bool(g.get("largo"))          # "largo": true → hasta ~3 min (máximo de Shorts, Reels y TikTok)
    max_l, max_c = (24, 2600) if largo else (14, 900)
    if not 3 <= len(ls) <= max_l:
        err.append(f"el guion tiene {len(ls)} líneas (entre 3 y {max_l})")
    for i, ln in enumerate(ls, 1):
        if not ln.get("say"):
            err.append(f"línea {i}: falta 'say'")
        if re.search(r"\d", ln.get("say", "")):
            err.append(f"línea {i}: 'say' tiene cifras; escribilas en letras (los números con cifras van en 'sub')")
        t = (ln.get("escena") or {}).get("tipo", "golpe")
        if t not in TIPOS:
            err.append(f"línea {i}: tipo de escena '{t}' no existe ({', '.join(sorted(TIPOS))})")
    total = sum(len(ln.get("say", "")) for ln in ls)
    if total > max_c:
        err.append(f"el texto suma {total} caracteres (≈ {total / 15:.0f} s); el máximo es {max_c}"
                   + ("" if largo else " (para más largo, poné \"largo\": true)"))
    if err:
        sys.exit("Guion con problemas:\n  - " + "\n  - ".join(err))
    if ls and len(ls[0].get("say", "")) > 60:
        print(f"⚠ ritmo: la línea 1 tiene {len(ls[0]['say'])} caracteres; el gancho tiene que entrar en ~1,5 s (≤ 45)", flush=True)
    for i, ln in enumerate(ls, 1):
        if len(ln.get("say", "")) > 140:
            print(f"⚠ ritmo: la línea {i} tiene {len(ln['say'])} caracteres (≈ {len(ln['say']) / 13:.0f} s en una sola escena); conviene partirla", flush=True)


def navegador():
    for c in [os.environ.get("HYPERFRAMES_BROWSER_PATH"), "/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell",
              "/tmp/chromium"]:
        if c and Path(c).exists():
            return c
    return None


def npx(args, cwd, log=None):
    env = dict(os.environ)
    b = navegador()
    if b:
        env["HYPERFRAMES_BROWSER_PATH"] = b
    env.setdefault("HYPERFRAMES_TELEMETRY", "0")
    r = subprocess.run(["npx", "--yes", HF] + args, cwd=cwd, env=env, capture_output=True, text=True)
    if log:
        Path(log).write_text(r.stdout + "\n" + r.stderr)
    return r


def medir(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True).stdout.strip()
    return dict(lufs=float(i[-1]) if i else None, pico=float(p[-1]) if p else None, dur=float(d or 0))


def hoja(video, escenas, out):
    """Hoja de cuadros: un cuadro a mitad de cada escena, en una grilla de 4 columnas."""
    tmp = Path(out).parent / "_cuadros"
    tmp.mkdir(exist_ok=True)
    fs = []
    for i, s in enumerate(escenas):
        t = s["start"] + s["dur"] - (0.9 if s["pushout"] is not None else 0.3)
        f = tmp / f"c{i:02d}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=270:480", str(f)], check=True)
        fs.append(f)
    cols = 4
    rows = (len(fs) + cols - 1) // cols
    while len(fs) < rows * cols:
        f = tmp / f"vacio{len(fs)}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x111111:s=270x480", "-frames:v", "1", str(f)], check=True)
        fs.append(f)
    inputs = sum([["-i", str(f)] for f in fs], [])
    xs = "|".join(f"{(k % cols) * 270}_{(k // cols) * 480}" for k in range(len(fs)))
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", f"xstack=inputs={len(fs)}:layout={xs}", "-frames:v", "1", "-update", "1", str(out)], check=True)
    shutil.rmtree(tmp)


CREDITOS_MUSICA = "Música original compuesta para este video con instrumentos sampleados (lemo-opuscar)."


def publicacion(g, insts, out, cred_img=""):
    p = dict(g.get("publicar", {}))
    p.setdefault("titulo", g["titulo"])
    desc = p.get("descripcion", "")
    cred = [CREDITOS_MUSICA]
    if any(i in insts for i in ("piano",)):
        cred.append('Piano: "Salamander Grand Piano V3" de Alexander Holm (CC BY 3.0).')
    cred.append("Samples CC0: VS Chamber Orchestra Community Edition, Versilian Community Sample Library, FreePats.")
    if cred_img:
        cred.append(cred_img)
    if g.get("fuentes"):
        cred.append("Fuentes: " + ", ".join(g["fuentes"]) + ".")
    tags = p.get("hashtags", [])
    p["descripcion_completa"] = (desc + "\n\n" + " ".join(f"#{h.lstrip('#')}" for h in tags) + "\n\n" + "\n".join(cred)).strip()
    Path(out).write_text(json.dumps(p, ensure_ascii=False, indent=1))
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("guion")
    ap.add_argument("--motor", choices=["chatterbox", "kokoro", "grabada"])
    ap.add_argument("--borrador", action="store_true", help="render rápido (calidad draft, 24 fps)")
    ap.add_argument("--sin-render", action="store_true")
    ap.add_argument("--muestra", help="WAV de referencia para clonar la voz")
    a = ap.parse_args()

    gp = Path(a.guion).resolve()
    g = json.loads(gp.read_text())
    validar(g)
    slug = gp.parent.name
    sal = gp.parent / "salida"
    sal.mkdir(exist_ok=True)
    t_ini = time.time()
    tiempos = {}

    paso("Voz")
    t = time.time()
    tim = voz.generar(g, sal, a.motor, a.muestra)
    tiempos["voz"] = time.time() - t
    print(f"  narración: {tim['dur']:.1f} s ({tim['motor']})")

    creditos_img = []
    if any(True for _ in imagenes.recorrer(g)):
        paso("Imágenes")
        extra = sal / "_assets"
        if extra.exists():
            shutil.rmtree(extra)
        creditos_img = imagenes.preparar_todas(g, gp.parent, extra)
        (sal / "derechos-imagenes.json").write_text(json.dumps(creditos_img, ensure_ascii=False, indent=1))
        print(f"  {len(creditos_img)} imagen(es) con crédito registrado")

    paso("Escenas")
    escenas, fin, cues, subs, pal = ESC.armar(g, tim, slug)
    if g.get("subtitulos", True) is False:
        subs = []
    else:  # en las citas el texto ya está en pantalla
        citas = [(s["start"], s["start"] + s["dur"]) for s in escenas if s["id"].endswith("-cita")]
        subs = [r for r in subs if not any(a0 <= r[0] < b0 for a0, b0 in citas)]
    print(f"  {len(escenas)} escenas, {fin:.1f} s, paleta {pal}: " + ", ".join(s["id"] for s in escenas))

    paso("Música, efectos y mezcla")
    import audio
    t = time.time()
    mezcla, insts = audio.mezclar(sal, g, tim, escenas, fin, cues, ESC.semilla(slug) % 1000)
    tiempos["audio"] = time.time() - t

    paso("Proyecto HyperFrames")
    pj = proyecto.escribir(sal / "proyecto", escenas, fin, subs, mezcla, g["titulo"], ESC.PALETAS[pal]["acc"], sal / "_assets",
                          marca=g.get("marca", "@lodelhongo"))
    r = npx(["check", "--json"], pj, sal / "check.log")
    try:
        chk = json.loads(r.stdout[r.stdout.index("{"):])
        errs = [f for f in chk.get("findings", chk.get("issues", [])) if f.get("severity") == "error"]
        print(f"  chequeo: {len(errs)} error(es)" + "".join(f"\n    - {e.get('message', e)}" for e in errs[:8]))
    except (ValueError, AttributeError):
        print("  chequeo: ver salida/check.log")
    pub = publicacion(g, insts, sal / "publicacion.json", imagenes.linea_creditos(creditos_img))
    if a.sin_render:
        print(f"\nListo sin render ({time.time() - t_ini:.0f} s). Proyecto en {pj}")
        return

    paso("Render")
    t = time.time()
    crudo = sal / "_video_mudo.mp4"
    args = ["render", "-o", str(crudo), "--quiet"]
    args += ["-q", "draft", "-f", "24"] if a.borrador else ["-q", "standard"]
    r = npx(args, pj, sal / "render.log")
    if r.returncode or not crudo.exists():
        sys.exit("El render falló, ver salida/render.log:\n" + (r.stderr or r.stdout)[-2000:])
    tiempos["render"] = time.time() - t
    final = sal / f"{slug}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(crudo), "-i", str(mezcla), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)], check=True)
    crudo.unlink()

    paso("Controles")
    m = medir(final)
    ok = abs(m["lufs"] + 14) < 1.0 and m["pico"] < -0.5 and 15 <= m["dur"] <= 180
    print(f"  duración {m['dur']:.1f} s · sonoridad {m['lufs']} LUFS · pico {m['pico']} dBFS → {'OK' if ok else 'REVISAR'}")
    hoja(final, escenas, sal / "hoja.jpg")
    tiempos["total"] = time.time() - t_ini
    (sal / "informe.json").write_text(json.dumps(dict(video=str(final.name), medidas=m, ok=ok, paleta=pal,
                                                      tiempos={k: round(v) for k, v in tiempos.items()}, titulo=pub["titulo"]), ensure_ascii=False, indent=1))
    print(f"\n✔ {final}  ({tiempos['total'] / 60:.1f} min: " + ", ".join(f"{k} {v:.0f}s" for k, v in tiempos.items() if k != "total") + ")")


if __name__ == "__main__":
    main()
