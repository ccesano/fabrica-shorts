"""Pasa las frases por las mismas transformaciones que la fábrica (pronunciación + ll→sch) y arma trabajos.json."""
import json, sys
sys.path.insert(0, "fabrica")
from voz import pronunciar, rioplatense
fr = json.load(open("pruebas/voz/frases.json"))
items = []
for i, f in enumerate(fr):
    em = float(f["emocion"])
    items.append({"say": rioplatense(pronunciar(f["say"]), "sch"), "exag": round(0.3 + 0.6 * em, 3),
                  "cfg": round(0.5 - 0.2 * em, 3), "temp": 0.75, "n": i})
json.dump(items, open("pruebas/voz/trabajos.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(items, ensure_ascii=False, indent=1))
