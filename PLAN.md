# Plan del proyecto

Cada hito debe ser **usable por sí solo**. Si un hito no se puede probar, es
demasiado grande: pártelo.

Regla de oro: **no se empieza un hito hasta que el anterior cumple su criterio de
"terminado cuando"**.

---

## Hito 0 — Entorno listo

- **Qué hace:** deja Python en condiciones de instalar librerías.
- **Comandos (hecho, sin `sudo`):**
  ```bash
  cd /media/spicyguy17/Proyectos/python/subtitulos-en-vivo
  python3 -m venv --without-pip .venv
  curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
  .venv/bin/python /tmp/get-pip.py
  ```
  No hizo falta instalar `python3-venv` en el sistema: `--without-pip` + el script
  oficial de PyPA deja `pip` **dentro** del entorno, sin tocar nada del sistema.
- **Cómo se prueba:** `.venv/bin/python -m pip --version` responde.
- **Terminado cuando:** `pip` funciona dentro del entorno y no fuera.
- **Estado:** **hecho** (2026-11-07) — pip 26.3 dentro de `.venv`.

---

## Hito 1 — Escuchar el audio del sistema (Linux)

- **Qué hace:** captura lo que suena por los altavoces y muestra un medidor de volumen.
  Todavía no transcribe nada. Es la prueba de que "el oído" funciona.
- **Cómo se prueba:**
  1. Averiguar el dispositivo:
     ```bash
     pactl get-default-sink
     pactl list short sources
     ```
     El nombre del monitor es el de la salida + `.monitor`
     (aquí: `alsa_output.pci-0000_00_1b.0.analog-stereo.monitor`).
  2. Ejecutar y poner un vídeo de YouTube en inglés.
  3. Debe moverse una barra de volumen; en silencio, quedarse en cero.
- **Terminado cuando:** la barra responde al vídeo y vuelve a cero al pausarlo, sin
  cortes ni errores durante 2 minutos seguidos.
- **Riesgo:** el nombre del monitor cambia si se conectan auriculares. El programa debe
  **descubrirlo solo**, no llevarlo escrito a mano.
- **Estado:** **verificado en lo esencial** (2026-11-07). Un tono de prueba mueve la
  barra al 52 % y el silencio la deja en 0 %. La captura de YouTube se confirmó de
  forma indirecta en el hito 3 (10 bloques transcritos) y de forma directa al cambiar
  a Bluetooth a mitad de vídeo: `[audio] salida cambiada: …` y siguió transcribiendo.
  **Falta solo** la prueba de 2 minutos de `--medidor` con un vídeo (la barra moviéndose
  y volviendo a 0 % al pausar); el fondo del hito ya está demostrado.

---

## Hito 2 — Transcribir inglés en la terminal

- **Qué hace:** pasa el audio por Whisper y escribe frases en inglés, con la hora.
  Incluye una medida de velocidad (**RTF**: segundos de proceso por segundo de audio).
- **Comandos:**
  ```bash
  python -m pip install faster-whisper
  python subtitulos.py --solo-ingles
  ```
  La primera ejecución descarga el modelo (~500 MB para `small.en`). Es la única
  descarga grande del proyecto.
- **Cómo se prueba:** vídeo de YouTube en inglés con habla clara durante 3 minutos.
- **Terminado cuando:**
  1. Se leen **5 frases seguidas con sentido** (no palabras sueltas).
  2. El RTF impreso es **menor que 0,6** (procesa más rápido de lo que ocurre).
- **Puerta de decisión:** es aquí donde se elige el motor con datos, no antes.
  - RTF > 1 → bajar a `base.en`.
  - RTF < 0,4 pero texto pobre → probar `medium.en` y medir otra vez.
  - Texto pobre incluso con `medium` → evaluar nube (Groq u OpenAI). El cambio es de
    una línea en `motor.py`.
