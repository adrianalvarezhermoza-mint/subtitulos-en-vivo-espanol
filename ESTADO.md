# Estado del proyecto

> **Para la IA:** leer al inicio de cada sesión de este proyecto y actualizar al final.
> **Última actualización:** 2026-11-07 (noche)

## Dónde estamos

- Hito actual: **3 — Traducir al español: CERRADO** (2026-11-07). Prueba en vivo con
  YouTube: 10 bloques seguidos, inglés + español con tildes correctas, RTF 0,41–0,58
  tras el primer bloque. Se entendían las frases sin mirar el inglés.
- Hito 2 (transcribir inglés): **CERRADO**.
- Cambio de dispositivo en vivo: **VERIFICADO** con Bluetooth real, en los dos sentidos
  (análogo → Bluetooth y Bluetooth → análogo), sin reiniciar.
- Corte por pausa (frases enteras a Whisper y Argos): **IMPLEMENTADO Y MEDIDO**
  (2026-11-07), RTF 0,23–0,30 con bloques de 11–12 s.
- VAD activado (quita música y ruido antes de transcribir): **IMPLEMENTADO Y MEDIDO**,
  evita las repeticiones del modelo y va hasta 6× más rápido con audio ruidoso.
- Hito 1: falta solo la prueba de 2 min de `--medidor` con un vídeo; el fondo ya está
  demostrado.
- Siguiente: **hito 4 (Windows), solo si las reuniones van a ocurrir allí**. Si son en el
  navegador de este Linux, el proyecto ya sirve y el hito 4 se queda opcional.
- Modelo por defecto: **`base.en`** (carpeta local `modelos/base.en-local/`), 2 hilos, int8.
- ¿Funciona? **Sí.** RTF 0,71–0,73 en este equipo en reposo (medido sin VAD; con VAD no
  empeora). Texto comprensible.
- **Todo el trabajo de esta sesión está en disco pero SIN COMMIT** (ver «Git» al final).

## Medidas (2026-11-07, este equipo: Haswell ULT, 2 núcleos reales, sin GPU)

Prueba: `pruebas/jfk_22s.wav` (22 s de habla clara).

| Modelo | Hilos | Tipo | RTF | Veredicto |
|---|---|---|---|---|
| `small.en` | 4 | int8 | 2,99 | inviable |
| `small.en` | 2 | int8 | 2,24 | inviable en vivo |
| `small.en` | 2 | float32 | 3,40 | peor que int8 |
| **`base.en`** | **2** | **int8** | **0,73** | **elegido** |
| `base.en` | 4 | int8 | 0,97 | peor que 2 hilos |
| `base.en` (por defecto del programa) | 2 | int8 | 0,71 | confirma |

- **RTF** = segundos de proceso por segundo de audio. Para el vivo hace falta < 1.
- **4 hilos es peor que 2**: el CPU tiene 2 núcleos reales con hyperthreading; los hilos
  compiten. `cpu_threads=2` es la configuración correcta aquí.
- **int8 gana a float32** en este procesador (2,24 contra 3,40).
- `base.en` transcribe algo peor que `small.en` (fragmenta y confunde alguna palabra),
  pero es la diferencia entre 15 s y 49 s de proceso para 22 s de audio. Con 2 s de
  bloques y 1 voz clara es suficiente.
- En un CPU moderno de 4 núcleos `base.en` debería quedar en 0,3–0,5. **La medición del
  hito 4 en Windows decide si se puede subir a `small.en` allí.**

## Cómo se descargan los modelos (lección)

La librería de HuggingFace **se cuelga** (0 KB/s, proceso vivo, archivo `.incomplete`)
detrás de este enlace. Funciona `curl` con reanudación:

```bash
cd modelos && mkdir <nombre>-local && cd <nombre>-local
for f in config.json model.bin tokenizer.json vocabulary.txt; do
  curl -L --retry 5 -C - -o "$f" \
    "https://huggingface.co/Systran/faster-whisper-<nombre>/resolve/main/$f"
done
```

