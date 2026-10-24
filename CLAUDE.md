# Fábrica de Shorts — instrucciones para Claude

Este repo convierte **un pedido = un video**: Claude escribe `videos/<slug>/guion.json`, y la fábrica hace la voz
clonada de Carlos, las escenas (HyperFrames + collage de papel), la música, la mezcla, el render y los controles.
Canal: público hispanohablante de Latinoamérica, adultos de 50+. Formato 9:16, 35–60 s.

## Cuando Carlos pide un video ("hacé un short sobre X")

1. **Investigar** el tema con búsqueda web. Cada dato del guion tiene que estar verificado; anotar las fuentes en `"fuentes"`.
   Si algo no se puede confirmar, no va.
2. **Escribir** `videos/<AAAA-MM-DD>-<slug-corto>/guion.json` (formato abajo). Copiá la estructura de
   `videos/maradona-despedida/guion.json`, que es el ejemplo de referencia.
3. **Commit + push a `main`** con el mensaje `video: <título>`. El flujo de GitHub *Fabricar* renderiza solo
   y abre un issue de revisión con el video. **No renderices en la sesión** salvo que Carlos lo pida (gasta tiempo y tokens).
   Para probar el guion sin render: `.venv/bin/python fabrica/make_short.py videos/<slug>/guion.json --sin-render --motor kokoro`
   (requiere `bash setup.sh sin-voz` una vez por sesión).
4. Responder con el título, una línea sobre el enfoque y el link al commit. Nada más.

Si Carlos pide cambios a un video ya hecho: editar su `guion.json` y volver a pushear (la voz de las líneas que no
cambiaron se reutiliza).

## Reglas del guion

- 7 a 10 líneas, **≤ 850 caracteres** de narración en total (≈ 50–58 s con la voz clonada).
- **Línea 1 = gancho** en ≤ 3 s: el hecho más sorprendente o la promesa. Nada de "Hola, hoy les cuento…".
- **Última línea = cierre + pregunta** para comentarios ("¿Vos lo viviste? Contalo en los comentarios.").
- `say` es lo que se lee: **números en letras** ("cincuenta mil", "mil novecientos ochenta y seis"), nombres
  extranjeros escritos como se pronuncian en castellano si son difíciles ("Stóichkov", "Súker").
  `sub` es el subtítulo: ahí sí van cifras y ortografía original.
- Oraciones cortas. Tono de alguien que cuenta una historia a un amigo, rioplatense neutro (vos).
- `emocion` por línea (0 = calmo, 1 = muy intenso): varía la entonación de la voz clonada. Usar 0.4–0.6 de base y
  0.75–0.9 en el clímax.
- `pausa` (s) después de cada línea: 0.4–0.6 normal, 1–1.4 antes y después de una frase textual.
- **Variar** de un video a otro: tipos de escena, paleta, ánimo musical, objeto. YouTube desmonetiza contenido
  "repetitivo o de plantilla", así que no repetir la misma secuencia de escenas dos videos seguidos.

## Formato de `guion.json`

```jsonc
{
  "titulo": "…",                      // interno
  "paleta": "bombonera",              // bombonera | atardecer | bosque | diario | oceano | neon (opcional; si falta se elige sola)
  "musica": {"animo": "epico"},       // epico | nostalgico | misterio | alegre | tension ; "volumen": 0.5 opcional
  "ambiente": "cancha",               // cancha | lluvia | ciudad | ninguno
  "subtitulos": true,
  "fuentes": ["…"],
  "lineas": [
    {"say": "…", "sub": "…", "emocion": 0.5, "pausa": 0.5, "musica": "golpe",   // musica: silencio | subida | golpe (opcional)
     "escena": {"tipo": "…", …}}
  ],
  "publicar": {"titulo": "… #shorts", "descripcion": "…", "hashtags": ["…"]}
}
```

### Tipos de escena (una por línea)

| tipo | para qué | campos |
|---|---|---|
| `golpe` | gancho, giros, frases fuertes: tipografía gigante sobre fondo liso | `palabras` (2–4 renglones), `kicker` opcional |
| `collage` | contexto con un objeto de papel | `etiqueta`, `objeto`, `objeto2`?, `palabras` (≤ 2), `sello`?, `sello_en`? |
| `cifra` | un número que impacta (cuenta hasta el valor) | `numero`, `etiqueta`?, `prefijo`?, `sufijo`?, `decimales`?, `palabra`?, `en`? |
| `lista` | nombres, pasos, ejemplos | `items` (≤ 6), `etiqueta`?, `remate`?, `numerada`? |
| `cita` | frase textual de alguien | `texto` (con `*énfasis*`), `autor` |
| `cierre` | final + pregunta | `titulo` (renglones), `cta`, `objeto`? |

- Una palabra entre `*asteriscos*` sale en color de acento.
- Cada palabra aparece cuando la voz la dice. Si el texto en pantalla no coincide con lo leído, usar
  `{"texto": "EN PANTALLA", "en": "fragmento del say"}`.
- Textos en pantalla cortos: `etiqueta` ≤ 32 caracteres, `palabras` ≤ 16 caracteres por renglón.

### Objetos (`"objeto": {"tipo": …}`)

`pelota` · `camiseta` {base, color, estilo: rayas|banda|mitad|lisa, nombre, numero, letra} · `reloj` {minuto | hora "HH:MM"}
· `vinilo` {titulo} · `tele` {texto} · `entrada` {titulo, nombre, campos{…}, talon} · `recorte` {volanta, titular}
· `planilla` {volanta, titulo, filas [[n, texto]]} · `marcador` {filas [[equipo, goles]]} · `calendario` {dia, mes, anio}
· `postal` {texto, lugar, colores[]} · `foto` {src, epigrafe} (imagen en `videos/<slug>/` con licencia libre).
Cualquiera acepta `"en"` para aparecer en un momento de la narración. Si hace falta un objeto nuevo, se agrega en
`fabrica/objetos.py` (+ estilos en `plantilla/assets/lib/fabrica.css`).

## Cómo está armado

- `fabrica/make_short.py` — orquesta todo; `--motor kokoro|chatterbox|grabada`, `--borrador`, `--sin-render`.
- `fabrica/voz.py` (+ `motor_chatterbox.py`) — voz por línea, control con Whisper y re-generación si no se entiende; caché en `.cache/voz`.
- `fabrica/escenas.py` / `objetos.py` / `proyecto.py` — escenas → proyecto HyperFrames (`plantilla/`).
- `fabrica/audio.py` — música original (instrumentos de lemo-opuscar), ambiente, efectos y mezcla a −14 LUFS.
- `plantilla/assets/lib/collage.js` — animación (paper-collage-skill, MIT) extendida con tipografía cinética, contador y transiciones.
- `.github/workflows/` — *Fabricar* (render + issue de revisión) y *Publicar* (al aprobar, sube a YouTube, Instagram y TikTok vía Buffer).
- `setup.sh` — instala todo en una máquina nueva. La muestra de voz va cifrada (`voces/LEEME.md`).
