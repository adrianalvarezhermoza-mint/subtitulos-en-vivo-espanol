#!/usr/bin/env python3
"""Subtítulos en vivo inglés → español, en la terminal.

Estado actual: HITO 1. Solo se escucha el audio del sistema y se muestra el
nivel. Todavía no transcribe ni traduce.

    python3 subtitulos.py --listar
    python3 subtitulos.py
    python3 subtitulos.py --fuente nombre --duracion 5
"""

from __future__ import annotations

import argparse
import sys
import time

import audio


def barra(fraccion: float, ancho: int = 28) -> str:
    """Barra ASCII, para que se vea igual en Linux y en CMD."""
    llenos = int(round(fraccion * ancho))
    return "#" * llenos + "-" * (ancho - llenos)


def listar() -> int:
    fuentes = audio.listar_fuentes()
    if not fuentes:
        print("No se encontró ninguna fuente de audio. ¿Está sonando algo?")
        return 1
    predeterminada = audio.mejor_monitor()
    for i, (nombre, es_monitor) in enumerate(fuentes):
        marca = "*" if nombre == predeterminada else " "
        tipo = "monitor (lo que suena)" if es_monitor else "micrófono"
        print(f"{marca} {i}  {nombre}  [{tipo}]")
    print("\n* = la que se usaría por defecto")
    return 0


def medidor(fuente: str, duracion: float | None) -> int:
    if audio.BYTES_POR_SEGUNDO <= 0:
        return 1
    proceso = audio.abrir_captura(fuente)
    bloque = audio.BYTES_POR_SEGUNDO // 8  # 125 ms

    print(f"Fuente: {fuente}")
    print("Formato: 16 kHz mono s16le")
    print("Pon un vídeo en inglés. Ctrl+C para salir.\n")

    inicio = time.monotonic()
    try:
        while True:
            if duracion is not None and time.monotonic() - inicio >= duracion:
                break
            datos = audio.leer(proceso, bloque)
            if not datos:
                print("\nLa captura se cerró sola. ¿Se desconectó el audio?")
                return 1
            volumen = audio.rms(datos)
            nivel = audio.nivel_visible(volumen)
            sys.stdout.write(
                f"\r {nivel * 100:3.0f}%  [{barra(nivel)}]  {volumen:0.4f}"
            )
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=3)
        except Exception:
            proceso.kill()

    print("\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Subtítulos EN→ES en la terminal (hito 1: medidor de audio)."
    )
    parser.add_argument(
        "--listar", action="store_true", help="mostrar las fuentes de audio y salir"
    )
    parser.add_argument(
        "--fuente", metavar="NOMBRE", help="usar esta fuente en vez de la detectada"
    )
    parser.add_argument(
        "--duracion",
        type=float,
        metavar="SEG",
        help="parar solo tras N segundos (para pruebas)",
    )
    args = parser.parse_args()

    if args.listar:
        return listar()

    fuente = args.fuente or audio.mejor_monitor()
    if not fuente:
        print("No hay ningún monitor de audio disponible.")
        print("Prueba `python3 subtitulos.py --listar` y elige uno con --fuente.")
        return 1

    return medidor(fuente, args.duracion)


if __name__ == "__main__":
    sys.exit(main())