## Cómo ejecutarlo

```bash
cd /media/spicyguy17/Proyectos/python/subtitulos-en-vivo

.venv/bin/python subtitulos.py --listar
.venv/bin/python subtitulos.py --medidor
.venv/bin/python subtitulos.py                          # transcribir y traducir en vivo
.venv/bin/python subtitulos.py --archivo pruebas/jfk_22s.wav --medir

.venv/bin/python traductor.py --comprobar              # qué motores están listos
.venv/bin/python traductor.py --motor mentira "hello"  # probar sin instalar nada
.venv/bin/python traductor.py "hello world"            # traducir de verdad
```

## Traducción: medidas (2026-11-07, mismo equipo)

Instalado `argostranslate` 1.11.0 con **torch 2.15.0+cpu** (209 MB, sin CUDA). El modelo
en→es se instaló solo desde el `.argosmodel` local, sin red. Calidad de las 5 frases de
prueba: correcta y con tildes («Creo que deberíamos posponer el lanzamiento hasta el
segundo trimestre»).

| Configuración de Argos | 1.ª frase | Siguientes | RAM máx. |
|---|---|---|---|
| Por defecto (`DEFAULT`, beam 4) | 4,4 s | 200–470 ms | 606 MB |
| `MINISBD` + `beam_size=1` | 0,6–1,9 s | 74–207 ms | 540 MB |
| `MINISBD` + `beam=1` + `int8` + 2 hilos | **0,36 s** | **74–123 ms** | 539 MB |
| `float32` | 0,8 s | 170–266 ms | 968 MB |

Con **Whisper + Argos cargados a la vez** (uso real): ~965 MB de RAM. El archivo de
22 s tarda 24,3 s en total (RTF 0,72 sin contar la carga de modelos).

- **`int8` es obligatorio aquí**: mismo texto, la mitad de RAM y el doble de velocidad.
- **`MINISBD`** evita cargar los modelos de frases de Stanza/SpaCy al traducir (ahorra
  ~65 MB y casi 4 s en la primera frase). Aun así, `argostranslate` importa `torch`,
  `spacy` y `stanza` igualmente: no se puede bajar de ~400 MB de RAM.
- **La primera frase siempre tarda** (carga del modelo). Hay que cargar el traductor
  antes de empezar a capturar, no en el primer subtítulo.
- Frases repetidas: Argos las cachea y devuelve en 0 ms.

## Cambio de dispositivo de audio a mitad de sesión (2026-11-07)

Antes, `subtitulos.py` elegía el monitor **solo al arrancar**. Si a mitad de sesión se
conectaban unos auriculares Bluetooth (o se cambiaba la salida por defecto), el programa
seguía escuchando la salida vieja: silencio hasta reiniciar.

Ahora `audio.Captura` es dueña del proceso `parec` y, **cada 15 s**, pregunta con dos
llamadas pequeñas a `pactl` cuál es la salida por defecto:

- Si cambió, cierra `parec` y lo reabre sobre el monitor nuevo. Avisa en pantalla:
  `[audio] salida cambiada: <nombre>`.
- Si `parec` muere de golpe (se desconecta el dispositivo), también intenta reabrir en
  la salida actual antes de rendirse.
- No gasta RAM apreciable: no se crean hilos ni se cargan datos; solo se lanzan dos
  procesos `pactl` cada 15 s.
- Con `--fuente NOMBRE` **no cambia nunca** de dispositivo: el usuario eligió ese.

Probado con el código real: (1) cambio simulado de Bluetooth al monitor analógico →
reabrió y siguió leyendo; (2) `parec` terminado a propósito → reabrió en la salida nueva;
(3) con `--fuente` fija → no reabrió y devolvió 0 bytes (fin de captura). Sin procesos
`parec` colgados al salir.

