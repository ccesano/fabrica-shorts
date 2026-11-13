# Rutina diaria automática (tareas programadas)

Objetivo de Carlos: **mínimo 2 videos por día**, uno de **fútbol** y uno de **interés general** (música, famosos,
historia, inventos, gente común, casos reales). Todo pasa por la *Mesa de guiones*
(https://claude.ai/artifact/BhPC4PrHy9mLcGiBbWBair) con la herramienta `ArtifactData`; las reglas del guion y del
formato están en `CLAUDE.md` y se cumplen igual que en el chat.

## MODO: automático

> Interruptor. Valores: `automático` o `manual`. Lo cambia Claude cuando Carlos lo pide ("volvé al modo manual").

- **automático** (desde el 12/11/2026, a pedido de Carlos): los temas, los guiones, la fabricación y la publicación salen
  solos. Carlos ya no aprueba ni pide publicar; mira cuando quiere y frena si algo no le gusta. Excepciones que **siempre**
  esperan su aprobación (quedan en `borrador` y se le avisa): temas `sensible`, crímenes o violencia, muertes de los
  últimos 12 meses, tragedias con víctimas, menores de edad, o acusaciones contra personas vivas.
- **manual**: nunca se fabrica algo que Carlos no aprobó en la Mesa (`estado: "aprobado"`) y nunca se publica algo que no
  pidió publicar (`estado: "publicacion pedida"`).

En los dos modos: si algo falla o es dudoso, se deja como está y se avisa; y nunca se inventan datos.

**Cómo frena Carlos un video automático:** editando cualquier cosa del guion en la Mesa (pasa a `con cambios` y no se
publica hasta que lo apruebe), escribiendo algo en la nota general, o borrando el post en Buffer antes de la hora.

## Documento de cada guion en la Mesa (colección `guiones`, id = slug)

Además de los campos de `CLAUDE.md` (`titulo, slug, creado, estado, meta, meta_original, lineas[…], fotos[…],
publicar, nota_general`):

- `categoria`: `"fútbol"` o `"general"` (define la hora por defecto de publicación: 19:00 / 22:00).
- `largo`: true si usa `"largo": true`.
- `guion`: **el `guion.json` completo** que se va a fabricar (objeto). Es la fuente para fabricar: no hay otra copia.
- `tema`: id del tema del banco (`t0xx` / `c…`) si salió de ahí.
- `fabricado`: link al commit · `issue`: número del issue de revisión.
- `video`: `{"url": ".../releases/download/video-<slug>/<slug>.mp4", "hoja": ".../hoja.jpg"}`.
- `publicar_pedido`: `{"cuando": "AAAA-MM-DD HH:MM" | "ahora", "pedido_en"}` (lo escribe la página).
- `auto`: true si lo aprobó la rutina (modo automático) · `publicar_auto`: `"AAAA-MM-DD HH:MM"` (hoy 19:00 fútbol,
  22:00 general) · `verificado`: resumen del chequeo de datos independiente.

Estados: `borrador` → (Carlos corrige: `con cambios`) → `aprobado` (botón de Carlos) → `fabricando` → `listo`
(video en la Mesa) → `publicacion pedida` (botón de Carlos) → `programado` / `publicado`. Si falla: `falla`.
Si Carlos edita un guion ya fabricado, vuelve a `con cambios` y hay que aprobarlo de nuevo.

## 0. Propuestas de temas para mañana (todos los días, listas a las 19:00)

1. Clonar/actualizar el repo y leer `CLAUDE.md` y este archivo. Fecha objetivo = **mañana** (hora Argentina).
2. Si ya hay temas con `propuesta == <mañana>` en la colección `temas`, no duplicar.
3. Proponer **3 de fútbol y 3 de interés general** (música, famosos, historia, inventos, gente común, casos reales),
   ordenados del más recomendado al menos. Mezclar:
   - **Efemérides de mañana** (buscar en la web: "un día como hoy <día> de <mes>" fútbol / historia / música).
   - **Actualidad de mañana**: partidos grandes, finales, clásicos, aniversarios redondos, homenajes.
   - **Banco**: temas `pendiente` no `sensible` que no se hayan hecho; si Carlos dejó alguno `elegido` sin usar, va primero.
   Cada propuesta tiene que pasar el filtro de "Qué historias contar" de `CLAUDE.md`, y el dato central tiene que estar
   confirmado por al menos una fuente seria (si no, no se propone). No repetir temas ya hechos (`estado == "hecho"`
   o con un guion en la Mesa).
4. Cargarlas en `temas`:
   - Tema nuevo: doc `t<n>` con el número siguiente: `n, titulo, gancho` (una línea que enganche), `categoria`
     ("Fútbol", "Música", "Famosos", "Historia", "Inventos y curiosidades" o "Gente común"), `formatos`, `sensible`,
     `estado: "pendiente"`, `propuesta: "<mañana AAAA-MM-DD>"`, `porque` (ej. "Efeméride: 27/10/1986" o "Actualidad:
     se juega el clásico" o "Del banco"), `fuente` (link principal).
   - Tema del banco: `update` con `propuesta` y `porque`.
5. Mensaje final corto para Carlos: las 6 propuestas en una línea cada una y "Elegí en la Mesa (Banco de historias →
   Propuestas para mañana) antes de las 5".

## A. Guiones del día (todos los días, listos a las 5:00; la tarea arranca 4:44)

1. Clonar/actualizar el repo `ccesano/fabrica-shorts` y leer `CLAUDE.md`.
2. Ver qué hay en la Mesa (`ArtifactData list guiones`): si ya hay guiones de hoy, no duplicar.
3. Elegir **2 temas**: uno de fútbol y uno de interés general (fútbol = `categoria` "Fútbol" o las subcategorías
   viejas de t001–t100; general = el resto).
   - Primero, de las **propuestas de hoy** (`propuesta == <hoy>`), las que Carlos marcó `elegido`.
   - Después, cualquier otro tema del banco `elegido` (los agregados por Carlos, `origen: "Carlos"`, tienen prioridad).
   - Si en una categoría no eligió nada: la **primera propuesta de hoy** de esa categoría (menor `n`), y avisarlo en el
     mensaje final ("no elegiste de fútbol, fui con la primera propuesta").
   - Si tampoco hay propuestas: una efeméride de hoy, actualidad o un `pendiente` no `sensible` del banco.
   Variar: no repetir paleta, música ni estructura de escenas del video anterior.
4. Para cada tema: investigar con búsqueda web (cada dato con 2 fuentes si se puede; si no se confirma, no va),
   buscar fotos libres (push de `investigacion/<slug>/consultas.json` → el flujo *Buscar imágenes* devuelve
   `resultados.json` en ~2 min) y escribir el `guion.json` según `CLAUDE.md` (si la historia necesita más de 60 s
   para entenderse: `"largo": true`). Elegir 2 a 4 **efectos** para esa historia (tabla "Efectos" de `CLAUDE.md`),
   distintos de los del guion anterior, y nombrarlos en la columna "En pantalla".
5. Validar sin render: `.venv/bin/python fabrica/make_short.py <ruta>/guion.json --sin-render --motor kokoro`
   (si no hay `.venv`: `bash setup.sh sin-voz`). Con fotos de Commons bloqueadas desde la sesión, alcanza con
   `validar()` de `make_short.py`. **No pushear el guion** (el push dispara la fábrica).
6. **Chequeo de datos independiente** (los dos modos, obligatorio en automático): un agente aparte (herramienta Agent,
   general-purpose) que **no** escribió el guion recibe solo el `guion.json` y sus `fuentes`, y verifica con búsqueda web
   cada afirmación de `say`, `sub` y los textos en pantalla (nombres, fechas, cifras, citas textuales, créditos y licencias
   de las fotos). Devuelve la lista de lo que no pudo confirmar. Lo no confirmado se corrige o se saca; si es el corazón
   de la historia, se cambia de tema. Guardar el resumen en `verificado`. (Si la sesión no tiene Agent, hacer una segunda
   pasada propia releyendo cada fuente.)
7. Cargar cada guion en la Mesa (`ArtifactData set guiones/<slug>`) con todos los campos, `categoria`, `guion` (el JSON
   completo) y `tema`. En el banco, al tema usado ponerle `guion: <slug>`.
   - **Modo manual**, o tema de las excepciones del modo automático → `estado: "borrador"`.
   - **Modo automático** → `estado: "aprobado"`, `auto: true`, `publicar_auto: "<hoy> 19:00"` (fútbol) o
     `"<hoy> 22:00"` (general), y fabricar ya: escribir `videos/<slug>/guion.json` de los dos, **un solo commit y un
     solo push a `main`** ("video: <título 1> + <título 2>"; el flujo *Fabricar* toma todos los guiones de la subida) y
     poner `estado: "fabricando"` y `fabricado` con el link del commit.
8. Terminar con un resumen corto para el aviso al celular. Manual: los dos títulos y "revisalos en la Mesa".
   Automático: los dos títulos con su hora ("hoy 19:00 / 22:00, se fabrican ahora; si querés frenar alguno, editalo en
   la Mesa antes de las 12:40"), y cuál quedó esperando su aprobación y por qué.

## B. Revisión de la Mesa (8:40, 12:40, 16:40 y 18:40; si no hay nada pendiente, termina enseguida)

Leer todos los guiones (`ArtifactData list guiones`) y, para cada uno según su estado:

- **`aprobado`** → fabricar:
  1. Tomar `guion` del documento y aplicar lo que Carlos cambió en la Mesa: `lineas[i].voz` → `say` (y `sub`, con
     cifras en `sub` y números en letras en `say`), `emocion`, `meta` (paleta, música, ambiente), `publicar`
     (título y descripción). Las `nota` de cada línea y la `nota_general` son pedidos: aplicarlos si se pueden hacer
     con los tipos de escena y objetos disponibles; si piden un **dato nuevo**, verificarlo antes; si no se puede,
     explicarlo en el resumen y no inventar.
  2. Validar, escribir `videos/<slug>/guion.json`, commit `video: <título>` y push a `main`.
  3. Actualizar el doc: `estado: "fabricando"`, `fabricado: <link commit>`, y el `guion` con los cambios aplicados.
- **`fabricando`** → ver si terminó: issue con `<!-- slug: <slug> -->` (`gh api repos/ccesano/fabrica-shorts/issues`)
  y release `video-<slug>`. Si está: `estado: "listo"`, `issue`, `video {url, hoja, ver, ver_id}`.
  `url` y `hoja` son las URLs de descarga del release. **Para que Carlos lo vea en el celular** (la página no puede
  reproducir el link de GitHub, que además fuerza la descarga): bajar el mp4 con
  `gh api -H "Accept: application/octet-stream" repos/ccesano/fabrica-shorts/releases/assets/<id>` (no `gh release download`,
  usa GraphQL y falla), hacer una copia liviana
  `ffmpeg -i in.mp4 -vf scale=720:-2 -c:v libx264 -crf 27 -c:a aac -b:a 96k -movflags +faststart <slug>-ver.mp4`
  (≈ 4 MB; el límite de assets es 15 MB), subirla a la Mesa con `Artifact` (`asset: true`, `url` de la Mesa) y guardar
  `ver: "/_blob/<id>"` y `ver_id: "<id>"`. La Mesa reproduce `ver`; el link de abajo es para descargar en calidad completa.
  Si hay un issue con etiqueta `falla` posterior al commit: `estado: "falla"` y explicar el error en el resumen.
  Si queda `listo` y tiene `auto: true`, seguir en la misma pasada con la regla de abajo (no esperar a la próxima revisión).
- **`publicacion pedida`** → comentar en el issue `/publicar` (si `cuando` es "ahora") o `/publicar AAAA-MM-DD HH:MM`;
  esperar la respuesta del flujo *Publicar* (✅ Enviado a Buffer) y poner `estado: "programado"` (o `"publicado"` si
  fue "ahora"). Marcar el tema del banco como `hecho`.
- **`listo` con `auto: true`** (solo en modo automático y solo en las revisiones de las 12:40 en adelante, para que
  Carlos tenga la mañana para mirarlo) → programar solo si: el `informe.json` del release dice `"ok": true`, el doc
  sigue en `listo` y `nota_general` está vacía. Comentar en el issue `/publicar <publicar_auto>` (si esa hora ya pasó:
  `/publicar` ahora… solo si son menos de las 23:00; si no, el día siguiente a la misma hora), esperar
  "✅ Enviado a Buffer", poner `estado: "programado"` y marcar el tema del banco como `hecho`. Si el informe no dice ok,
  no publicar: `estado: "falla"` y avisar.
- Si el flujo *Publicar* responde **"❌ No se pudo publicar"** (Buffer no aceptó o no pudo bajar el video aun después de
  reintentar): `estado: "falla"`, aviso al celular con el motivo, y no reintentar sola más de una vez por revisión.
- **`programado`** con fecha ya pasada → confirmar en Buffer antes de marcarlo: correr el flujo *Estado en Buffer*
  (`gh api -X POST repos/ccesano/fabrica-shorts/actions/workflows/estado-buffer.yml/dispatches -f ref=main -f 'inputs[ids]=<ids>'`,
  los ids están en el comentario "✅ Enviado a Buffer" del issue) y leer el log. Si los tres dicen `sent`: `estado: "publicado"`.
  Si alguno dice `error`: volver a poner la etiqueta `revision` en el issue, comentar `/publicar` (sale ya, solo esa red si
  es una: `/publicar youtube`) y avisar al celular. (Desde el 13/11 los programados usan un link fijo en la rama `publicos`;
  antes el link del release vencía en ~1 h y fallaban los programados con más anticipación.)

Si no hubo nada que hacer, terminar sin aviso. Si hubo cambios, resumen corto: qué se fabricó, qué video está listo
para ver en la Mesa, qué quedó programado, qué falló.
