# Estado del proyecto

> **Para la IA:** leer al inicio de cada sesión de este proyecto y actualizar al final.
> **Última actualización:** 2026-11-07

## Dónde estamos

- Hito actual: **0 — Entorno listo** (diseño cerrado, todavía sin código)
- Último cambio: se creó el proyecto, el `README.md` con la evaluación de motores y el
  `PLAN.md` con los 7 hitos. Nada instalado.
- ¿Funciona? **No** — no existe código todavía. Es lo esperado en el hito 0.

## Próxima acción

1. Pedir permiso e instalar `python3-pip` y `python3-venv` (~15 MB) → cerrar hito 0.
2. Crear `.venv` y escribir `audio.py` + `subtitulos.py --listar` (solo medidor de
   volumen) → cerrar hito 1.
3. Escribir `requirements.txt` **solo** cuando se sepa qué se instala en cada hito.

## Decisiones tomadas

- **Transcripción local con `faster-whisper small.en` (int8).** Privacidad (son voces
  de otras personas), coste cero, sin dependencia de internet. La nube queda como plan
  B y solo se evalúa si el hito 2 no da la talla. Comparativa completa en `README.md`.
- **Traducción con Argos por defecto, DeepL como opción.** Argos es offline; DeepL
  mejora la calidad recibiendo **solo texto**, nunca audio (límite gratuito ≈10 h/mes).
- **Sin interfaz gráfica.** La salida es texto en la terminal, con `\r` para la frase en
  curso. Es lo más liviano y funciona igual en Linux y CMD.
- **Un solo código para los dos sistemas.** La diferencia se aísla en `audio.py`:
  `parec` + monitor en Linux, WASAPI *loopback* con `soundcard` en Windows.
- **Python 3.12** (ya instalado aquí) y entorno virtual en el proyecto.
- **Menos de 400 líneas** repartidas en 4 archivos. Si crece, se recorta.

## Bugs conocidos

- [ ] Ninguno todavía (no hay código).

## No tocar

- Nada por ahora. Cuando el hito 2 funcione, se anotará aquí el bloque de
  `motor.transcribir()` como estable.

## Notas de entorno

- Desarrollo y pruebas: este equipo (Linux Mint 22.3, 4 núcleos, sin GPU, 55 GB libres).
- Despliegue: el Windows del usuario (≥8 GB RAM), vía CMD.
- El monitor de audio de este equipo es
  `alsa_output.pci-0000_00_1b.0.analog-stereo.monitor` — pero el código **no** debe
  llevarlo escrito: tiene que descubrirlo con `pactl`.
