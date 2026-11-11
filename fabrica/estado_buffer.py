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
for pid in sys.argv[1:]:
    for q in ('query($id: PostId!) { post(input: {id: $id}) { %s } }', 'query($id: String!) { post(input: {id: $id}) { %s } }'):
        try:
            print(pid, json.dumps(gql(q % " ".join(simples), {"id": pid})["post"], ensure_ascii=False))
            break
        except Exception as e:
            err = e
    else:
        print(pid, "ERROR:", err)
