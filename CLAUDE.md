# Fábrica de Shorts — instrucciones para Claude

Este repo convierte **un pedido = un video**: Claude escribe `videos/<slug>/guion.json`, y la fábrica hace la voz
clonada de Carlos, las escenas (HyperFrames + collage de papel), la música, la mezcla, el render y los controles.
Canal: público hispanohablante de Latinoamérica, adultos de 50+. Formato 9:16, 35–60 s.

## Cuando Carlos pide un video ("hacé un short sobre X")

El guion **siempre pasa por Carlos antes de fabricarse**. Dos tiempos:

**A. Propuesta (no se pushea nada todavía)**
1. **Investigar** el tema con búsqueda web. Cada dato del guion tiene que estar verificado; anotar las fuentes en `"fuentes"`.
   Si algo no se puede confirmar, no va.
2. **Mostrar el guion en el chat** como una tabla, una fila por línea:
   `# | Voz (say) | En pantalla (tipo de escena + textos + objeto) | Emoción`
   y arriba, en una línea: paleta · ánimo de la música · ambiente · duración estimada (caracteres / 15 ≈ segundos).
   Debajo, el título y la descripción de la publicación. Terminar preguntando qué cambiar.
   **Además**, cargar el guion en la *Mesa de guiones* (https://claude.ai/artifact/BhPC4PrHy9mLcGiBbWBair) con
   `ArtifactData` `set` en la colección `guiones`, doc id = slug. Campos: `titulo, slug, creado (ISO), estado: "borrador",
   meta {paleta, musica, ambiente}, meta_original (copia), lineas [{n, tipo, voz, voz_original, pantalla,
   pantalla_original, emocion, emocion_original, nota: ""}], fotos [{n, titulo, url (página de Commons), licencia}],
   publicar {titulo, descripcion}, nota_general: ""`. Ahí Carlos corrige (se guarda solo) y toca *Aprobar*.
   Cuando escriba "listo", leer el doc (`ArtifactData get`), aplicar las líneas cambiadas y las notas
   (`nota` por línea y `nota_general` son pedidos para Claude) y, si `estado` es `"aprobado"`, fabricar.
3. **Iterar** con sus pedidos creativos (gancho, objetos, colores, música, qué frase más emotiva, etc.) hasta que diga
   que está bien ("dale", "ok", "fabricalo"). Las palabras de Carlos mandan sobre las reglas de abajo, salvo los datos
   sin verificar.

**B. Fabricación (solo con su OK)**
4. Escribir `videos/<AAAA-MM-DD>-<slug-corto>/guion.json` (formato abajo; ejemplo de referencia:
   `videos/maradona-despedida/guion.json`).
5. **Commit + push a `main`** con el mensaje `video: <título>`. El flujo de GitHub *Fabricar* renderiza solo
   y abre un issue de revisión con el video. **No renderices en la sesión** salvo que Carlos lo pida (gasta tiempo y tokens).
   Para validar el JSON sin render: `.venv/bin/python fabrica/make_short.py videos/<slug>/guion.json --sin-render --motor kokoro`
   (requiere `bash setup.sh sin-voz` una vez por sesión).
6. Responder con el título y el link al commit; el video llega en ~15 min como issue *Revisar: …*.

Si Carlos pide cambios a un video ya hecho: editar su `guion.json` y volver a pushear (la voz de las líneas que no
cambiaron se reutiliza y el issue se actualiza con la versión nueva).
Si pide varios videos juntos, proponer todos los guiones en el mismo mensaje (uno debajo del otro) y fabricar los aprobados.

## Rutina automática

Hay tres tareas programadas: una propone temas para el día siguiente (19:00), otra arma los guiones del día (listos a las 5:00) y otra revisa la Mesa cada hora (fabricar lo aprobado,
traer los videos, programar lo que Carlos pidió publicar). Cómo funcionan y los campos extra de la Mesa: `RUTINA.md`.
Si Carlos pide un video desde el chat, se sigue el flujo de arriba, pero al cargarlo en la Mesa se agregan `categoria`
y `guion` (el JSON completo) para que la rutina pueda fabricarlo cuando lo apruebe.

## Qué historias contar

Concepto del canal: **historias increíbles y reales** (fútbol, música, famosos, historia, inventos y gente común), con
ángulo argentino y latinoamericano. La promesa es "esto pasó de verdad", así que verificar es lo más importante: lo que
no se confirma no va, y una leyenda se cuenta como leyenda ("dicen que…").
Filtro: **¿se sostiene contada en una mesa de café, sin mostrar el video?** No usamos video ni audio de terceros: nada de
goles para *ver*, canciones, letras ni fragmentos de TV. Famosos: solo hechos documentados, nunca rumores. Gente común:
solo historias ya publicadas en medios, sin exponer a personas vulnerables ni a menores; tragedias con respeto.

**Banco de historias**: pestaña de la Mesa de guiones, colección `temas` (`n, titulo, gancho, categoria, formatos[],
sensible, estado` = pendiente | elegido | hecho | descartado). Categorías: Fútbol (los docs t001–t100 tienen la
subcategoría vieja en `categoria`; la página los agrupa como Fútbol), Música, Famosos, Historia, Inventos y curiosidades,
Gente común. Carlos puede agregar las suyas desde la página (`origen: "Carlos"`, `fuente`, `nota`, id `c…`).
Cuando pida "armá las elegidas", leerlas (`ArtifactData query` con `estado == elegido`), investigar y proponer los guiones.
Al publicar un video, marcar su tema como `hecho`. Para sumar ideas, agregar docs `t<n>` con el número siguiente.

## Reglas del guion

- 7 a 10 líneas, **≤ 850 caracteres** de narración en total (≈ 50–58 s con la voz clonada). Si Carlos pide contar más o
  la historia no se entiende en 60 s: `"largo": true` (hasta 24 líneas / 2600 caracteres, ≈ 3 min, el máximo de Shorts).
- **Línea 1 = gancho en ~1,5 s**: una frase de **5 a 8 palabras (≤ 45 caracteres)** con el hecho más sorprendente o la
  promesa ("Dos hermanos mataron a sus padres."). El contexto va en la línea 2. Nada de "Hola, hoy les cuento…".
- **Ritmo: nada quieto.** Cada línea es una escena: mejor líneas cortas (≤ 110 caracteres, ≈ 8 s) y más escenas que
  pocas escenas largas. Si una idea necesita más, partila en dos líneas con escenas distintas. La fábrica avisa
  ("⚠ ritmo") cuando la línea 1 o alguna línea se pasa. La cámara ya se mueve sola en todas las escenas.
- **Última línea = cierre + pregunta** para comentarios ("¿Vos lo viviste? Contalo en los comentarios.").
- `say` es lo que se lee: **números en letras** ("cincuenta mil", "mil novecientos ochenta y seis"), nombres
  extranjeros escritos como se pronuncian en castellano si son difíciles ("Stóichkov", "Súker").
  `sub` es el subtítulo: ahí sí van cifras y ortografía original.
- Oraciones cortas. Tono de alguien que cuenta una historia a un amigo, rioplatense neutro (vos).
- El `say` se escribe con ortografía normal: la fábrica cambia sola **solo la ll por "sch"** antes de pasarlo a la voz
  clonada ("lluvia" → "schuvia"); la y queda como y. Es lo que eligió Carlos tras escuchar las pruebas, con la muestra
  de voz original (`voces/muestra.wav.gpg`). Otras opciones: `"voz": {"rioplatense": "sch+y"}`, `"ll"`, `"y"` o `false`.
- Pronunciación de nombres: `fabrica/voz.py` tiene un diccionario `PRONUNCIAR` (ej. "Newell's" → "Ñuls") que se aplica
  solo a lo que lee la voz; el `say` y los subtítulos quedan con la ortografía original. Para un video puntual:
  `"voz": {"pronunciar": {"Nombre": "Cómo se dice"}}`. Si Carlos corrige cómo se dice un nombre, sumarlo al diccionario.
- `emocion` por línea (0 = calmo, 1 = muy intenso): varía la entonación de la voz clonada. Usar 0.4–0.6 de base y
  0.75–0.9 en el clímax.
- `pausa` (s) después de cada línea: 0.4–0.6 normal, 1–1.4 antes y después de una frase textual.
- **Variar** de un video a otro: tipos de escena, paleta, ánimo musical, objeto. YouTube desmonetiza contenido
  "repetitivo o de plantilla", así que no repetir la misma secuencia de escenas dos videos seguidos.

## Formato de `guion.json`

```jsonc
{
  "titulo": "…",                      // interno
  "paleta": "bombonera",              // bombonera | atardecer | bosque | diario | oceano | neon | banda (blanco/rojo/negro) (opcional; si falta se elige sola)
  "musica": {"animo": "epico"},       // epico | nostalgico | misterio | alegre | tension ; "volumen": 0.5 opcional
  "ambiente": "cancha",               // cancha | lluvia | ciudad | ninguno, o varios: ["lluvia", "cancha"]
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
| `foto` | una imagen real como protagonista (con marco o recortada) | `foto` {…}, `etiqueta`?, `palabras` (≤ 2), `sello`? |
| `jugada` | una jugada dibujada: corrida punteada, rivales y arquero de papel, y el remate | `etiqueta`?, `corrida_en`, `remate_en`, `sentido` (izquierda\|derecha), `rivales` (0–3), `arquero` (parado\|eludido), `resultado` (gol\|afuera), `arquero_color`?, `rival_color`?, `palabras` (1)?, `sello`? |
| `dupla` | dos palabras grandes, cada una con su objeto de papel abajo (ej. MILLONARIO + billetes / GALLINA + gallina) | `partes` [{`palabra`, `objeto`}, {…}], `kicker`? |
| `cierre` | final + pregunta | `titulo` (renglones), `cta`, `objeto`? |

Categoría de YouTube en `publicar.categoria_youtube`: 17 deportes, 24 entretenimiento (por defecto), 27 educación, 10 música, 25 noticias.

- Una palabra entre `*asteriscos*` sale en color de acento.
- Cada palabra aparece cuando la voz la dice. Si el texto en pantalla no coincide con lo leído, usar
  `{"texto": "EN PANTALLA", "en": "fragmento del say"}`.
- Textos en pantalla cortos: `etiqueta` ≤ 32 caracteres, `palabras` ≤ 16 caracteres por renglón.
- **Zona segura** (ya resuelta en `escenas.py`): el contenido termina antes de y≈1280 (abajo van los subtítulos, y
  más abajo el usuario y el título de cada app) y a partir de y≈850 deja ~170 px libres a la derecha (botones de
  TikTok, Reels y Shorts). Si se agrega una escena o un objeto nuevo, respetar esas zonas.
- **Marca**: cada video lleva "@lodelhongo" chico, vertical, en el borde izquierdo (`"marca"` en el guion para cambiarlo).

### Objetos (`"objeto": {"tipo": …}`)

`pelota` · `camiseta` {base, color, estilo: rayas|banda|mitad|lisa, nombre, numero, letra} · `reloj` {minuto | hora "HH:MM"}
· `vinilo` {titulo} · `tele` {texto} · `entrada` {titulo, nombre, campos{…}, talon} · `recorte` {volanta, titular}
· `planilla` {volanta, titulo, filas [[n, texto]]} · `marcador` {filas [[equipo, goles]]} · `calendario` {dia, mes, anio}
· `postal` {texto, lugar, colores[]} · `gallina` {banda} · `billetes` {valor} · `foto` (ver abajo).
Cualquiera acepta `"en"` para aparecer en un momento de la narración. Si hace falta un objeto nuevo, se agrega en
`fabrica/objetos.py` (+ estilos en `plantilla/assets/lib/fabrica.css`).

### Imágenes reales (`foto`)

```jsonc
{"tipo": "foto", "url": "https://upload.wikimedia.org/…/archivo.jpg",   // URL DIRECTA al archivo (o "src": archivo en videos/<slug>/)
 "pagina": "https://commons.wikimedia.org/wiki/File:…",                 // página de la imagen
 "credito": "Autor / Archivo General de la Nación", "licencia": "dominio público",
 "tratamiento": "sepia",      // color | byn | sepia — fotos viejas en sepia o byn quedan mejor con el papel
 "recorte": true,             // true = se le quita el fondo (personas, objetos); false = foto con marco y cinta
 "epigrafe": "La Bombonera, 1940"}
```

- Buscar fotos **durante la investigación**, primero en Wikimedia Commons (y Openverse). Fotos argentinas con más de
  20 años de publicadas suelen estar en dominio público (ley 11.723, art. 34; en Commons: `PD-AR-Photo`).
- Carlos tiene una ONG con permisos sobre otras imágenes. Si una foto no tiene licencia libre, se puede usar igual
  **solo si Carlos la aprueba**: marcarla en la tabla del guion con ⚠️ y poner `"licencia": "uso autorizado (ONG)"`.
- Siempre completar `credito`, `licencia` y `pagina`: quedan en `salida/derechos-imagenes.json` y el crédito va solo a la descripción.
- Nunca video ni audio de terceros (partidos, TV, relatos de radio): Content ID los detecta y arriesga strikes.
  Un relato famoso va como `cita` (texto breve, con autor) leído por la voz de Carlos; la jugada, con `jugada` + una foto.
- En la tabla del guion, mostrar cada foto como link para que Carlos la vea antes de aprobar.
- Desde las sesiones de Claude Wikimedia puede estar bloqueado para descargar; no importa: la descarga la hace
  GitHub Actions. Verificá la URL directa del archivo leyendo la página de Commons con WebFetch.

## Cómo está armado

- `fabrica/make_short.py` — orquesta todo; `--motor kokoro|chatterbox|grabada`, `--borrador`, `--sin-render`.
- `fabrica/voz.py` (+ `motor_chatterbox.py`) — voz por línea, control con Whisper y re-generación si no se entiende; caché en `.cache/voz`.
- `fabrica/escenas.py` / `objetos.py` / `proyecto.py` — escenas → proyecto HyperFrames (`plantilla/`).
- `fabrica/imagenes.py` — descarga, sepia/byn, recorte de fondo (IS-Net) y créditos de las fotos.
- `fabrica/audio.py` — música original (instrumentos de lemo-opuscar), ambiente, efectos y mezcla a −14 LUFS.
- `plantilla/assets/lib/collage.js` — animación (paper-collage-skill, MIT) extendida con tipografía cinética, contador y transiciones.
- `.github/workflows/` — *Fabricar* (render + issue de revisión) y *Publicar* (al aprobar, sube a YouTube, Instagram y TikTok vía Buffer).
- `setup.sh` — instala todo en una máquina nueva. La muestra de voz va cifrada (`voces/LEEME.md`).
