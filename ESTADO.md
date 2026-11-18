# Estado del proyecto

> **Para la IA:** leer al inicio de cada sesión de este proyecto y actualizar al final.
> **Última actualización:** 2026-11-07

## Dónde estamos

- Hito actual: **2 — Transcribir inglés** (funciona, velocidad insuficiente en este equipo)
- Último cambio: `faster-whisper` instalado y modelo `small.en` descargado. `motor.py`
  escrito, `subtitulos.py` con `--archivo`, `--modelo`, `--glosario` y `--medir`.
  Transcripción **perfecta** en la prueba (JFK, 66 s: texto íntegro y correcto).
- ¿Funciona? **Sí para transcribir; no para el vivo en este equipo.** Ver medidas.

## Medidas (2026-11-07, este equipo: Haswell ULT, 2 núcleos reales, sin GPU)

Prueba: `pruebas/jfk_22s.wav` (22 s de habla clara).

| Modelo | Hilos | Precisión | RTF | Veredicto |
|---|---|---|---|---|
| `small.en` int8 | 4 | correcta | 2,99 | inviable |
| `small.en` int8 | **2** | correcta | **2,24** | inviable en vivo |
| `small.en` float32 | 2 | correcta | 3,40 | peor que int8 |
| `base.en` | 2 y 4 | — | **no medido** | descarga imposible hoy |

- **RTF** = segundos de proceso por segundo de audio. Para el vivo hace falta < 1.
- **4 hilos es peor que 2**: el CPU tiene 2 núcleos reales e hyperthreading; los hilos
  compiten. `cpu_threads=2` es la configuración correcta aquí.
- **int8 gana a float32** en este procesador (2,24 contra 3,40).
- `base.en` (145 MB) **no se pudo descargar**: la conexión con HuggingFace cayó a
  ~44 KB/s y el intento terminó en *read operation timed out*. No es un fallo del
  código; es la red.

**Extrapolación:** `base.en` tiene ~3× menos parámetros que `small.en`; aquí daría un
RTF de ~0,75–0,9, justo en el límite. Este equipo es el **peor caso** (portátil de
2013–2014, 15 W). El Windows del usuario, con 4 núcleos modernos, debería quedar en
0,3–0,5. **La decisión del modelo se toma allí, no aquí.**

## Cómo ejecutarlo

```bash
cd /media/spicyguy17/Proyectos/python/subtitulos-en-vivo

.venv/bin/python subtitulos.py --listar
.venv/bin/python subtitulos.py --medidor
.venv/bin/python subtitulos.py                          # transcribir en vivo
.venv/bin/python subtitulos.py --archivo pruebas/jfk_22s.wav --medir
```

## Próxima acción

1. **Cuando la red lo permita:** `--modelo base.en` (145 MB) y repetir la medición.
2. Añadir `--bench` para que la misma medición se pueda correr en el Windows del hito 4
   con un comando, sin tocar código.
3. Hito 3: `traductor.py` con Argos y DeepL intercambiables.

## Decisiones tomadas

- **`cpu_threads=2`**, no 4. Medido: 2,24 contra 2,99.
- **int8**, no float32. Medido: 2,24 contra 3,40.
- **`av==13.1.0` fijado en `requirements.txt`.** `av` 19 eliminó `metadata_errors` y
  faster-whisper 1.2.1 todavía lo usa: sin el pin, transcribir archivos falla con
  `TypeError`. Costó 20 minutos encontrarlo; no volver a subirlo sin probar.
- **Transcripción local, `faster-whisper`.** Sin PyTorch: 472 MB de entorno en vez de
  ~2 GB.
- **Traducción intercambiable (Argos/DeepL) con respaldo automático.** ~30 líneas.
- **Glosario en `glosario.txt`** como `initial_prompt`.
- **Sin interfaz gráfica.** Texto en terminal.
- **Un solo código para Linux y Windows**; la diferencia se aísla en `audio.py`.

## Bugs conocidos

- [ ] `base.en` no descarga (red). Reintentar más tarde; no es código.
- [x] `TypeError: metadata_errors` al transcribir archivos → `av==13.1.0`.

## No tocar

- `audio.leer()`, `audio.rms()`: funcionan.
- `motor.transcribir_pcm()`: texto correcto; solo discute la velocidad, no la calidad.

## Notas de entorno

- Este equipo es el **peor caso** de rendimiento. No sirve para decidir el modelo final.
- Modelos en `modelos/` (~464 MB), entorno en `.venv/` (472 MB). Nada en el sistema.
- El test de 22 s se genera con: copiar dos veces `pruebas/jfk.wav` con `wave`.
