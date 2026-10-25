"""Paso de voz: guion → un WAV por línea, narración completa y timings.json.

Motores:
  chatterbox  voz clonada (Chatterbox Multilingual, MIT). Necesita la muestra de voz (voces/*.wav) y .venv-voz.
  kokoro      voz sintética offline (respaldo rápido, sin clonar).
  grabada     archivos propios: videos/<slug>/voz/l1.wav, l2.wav… (uno por línea).
Cada línea puede llevar "emocion" (0 = calmo, 1 = muy intenso) y "pausa" (segundos de silencio después).
Las líneas ya generadas se reutilizan (caché por texto + emoción + voz), así que retocar el video no regenera la voz.
Control: cada línea se re-transcribe con Whisper; si no coincide con el texto, se regenera con otra semilla.
"""
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np
import soundfile as sf

RAIZ = Path(__file__).resolve().parent.parent
MODELOS = Path(os.environ.get("FABRICA_MODELOS", RAIZ / "modelos"))
PY_VOZ = os.environ.get("FABRICA_PY_VOZ", str(RAIZ / ".venv-voz/bin/python"))
SR = 24000
LEAD = 0.35


def rioplatense(texto, modo="y"):
    """Cambia la ll antes de pasarle el texto a la voz clonada.
    modo "sch" (por defecto, elegido por Carlos): ll → sch, la y no se toca · "sch+y": también la y consonante
    · "y": ll → y · "ll": ll → sh · "ll+y": ll y la y consonante → sh."""
    if not modo:
        return texto
    import re as _re
    if modo == "y":
        return _re.sub(r"LL", "Y", _re.sub(r"Ll", "Y", _re.sub(r"ll", "y", texto)))
    if modo in ("sch", "sch+y"):   # elegido por Carlos: "sch" = solo la ll → sch; la y queda como y
        t = _re.sub(r"LL", "SCH", _re.sub(r"Ll", "Sch", _re.sub(r"ll", "sch", texto)))
        if modo == "sch":
            return t
        t = _re.sub(r"(?<![A-Za-zÁÉÍÓÚáéíóúñÑ])y(?=[aeiouáéíóú])", "sch", t)
        t = _re.sub(r"(?<![A-Za-zÁÉÍÓÚáéíóúñÑ])Y(?=[aeiouáéíóú])", "Sch", t)
        return _re.sub(r"(?<=[aeiouáéíóúAEIOU])y(?=[aeiouáéíóú])", "sch", t)
    t = _re.sub(r"ll", "sh", texto)
    t = _re.sub(r"Ll", "Sh", t)
    t = _re.sub(r"LL", "SH", t)
    if modo == "ll+y":   # y seguida de vocal (yo, ya, ayer, playa), no la conjunción "y"
        t = _re.sub(r"(?<![A-Za-zÁÉÍÓÚáéíóúñÑ])y(?=[aeiouáéíóú])", "sh", t)
        t = _re.sub(r"(?<![A-Za-zÁÉÍÓÚáéíóúñÑ])Y(?=[aeiouáéíóú])", "Sh", t)
        t = _re.sub(r"(?<=[aeiouáéíóú])y(?=[aeiouáéíóú])", "sh", t)
    return t


def _norm_txt(s):
    try:
        from num2words import num2words
        s = re.sub(r"\d+", lambda m: num2words(int(m.group()), lang="es"), s)
    except ImportError:
        pass
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"sch|sh|ll|ch", "y", s)   # la sh rioplatense se transcribe de muchas formas
    return re.sub(r"[^a-zñ ]+", " ", s).split()


def parecido(esperado, oido):
    """Fracción de las palabras esperadas que aparecen, en orden, en lo transcripto."""
    a, b = _norm_txt(esperado), _norm_txt(oido)
    m = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sum(x.size for x in m.get_matching_blocks()) / max(1, len(a))


_ASR = None


def transcribir(path, desde=0.0, hasta=1.0):
    global _ASR
    import sherpa_onnx
    m = MODELOS / "sherpa-onnx-whisper-base"
    if _ASR is None:
        _ASR = sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=str(m / "base-encoder.int8.onnx"), decoder=str(m / "base-decoder.int8.onnx"),
            tokens=str(m / "base-tokens.txt"), language="es", task="transcribe", num_threads=2)
    a, sr = sf.read(path, dtype="float32")
    if a.ndim > 1:
        a = a.mean(1)
    if sr != 16000:
        import soxr
        a = soxr.resample(a, sr, 16000)
    a = a[int(len(a) * desde): int(len(a) * hasta)]
    out = []
    for i in range(0, len(a), 16000 * 28):
        s = _ASR.create_stream()
        s.accept_waveform(16000, a[i:i + 16000 * 28])
        _ASR.decode_stream(s)
        out.append(s.result.text.strip())
    return " ".join(out)


def recortar(x, sr, umbral=0.012):
    """Saca silencios y respiraciones sueltas en los bordes."""
    a = np.abs(x)
    win = int(0.02 * sr)
    env = np.convolve(a, np.ones(win) / win, mode="same")
    idx = np.where(env > umbral)[0]
    if len(idx) == 0:
        return x
    return x[max(0, idx[0] - int(0.04 * sr)): idx[-1] + int(0.12 * sr)]


def _leer(path):
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    if sr != SR:
        import soxr
        x = soxr.resample(x, sr, SR)
    return x


def _clave(motor, ref, ln, intento, texto=None):
    h = hashlib.sha1()
    h.update(f"{motor}|{texto or ln['say']}|{ln.get('emocion', 0.5)}|{ln.get('velocidad', 1)}|{intento}".encode())
    if ref and Path(ref).exists():
        h.update(Path(ref).read_bytes()[:200000])
    return h.hexdigest()[:12]