- **Estado:** **cerrado** (2026-11-07). Modelo elegido: **`base.en`, 2 hilos, int8 →
  RTF 0,71–0,73** en este equipo. `small.en` quedó en 2,24 y se descartó. Texto algo
  peor que `small.en` pero comprensible. Medidas completas en `ESTADO.md`. En Windows
  se puede intentar subir a `small.en` (hito 4).

---

## Hito 3 — Traducir al español

- **Qué hace:** traduce cada frase al español y la imprime con tildes correctas.
- **Comandos:**
  ```bash
  # PyTorch CPU primero: evita los ~2,5 GB de CUDA que no se usan.
  python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
  python -m pip install argostranslate
  # El modelo en→es se instala solo desde modelos/argos/*.argosmodel, sin red.
  python traductor.py --comprobar
  python traductor.py "hello world"
  ```
- **Cómo se prueba:** mismo vídeo del hito 2. Comparar 5 frases de Argos contra las
  mismas 5 pasadas por DeepL (si se tiene clave).
- **Terminado cuando:** se entiende el sentido de 5 frases seguidas sin mirar el
  inglés, y las tildes/ñ salen bien.
- **Puerta de decisión:** si Argos confunde el sentido en más de 1 de cada 5 frases,
  se activa DeepL por defecto (`--traductor deepl`). Solo se envía texto.
- **Estado:** **cerrado** (2026-11-07). `traductor.py` e integración en `subtitulos.py`
  con Argos real. Prueba en vivo con YouTube: 10 bloques seguidos con inglés + español,
  tildes correctas, RTF 0,41–0,58 tras el primer bloque. Ajustes medidos aplicados
  (`int8`, `MINISBD`, `beam_size=1`, 2 hilos). Calidad: suficiente para seguir una
  reunión; falla alguna palabra aislada (`yacht` → «yup»/«dollar»), que es trabajo del
  glosario (hito 5).

---

## Hito 4 — Funcionar en el Windows (CMD)

- **Qué hace:** la misma aplicación, con la captura cambiada a WASAPI *loopback*.
- **Pasos:**
  1. Copiar la carpeta (sin `.venv`, sin `modelos/`) al disco interno del Windows.
  2. Instalar Python 3.12 y crear el entorno:
     ```bat
     py -3.12 -m venv .venv
     .venv\Scripts\activate
     python -m pip install -r requirements.txt
     ```
  3. `chcp 65001` antes de ejecutar, y fuente **Consolas** en la ventana.
  4. `python subtitulos.py --listar` → elegir el dispositivo correcto
     (altavoces o auriculares, el que se esté usando).
  5. Abrir Zoom y hablar (o poner un vídeo) desde otra ventana.
- **Cómo se prueba:** el medidor se mueve con el audio de Zoom.
- **Terminado cuando:** transcribe y traduce durante 5 minutos seguidos, con el mismo
  aspecto que en Linux.
- **Paso obligatorio antes de dar el hito por bueno:** correr aquí la medición que no
  se pudo hacer en Linux:
  ```bat
  python subtitulos.py --archivo pruebas\jfk_22s.wav --medir
  ```
  y elegir el modelo con el número en la mano (`base.en` si el RTF pasa de 1). Este
  equipo decide; el Linux de desarrollo solo dio el peor caso.
- **Riesgo (el único punto ciego del plan):** enumerar los dispositivos de *loopback*.
  Si `soundcard` no los lista bien, se cambia a `pyaudiowpatch` sin tocar el resto.
- **Estado:** pendiente

---

## Hito 5 — Prueba con una reunión de verdad y refinamiento

- **Qué hace:** validar con audio realista (varias voces, acentos, compresión de Zoom)
  y corregir **con datos, no a ojo**.
- **Preparación:** avisar a los participantes. Grabar 10 minutos de una reunión de
  prueba, o usar una grabación a la que se tenga derecho. Ese material **no cambia
  nunca**: todas las comparaciones se hacen contra él.

### A — Línea base, antes de tocar código

