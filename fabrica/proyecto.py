"""Escribe el proyecto HyperFrames de un video a partir de las escenas armadas.
Basado en scripts/build.py de paper-collage-skill (MIT)."""
import json
from html import escape as html_escape
import shutil
from pathlib import Path

PLANTILLA = Path(__file__).resolve().parent.parent / "plantilla"


def _scene_html(s):
    attrs = [f'data-seed="{s["seed"]}"', f'data-shake="{14 if s["solid"] else 8}"']
    if s.get("zoom") is not None:
        attrs.append(f'data-zoom="{s["zoom"]}"')
    if s["exit"] is not None:
        attrs.append(f'data-exit="{s["exit"]}"')
    if s["push"]:
        attrs.append('data-push="1"')
        attrs.append(f'data-trans="{s["trans"]}"')
    if s["pushout"] is not None:
        attrs.append(f'data-pushout="{s["pushout"]}"')
        attrs.append(f'data-outdir="{s["outdir"]}"')
    p = s["pal"]
    style = f'--bg: {s["bg"]}; --deep: {p["deep"]}; --acc: {p["acc"]}; --acc2: {p["acc2"]}; --ink: {p["ink"]}'
    cls = "cg-stage solid" if s["solid"] else "cg-stage"
    bd = '<div class="cg-bg-grid"></div><div class="cg-bg-crumple"></div>'
    world = "\n            ".join(s["world"])
    sid = s["id"]
    return f"""<!doctype html>
<html>
  <head><meta charset="UTF-8" /></head>
  <body>
    <!-- Generado por fabrica/proyecto.py desde el guion. No editar a mano. -->
    <template id="{sid}-template">
      <div id="{sid}-root" data-composition-id="{sid}" data-width="1080" data-height="1920" data-duration="{s["dur"]}" style="position: absolute; inset: 0">
        <div id="{sid}-stage" class="{cls}" {" ".join(attrs)} style="{style}">
          {bd}
          <div class="cg-world">
            {world}
          </div>
        </div>
      </div>
      <script>
        Collage.scene("{sid}", "{sid}-stage", {s["dur"]}, 1);
      </script>
    </template>
  </body>
</html>
"""


def escribir(dest, escenas, fin, subs, audio_wav, titulo, acento, extra_assets=None, marca="@lodelhongo"):
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(PLANTILLA, dest)
    if extra_assets and Path(extra_assets).exists():
        shutil.copytree(extra_assets, dest / "assets", dirs_exist_ok=True)
    (dest / "compositions").mkdir(exist_ok=True)
    (dest / "assets/audio").mkdir(parents=True, exist_ok=True)
    shutil.copy(audio_wav, dest / "assets/audio/mezcla.wav")
    for s in escenas:
        (dest / "compositions" / f'{s["id"]}.html').write_text(_scene_html(s))
    hosts = [f'      <div id="el-{s["id"]}" class="scene" style="z-index: {z}" data-composition-id="{s["id"]}" '
             f'data-composition-src="compositions/{s["id"]}.html" data-start="{s["start"]}" data-duration="{s["dur"]}" '
             f'data-track-index="{1 + (z - 1) % 2}"></div>' for z, s in enumerate(escenas, start=1)]
    script = ""
    if subs or marca:   # la capa de subtítulos también lleva la marca del canal
        (dest / "assets/lib/captions.js").write_text(f"window.CAPTIONS = {json.dumps(subs or [], ensure_ascii=False)};\nwindow.CAPTIONS_END = {fin};\n")
        (dest / "compositions/captions.html").write_text(CAPTIONS_HTML.replace("__END__", str(fin)).replace("__MARCA__", html_escape(marca or "")))
        hosts.append(f'      <div id="el-captions" class="scene" style="z-index: 50" data-track-kind="captions" data-composition-id="captions" '
                     f'data-composition-src="compositions/captions.html" data-start="0" data-duration="{fin}" data-track-index="5"></div>')
        script = '\n    <script src="assets/lib/captions.js"></script>'
    hosts.append(f'      <audio id="vo" src="assets/audio/mezcla.wav" data-start="0" data-duration="{fin}" data-track-index="10" data-volume="1"></audio>')
    css = "\n".join((dest / "assets/lib" / f).read_text() for f in ("collage.css", "fabrica.css"))
    css += f"\n:root {{ --cap-acc: {acento}; }}\n"
    (dest / "index.html").write_text(INDEX_HTML.format(css=css, script=script, end=fin, body="\n".join(hosts), title=titulo))
    return dest


INDEX_HTML = """<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>{title}</title>
    <script src="assets/lib/gsap.min.js"></script>
    <script src="assets/lib/collage.js"></script>{script}
    <style>
{css}
    </style>
  </head>
  <body>
    <!-- Generado por fabrica/proyecto.py. -->
    <div id="root" data-composition-id="main" data-width="1080" data-height="1920" data-duration="{end}">
{body}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
"""

CAPTIONS_HTML = """<!doctype html>
<html>
  <head><meta charset="UTF-8" /></head>
  <body>
    <template id="captions-template">
      <div id="cap-root" data-composition-id="captions" data-width="1080" data-height="1920" data-duration="__END__" style="position: absolute; inset: 0">
        <div class="cap-wrap"><span id="cap-text" class="cap" data-layout-allow-overlap></span></div>
        <div class="marca" data-layout-allow-overlap>__MARCA__</div>
      </div>
      <script>
        (function () {
          var el = document.getElementById("cap-text");
          var rows = window.CAPTIONS || [];
          function render(t) {
            var row = null;
            for (var i = rows.length - 1; i >= 0; i -= 1) {
              if (t >= rows[i][0]) { row = t < rows[i][1] ? rows[i] : null; break; }
            }
            if (!row) { el.textContent = ""; el.style.opacity = "0"; return; }
            var k = Math.min(1, Math.max(0, (t - row[0]) / 0.09));
            el.textContent = row[2];
            el.style.opacity = "1";
            el.style.transform = "scale(" + (1.1 - 0.1 * k).toFixed(4) + ")";
          }
          var end = window.CAPTIONS_END;
          var tl = gsap.timeline({ paused: true });
          var d = { t: 0 };
          tl.to(d, { t: end, duration: end, ease: "none", onUpdate: function () { render(d.t); } }, 0);
          render(0);
          window.__timelines["captions"] = tl;
        })();
      </script>
    </template>
  </body>
</html>
"""
