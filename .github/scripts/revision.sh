#!/usr/bin/env bash
# Sube el video renderizado como release (pre-release) y abre o actualiza el issue de revisión.
# uso: revision.sh <slug>     (necesita GH_TOKEN y GITHUB_REPOSITORY)
set -euo pipefail
s=$1; d=videos/$s/salida; tag="video-$s"
titulo=$(jq -r .titulo "$d/publicacion.json")
gh label create revision --color FBCA04 --description "Video esperando aprobación" --force >/dev/null
gh label create publicado --color 0E8A16 --force >/dev/null
gh label create descartado --color B60205 --force >/dev/null
gh release delete "$tag" -y --cleanup-tag >/dev/null 2>&1 || true
gh release create "$tag" --prerelease --title "$titulo" --notes "Video generado por la fábrica desde videos/$s/guion.json ($GITHUB_SHA)." \
  "$d/$s.mp4" "$d/hoja.jpg" "$d/publicacion.json" "$d/informe.json" "$d/voz/narracion.wav#voz-$s.wav" >/dev/null
base="https://github.com/$GITHUB_REPOSITORY/releases/download/$tag"
inf="$d/informe.json"
cuerpo=$(cat <<MD
<!-- slug: $s -->
## 🎬 $titulo

**▶️ [Ver el video]($base/$s.mp4)** · [hoja de cuadros]($base/hoja.jpg) · [guion](https://github.com/$GITHUB_REPOSITORY/blob/$GITHUB_SHA/videos/$s/guion.json)

![hoja]($base/hoja.jpg)

| Duración | Sonoridad | Pico | Controles | Tiempo de fabricación |
|---|---|---|---|---|
| $(jq -r '.medidas.dur|floor' $inf) s | $(jq -r .medidas.lufs $inf) LUFS | $(jq -r .medidas.pico $inf) dBFS | $(jq -r 'if .ok then "✅" else "⚠️ revisar" end' $inf) | $(jq -r '(.tiempos.total/60|floor|tostring)+" min"' $inf) |

**Texto de la publicación**

$(jq -r .descripcion_completa "$d/publicacion.json")

---
**Para decidir, comentá:**
- \`/publicar\` → sale ya en YouTube, Instagram y TikTok
- \`/publicar 2026-10-25 21:00\` → programado (hora de Argentina)
- \`/publicar youtube\` → solo en esa red (también \`instagram\`, \`tiktok\`)
- \`/descartar\` → se archiva

Para cambiar algo, pedíselo a Claude: edita el guion y el video se vuelve a fabricar acá mismo.
MD
)
n=$(gh issue list --label revision --state open --json number,body --jq ".[] | select(.body | contains(\"<!-- slug: $s -->\")) | .number" | head -1)
if [ -n "$n" ]; then
  gh issue edit "$n" --body "$cuerpo" >/dev/null
  gh issue comment "$n" --body "🔁 Nueva versión fabricada ($GITHUB_SHA). [Ver el video]($base/$s.mp4)" >/dev/null
  echo "issue #$n actualizado"
else
  gh issue create --title "Revisar: $titulo" --label revision --body "$cuerpo"
fi