def _chatterbox(items, ref):
    job = {"ref": str(ref), "idioma": "es", "items": items}
    jp = Path(items[0]["out"]).parent / "_trabajo.json"
    jp.write_text(json.dumps(job, ensure_ascii=False))
    env = dict(os.environ, PYTHONWARNINGS="ignore", TRANSFORMERS_VERBOSITY="error", TQDM_DISABLE="1")
    r = subprocess.run([PY_VOZ, str(Path(__file__).with_name("motor_chatterbox.py")), str(jp)], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in r.stdout.splitlines():
        if line.startswith("[chatterbox]"):
            print("  " + line, flush=True)
    if r.returncode:
        sys.exit("Chatterbox falló:\n" + r.stdout[-3000:])


def _kokoro(items, voz="em_alex"):
    from kokoro_onnx import Kokoro
    k = Kokoro(str(MODELOS / "kokoro-v1.0.onnx"), str(MODELOS / "voices-v1.0.bin"))
    for it in items:
        s, sr = k.create(it["say"], voice=voz, speed=it.get("speed", 0.95), lang="es")
        sf.write(it["out"], s, sr)


def generar(guion, carpeta, motor=None, ref=None, umbral=0.7, reintentos=2):
    carpeta = Path(carpeta)
    vdir = carpeta / "voz"
    cache = RAIZ / ".cache/voz"
    vdir.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    cfg = guion.get("voz", {})
    motor = motor or cfg.get("motor", "chatterbox")
    ref = Path(ref or cfg.get("muestra") or "voces/muestra.wav")
    if not ref.is_absolute() and not ref.exists():
        ref = RAIZ / ref
    if motor == "chatterbox" and not ref.exists():
        print(f"⚠ Falta la muestra de voz {ref} (ver voces/LEEME.md): uso Kokoro", flush=True)
        motor = "kokoro"
    if motor == "chatterbox" and not Path(PY_VOZ).exists():
        print("⚠ No está instalado Chatterbox (.venv-voz): uso Kokoro", flush=True)
        motor = "kokoro"
    lineas = guion["lineas"]
    modo_rio = cfg.get("rioplatense", "sch")
    hablado = [rioplatense(ln["say"], modo_rio) if motor == "chatterbox" else ln["say"] for ln in lineas]
    archivos = [None] * len(lineas)
    mejor = {}  # línea → (puntaje, archivo) del mejor intento
    pendientes = list(range(len(lineas)))
    intento = 0
    while pendientes:
        trabajos = []
        for i in pendientes:
            ln = lineas[i]
            em = float(ln.get("emocion", 0.5))
            key = _clave(motor, ref if motor == "chatterbox" else None, ln, intento, hablado[i])
            out = cache / f"{motor}-{key}.wav"
            archivos[i] = out
            if motor == "grabada":
                archivos[i] = carpeta / "voz" / f"l{i + 1}.wav"
                continue
            if not out.exists():
                trabajos.append(dict(say=hablado[i], exag=round(0.3 + 0.6 * em, 3), cfg=round(0.5 - 0.2 * em, 3),
                                     temp=0.75, seed=7 + intento * 101 + i, out=str(out), speed=0.95 * ln.get("velocidad", 1)))
        if trabajos:
            print(f"voz ({motor}): generando {len(trabajos)} línea(s)" + (f", intento {intento + 1}" if intento else ""), flush=True)
            _chatterbox(trabajos, ref) if motor == "chatterbox" else _kokoro(trabajos, cfg.get("kokoro", "em_alex"))
        malos = []
        for i in pendientes:
            if motor == "grabada" or not (MODELOS / "sherpa-onnx-whisper-base").exists():
                continue
            oido = transcribir(str(archivos[i]))
            p = parecido(lineas[i]["say"], oido)
            if p < umbral:  # Whisper a veces corta después de una pausa: escuchar por mitades
                oido = transcribir(str(archivos[i]), 0, 0.6) + " " + transcribir(str(archivos[i]), 0.4, 1)
                p = max(p, parecido(lineas[i]["say"], oido))
            if p > mejor.get(i, (-1, None))[0]:
                mejor[i] = (p, archivos[i])
            if p < umbral:
                print(f"  línea {i + 1}: se entendió «{oido}» ({p:.2f}) → se regenera", flush=True)
                malos.append(i)
        intento += 1
        pendientes = malos if intento <= reintentos else []
    for i, (p, f) in mejor.items():
        archivos[i] = f
    # armado de la narración
    pista = [np.zeros(int(LEAD * SR), np.float32)]
    t = LEAD
    tl = []
    for i, ln in enumerate(lineas):
        x = recortar(_leer(archivos[i]), SR)
        sf.write(vdir / f"l{i + 1}.wav", x, SR)
        d = len(x) / SR
        tl.append({"id": f"l{i + 1}", "t0": round(t, 3), "t1": round(t + d, 3), "say": ln["say"], "sub": ln.get("sub", ln["say"])})
        pausa = float(ln.get("pausa", 0.5))
        pista += [x, np.zeros(int(pausa * SR), np.float32)]
        t += d + pausa
    full = np.concatenate(pista)
    sf.write(vdir / "narracion.wav", full, SR)
    tim = {"motor": motor, "dur": round(len(full) / SR, 3), "lines": tl}
    (carpeta / "timings.json").write_text(json.dumps(tim, ensure_ascii=False, indent=1))
    return tim


if __name__ == "__main__":
    g = json.load(open(sys.argv[1]))
    print(json.dumps(generar(g, Path(sys.argv[1]).parent / "salida", *(sys.argv[2:3] or [None])), ensure_ascii=False, indent=1))
