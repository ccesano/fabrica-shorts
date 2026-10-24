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
m = ChatterboxMultilingualTTS.from_pretrained(device=dev)
print(f"[chatterbox] modelo cargado en {time.time() - t0:.0f}s ({dev})", flush=True)
for it in job["items"]:
    t = time.time()
    torch.manual_seed(int(it.get("seed", 7)))
    wav = m.generate(it["say"], language_id=job.get("idioma", "es"), audio_prompt_path=job["ref"],
                     exaggeration=float(it["exag"]), cfg_weight=float(it["cfg"]), temperature=float(it.get("temp", 0.75)))
    ta.save(it["out"], wav, m.sr)
    print(f"[chatterbox] {it['out'].rsplit('/', 1)[-1]}: {wav.shape[-1] / m.sr:.1f}s de audio en {time.time() - t:.0f}s", flush=True)
