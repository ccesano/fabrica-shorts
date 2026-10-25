"""Música original + ambiente + efectos + mezcla final (−14 LUFS) para cada video.

La música se compone sola a partir del ánimo del guion y de la línea de tiempo de la voz:
  ánimos: epico, nostalgico, misterio, alegre, tension
  intensidad por escena: arranca liviana, crece en el medio, hace silencio antes de una cita
  y estalla cuando termina; el cierre resuelve en mayor.
Cada línea puede forzar "musica": "silencio" | "subida" | "golpe" (golpe = timbal + platillo al terminar la línea).
Instrumentos: muestras de lemo-opuscar (VSCO2 CE, Salamander, FreePats, VCSL), ver CREDITOS.md.
"""
import json
import os
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

RAIZ = Path(__file__).resolve().parent.parent
LEMO = Path(os.environ.get("LEMO_DIR", RAIZ / "vendor/lemo-opuscar"))
sys.path.insert(0, str(LEMO))
from core.audio import sampler as S  # noqa: E402
from core.audio import sfx as X  # noqa: E402
from core.audio.sfx import SR, bp, lp, compress, limit, add  # noqa: E402

NOTAS = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def acorde(nombre):
    """'Dm' → (raíz midi en octava 2, [terceras/quintas]); '' mayor, 'm' menor."""
    menor = nombre.endswith("m")
    raiz = NOTAS[nombre[:-1] if menor else nombre]
    r = 36 + raiz  # C2 = 36
    return r, [r + 12, r + 12 + (3 if menor else 4), r + 19, r + 24]


ANIMOS = {
    "epico":      dict(bpm=76, prog=["Dm", "Bb", "Gm", "A"], fin=["D", "G", "D"], arpegio="guitar_nylon", pad="cellos", pad2="violins", mel="accordion", perc="gran_cassa"),
    "nostalgico": dict(bpm=70, prog=["C", "Am", "F", "G"], fin=["F", "G", "C"], arpegio="piano", pad="cellos", pad2="violins", mel="accordion", perc=None),
    "misterio":   dict(bpm=62, prog=["Am", "F", "Dm", "E"], fin=["Am", "E", "Am"], arpegio="piano", pad="cellos", pad2="violins", mel="glockenspiel", perc="timpani"),
    "alegre":     dict(bpm=104, prog=["G", "D", "Em", "C"], fin=["C", "D", "G"], arpegio="guitar_nylon", pad="accordion", pad2="violins", mel="accordion", perc="claps"),
    "tension":    dict(bpm=92, prog=["Em", "C", "Am", "B"], fin=["Am", "B", "E"], arpegio="piano", pad="cellos", pad2="violins", mel="violins", perc="timpani"),
}