## Arranque: el primer bloque tarda y el audio puede cortarse

Medido en la prueba en vivo: el primer bloque dio **RTF 1,66** (tarda más que el audio
que procesa) y luego bajó a 0,41–0,58. Además el usuario notó el audio cortándose al
empezar. Causa probable: los dos modelos cargando (10–15 s) mientras el navegador
empieza a reproducir; la CPU de 2 núcleos se satura y el audio Bluetooth sufre.

Mitigación (sin tocar código): arrancar `subtitulos.py` **primero**, esperar a ver
`Ctrl+C para salir.`, y **después** poner el vídeo.

Con el corte por pausa (2026-11-07) el primer bloque puede tardar más: si el vídeo
empieza hablando sin pausas, el bloque crece hasta el tope de 12 s y hasta que no se
cierra no se transcribe. Si la primera línea tarda demasiado, bajar el tope:
`--chunk 8` (el corte en pausas sigue funcionando).

## Prueba real del cambio de dispositivo (2026-11-07 19:55)

Arrancado con los altavoces como salida por defecto y, con el vídeo en marcha,
conectados unos auriculares Bluetooth. Apareció

```
[audio] salida cambiada: bluez_output.88_92_CC_D4_6F_8B.1.monitor
```

y siguió transcribiendo sin reiniciar. **Próxima acción 1: verificada.**

- Tardó unos segundos en notarse: se revisa cada 15 s y solo al terminar el bloque en
  curso. No se perdió texto en el cambio.
- RTF de esa prueba: **1,18 · 0,66 · 1,11 · 0,52 · 1,03 · 0,41**. Los bloques > 1 no
  acumularon retraso (la cola es de 3 y descarta), pero indican CPU justa: Bluetooth
  + vídeo + Whisper en 2 núcleos. Antes del Bluetooth esa sesión iba a 0,41–0,58.
- No se sabe aún cuánto de ese pico es el Bluetooth y cuánto el navegador. Se mide con
  `--archivo pruebas/jfk_22s.wav --medir` con y sin Bluetooth, en reposo.

## Bloques de 5 s: frases partidas y contexto perdido (2026-11-07)

Evidencia de la prueba en vivo:

| Inglés | Español |
|---|---|
| `Almost seven years of the` | `Casi siete años de los` |
| `development in close to $150 million…` | `desarrollo en cerca de $150 millones…` |

El traductor no falló: **la unidad que recibe está partida**. Dos causas:

1. `SEGUNDOS_BLOQUE = 5.0` corta el audio cada 5 s caiga donde caiga, sin mirar las
   pausas del habla. Una frase de 7 s se convierte en dos trozos.
2. Argos traduce **cada bloque aislado**, sin memoria del anterior. Sin sujeto en el
   primer trozo, el español pierde el hilo.

Arreglo previsto (hito 5, caja «Cortó frases», ~30 min): **cortar en silencio**
(≥0,3 s) en vez de a los 5 s fijos, con un tope máximo de ~12 s para que un orador
rápido no bloquee la salida.

- Subir `--chunk` a 10 s **no** es la solución: con RTF ~1 el retraso ya es de 5–6 s y
  crecería. Bloques variables dan frases completas sin esperar de más.
- Alternativa si el silencio no basta: imprimir el inglés al instante y **retener la
  traducción** hasta cerrar la frase (por puntuación). Cuesta un bloque de retraso en
  el español.

## Corte por pausa: implementado y medido (2026-11-07)

Cambio en el hilo `lector` de `subtitulos.py`:

- `SEGUNDOS_BLOQUE` pasa de 5,0 a **12,0** y deja de ser un ritmo fijo: ahora es el **tope**.
- `PAUSA_CORTE = 0,3` s cierra el bloque; `MIN_BLOQUE = 1,0` s evita trozos sin contexto.
- El silencio inicial no se acumula y la pausa final no se envía a Whisper.
- Si la captura termina sola, el último trozo se envía (antes se perdía).
- `--chunk` sigue existiendo, pero ahora significa «tope».

