# Muestra de voz

La fábrica clona la voz a partir de `voces/muestra.wav`: 15 a 30 segundos leyendo con naturalidad,
sin música ni eco, en un lugar silencioso. Ese archivo **no se sube nunca** al repo tal cual
(cualquiera podría clonar tu voz con él).

Para que GitHub Actions pueda usarla, se guarda cifrada:

```bash
gpg --batch --symmetric --cipher-algo AES256 --passphrase "TU_CLAVE" -o voces/muestra.wav.gpg voces/muestra.wav
```

y la clave va como secret del repo, `VOZ_CLAVE` (Settings → Secrets and variables → Actions).
`setup.sh` la descifra sola si encuentra `VOZ_CLAVE`.

Para cambiar el tono, se puede grabar otra muestra (por ejemplo más enérgica) y elegirla en el guion:
`"voz": {"muestra": "voces/energica.wav"}`.
