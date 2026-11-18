# Estado del proyecto

> **Para la IA:** leer al inicio de cada sesión de este proyecto y actualizar al final.
> **Última actualización:** 2026-11-07

## Dónde estamos

- Hito actual: **2 — Transcribir inglés: CERRADO**. Hito 3 (traductor) es el siguiente.
- Modelo por defecto: **`base.en`** (carpeta local `modelos/base.en-local/`), 2 hilos, int8.
- ¿Funciona? **Sí.** RTF 0,71–0,73 en este equipo (el peor caso), texto comprensible.

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
.venv/bin/python subtitulos.py                          # transcribir en vivo
.venv/bin/python subtitulos.py --archivo pruebas/jfk_22s.wav --medir
```

## Próxima acción

1. Hito 3: `traductor.py` — `traducir(texto)` con backends `_argos` y `_deepl`
   intercambiables, respaldo automático DeepL→Argos, traductor de mentira para probar
   sin descargas.
2. Pendiente de red: modelo Argos en→es (~150 MB). No bloquea escribir el código.
3. Hito 4 en Windows: copiar la carpeta sin `.venv` ni `modelos/`, `pip install -r
   requirements.txt`, `chcp 65001`, `--listar`, y medición con `--archivo`.
4. Añadir `--bench` para que la medición del hito 4 sea un solo comando.

## Decisiones tomadas

- **`base.en` local, 2 hilos, int8.** Medido: 0,71–0,73 de RTF.
- **`cpu_threads=2`**, no 4. Medido: 0,73 contra 0,97.
- **`MODELO_POR_DEFECTO` es la ruta local**, no el nombre: así no intenta descargar al
  arrancar y falla rápido si falta el modelo.
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

## Notas de entorno

- Este equipo es el **peor caso** de rendimiento. En Windows debería ir mejor.
- Modelos en `modelos/` (~610 MB), entorno en `.venv/` (447 MB). Nada en el sistema.
- El test de 22 s se genera copiando dos veces `pruebas/jfk.wav` con `wave`.
- La red de este equipo es variable (44 KB/s a 1,7 MB/s); no es fallo del proyecto.