| Prueba | Resultado |
|---|---|
| Sintética: 3 frases de 2,5 s con pausas de 0,6 s | 3 bloques de 2,5 s (antes salían 6 de 1,25) |
| Sintética: monólogo de 20 s sin pausas | 12,0 + 8,0 s (actúa el tope) |
| Sintética: blip de 0,4 s + frase | 1 bloque de 4,0 s (no corta por debajo de 1 s) |
| Sintética: solo silencio | 0 bloques |
| Real (altavoz virtual + `jfk_60s.wav`) | 6 bloques, **todos al tope** |
| Real (`jfk.wav` ×3 con 0,7 s entre copias) | 3 bloques de 11 s, uno por frase, **RTF 0,23–0,30** |

- **RTF con bloques de 11–12 s: 0,23–0,30**, mejor que con 5 s (0,41–0,58): menos
  sobrecarga por bloque. El troceado grande también ahorra CPU.
- El español sale con sujeto y verbo: «Y así mis compatriotas americanos, no pregunten
  qué puede hacer su país por ustedes, pregunten qué pueden hacer por su país.»
- Residuo: hasta 0,1 s de silencio al inicio del bloque, por la granularidad de 125 ms
  del lector. Inofensivo para Whisper.
- **`pruebas/jfk_60s.wav` es el clip de 11 s repetido 6 veces pegado, sin pausas**: sirve
  para medir RTF, no para probar el corte por pausa. Sus 527 tramos no tienen ni una
  pausa ≥ 0,3 s (nivel mínimo 0,0046, umbral 0,008).
- Las frases repetidas que salieron en esa prueba («I saw my…») son de Whisper con audio
  en bucle, no del troceado.
- La prueba real se hizo con un `module-null-sink` de PipeWire y `paplay`, y se
  desmontó después. El navegador del usuario no interviene en el audio capturado.

## VAD: el modelo dejaba de repetirse (2026-11-07)

En la prueba real aparecieron repeticiones dentro de un mismo bloque («About the gift.
About the gift.», «And were elderly. And were elderly.») y una cadena de `S***`.
`condition_on_previous_text` ya estaba en `False`, así que la causa no era el contexto:
eran **bloques que terminaban en música, ruido o silencio**, donde `base.en` entra en
bucle. Con bloques de hasta 12 s eso pasó a ser frecuente (con 5 s casi no cabía).

Medido con `jfk.wav` + 8 s de ruido, mismo audio y mismo equipo:

| | Tiempo | RTF | Texto |
|---|---|---|---|
| sin VAD | 20,07 s | 1,06 | correcto (el ruido lo ignoró de milagro) |
| **con VAD** | **3,47 s** | **0,18** | idéntico |

Por eso `motor.transcribir_pcm()` y `transcribir_archivo()` usan ahora
**`vad_filter=True`**: descarta antes de transcribir lo que no es voz. El modelo VAD
(Silero) viene dentro de `faster-whisper` y no necesita red.

Comprobado que no se come la voz:

| Caso | Sin VAD | Con VAD | Palabras en común |
|---|---|---|---|
| `jfk_22s.wav` limpio | 24,82 s | 22,69 s | 14/14 (100 %) |
| la misma voz a ×0,08 de volumen | 19,74 s | 19,13 s | 14/15 (93 %) |
| voz + 6 s de silencio al final | 20,09 s | 20,94 s | 14/14 (100 %) |

- La ganancia grande es con música o ruido (6× más rápido). Con voz limpia apenas cambia.
- **Las medidas de RTF anteriores a esta fecha son sin VAD**; las nuevas no son
  directamente comparables en audio con ruido.
- No se ha podido reproducir el `S***` exacto del vídeo (no se guardó ese audio). Si
  vuelve a salir, el siguiente paso es limpiar repeticiones en el texto, no tocar el VAD.

