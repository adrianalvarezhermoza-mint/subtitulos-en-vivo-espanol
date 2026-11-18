"""Transcripción con Whisper, en local.

Dos funciones públicas, una para cada forma de entrar audio:

    transcribir_pcm(bytes)     audio en vivo, 16 kHz mono s16le
    transcribir_archivo(ruta)  un archivo ya grabado (para pruebas y hito 5)

El resto del programa no sabe qué hay debajo. Cambiar a una API de nube sería
escribir otra versión de estas dos funciones, y nada más.

El modelo se carga una sola vez y se reutiliza: cargarlo tarda segundos y no
puede pasar en cada frase.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

IDIOMA = "en"
MODELO_POR_DEFECTO = "small.en"
RAIZ_MODELOS = Path(__file__).parent / "modelos"

_modelo: WhisperModel | None = None
_nombre_cargado: str | None = None


def cargar(nombre: str = MODELO_POR_DEFECTO) -> WhisperModel:
    """Carga el modelo la primera vez y lo reutiliza después.

    int8 es la cuantización que hace viable la CPU: ocupa la mitad y va el doble
    de rápido, con una pérdida de calidad pequeña.
    """
    global _modelo, _nombre_cargado
    if _modelo is not None and _nombre_cargado == nombre:
        return _modelo

    print(f"Cargando modelo {nombre} (la primera vez descarga ~500 MB)…", flush=True)
    _modelo = WhisperModel(
        nombre,
        device="cpu",
        compute_type="int8",
        download_root=str(RAIZ_MODELOS),
        cpu_threads=4,
    )
    _nombre_cargado = nombre
    return _modelo


def transcribir_pcm(pcm: bytes, glosario: str = "", nombre: str = MODELO_POR_DEFECTO) -> str:
    """Transcribe un bloque de audio crudo (16 kHz, mono, s16le) y devuelve el texto."""
    modelo = cargar(nombre)
    muestras = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    segmentos, _ = modelo.transcribe(
        muestras,
        language=IDIOMA,
        beam_size=1,
        condition_on_previous_text=False,
        initial_prompt=glosario or None,
    )
    return " ".join(s.text.strip() for s in segmentos).strip()


def transcribir_archivo(ruta: str | Path, glosario: str = "", nombre: str = MODELO_POR_DEFECTO):
    """Transcribe un archivo (wav, mp3, ogg…) y devuelve (segmentos, info).

    faster-whisper decodifica solo, con PyAV; no hace falta ffmpeg aparte.
    """
    modelo = cargar(nombre)
    segmentos, info = modelo.transcribe(
        str(ruta),
        language=IDIOMA,
        beam_size=1,
        condition_on_previous_text=False,
        initial_prompt=glosario or None,
    )
    return list(segmentos), info


def leer_glosario(ruta: str | Path | None) -> str:
    """Lee el glosario y devuelve una sola línea, sin comentarios."""
    if not ruta:
        return ""
    texto = Path(ruta).read_text(encoding="utf-8")
    lineas = [l.strip() for l in texto.splitlines() if l.strip() and not l.startswith("#")]
    return " ".join(lineas)
