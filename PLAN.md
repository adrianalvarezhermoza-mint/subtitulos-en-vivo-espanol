# Plan del proyecto

Cada hito debe ser **usable por sí solo**. Si un hito no se puede probar, es
demasiado grande: pártelo.

Regla de oro: **no se empieza un hito hasta que el anterior cumple su criterio de
"terminado cuando"**.

---

## Hito 0 — Entorno listo

- **Qué hace:** deja Python en condiciones de instalar librerías.
- **Comandos:**
  ```bash
  sudo apt install python3-pip python3-venv      # ~15 MB
  cd /media/spicyguy17/Proyectos/python/subtitulos-en-vivo
  python3 -m venv .venv
  source .venv/bin/activate
  python -m pip install --upgrade pip
  ```
- **Cómo se prueba:** `python -m pip --version` responde con una versión.
- **Terminado cuando:** `pip` funciona **dentro** del entorno `.venv` y no fuera.
- **Estado:** pendiente — **requiere permiso explícito de instalación**.

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
- **Estado:** pendiente

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
- **Estado:** pendiente

---

## Hito 3 — Traducir al español

- **Qué hace:** traduce cada frase al español y la imprime con tildes correctas.
- **Comandos:**
  ```bash
  python -m pip install argostranslate
  python -c "import argostranslate.package as p; p.update_package_index(); \
             pk=p.get_available_packages(); \
             p.install_from_path([x for x in pk if x.from_code=='en' and x.to_code=='es'][0].download())"
  python subtitulos.py
  ```
- **Cómo se prueba:** mismo vídeo del hito 2. Comparar 5 frases de Argos contra las
  mismas 5 pasadas por DeepL (si se tiene clave).
- **Terminado cuando:** se entiende el sentido de 5 frases seguidas sin mirar el
  inglés, y las tildes/ñ salen bien.
- **Puerta de decisión:** si Argos confunde el sentido en más de 1 de cada 5 frases,
  se activa DeepL por defecto (`--traductor deepl`). Solo se envía texto.
- **Estado:** pendiente

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
- **Riesgo (el único punto ciego del plan):** enumerar los dispositivos de *loopback*.
  Si `soundcard` no los lista bien, se cambia a `pyaudiowpatch` sin tocar el resto.
- **Estado:** pendiente

---

## Hito 5 — Prueba con una reunión de verdad

- **Qué hace:** validar con audio realista (varias voces, acentos, compresión de Zoom).
- **Preparación:** avisar a los participantes. Grabar 10 minutos de una reunión de
  prueba, o usar una grabación a la que se tenga derecho.
- **Cómo se prueba:** reproducir la grabación y leer los subtítulos en vivo.
- **Terminado cuando:** se entiende **al menos 8 de cada 10 frases**. Si no, se anota
  qué falla (nombres, siglas, acentos, cortes) en `ESTADO.md` antes de tocar código.
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
