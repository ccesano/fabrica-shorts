"""uso: python generar.py <variante> <salida>   variante: actual | v3 | latam
Genera las frases de trabajos.json con la muestra de voz de Carlos, con los mismos ajustes que la fábrica."""
import json, sys, time
from pathlib import Path
import torch, torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

var, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
t0 = time.time()
if var == "actual":
    m = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
elif var == "v3":
    m = ChatterboxMultilingualTTS.from_pretrained(device="cpu", t3_model="v3")
else:  # latam: el modelo afinado para castellano latinoamericano, con el resto de los archivos del modelo general
    from huggingface_hub import snapshot_download, hf_hub_download
    d = Path(snapshot_download(repo_id="ResembleAI/chatterbox", allow_patterns=["ve.pt", "s3gen.pt", "grapheme_mtl_merged_expanded_v1.json", "conds.pt", "Cangjie5_TC.json"]))
    from huggingface_hub import list_repo_files
    REPO = "ResembleAI/Chatterbox-Multilingual-es-mx-latam"
    archivos = list_repo_files(REPO)
    print("archivos del pack latam:", archivos, flush=True)
    t3 = next(f for f in archivos if f.startswith("t3_") and f.endswith(".safetensors"))
    dst = d / Path(t3).name
    if not dst.exists():
        dst.symlink_to(hf_hub_download(REPO, t3))
    m = ChatterboxMultilingualTTS.from_local(d, "cpu", t3_model=dst.name)
    s3 = next((f for f in archivos if f.startswith("s3gen") and f.endswith(".safetensors")), None)
    if s3:   # el pack trae su propio generador de audio; si no encaja, queda el general
        from safetensors.torch import load_file
        try:
            sd = load_file(hf_hub_download(REPO, s3))
            sd = sd["model"][0] if "model" in sd else sd
            faltan, sobran = m.s3gen.load_state_dict(sd, strict=False)
            print(f"[latam] {s3} cargado (faltan {len(faltan)}, sobran {len(sobran)})", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"[latam] no pude usar {s3}: {e}; sigo con el s3gen general", flush=True)
print(f"[{var}] modelo cargado en {time.time() - t0:.0f}s", flush=True)
for it in json.load(open("pruebas/voz/trabajos.json")):
    torch.manual_seed(7)
    t = time.time()
    wav = m.generate(it["say"], language_id="es", audio_prompt_path="voces/muestra.wav",
                     exaggeration=it["exag"], cfg_weight=it["cfg"], temperature=it["temp"])
    ta.save(str(out / f"{it['n']}.wav"), wav, m.sr)
    print(f"[{var}] frase {it['n']}: {wav.shape[-1] / m.sr:.1f}s en {time.time() - t:.0f}s", flush=True)
