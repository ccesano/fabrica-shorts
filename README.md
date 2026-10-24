# Fábrica de Shorts

**Un pedido = un video.** Le pedís a Claude un tema, Claude investiga y escribe el guion, y la fábrica hace el resto:
tu voz clonada, las escenas (HyperFrames + collage de papel), música original, efectos, mezcla, render y controles.
El video queda esperando tu aprobación en un *issue*, y cuando comentás `/publicar` sale en YouTube Shorts,
Instagram Reels y TikTok.

```
Vos: "hacé un short sobre el gol de Maradona a los ingleses"
  └─ Claude: investiga → videos/<fecha>-<slug>/guion.json → push
       └─ GitHub Actions "Fabricar": voz → escenas → música → render → issue "Revisar: …"
            └─ Vos (desde el celular): mirás el video y comentás /publicar  (o /descartar)
                 └─ GitHub Actions "Publicar": Buffer → YouTube + Instagram + TikTok
```

## Puesta en marcha (una sola vez)

En el repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Para qué | De dónde sale |
|---|---|---|
| `VOZ_CLAVE` | descifrar tu muestra de voz (`voces/muestra.wav.gpg`) | te la pasó Claude |
| `BUFFER_TOKEN` | publicar en las 3 redes | buffer.com → conectar YouTube, Instagram y TikTok → Settings → API → crear API key |
| `CLOUDINARY_URL` | *solo si el repo es privado*: Buffer necesita una URL pública del video | cloudinary.com (gratis) → Dashboard → API environment variable |

Instagram tiene que ser cuenta profesional (Creator o Business) para que Buffer publique Reels solo.

## Uso diario

- **Pedir un video:** en Claude, con este repo conectado: "hacé un short sobre …". Podés dar el enfoque, el tono o los datos.
- **Revisar:** te llega el issue *Revisar: …* con el video, la hoja de cuadros y el texto de la publicación.
- **Decidir** comentando en el issue:
  - `/publicar` → sale ya
  - `/publicar 2026-10-25 21:00` → programado (hora de Argentina)
  - `/publicar youtube instagram` → solo en esas redes
  - `/descartar`
- **Cambios:** pedíselos a Claude; edita el guion y el video se vuelve a fabricar en el mismo issue.

## A mano (en tu PC con Linux/WSL o en una sesión de Claude)

```bash
bash setup.sh                                   # instala todo (~6 GB)
.venv/bin/python fabrica/make_short.py videos/maradona-despedida/guion.json
.venv/bin/python fabrica/make_short.py videos/…/guion.json --motor kokoro --borrador   # prueba rápida
```

Con la RTX de tu PC, Chatterbox usa la GPU sola y la voz tarda segundos en vez de minutos.

## Tiempos y costos

Medido en una máquina de 2 núcleos sin GPU: voz clonada ≈ 1 min por cada 6 s de audio (≈ 10 min por video, se
hace una sola vez por línea), música y mezcla ≈ 10 s, render ≈ 4 min. Todo el software es gratuito y de código
abierto; ver [CREDITOS.md](CREDITOS.md).