## Próxima acción

1. **Repetir la prueba del vídeo de Picasso**, ahora con VAD. El corte por pausa ya se
   vio funcionando en esa prueba (frases enteras: «un electricista retirado que había
   trabajado para Pablo Picasso…»). Falta comprobar que desaparecen las cadenas de
   `S***` y las frases duplicadas. Mirar también el nombre: `Gunnecht`/`Guinec` →
   glosario.
2. Glosario: `yacht` salió como «yup»/«dollar» en el vídeo de yates. Añadirlo a
   `glosario.txt` (el `initial_prompt` lo sesga) y volver a probar ese vídeo.
3. Decidir el hito 4: **solo si las reuniones van a ser en Windows**. Si son en el
   navegador de este Linux, no hace falta.
4. Añadir `--bench` para que la medición del hito 4 sea un solo comando.
5. Pendiente menor: la prueba de 2 min de `--medidor` con vídeo (barra moviéndose,
   0 % al pausar, sin cortes). Cierra el hito 1 por completo.

## Decisión tomada: PyTorch CPU

`argostranslate` → `stanza` → `torch`. El wheel normal de Linux trae CUDA (~2,5–3 GB)
aunque no haya GPU, así que se instaló **primero** el wheel CPU:

```bash
.venv/bin/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install argostranslate
```

- torch 2.15.0+cpu: 209,5 MB de descarga.
- Entorno final: **1,6 GB** (frente a 447 MB antes).
- Sin CUDA instalado: no se desperdician ~2,5 GB en este equipo ni en el Windows.

## Decisiones tomadas

- **`base.en` local, 2 hilos, int8.** Medido: 0,71–0,73 de RTF.
- **`cpu_threads=2`**, no 4. Medido: 0,73 contra 0,97.
- **`MODELO_POR_DEFECTO` es la ruta local**, no el nombre: así no intenta descargar al
  arrancar y falla rápido si falta el modelo.
- **Corte por pausa (0,3 s) con tope de 12 s**, no bloques fijos de 5 s. Medido en
  este equipo: RTF 0,23–0,30 contra 0,41–0,58, y las frases llegan enteras al traductor.
- **`vad_filter=True` siempre.** Medido con ruido al final: 3,47 s contra 20,07 s. Con
  voz limpia no cambia el texto. Sin VAD, un bloque con música hace que `base.en` se
  repita.
- **`av==13.1.0` fijado en `requirements.txt`.** `av` 19 eliminó `metadata_errors` y
  faster-whisper 1.2.1 todavía lo usa: sin el pin, transcribir archivos falla con
  `TypeError`. Costó 20 minutos encontrarlo; no volver a subirlo sin probar.
- **Transcripción local, `faster-whisper`.** Sin PyTorch: 447 MB de entorno.
- **Descargas de modelos con `curl`**, nunca con el cliente de HuggingFace.
- **Traducción intercambiable (Argos/DeepL) con respaldo automático.**
- **Glosario en `glosario.txt`** como `initial_prompt`.
- **Sin interfaz gráfica.** Texto en terminal.

## Bugs conocidos

- Ninguno abierto.
- [x] `TypeError: metadata_errors` al transcribir archivos → `av==13.1.0`.
- [x] `base.en` no descargaba → cliente de HuggingFace colgado; resuelto con `curl`.

## No tocar

- `audio.leer()`, `audio.rms()`: funcionan.
- `motor.transcribir_pcm()`: texto correcto; la velocidad ya está dentro del objetivo.
- **`vad_filter=True`**: no quitarlo. Sin él, un bloque con música o ruido hace que
  `base.en` se repita y cuesta hasta 6× más.
- **`SEGUNDOS_BLOQUE = 12.0` es un tope, no un ritmo**: el bloque se cierra en la pausa
  de 0,3 s. No volver a fijar bloques por reloj.

## Git

