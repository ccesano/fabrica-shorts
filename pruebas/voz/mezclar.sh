#!/usr/bin/env bash
# Une las 4 frases de cada variante (con silencio entre medio), normaliza el volumen y les pone una letra al azar.
set -euo pipefail
mkdir -p salida-voz
letras=(A B C); vars=(actual v3 latam)
orden=$(python3 -c "import random;v=['actual','v3','latam'];random.shuffle(v);print(' '.join(v))")
i=0; : > salida-voz/clave.txt
for v in $orden; do
  [ -f "voz-$v/0.wav" ] || { echo "falta $v"; i=$((i+1)); continue; }
  args=(); filt=""; n=0
  for f in voz-$v/0.wav voz-$v/1.wav voz-$v/2.wav voz-$v/3.wav; do args+=(-i "$f"); filt+="[$n:a]aresample=24000,apad=pad_dur=0.8[a$n];"; n=$((n+1)); done
  filt+="[a0][a1][a2][a3]concat=n=4:v=0:a=1,loudnorm=I=-16:TP=-1.5[o]"
  ffmpeg -v error -y "${args[@]}" -filter_complex "$filt" -map "[o]" -ar 44100 -b:a 160k "salida-voz/voz-${letras[$i]}.mp3"
  echo "${letras[$i]} = $v" >> salida-voz/clave.txt
  i=$((i+1))
done
ls -la salida-voz
