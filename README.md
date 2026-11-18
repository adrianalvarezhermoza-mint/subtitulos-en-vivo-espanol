# Subtítulos en vivo EN → ES

Una frase: **escucha el audio de una reunión en inglés y escribe la traducción al
español en la terminal, sin ventanas y sin enviar el audio a ninguna empresa.**

Sirve para una sola persona que **solo necesita entender**, no intervenir. Por eso el
retraso de 6–10 segundos es aceptable y el diseño puede ser mucho más simple y ligero.

## Autoría y créditos

**Código y documentación escritos por un asistente de IA (OpenCode)**, a partir de
las indicaciones de **Adrian Alvarez Hermoza**. Las pruebas en vivo, las decisiones
de diseño y la verificación de los resultados (incluido el cambio de dispositivo
Bluetooth y las medidas de RTF y de traducción) las hizo Adrian en su equipo.

Se declara expresamente para no atribuir a una persona trabajo realizado por IA.

## El encargo (restricciones de diseño)

| Restricción | Consecuencia |
|---|---|
| **Sin interfaz gráfica** | Todo se imprime en la terminal. Nada de ventanas, iconos ni Tk. |
| **Lo más liviano posible** | Pocas librerías, modelos pequeños, 1 hilo de captura + 1 de proceso. |
| **Solo Linux (esta terminal)** | Sin código de otros sistemas que mantener. |
| **Reunión en Zoom** | Se captura el audio del sistema, no la app: da igual navegador o escritorio. |
| **Solo escuchar** | Se puede usar audio acumulado; no hace falta latencia de conversación. |

## Cómo se usa

```bash
# Linux: detecta solo el monitor de audio del sistema
python3 subtitulos.py

# Linux: ver qué dispositivos hay y elegir uno
python3 subtitulos.py --listar
python3 subtitulos.py --fuente NOMBRE

# Solo Linux: no hay versión para Windows (decisión 2026-11-17)

# Opciones reales
#   --modelo base.en       (por defecto; small.en resultó demasiado lento aquí)
#   --chunk 12             (tope del bloque; antes se corta en las pausas)
#   --traductor argos      (argos sin red | deepl con clave | ninguno)
#   --medidor              (solo ver el nivel de volumen)
```

## Arquitectura

```
 ┌──────────────┐  PCM 16 kHz  ┌───────────────┐  inglés  ┌────────────┐  español
 │ Audio del    │ ───────────► │ Whisper local │ ───────► │ Traductor  │ ───────► terminal
 │ sistema      │ trozos hasta 12 s │ (CPU, int8)   │  texto   │ Argos/API  │
 └──────────────┘              └───────────────┘          └────────────┘
        ▲
        │  parec (monitor de PipeWire)
```

Cuatro piezas, cuatro archivos. Ni una más:

| Archivo | Responsabilidad | Líneas aprox. |
|---|---|---|
| `subtitulos.py` | arranque, argumentos, bucle principal, impresión | ~80 |
| `audio.py` | captura y troceado; elige backend según el sistema | ~80 |
| `motor.py` | transcripción (local/API), con una sola función pública | ~70 |
| `traductor.py` | traducción (local/API), con una sola función pública | ~50 |

Objetivo: **menos de 400 líneas en total**. Si se pasa de 800, algo se está
sobre-diseñando.

Más un archivo de datos, que no es código: `glosario.txt` (ver abajo).

### Formato de audio

- **16 kHz, mono, 16 bits** — es lo que Whisper espera; convertir antes de transcribir
  sería gastar CPU para nada.
- Linux: `parec --format=s16le --rate=16000 --channels=1` escribe PCM crudo por
  *stdout*. Cero librerías de audio.
- **Troceado:** se acumula audio y el bloque se cierra en la primera pausa de **0,3 s**,
  con un **tope de 12 s** por si alguien habla sin parar. Así llega la frase entera a
  Whisper y a Argos (con bloques fijos de 5 s se partían y la traducción perdía el
  sujeto). La pausa final no se envía. Si un bloque no tiene voz, **no se transcribe**:
  eso ahorra la mayor parte de la CPU en los ratos muertos.
- **VAD antes de transcribir:** Whisper descarta música, ruido y silencio. Sin eso, un
  bloque que acaba en ruido hace que el modelo se repita y cuesta hasta 6× más.

### Dos hilos

Uno lee audio (bloqueante) y otro transcribe. Se comunican con una cola. Si la cola
crece, se descartan los bloques más viejos: es preferible perder texto a acumular
retraso. Nunca se bloquea la lectura de audio.

### Presentación en terminal

