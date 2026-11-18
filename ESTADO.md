# Estado del proyecto

> **Para la IA:** leer al inicio de cada sesión de este proyecto y actualizar al final.
> **Última actualización:** 2026-11-07

## Dónde estamos

- Hito actual: **1 — Escuchar el audio del sistema** (casi terminado)
- Último cambio: hito 0 cerrado (`.venv` con pip, sin tocar el sistema) y hito 1
  escrito: `audio.py` (captura con `parec`) y `subtitulos.py` (`--listar`, medidor).
- ¿Funciona? **Sí, la captura.** Probada con un tono de prueba: 52 % de nivel. En
  silencio marca 0 %. Falta la prueba real con un vídeo de YouTube.

## Cómo ejecutarlo

```bash
cd /media/spicyguy17/Proyectos/python/subtitulos-en-vivo

.venv/bin/python subtitulos.py --listar        # ver dispositivos
.venv/bin/python subtitulos.py                 # medidor en vivo
.venv/bin/python subtitulos.py --duracion 5    # prueba automática
```

No hace falta `activate`: se llama al Python del entorno directamente.

## Próxima acción

1. **Tú:** poner un vídeo en inglés y ejecutar el medidor. Confirmar que la barra
   sube y baja con la voz (criterio de fin del hito 1).
2. Yo: `pip install faster-whisper` y escribir `motor.py` + el bucle de troceado
   (hito 2). La primera ejecución descarga `small.en` (~500 MB).
3. Medir el RTF e imprimirlo. Ese número decide `small.en` vs `base.en`.

## Decisiones tomadas

- **Transcripción local con `faster-whisper small.en` (int8).** Privacidad (son voces
  de otras personas), coste cero, sin dependencia de internet. La nube es plan B y
  solo se evalúa si el hito 2 no da la talla.
- **Traducción intercambiable: Argos (por defecto) y DeepL (opcional), con respaldo
  automático.** Una función `traducir(texto)` y dos implementaciones detrás; ~30
  líneas y 0 MB extra (DeepL usa `urllib`). Si DeepL falla, se sigue con Argos.
  Carga perezosa y `requirements-offline.txt` para no arrastrar 150 MB si no se usan.
- **Glosario en `glosario.txt` como `initial_prompt`.** La mejora más barata para
  nombres y siglas. Es a la vez configuración y material de prueba.
- **Sin interfaz gráfica.** Texto en la terminal, con `\r` para la frase en curso.
- **Un solo código para Linux y Windows.** La diferencia se aísla en `audio.py`.
- **Python 3.12 y `.venv` local.** `pip` se instaló dentro del entorno con
  `--without-pip` + el script oficial de PyPA: **cero cambios en el sistema**.
- **Menos de 400 líneas** en 4 archivos. Si crece, se recorta.

## Bugs conocidos

- [ ] Ninguno.

## No tocar

- `audio.leer()` y `audio.rms()`: funcionan y son la base de todo lo demás. Si hay que
  tocar algo del audio, primero se añade una prueba.

## Notas de entorno

- Desarrollo y pruebas: este equipo (Linux Mint 22.3, 4 núcleos, sin GPU, 55 GB libres).
- Despliegue: el Windows del usuario (≥8 GB RAM), vía CMD.
- Monitor detectado aquí: `alsa_output.pci-0000_00_1b.0.analog-stereo.monitor`, pero el
  código lo descubre con `pactl get-default-sink`; **no** está escrito a mano.
- Un tono de 440 Hz al 5 % de amplitud da ~52 % en el medidor: sirve como prueba
  rápida sin depender de un vídeo.
