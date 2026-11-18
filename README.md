# Subtítulos en vivo EN → ES

Una frase: **escucha el audio de una reunión en inglés y escribe la traducción al
español en la terminal, sin ventanas y sin enviar el audio a ninguna empresa.**

Sirve para una sola persona que **solo necesita entender**, no intervenir. Por eso el
retraso de 6–10 segundos es aceptable y el diseño puede ser mucho más simple y ligero.

## El encargo (restricciones de diseño)

| Restricción | Consecuencia |
|---|---|
| **Sin interfaz gráfica** | Todo se imprime en la terminal. Nada de ventanas, iconos ni Tk. |
| **Lo más liviano posible** | Pocas librerías, modelos pequeños, 1 hilo de captura + 1 de proceso. |
| **Linux (esta terminal) y Windows (CMD)** | Un solo código; solo cambia la captura de audio. |
| **Reunión en Zoom** | Se captura el audio del sistema, no la app: da igual navegador o escritorio. |
| **Solo escuchar** | Se puede usar audio acumulado; no hace falta latencia de conversación. |

## Cómo se usará (se completa cuando exista el código)

```bash
# Linux: detecta solo el monitor de audio del sistema
python3 subtitulos.py

# Linux: ver qué dispositivos hay y elegir uno
python3 subtitulos.py --listar

# Windows: elegir el dispositivo de salida (altavoces o auriculares)
python subtitulos.py --dispositivo 3

# Opciones previstas
--modelo small.en      # o base.en si el equipo va justo
--chunk 5              # segundos de audio por bloque
--traductor argos      # argos (offline) | deepl (requiere clave)
```

## Arquitectura

```
 ┌──────────────┐  PCM 16 kHz  ┌───────────────┐  inglés  ┌────────────┐  español
 │ Audio del    │ ───────────► │ Whisper local │ ───────► │ Traductor  │ ───────► terminal
 │ sistema      │  trozos ~5 s │ (CPU, int8)   │  texto   │ Argos/API  │
 └──────────────┘              └───────────────┘          └────────────┘
        ▲
        │  parec            (Linux, monitor de PipeWire)
        │  WASAPI loopback  (Windows, incluido en el sistema)
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
- Windows: WASAPI en modo compartido remuestrea solo; se le pide 16 kHz directamente.
- **Troceado:** bloques de ~5 s, cortando preferentemente en un silencio (0,3 s) para no
  partir palabras. Si un bloque está por debajo de un umbral de volumen, **no se
  transcribe**: eso ahorra la mayor parte de la CPU en los ratos muertos.

### Dos hilos

Uno lee audio (bloqueante) y otro transcribe. Se comunican con una cola. Si la cola
crece, se descartan los bloques más viejos: es preferible perder texto a acumular
retraso. Nunca se bloquea la lectura de audio.

### Presentación en terminal

- Una línea por frase terminada, con hora: `[12:03:41] Y así cerramos el trimestre…`
- La frase "en curso" se reescribe en la misma línea con `\r` y se fija con `\n` al
  terminar. Sin repintar la pantalla → sin parpadeo.
- UTF-8 en ambos sistemas (`chcp 65001` en CMD + `reconfigure` en Python).
  En CMD hace falta una fuente TrueType (Consolas) o las tildes salen como cajas.

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

**Decisión: transcripción local con `faster-whisper small.en` (int8).**

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

## Qué cambia entre Linux y Windows

| Pieza | Linux | Windows | ¿Cambia el código? |
|---|---|---|---|
| Captura | `parec` sobre el *monitor* | WASAPI *loopback* (`soundcard`) | **sí, ~40 líneas aisladas** |
| Transcripción | faster-whisper | igual | no |
| Traducción | Argos / DeepL | igual | no |
| Terminal | UTF-8 nativo | `chcp 65001` + fuente TrueType | casi no |
| Instalación | `apt` + `venv` | instalador de Python + `venv` | no es código |

Todo lo pesado (Whisper, CTranslate2, Argos) son bibliotecas C++ con versión para cada
sistema: el mismo `pip install` funciona en ambos. **El único punto ciego es enumerar y
elegir el dispositivo de *loopback* en Windows**, y se resuelve en 15–30 minutos delante
de la máquina.

## Presupuesto de retraso (objetivo)

| Etapa | Tiempo |
|---|---|
| Acumular un bloque | 4–5 s |
| Transcribir (`small.en` int8, 4 núcleos) | 1,5–3 s |
| Traducir | 0,1–0,3 s |
| **Total percibido** | **6–8 s** |

Si supera los 12 s, se baja a `base.en` o se recorta el bloque a 3 s.

## Requisitos

- **Disco:** ~1,5 GB (modelos ~700 MB, dependencias ~500 MB, margen).
- **RAM:** ~1,5 GB en funcionamiento. Cabe en 8 GB.
- **CPU:** 4 núcleos es el mínimo razonable para `small.en`.
- **Sin GPU. Sin cuenta. Sin conexión** (salvo que se elija DeepL).

## Estado

El avance real, la próxima acción y los bugs viven en **`ESTADO.md`**.
Los pasos ordenados y sus criterios de aceptación viven en **`PLAN.md`**.

## Reglas del proyecto

- Un hito a la vez. No se empieza el siguiente hasta que el anterior funcione.
- Cada cambio se prueba a mano antes de darlo por bueno.
- Nada de dependencias nuevas sin avisar.
- **Nada de interfaz gráfica.** Si una idea necesita una ventana, va a "fuera de alcance".
