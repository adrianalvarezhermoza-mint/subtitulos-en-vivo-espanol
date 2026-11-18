#!/usr/bin/env python3
"""Subtítulos en vivo inglés → español, en la terminal.

Estado actual: HITO 2. Escucha el audio del sistema y transcribe el inglés.
Todavía no traduce.

    python3 subtitulos.py --listar
    python3 subtitulos.py --medidor          # solo nivel de volumen
    python3 subtitulos.py                    # transcribir en vivo
    python3 subtitulos.py --archivo x.wav --medir
"""

from __future__ import annotations

import argparse
import queue
import sys
import threading
import time
from pathlib import Path

import audio
import motor

UMBRAL_SILENCIO = 0.008  # por debajo de esto no vale la pena gastar CPU
SEGUNDOS_BLOQUE = 5.0


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


def archivo(ruta: str, glosario: str, modelo: str) -> int:
    """Transcribe un archivo ya grabado. Sirve de prueba y para el hito 5."""
    motor.cargar(modelo)  # fuera del cronómetro: cargar no es transcribir
    inicio = time.monotonic()
    segmentos, info = motor.transcribir_archivo(ruta, glosario, modelo)
    total = time.monotonic() - inicio

    for segmento in segmentos:
        print(f"[{segmento.start:6.1f}] {segmento.text.strip()}")

    print()
    print(f"{len(segmentos)} segmentos · {info.duration:.1f} s de audio "
          f"en {total:.1f} s de proceso")
    print(f"RTF: {total / info.duration:.2f}  (< 1 significa más rápido que el habla)")
    return 0


def vivo(fuente: str, glosario: str, modelo: str, bloque_seg: float, medir: bool) -> int:
    proceso = audio.abrir_captura(fuente)
    cola: queue.Queue[bytes | None] = queue.Queue(maxsize=3)
    parar = threading.Event()

    def lector() -> None:
        paso = audio.BYTES_POR_SEGUNDO // 8  # 125 ms
        acumulado = bytearray()
        while not parar.is_set():
            datos = audio.leer(proceso, paso)
            if not datos:
                break
            acumulado += datos
            if len(acumulado) >= audio.BYTES_POR_SEGUNDO * bloque_seg:
                bloque = bytes(acumulado)
                acumulado.clear()
                if audio.rms(bloque) < UMBRAL_SILENCIO:
                    continue  # silencio: no se transcribe, se ahorra la CPU
                try:
                    cola.put(bloque, timeout=1)
                except queue.Full:
                    pass  # preferible perder un bloque a acumular retraso
        parar.set()
        cola.put(None)

    def trabajador() -> None:
        while True:
            pcm = cola.get()
            if pcm is None:
                break
            inicio = time.monotonic()
            try:
                texto = motor.transcribir_pcm(pcm, glosario, modelo)
            except Exception as error:  # no tumbar la reunión por un bloque raro
                print(f"\n[error] {error}", file=sys.stderr)
                continue
            if not texto:
                continue
            sufijo = ""
            if medir:
                segundos = len(pcm) / audio.BYTES_POR_SEGUNDO
                sufijo = f"  (rtf {(time.monotonic() - inicio) / segundos:.2f})"
            sys.stdout.write("\r" + " " * 60 + "\r")
            print(f"[{time.strftime('%H:%M:%S')}] {texto}{sufijo}", flush=True)

    hilo_lector = threading.Thread(target=lector, daemon=True)
    hilo_trabajador = threading.Thread(target=trabajador, daemon=True)
    hilo_lector.start()
    hilo_trabajador.start()

    print(f"Fuente: {fuente}")
    print(f"Modelo: {modelo} · bloques de {bloque_seg:.0f} s")
    print("Ctrl+C para salir.\n")

    try:
        while hilo_trabajador.is_alive():
            hilo_trabajador.join(timeout=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        parar.set()
        proceso.terminate()
        try:
            proceso.wait(timeout=3)
        except Exception:
            proceso.kill()

    return 0


def main() -> int:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Subtítulos EN→ES en la terminal.")
    parser.add_argument("--listar", action="store_true", help="mostrar fuentes y salir")
    parser.add_argument("--medidor", action="store_true", help="solo nivel de volumen")
    parser.add_argument("--fuente", metavar="NOMBRE", help="fuente de audio a usar")
    parser.add_argument("--archivo", metavar="RUTA", help="transcribir un archivo")
    parser.add_argument("--modelo", default=motor.MODELO_POR_DEFECTO)
    parser.add_argument("--glosario", default="glosario.txt", help="texto de apoyo")
    parser.add_argument("--chunk", type=float, default=SEGUNDOS_BLOQUE,
                        help="segundos de audio por bloque")
    parser.add_argument("--duracion", type=float, help="parar tras N segundos")
    parser.add_argument("--medir", action="store_true", help="mostrar el RTF")
    args = parser.parse_args()

    if args.listar:
        return listar()

    rutas = Path(args.glosario)
    glosario = motor.leer_glosario(rutas) if rutas.exists() else ""

    if args.archivo:
        return archivo(args.archivo, glosario, args.modelo)

    fuente = args.fuente or audio.mejor_monitor()
    if not fuente:
        print("No hay ningún monitor de audio disponible.")
        print("Prueba `python3 subtitulos.py --listar` y elige uno con --fuente.")
        return 1

    if args.medidor:
        return medidor(fuente, args.duracion)
    return vivo(fuente, glosario, args.modelo, args.chunk, args.medir)


if __name__ == "__main__":
    sys.exit(main())