- Una línea por frase terminada, con hora: `[12:03:41] Y así cerramos el trimestre…`
- La frase "en curso" se reescribe en la misma línea con `\r` y se fija con `\n` al
  terminar. Sin repintar la pantalla → sin parpadeo.
- UTF-8 nativo en Linux; no hace falta configurar la terminal.

### Transcripción guardada

Cada sesión escribe en `transcripcion-AAAA-MM-DD.txt`, dentro de la carpeta del
proyecto: la hora, la frase en inglés y su traducción. El archivo se crea **solo
en tu equipo** y está en `.gitignore`, así que nunca se sube a GitHub. Es texto
llano: unas decenas de KB por sesión, y no cambia el consumo de memoria.

Si no se puede crear el archivo, el programa avisa y sigue mostrando los
subtítulos en pantalla.

### Glosario: la mejora más barata

`glosario.txt` es una lista de nombres propios, siglas y términos de la reunión:

```
Marta Ruiz, Kenji Watanabe, Logística, SLA, backlog, churn, rollout, versión 4.2
```

Se pasa como `initial_prompt` a Whisper (texto previo que orienta la transcripción)
y opcionalmente a DeepL como términos que no debe traducir. **Una línea de código,
y los nombres dejan de salir deformados.** Es la mejora con mejor relación
esfuerzo/resultado en audio de reunión.

El mismo archivo sirve como **material de prueba**: se le van añadiendo las palabras
que fallaron en el hito 5.

## Evaluación: ¿transcripción con IA en la nube o local?

La pregunta era explícita. Comparación con los números que importan aquí:

| Motor | Dónde | RAM | Velocidad (4 núcleos) | Calidad en reunión | Coste | Internet | El audio sale |
|---|---|---|---|---|---|---|---|
| faster-whisper `base.en` int8 | local | ~300 MB | 5–8× tiempo real | aceptable | 0 | no | no |
| **faster-whisper `small.en` int8** | **local** | **~700 MB–1 GB** | **2–4× tiempo real** | **buena** | **0** | **no** | **no** |
| whisper.cpp `small.en` | local | ~500 MB | 2–5× tiempo real | igual | 0 | no | no |
| Groq `whisper-large-v3-turbo` | nube | ~0 | casi instantáneo | muy buena | ~0,04 USD/h | sí | **sí** |
| OpenAI `whisper-1` / `gpt-4o-transcribe` | nube | ~0 | 1–2 s | muy buena | ~0,36 USD/h | sí | **sí** |
| AssemblyAI / Deepgram | nube | ~0 | streaming | muy buena | 0,25–0,40 USD/h | sí | **sí** |

**Decisión: transcripción local con `faster-whisper base.en` (int8).**

Por qué, en orden de peso:

1. **Privacidad.** Una reunión son las voces de otras personas. Mandarlas a un tercero
   exige avisarles y, según el sitio, permiso. El audio no sale del equipo.
2. **Dependencia cero.** Si falla internet o el proveedor cambia precios, la reunión
   sigue funcionando.
3. **Coste cero** y sin cuentas ni claves.
4. **La latencia no importa aquí.** El único punto donde la nube gana de verdad es en
   velocidad, y no lo necesitamos porque solo se escucha.

Donde la nube **sí** gana es en calidad con audio difícil (varias voces, acentos,
compresión de Zoom). Si en el hito 2 la transcripción local resulta insuficiente, el
cambio es una línea de configuración: `motor.py` expone `transcribir(audio) -> texto`
y por debajo puede haber un proveedor de nube. **No se decide de oído: se mide en el
hito 2.**

`whisper.cpp` queda como plan B si el equipo no mueve `small` en tiempo real: es más
ligero, pero más manual de instalar. No se empieza por ahí.

## Evaluación: ¿y la traducción?

Traducir es el eslabón que más se nota. Un texto transcrito al 90% y traducido al 80%
se entiende peor que uno al 85% y traducido al 95%.

| Traductor | Dónde | Calidad | Coste | Envía texto |
|---|---|---|---|---|
| Argos Translate en→es | local | suficiente para entender; flojo con jerga y nombres | 0 | no |
| DeepL API Free | nube | notablemente mejor | 0 hasta 500 000 caracteres/mes (≈10 h de reunión) | sí, solo texto |

**Decisión: los dos son intercambiables; Argos por defecto, DeepL opcional.**

La clave: DeepL **solo recibe texto, nunca audio**. Es un compromiso razonable si la
calidad de Argos no basta.

### Cómo se hace el intercambio

Una sola función pública y dos implementaciones escondidas detrás:

```
traductor.py
├── traducir(texto) -> texto     ← lo único que ve el resto del programa
├── _argos(texto)                ← offline
└── _deepl(texto)                ← HTTP con urllib (biblioteca estándar)
```

```toml
# config.toml
traductor = "argos"   # argos | deepl
```

`subtitulos.py` no cambia ni una línea. Es la misma frontera que en `motor.py`.

**Respaldo automático:** si DeepL falla (sin internet, cuota agotada, clave
inválida), se usa Argos y se avisa con una línea. El peor caso nunca es "la reunión
se queda sin subtítulos". Coste: ~10 líneas.

**Qué pesa:**

| Elemento | Coste marginal |
|---|---|
| Código del conmutador | ~30 líneas (< 2 KB) |
| Cliente de DeepL | **0 MB** — `urllib` ya viene con Python |
| Paquete `argostranslate` | ~3–5 MB |
| Modelo Argos en→es | ~120–160 MB en disco |
| RAM con Argos cargado | ~150–300 MB |
| RAM con DeepL | ~0 |

La opción "gratis y offline" es la **pesada**; la de nube no ocupa nada local pero
necesita internet, una clave y que el texto salga del equipo.

**Dos trucos para que no engorde:**

1. **Carga perezosa:** Argos se importa solo cuando se usa. En modo DeepL esos
   ~300 MB de RAM nunca se tocan.
2. **Requisitos separados:** `requirements.txt` con lo mínimo y
   `requirements-offline.txt` con `argostranslate`. Quien use solo DeepL no
   descarga el modelo.

**Aviso sobre el plan gratuito de DeepL:** 500 000 caracteres/mes (≈ 10 h de
reunión), pero para obtener la clave suelen pedir tarjeta para verificar identidad
—sin cobro dentro del límite—. Hay que comprobarlo antes de prometer que sale
gratis. La clave gratuita termina en `:fx` y usa `api-free.deepl.com`; el código
elige el endpoint según la clave.

## Alcance: solo Linux

La decisión se tomó el 2026-11-17: **no se porta a Windows**. El proyecto se usa en
esta terminal (Linux) y ahí está terminado en lo que a código se refiere.

Razones: el único punto ciego técnico era enumerar el dispositivo de *loopback* de
WASAPI en un portátil con 4 GB de RAM, sin poder medirlo desde aquí; y todo el valor
del proyecto depende de que las reuniones ocurran en este equipo. Si eso cambiara,
el trabajo no se pierde: el historial de Git conserva el plan del hito 4.

Todo lo pesado (Whisper, CTranslate2, Argos) corre aquí en CPU, sin GPU y sin conexión
salvo que se elija DeepL.

## Presupuesto de retraso (objetivo)

| Etapa | Tiempo |
|---|---|
| Acumular un bloque | hasta 12 s (corta en la pausa) |
| Transcribir (`base.en` int8, 2 núcleos) | 2–4 s |
| Traducir | 0,1–0,3 s |
| **Total percibido** | **4–8 s** (según la pausa) |

Si supera los 12 s, se baja el tope con `--chunk 8` (el corte por pausa sigue activo).

## Requisitos

- **Disco:** entorno ~1,6 GB (con PyTorch CPU para Argos) + modelos ~230 MB.
- **RAM:** ~1 GB en funcionamiento con Whisper y Argos cargados (medido: ~965 MB).
- **CPU:** 2 núcleos reales bastan con `base.en` int8; más núcleos ayudan.
- **Sin GPU. Sin cuenta. Sin conexión** (salvo que se elija DeepL).
- **Los modelos no están en el repo** (`.gitignore`): se descargan con `curl` y se
  copian a `modelos/` (instrucciones en `ESTADO.md`). Sin ellos no arranca.

## Estado

El avance real, la próxima acción y los bugs viven en **`ESTADO.md`**.
Los pasos ordenados y sus criterios de aceptación viven en **`PLAN.md`**.
Para avisar en una clase de que usas la herramienta, hay un texto listo en
**`AVISO.md`**.

## Licencia

MIT: puedes usar, copiar y modificar el proyecto, también en privado o en otro
repositorio, siempre que conserves el aviso de autoría. El texto completo está
en `LICENSE`. Las transcripciones que generes no forman parte del repo.

## Reglas del proyecto

- Un hito a la vez. No se empieza el siguiente hasta que el anterior funcione.
- Cada cambio se prueba a mano antes de darlo por bueno.
- Nada de dependencias nuevas sin avisar.
- **Nada de interfaz gráfica.** Si una idea necesita una ventana, va a "fuera de alcance".
