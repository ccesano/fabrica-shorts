"""Publica un video aprobado en YouTube Shorts, Instagram Reels y TikTok a través de la API de Buffer.

uso: python fabrica/publicar.py <url_publica_del_mp4> <publicacion.json> [--cuando 2026-10-25T21:00:00Z] [--solo youtube,instagram]
     python fabrica/publicar.py --canales      (lista los canales conectados en Buffer)

Necesita la variable BUFFER_TOKEN (API key de Buffer: publish.buffer.com → Settings → API).
El video tiene que estar en una URL pública hasta que se publique (Buffer lo descarga de ahí).
Solo usa la biblioteca estándar de Python.
"""
import argparse
import json
import time
import os
import sys
import urllib.request

API = "https://api.buffer.com"
SERVICIOS = ("youtube", "instagram", "tiktok")
IG_MAX = 2196


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


def url_final(url):
    """Los links de descarga de un release de GitHub redirigen a otro host; Buffer no sigue la redirección."""
    if "github.com" not in url:
        return url
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.geturl()
    except Exception as e:  # noqa: BLE001
        print(f"aviso: no pude resolver la URL final ({e}); uso la original", flush=True)
        return url


def estado(pid):
    """Estado real del post en Buffer (programado, enviando, enviado, error) y el mensaje de error si lo hay.
    createPost puede responder bien y el post quedar en "error" segundos después (ej. si no pudo bajar el video)."""
    for q in ('query($id: PostId!) { post(input: {id: $id}) { status error { message } } }',
              'query($id: String!) { post(input: {id: $id}) { status error { message } } }'):
        try:
            p = gql(q, {"id": pid})["post"]
            return p.get("status"), (p.get("error") or {}).get("message")
        except Exception as e:  # noqa: BLE001
            ultimo = e
    print(f"aviso: no pude leer el estado del post {pid} ({ultimo})", flush=True)
    return None, None


def confirmar(pid, espera=25):
    """Espera hasta `espera` s a que Buffer valide el post. Devuelve None si quedó bien, o el error."""
    fin = time.time() + espera
    while True:
        st, err = estado(pid)
        if st == "error":
            return err or "Buffer marcó el post con error"
        if st in ("sent", "sending") or time.time() >= fin:
            return None
        time.sleep(5)


def publicar(url, pub, cuando=None, solo=None):
    original = url
    url = url_final(url)
    texto = pub.get("descripcion_completa") or pub.get("descripcion", "")
    resultados = {}
    for c in canales():
        s = c["service"].lower()
        if s not in SERVICIOS or (solo and s not in solo):
            continue
        txt = texto if s != "tiktok" else (pub.get("titulo", "") + "\n\n" + texto)[:2000]
        if s == "instagram" and len(txt) > IG_MAX:   # Instagram corta en 2196: se recorta desde el final (fuentes)
            txt = txt[:IG_MAX - 1].rsplit("\n", 1)[0].rstrip() + "…"
        base = {"text": txt, "channelId": c["id"],
                "schedulingType": "automatic", "assets": [{"video": {"url": url, "metadata": {"thumbnailOffset": int(pub.get("portada_ms", 1500))}}}]}
        if cuando:
            base.update(mode="customScheduled", dueAt=cuando)
        else:
            base.update(mode="shareNow")
        meta = metadatos(s, pub)
        intentos = [dict(base, metadata=meta), base] if meta else [base]
        errores = []
        for inp in intentos:
            for vuelta in range(3):   # si Buffer no pudo bajar el video, se reintenta con una URL recién resuelta
                try:
                    r = gql(MUT, {"input": inp})["createPost"]
                except RuntimeError as e:
                    r = {"message": str(e)}
                if not r.get("post"):
                    break
                err = confirmar(r["post"]["id"])
                if not err:
                    break
                print(f"{s:10s} intento {vuelta + 1}: Buffer marcó error ({err}); reintento en 20 s", flush=True)
                errores.append(f"post {r['post']['id']} con error: {err}")
                r = {"message": err}
                time.sleep(20)
                url = url_final(original)
                inp = dict(inp, assets=[{"video": dict(inp["assets"][0]["video"], url=url)}])
            if r.get("post"):
                resultados[s] = {"ok": True, "id": r["post"]["id"], "cuando": r["post"].get("dueAt")}
                break
            # se guardan los errores de todos los intentos: el del intento con metadatos es el que importa
            errores.append(("con metadatos: " if inp.get("metadata") else "sin metadatos: ") + str(r.get("message")))
            resultados[s] = {"ok": False, "error": " | ".join(errores)}
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
