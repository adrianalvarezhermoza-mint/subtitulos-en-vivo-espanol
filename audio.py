"""Captura del audio del sistema.

Solo biblioteca estándar: `parec` (de PipeWire/PulseAudio) escribe PCM crudo por
su salida estándar y aquí lo leemos por bloques.

Formato fijo: 16 kHz, mono, 16 bits con signo little-endian (s16le), que es
exactamente lo que Whisper espera. Convertir después sería gastar CPU para nada.

En Windows este archivo tendrá un hermano (`audio_windows.py`) con WASAPI
loopback; la interfaz pública es la misma: listar_fuentes(), mejor_monitor(),
abrir_captura(), leer(), rms().
"""

from __future__ import annotations

import math
import subprocess
import sys
import time
from array import array

RATE = 16_000
CANALES = 1
BYTES_POR_MUESTRA = 2
BYTES_POR_SEGUNDO = RATE * CANALES * BYTES_POR_MUESTRA


def _pactl(*args: str) -> str:
    """Ejecuta pactl y devuelve su salida, o cadena vacía si falla."""
    try:
        salida = subprocess.run(
            ["pactl", *args], capture_output=True, text=True, timeout=5
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return salida.stdout if salida.returncode == 0 else ""


def listar_fuentes() -> list[tuple[str, bool]]:
    """Devuelve [(nombre, es_monitor)] de las fuentes de audio disponibles.

    Un "monitor" es lo que suena por los altavoces: es lo que queremos.
    Un micrófono normal no sirve para escuchar una reunión.
    """
    fuentes: list[tuple[str, bool]] = []
    for linea in _pactl("list", "short", "sources").splitlines():
        campos = linea.split("\t")
        if len(campos) < 2:
            continue
        nombre = campos[1]
        fuentes.append((nombre, nombre.endswith(".monitor")))
    return fuentes


def mejor_monitor() -> str | None:
    """Elige el monitor de la salida por defecto; si no, el primer monitor."""
    salida = _pactl("get-default-sink").strip()
    if salida:
        candidato = f"{salida}.monitor"
        if any(n == candidato for n, _ in listar_fuentes()):
            return candidato
    for nombre, es_monitor in listar_fuentes():
        if es_monitor:
            return nombre
    return None


def abrir_captura(fuente: str) -> subprocess.Popen:
    """Arranca `parec` y devuelve el proceso del que se lee el PCM crudo."""
    return subprocess.Popen(
        [
            "parec",
            f"--device={fuente}",
            "--format=s16le",
            f"--rate={RATE}",
            f"--channels={CANALES}",
            "--latency-msec=50",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )


def _cerrar(proceso: subprocess.Popen) -> None:
    """Termina `parec` sin dejar procesos colgados."""
    if proceso.poll() is not None:
        return
    proceso.terminate()
    try:
        proceso.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proceso.kill()
        proceso.wait(timeout=3)


def leer(proceso: subprocess.Popen, n_bytes: int) -> bytes:
    """Lee exactamente n_bytes (o menos si el proceso termina).

    Un pipe puede devolver menos de lo pedido, así que hay que insistir.
    """
    if proceso.stdout is None:
        return b""
    trozos: list[bytes] = []
    leidos = 0
    while leidos < n_bytes:
        trozo = proceso.stdout.read(n_bytes - leidos)
        if not trozo:
            break
        trozos.append(trozo)
        leidos += len(trozo)
    return b"".join(trozos)


def rms(bloque: bytes) -> float:
    """Volumen eficaz del bloque, de 0.0 (silencio) a 1.0 (saturación).

    array('h') interpreta los bytes como enteros de 16 bits. En x86 y ARM
    little-endian coincide con el formato que entrega parec.
    """
    if len(bloque) < BYTES_POR_MUESTRA:
        return 0.0
    muestras = array("h")
    muestras.frombytes(bloque[: len(bloque) // BYTES_POR_MUESTRA * BYTES_POR_MUESTRA])
    if not muestras:
        return 0.0
    suma = 0
    for muestra in muestras:
        suma += muestra * muestra
    return math.sqrt(suma / len(muestras)) / 32768.0


def nivel_visible(volumen: float) -> float:
    """Convierte el volumen en algo que se vea bien en una barra.

    El oído no es lineal: la voz normal ronda 0.02–0.15 de RMS. En escala
    logarítmica, -60 dBFS se ve como 0 y 0 dBFS como 1.
    """
    if volumen <= 1e-6:
        return 0.0
    db = 20.0 * math.log10(volumen)
    return max(0.0, min(1.0, (db + 60.0) / 60.0))


class Captura:
    """Mantiene abierto `parec` sobre la salida por defecto.

    Si cambia la salida (por ejemplo, se conectan unos auriculares Bluetooth a
    mitad de sesión), cierra `parec` y lo reabre sobre la nueva. Solo consulta
    `pactl` cada `revisar_cada` segundos: dos llamadas pequeñas, sin gastar RAM.

    Con `seguir=False` (el usuario eligió `--fuente`) nunca cambia de fuente.
    """

    def __init__(self, fuente: str, seguir: bool = True,
                 revisar_cada: float = 15.0) -> None:
        self.fuente = fuente
        self.seguir = seguir
        self.revisar_cada = revisar_cada
        self.cerrada = False
        self._proceso: subprocess.Popen | None = None
        self._proxima_revision = 0.0
        self._abrir()

    def _abrir(self) -> None:
        if self._proceso is not None:
            _cerrar(self._proceso)
        self._proceso = abrir_captura(self.fuente)
        self._proxima_revision = time.monotonic() + self.revisar_cada

    def _revisar(self) -> bool:
        """Reabre si cambió la salida por defecto. Devuelve True si reabrió."""
        if self.cerrada or not self.seguir:
            return False
        nueva = mejor_monitor()
        if not nueva or nueva == self.fuente:
            return False
        self.fuente = nueva
        self._abrir()
        return True

    def leer(self, n_bytes: int) -> bytes:
        """Lee PCM de la fuente actual, cambiando de fuente si hace falta."""
        if self.cerrada or self._proceso is None:
            return b""
        datos = leer(self._proceso, n_bytes)
        if datos:
            if time.monotonic() >= self._proxima_revision:
                self._revisar()
            return datos
        # `parec` terminó: o se desconectó el dispositivo, o cambió la salida.
        if self._revisar() and self._proceso is not None:
            return leer(self._proceso, n_bytes)
        return b""

    def cerrar(self) -> None:
        """Cierra la captura y no la reabre."""
        self.cerrada = True
        if self._proceso is not None:
            _cerrar(self._proceso)
            self._proceso = None
