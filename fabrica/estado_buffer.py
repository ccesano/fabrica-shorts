"""Muestra el estado de posts de Buffer por id (y si la cola de cada canal está pausada).

uso: python fabrica/estado_buffer.py <id> [<id> …]
"""
import json, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from publicar import gql, canales

for c in canales():
    print(f"canal {c['service']:<10} {c['name']}: cola pausada = {c.get('isQueuePaused')}")

# campos del tipo Post (introspección), para no adivinar el esquema
t = gql('query { __type(name: "Post") { fields { name type { kind name ofType { kind name } } } } }')["__type"]
simples = [f["name"] for f in t["fields"] if (f["type"].get("kind") in ("SCALAR", "ENUM")) or
           ((f["type"].get("ofType") or {}).get("kind") in ("SCALAR", "ENUM"))]
print("campos Post:", ", ".join(f["name"] for f in t["fields"]))
ef = next((f for f in t["fields"] if f["name"] == "error"), None)
if ef:
    en = ef["type"].get("name") or (ef["type"].get("ofType") or {}).get("name")
    et = gql('query($n: String!) { __type(name: $n) { fields { name type { kind ofType { kind } } } } }', {"n": en})["__type"]
    sub = [f["name"] for f in (et or {}).get("fields") or [] if "SCALAR" in (f["type"]["kind"], (f["type"].get("ofType") or {}).get("kind")) or "ENUM" in (f["type"]["kind"], (f["type"].get("ofType") or {}).get("kind"))]
    if sub:
        simples.append("error { %s }" % " ".join(sub))
for pid in sys.argv[1:]:
    for q in ('query($id: PostId!) { post(input: {id: $id}) { %s } }', 'query($id: String!) { post(input: {id: $id}) { %s } }'):
        try:
            r = gql(q % " ".join(simples), {"id": pid})["post"]; r.pop("text", None)
            print(pid, json.dumps(r, ensure_ascii=False))
            break
        except Exception as e:
            err = e
    else:
        print(pid, "ERROR:", err)
