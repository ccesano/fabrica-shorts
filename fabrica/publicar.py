"""Publica un video aprobado en YouTube Shorts, Instagram Reels y TikTok a través de la API de Buffer.

uso: python fabrica/publicar.py <url_publica_del_mp4> <publicacion.json> [--cuando 2026-10-25T21:00:00Z] [--solo youtube,instagram]
     python fabrica/publicar.py --canales      (lista los canales conectados en Buffer)

Necesita la variable BUFFER_TOKEN (API key de Buffer: publish.buffer.com → Settings → API).
El video tiene que estar en una URL pública hasta que se publique (Buffer lo descarga de ahí).
Solo usa la biblioteca estándar de Python.
"""
import argparse
import json
import os
import sys
import urllib.request

API = "https://api.buffer.com"
SERVICIOS = ("youtube", "instagram", "tiktok")


def gql(query, variables=None):
    token = os.environ.get("BUFFER_TOKEN")
    if not token:
        sys.exit("Falta BUFFER_TOKEN")
    req = urllib.request.Request(API, data=json.dumps({"query": query, "variables": variables or {}}).encode(),
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Buffer respondió {e.code}: {e.read().decode()[:500]}")
    if d.get("errors"):
        raise RuntimeError("; ".join(x.get("message", str(x)) for x in d["errors"]))
    return d["data"]


def canales():
    orgs = gql("query { account { organizations { id name } } }")["account"]["organizations"]
    out = []
    for o in orgs:
        q = "query($id: OrganizationId!) { channels(input: {organizationId: $id}) { id name service isQueuePaused } }"
        try:
            chs = gql(q, {"id": o["id"]})["channels"]
        except RuntimeError:
            chs = gql(q.replace("OrganizationId!", "String!"), {"id": o["id"]})["channels"]
        out += [dict(c, org=o["name"]) for c in chs]
    return out


MUT = """mutation($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess { post { id dueAt } }
    ... on MutationError { message }
  }
}"""


def metadatos(servicio, pub):
    titulo = pub.get("titulo", "")[:100]
    if servicio == "youtube":
        return {"youtube": {"title": titulo, "categoryId": str(pub.get("categoria_youtube", "24")), "privacy": "public",
                            "madeForKids": False, "notifySubscribers": True, "isAiGenerated": bool(pub.get("contenido_sintetico", True))}}
    if servicio == "instagram":
        return {"instagram": {"type": "reel", "shouldShareToFeed": True}}
    if servicio == "tiktok":
        return {"tiktok": {"title": titulo}}
    return None


def publicar(url, pub, cuando=None, solo=None):
    texto = pub.get("descripcion_completa") or pub.get("descripcion", "")
    resultados = {}
    for c in canales():
        s = c["service"].lower()
        if s not in SERVICIOS or (solo and s not in solo):
            continue
        base = {"text": texto if s != "tiktok" else (pub.get("titulo", "") + "\n\n" + texto)[:2000], "channelId": c["id"],
                "schedulingType": "automatic", "assets": [{"video": {"url": url, "metadata": {"thumbnailOffset": int(pub.get("portada_ms", 1500))}}}]}
        if cuando:
            base.update(mode="customScheduled", dueAt=cuando)
        else:
            base.update(mode="shareNow")
        meta = metadatos(s, pub)
        intentos = [dict(base, metadata=meta), base] if meta else [base]
        for inp in intentos:
            try:
                r = gql(MUT, {"input": inp})["createPost"]
            except RuntimeError as e:
                r = {"message": str(e)}
            if r.get("post"):
                resultados[s] = {"ok": True, "id": r["post"]["id"], "cuando": r["post"].get("dueAt")}
                break
            resultados[s] = {"ok": False, "error": r.get("message")}
        print(f"{s:10s} {c['name']}: {resultados[s]}", flush=True)
    return resultados


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("publicacion", nargs="?")
    ap.add_argument("--cuando")
    ap.add_argument("--solo")
    ap.add_argument("--canales", action="store_true")
    a = ap.parse_args()
    if a.canales:
        for c in canales():
            print(f"{c['service']:10s} {c['name']:30s} {c['id']}  (org {c['org']})")
        sys.exit(0)
    pub = json.load(open(a.publicacion))
    res = publicar(a.url, pub, a.cuando, a.solo.split(",") if a.solo else None)
    json.dump(res, open("resultado_publicacion.json", "w"), ensure_ascii=False, indent=1)
    if not res:
        sys.exit("No encontré canales de YouTube, Instagram o TikTok conectados en Buffer")
    if not all(v["ok"] for v in res.values()):
        sys.exit(1)
