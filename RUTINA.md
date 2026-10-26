# Rutina diaria automática (tareas programadas)

Objetivo de Carlos: **mínimo 2 videos por día**, uno de **fútbol** y uno de **interés general** (música, famosos,
historia, inventos, gente común, casos reales). Todo pasa por la *Mesa de guiones*
(https://claude.ai/artifact/BhPC4PrHy9mLcGiBbWBair) con la herramienta `ArtifactData`; las reglas del guion y del
formato están en `CLAUDE.md` y se cumplen igual que en el chat.

**Nunca** se fabrica algo que Carlos no aprobó en la Mesa (`estado: "aprobado"`), y **nunca** se publica algo que no
pidió publicar (`estado: "publicacion pedida"`). Si algo falla o es dudoso, se deja como está y se avisa.

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
   para entenderse: `"largo": true`).
5. Validar sin render: `.venv/bin/python fabrica/make_short.py <ruta>/guion.json --sin-render --motor kokoro`
   (si no hay `.venv`: `bash setup.sh sin-voz`). Con fotos de Commons bloqueadas desde la sesión, alcanza con
   `validar()` de `make_short.py`. **No pushear el guion** (el push dispara la fábrica).
6. Cargar cada guion en la Mesa (`ArtifactData set guiones/<slug>`) con todos los campos, `estado: "borrador"`,
   `categoria`, `guion` (el JSON completo) y `tema`. En el banco, al tema usado ponerle `guion: <slug>`.
7. Terminar con un resumen corto para el aviso al celular: los dos títulos y "revisalos en la Mesa".

## B. Revisión de la Mesa (cada hora, de 9 a 23)

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
  y release `video-<slug>`. Si está: `estado: "listo"`, `issue`, `video {url, hoja}` (URLs de descarga del release).
  Si hay un issue con etiqueta `falla` posterior al commit: `estado: "falla"` y explicar el error en el resumen.
- **`publicacion pedida`** → comentar en el issue `/publicar` (si `cuando` es "ahora") o `/publicar AAAA-MM-DD HH:MM`;
  esperar la respuesta del flujo *Publicar* (✅ Enviado a Buffer) y poner `estado: "programado"` (o `"publicado"` si
  fue "ahora"). Marcar el tema del banco como `hecho`.
- **`programado`** con fecha ya pasada → `estado: "publicado"`.

Si no hubo nada que hacer, terminar sin aviso. Si hubo cambios, resumen corto: qué se fabricó, qué video está listo
para ver en la Mesa, qué quedó programado, qué falló.