Añadir `--registro`, que guarde un JSON por bloque: hora, segundos de audio, RTF, nivel
RMS, texto inglés, texto español, bloques descartados y longitud de la cola. Sin ese
registro no hay refinamiento, hay opiniones.

### B — Clasificar cada fallo en una sola caja

| Caja | Síntoma | Arreglo | Coste |
|---|---|---|---|
| No oyó | huecos en blanco | bajar umbral de silencio, `--listar` | minutos |
| Oyó mal | nombres, siglas, acentos | `glosario.txt` como `initial_prompt` | minutos |
| Tradujo mal | inglés correcto, español raro | glosario, DeepL, partir frases | minutos |
| Llegó tarde | texto viejo, cola creciendo | bloque más corto, `beam_size=1` | horas |
| Cortó frases | frases partidas | cortar en silencio (0,3 s) | ~30 min |

Se cuentan las frases de cada caja y se trabaja **por número de frases afectadas**, no
por lo que suene más interesante.

### C — Un cambio por vez

Se cambia una cosa, se vuelve a pasar los 10 minutos, y se anota el antes/después en
`ESTADO.md`. Si empeora, se revierte. Si se cambian tres cosas a la vez y mejora, no se
sabe cuál fue.

### D — Cuándo parar

Cuando se entiendan **8 de cada 10 frases** y las 2 que fallan sean nombres propios o
cifras: eso se resuelve mirando la pantalla un segundo, no con más código.

- **Cómo se prueba:** reproducir la grabación y leer los subtítulos en vivo.
- **Terminado cuando:** 8/10 frases entendidas, en dos rondas seguidas.
- **Estimación:** 3 rondas de ~1 h. La primera (glosario + cortes en silencio) suele
  resolver la mitad de los problemas.
- **Estado:** pendiente

---

## Hito 6 (opcional) — Un solo ejecutable

- **Qué hace:** empaquetar para Windows con PyInstaller: `subtitulos.exe` + carpeta de
  modelos. Sin instalar Python en la máquina de la reunión.
- **Nota:** **no se puede compilar desde Linux**. Se hace en el Windows, o con GitHub
  Actions usando un runner `windows-latest`.
- **Terminado cuando:** el `.exe` arranca en una carpeta limpia y transcribe.
- **Estado:** pendiente (solo si hace falta; no bloquea nada)

---

## Fuera de alcance (por ahora)

Esto **no** se va a hacer. Si aparece la tentación, se anota aquí y se discute, no se
implementa sobre la marcha:

- Interfaz gráfica, ventana flotante, bandeja del sistema, colores.
- Identificar **quién** habla (diarización): multiplica el tamaño y la complejidad.
- Guardar el acta, resúmenes, exportar `.srt`, historial en disco.
- Otros idiomas distintos de inglés → español.
- Latencia de conversación (< 3 s): no hace falta, solo se escucha.
- App móvil, versión web, Docker.
- `.exe` empaquetado: solo en el hito 6, y solo si se necesita.

## Decisiones pendientes

| Decisión | Se toma en | Cómo |
|---|---|---|
| `small.en` vs `base.en` vs `medium.en` | Hito 2 | según RTF y calidad medidas |
| Local vs nube para transcribir | Hito 2 | solo si lo local no basta |
| Argos vs DeepL | Hito 3 | comparando 5 frases |
| `soundcard` vs `pyaudiowpatch` | Hito 4 | el que enumere bien el *loopback* |

## Riesgos conocidos

1. **El *loopback* de Windows en auriculares.** Captura un dispositivo concreto: si se
   elige el equivocado, hay silencio. Mitigación: comando `--listar`.
2. **CPU justa.** Zoom + navegador + Whisper en 4 núcleos. Mitigación: `base.en`,
   bloques de 3 s, cerrar pestañas.
3. **Calidad con varias voces.** El punto débil real de Whisper pequeño. Mitigación:
   medirlo en el hito 5 antes de prometer nada.
4. **Consentimiento.** Capturar audio de una reunión requiere avisar. No es opcional.