def nombre(m):
    return ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][m % 12] + str(m // 12 - 1)


def componer(tim, escenas, lineas, fin, animo="epico", seed=1):
    rnd = random.Random(seed)
    S.seed(seed)
    A = ANIMOS.get(animo, ANIMOS["epico"])
    B = 60 / A["bpm"]
    BAR = 4 * B
    tls = tim["lines"]
    ev = []

    def E(t, inst, p, d, v, pan=0.0):
        if t < fin:
            ev.append(dict(t=round(t, 4), inst=inst, pitch=p if p is None or isinstance(p, str) else nombre(p), dur=d, vel=v, pan=pan))

    # intensidad por escena
    tipos = [s["id"].split("-", 1)[1] for s in escenas]
    n = len(escenas)
    nivel = []
    for i, tp in enumerate(tipos):
        lv = 1 if i < 2 else 2
        if i >= n * 0.55:
            lv = 3 if lv >= 2 else lv
        if i + 1 < n and tipos[i + 1] == "cita":
            lv = 0
        if tp == "cita":
            lv = 0
        if tp == "cierre":
            lv = 4
        m = lineas[i].get("musica")
        lv = {"silencio": 0, "subida": 3}.get(m, lv)
        nivel.append(lv)

    def escena_en(t):
        k = 0
        for i, s in enumerate(escenas):
            if t >= s["start"]:
                k = i
        return k

    # golpes: fin de una cita, líneas marcadas "golpe"
    golpes = [tls[i]["t1"] + 0.05 for i, tp in enumerate(tipos) if tp == "cita" or lineas[i].get("musica") == "golpe"]

    t = 0.25
    bar = 0
    motivo = rnd.choice([[0, 1, 2, 3], [0, 2, 1, 3], [0, 1.5, 2, 3], [0, 0.5, 1, 2, 3]])
    while t < fin - 1.0:
        k = escena_en(t + 0.01)
        lv = nivel[k]
        cierre = lv == 4
        ch = A["fin"][min(2, bar % 3)] if cierre else A["prog"][bar % len(A["prog"])]
        r, vs = acorde(ch)
        if lv == 0:
            # casi silencio: una nota grave sostenida y un par de notas sueltas
            E(t, A["pad"], r + 12, BAR, 0.26, 0.15)
            if bar % 2 == 0:
                E(t + 0.1, "piano", vs[2] + 12, 2.5, 0.25, -0.2)
        else:
            vel = {1: 0.45, 2: 0.5, 3: 0.55, 4: 0.5}[lv]
            # arpegio
            patron = [vs[0], vs[1], vs[2], vs[3], vs[2], vs[1], vs[2], vs[3]]
            if A["arpegio"] == "guitar_nylon" and animo == "alegre":
                for b in range(4):
                    for j, nn in enumerate(vs):
                        E(t + b * B + j * 0.018, "guitar_nylon", nn, B, vel - 0.05 + (0.08 if b % 2 == 0 else 0), -0.25)
            else:
                for j, nn in enumerate(patron):
                    E(t + j * B / 2, A["arpegio"], nn, B, vel - 0.12 + (0.06 if j % 4 == 0 else 0), -0.25)
            if lv >= 2:
                E(t, "contrabass", r + 12 if r < 40 else r, BAR, 0.45, 0.1)
                for nn in vs[1:]:
                    ev.append(dict(t=t, inst=A["pad"], pitch=nombre(nn), dur=BAR, vel=0.3, pan=0.2, attack=0.8))
            if lv >= 3:
                for nn in vs[1:]:
                    ev.append(dict(t=t, inst=A["pad2"], pitch=nombre(nn + 12), dur=BAR, vel=0.28, pan=0.3, attack=0.6))
                if A["perc"] == "gran_cassa":
                    for off, v in [(0, .55), (1.5 * B, .38), (2 * B, .47), (3 * B, .41), (3.5 * B, .33)]:
                        E(t + off, "gran_cassa", "hit", .9, v)
                elif A["perc"] == "claps":
                    for b in (1, 3):
                        E(t + b * B, "claps", "group", .5, .35)
                elif A["perc"] == "timpani" and bar % 2 == 0:
                    E(t, "timpani", r + 12, 1.5, .4)
            if lv >= 2 and A["mel"]:
                # melodía simple sobre notas del acorde
                base = vs[1] + 12
                escala = [base, base + 2 if ch[-1] != "m" else base + 3, base + 7, base + 12, base + 5]
                for j, b in enumerate(motivo):
                    nn = escala[(j + bar) % len(escala)] if j else vs[2] + 12
                    E(t + b * B, A["mel"], nn, B * 0.9, 0.5 if lv < 4 else 0.55, -0.1)
            if cierre and bar % 3 == 2:
                for nn in vs:
                    E(t, A["pad2"], nn + 12, BAR * 1.5, 0.4, 0.2)
        t += BAR
        bar += 1
    for g in golpes:
        E(g, "timpani", "D3", 2.5, 0.8)
        E(g, "crash", None, 3.5, 0.5, 0.25)
    mus = S.render(ev, dur=fin)
    mus = S.room(mus, size=0.5, mix=0.2)
    f = int(1.4 * SR)
    mus[-f:] *= np.linspace(1, 0, f)[:, None]
    return mus.astype(np.float32), golpes, sorted({e["inst"] for e in ev})


def ambiente(tipo, fin, golpes, seed=5):
    if isinstance(tipo, list):
        out = np.zeros((int(fin * SR), 2), np.float32)
        for k, t in enumerate(tipo):
            out += ambiente(t, fin, golpes, seed + k) * (0.8 if len(tipo) > 1 else 1)
        return out
    N = int(fin * SR)
    amb = np.zeros((N, 2), np.float32)
    if tipo in (None, "", "ninguno"):
        return amb
    r = np.random.default_rng(seed)
    tt = np.arange(N) / SR
    if tipo == "cancha":
        def multitud(sd):
            q = np.random.default_rng(sd)
            x = bp(q.standard_normal(N), 300, 2600, 2) + .5 * bp(q.standard_normal(N), 120, 500, 2)
            mod = .65 + .35 * np.sin(2 * np.pi * .55 * tt + q.random() * 6) * np.sin(2 * np.pi * .13 * tt + 1)
            return (x * mod / np.abs(x).max()).astype(np.float32)
        g = np.full(N, 0.07, np.float32)
        for t in golpes:
            g += (0.22 * np.exp(-np.clip(tt - t, 0, None) / 2.0) * (tt >= t)).astype(np.float32)
        amb[:, 0] = multitud(1) * g
        amb[:, 1] = multitud(2) * g
        for t in golpes:
            for _ in range(int(14 * 2.5)):
                tc = t + 0.15 + r.random() * 2.5
                if tc < fin - 0.5:
                    add(amb, S.hit("claps", "group", vel=.35 + .4 * r.random()) * 0.18, tc, 1.0, r.uniform(-.8, .8))
    elif tipo == "lluvia":
        for c in range(2):
            x = bp(r.standard_normal(N), 800, 9000, 2)
            gotas = (r.random(N) > 0.9993).astype(np.float32) * r.uniform(0.2, 1, N).astype(np.float32)
            gotas = bp(np.convolve(gotas, np.exp(-np.arange(200) / 30.0), mode="same"), 2000, 8000, 2)
            amb[:, c] = (x / np.abs(x).max() * 0.1 + gotas / (np.abs(gotas).max() + 1e-9) * 0.05).astype(np.float32)
    elif tipo == "ciudad":
        for c in range(2):
            x = lp(np.cumsum(r.standard_normal(N)) * 0.01, 400, 2)
            amb[:, c] = (x / np.abs(x).max() * 0.1).astype(np.float32)
    fade = int(0.8 * SR)
    amb[:fade] *= np.linspace(0, 1, fade)[:, None]
    amb[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return amb


def _papel(v=1.0):
    n = int(0.14 * SR)
    x = bp(np.random.standard_normal(n), 1500, 7000, 2) * np.exp(-np.arange(n) / (0.035 * SR))
    return (X.norm(x) * v).astype(np.float32)


def efectos(cues, fin):
    N = int(fin * SR)
    fx = np.zeros((N, 2), np.float32)
    for c in cues:
        k, t, g, pan = c["k"], c["t"], c.get("g", .3), c.get("pan", 0)
        if k == "whoosh":
            x = X.whoosh(c.get("d", .35), 1.0)
        elif k == "golpe":
            x = X.thump(1.0, 58)
        elif k == "corte":
            x = X.thump(1.0, 85)
        elif k == "pop":
            x = X.pop(1.0)
        elif k == "papel":
            x = _papel()
        elif k == "tecla":
            x = X.click(np.random.uniform(.85, 1.25), 1.0)
        elif k == "sello":
            x = X.clack(0.8, 1.0)
        elif k == "tic":
            x = X.click(1.7, 1.0)
        elif k == "ding":
            x = X.ding(1.0)
        else:
            continue
        add(fx, np.asarray(x, np.float32), t, g, pan)
    return fx


def loudnorm(src, dst, lufs=-14, tp=-1.5):
    m = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af", f"loudnorm=I={lufs}:TP={tp}:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(m[m.rindex("{"): m.rindex("}") + 1])
    af = (f"loudnorm=I={lufs}:TP={tp}:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
          f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-ar", "48000", dst], check=True)


def mezclar(carpeta, guion, tim, escenas, fin, cues, seed=1):
    carpeta = Path(carpeta)
    mcfg = guion.get("musica", {})
    animo = mcfg.get("animo", "epico") if isinstance(mcfg, dict) else str(mcfg)
    mus, golpes, insts = componer(tim, escenas, guion["lineas"], fin, animo, seed)
    amb = ambiente(guion.get("ambiente", "ninguno"), fin, golpes, seed)
    fx = efectos(cues, fin)
    N = int(fin * SR)
    v, vsr = sf.read(carpeta / "voz/narracion.wav", dtype="float32")
    import soxr
    v = soxr.resample(v, vsr, SR)
    v = compress(v / (np.abs(v).max() + 1e-9) * .9, thr=.3, ratio=3.0)
    vv = np.zeros(N, np.float32)
    vv[:min(N, len(v))] = v[:N]
    env = lp(np.abs(vv), 4.0, 1)
    duck = 1 - .55 * np.clip(env / (env.max() * .25 + 1e-9), 0, 1)
    vol = float(mcfg.get("volumen", 0.5)) if isinstance(mcfg, dict) else 0.5
    m = mus[:N] if len(mus) >= N else np.pad(mus, ((0, N - len(mus)), (0, 0)))
    mix = m * vol * duck[:, None] + amb * duck[:, None] ** .5 + fx + np.stack([vv, vv], 1)
    for c in range(2):
        mix[:, c] = limit(mix[:, c], .95)
    tmp = carpeta / "_mezcla_cruda.wav"
    sf.write(tmp, mix, SR)
    sf.write(carpeta / "musica.wav", m, SR)
    out = carpeta / "mezcla.wav"
    loudnorm(str(tmp), str(out))
    tmp.unlink()
    return out, insts
