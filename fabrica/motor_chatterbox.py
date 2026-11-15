"""Trabajador de Chatterbox Multilingual (corre en su propio entorno, .venv-voz).
uso: python motor_chatterbox.py trabajos.json
trabajos.json = {"ref": "voz.wav", "idioma": "es", "items": [{"say", "exag", "cfg", "temp", "seed", "out"}]}"""
import json
import sys
import time

import torch
import torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

job = json.load(open(sys.argv[1]))
torch.set_num_threads(max(1, torch.get_num_threads()))
dev = "cuda" if torch.cuda.is_available() else "cpu"
t0 = time.time()
MODELO = job.get("modelo", "v3-latam")


def cargar(modelo):
    """v3-latam (por defecto, elegido por Carlos el 15/11/2026 en una prueba a ciegas): Chatterbox Multilingual V3 con el
    pack afinado para castellano latinoamericano (su t3 y su s3gen). v3 / v2: el modelo general."""
    if modelo != "v3-latam":
        return ChatterboxMultilingualTTS.from_pretrained(device=dev, t3_model=modelo)
    from pathlib import Path
    from huggingface_hub import hf_hub_download, snapshot_download
    from safetensors.torch import load_file
    pack = "ResembleAI/Chatterbox-Multilingual-es-mx-latam"
    d = Path(snapshot_download(repo_id="ResembleAI/chatterbox",
                               allow_patterns=["ve.pt", "s3gen.pt", "grapheme_mtl_merged_expanded_v1.json", "conds.pt", "Cangjie5_TC.json"]))
    t3 = d / "t3_es_mx_latam.safetensors"
    if not t3.exists():
        t3.symlink_to(hf_hub_download(pack, "t3_es_mx_latam.safetensors"))
    m = ChatterboxMultilingualTTS.from_local(d, dev, t3_model=t3.name)
    sd = load_file(hf_hub_download(pack, "s3gen_v3.safetensors"))
    m.s3gen.load_state_dict(sd["model"][0] if "model" in sd else sd, strict=False)
    return m


m = cargar(MODELO)
print(f"[chatterbox] modelo {MODELO} cargado en {time.time() - t0:.0f}s ({dev})", flush=True)
for it in job["items"]:
    t = time.time()
    torch.manual_seed(int(it.get("seed", 7)))
    wav = m.generate(it["say"], language_id=job.get("idioma", "es"), audio_prompt_path=job["ref"],
                     exaggeration=float(it["exag"]), cfg_weight=float(it["cfg"]), temperature=float(it.get("temp", 0.75)))
    ta.save(it["out"], wav, m.sr)
    print(f"[chatterbox] {it['out'].rsplit('/', 1)[-1]}: {wav.shape[-1] / m.sr:.1f}s de audio en {time.time() - t:.0f}s", flush=True)