Al cerrar la sesión del 2026-11-07 el repositorio tiene **cambios sin confirmar**:

- Modificados: `subtitulos.py`, `motor.py`, `audio.py`, `README.md`, `PLAN.md`,
  `ESTADO.md`, `requirements.txt`.
- Sin seguimiento: `traductor.py` (todo el hito 3), que nunca se ha añadido.

No se ha hecho commit a propósito: es decisión del usuario. Cuando diga, un solo commit
con todo el hito 3 + corte por pausa + VAD deja el proyecto recuperable. Antes de
commitear, comprobar que `.gitignore` cubre `.venv/`, `__pycache__/` y `modelos/`.

## Notas de entorno

- Este equipo es el **peor caso** de rendimiento. En Windows debería ir mejor.
- Modelos en `modelos/` (~321 MB: 141 de Whisper + 84 del `.argosmodel` + 94 instalados),
  entorno en `.venv/` (1,6 GB). Nada en el sistema.
- El test de 22 s se genera copiando dos veces `pruebas/jfk.wav` con `wave`.
- La red de este equipo es variable (44 KB/s a 1,7 MB/s); no es fallo del proyecto.
- **Medir siempre con la máquina en reposo.** Con carga 4,17 el RTF subió a 1,15;
  en reposo dio 0,89 y antes 0,71–0,73. El mismo modelo, el mismo audio: cambia la carga.

## Equipo Windows de destino (captura del 2026-11-07)

- **Portátil, gama baja.** Nombre: `DESKTOP-GP7G2LU`.
- **CPU:** Intel Core **i3-1005G1** (Ice Lake, 2 núcleos / 4 hilos, 1,2 GHz base,
  3,4 GHz turbo). Es más moderno y rápido que el i3-4005U de este equipo; tiene AVX-512.
- **RAM: 4,00 GB (3,75 utilizables).** Este es el límite real del proyecto, no la CPU.
- **Disco:** SSD Samsung de **477 GB**. Espacio de sobra.
- **Gráfica:** Intel UHD (128 MB), sin GPU dedicada. Irrelevante: todo va por CPU.
- **Sistema:** 64 bits. La captura no muestra la versión (¿Windows 10 u 11?). Confirmar
  con `winver`; con 4 GB, Windows 11 deja muy poco margen.
- **Audio:** falta saber si usa altavoces o auriculares; decide el dispositivo de
  *loopback* del hito 4.

### Qué implica para el hito 4

- **`base.en`, no `small.en`.** Con 4 GB de RAM, `small.en` no es viable ni aunque la CPU
  aguante. Medir igualmente con `--archivo pruebas\jfk_22s.wav --medir`.
- **`cpu_threads=2`** también aquí: 2 núcleos reales, igual que en este equipo.
- **Riesgo de RAM:** Windows (2–2,5 GB) + Zoom (0,4 GB) + Whisper (0,3 GB) + Argos
  (0,3–0,5 GB) puede pasar de 3,5 GB. Mitigación: cerrar el navegador, usar `base.en`,
  y probar `ARGOS_CHUNK_TYPE=MINISBD` para no cargar Stanza/PyTorch en memoria.
- **Alternativa si no cabe:** DeepL para traducir (no carga Argos en local) o traducir
  solo lo que se muestra, no todo.

## Limpieza de modelos (2026-11-07)

- Borrado `models--Systran--faster-whisper-small.en` y su blob (`blobs/e6`, 462 MB):
  descartado por lento. `modelos/` pasó de 691 MB a 227 MB.
- Se conservan `base.en-local/` (141 MB) y `argos/translate-en_es-1_0.argosmodel` (84 MB),
  que son los que se copiarán al Windows.
- `models--Systran--faster-whisper-base.en/` (2,5 MB) es una caché incompleta de
  HuggingFace sin `model.bin`; no se usa (el modelo real es `base.en-local/`). Se puede
  borrar cuando se quiera.
