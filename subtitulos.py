#!/usr/bin/env python3
"""Subtítulos en vivo inglés → español, en la terminal.

Estado actual: HITO 3. Escucha el audio del sistema, transcribe el inglés y lo
traduce al español.

    python3 subtitulos.py --listar
    python3 subtitulos.py --medidor          # solo nivel de volumen
    python3 subtitulos.py                    # transcribir y traducir en vivo
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
import traductor

UMBRAL_SILENCIO = 0.008  # por debajo de esto no vale la pena gastar CPU
SEGUNDOS_BLOQUE = 12.0   # tope: un bloque nunca crece más que esto
PAUSA_CORTE = 0.3        # esta pausa cierra la frase (segundos)
MIN_BLOQUE = 1.0         # no cortar antes: un trozo más corto no da contexto


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


def medidor(fuente: str, duracion: float | None, seguir: bool) -> int:
    captura = audio.Captura(fuente, seguir=seguir)
    actual = captura.fuente
    bloque = audio.BYTES_POR_SEGUNDO // 8  # 125 ms

    print(f"Fuente: {captura.fuente}")
    print("Formato: 16 kHz mono s16le")
    print("Pon un vídeo en inglés. Ctrl+C para salir.\n")

    inicio = time.monotonic()
    try:
        while True:
            if duracion is not None and time.monotonic() - inicio >= duracion:
                break
            datos = captura.leer(bloque)
            if captura.fuente != actual:
                actual = captura.fuente
                print(f"\n[audio] salida cambiada: {actual}")
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
        captura.cerrar()

    print("\n")
    return 0


def _preparar_traduccion(motor_traducir: str) -> str:
    """Carga el traductor antes de empezar; si falla, sigue sin traducir."""
    try:
        elegido = traductor.preparar(motor_traducir)
    except traductor.ErrorTraduccion as error:
        print(f"[aviso] sin traducción: {error}", file=sys.stderr)
        return "ninguno"
    if elegido != "ninguno":
        print(f"Traductor: {elegido}")
    return elegido


def _traducir(texto: str, motor_traducir: str) -> tuple[str, str]:
    """Traduce un bloque. Si el motor falla, lo apaga para no repetir el error."""
    if motor_traducir == "ninguno":
        return "", motor_traducir
    try:
        return traductor.traducir(texto, motor_traducir), motor_traducir
    except traductor.ErrorTraduccion as error:
        print(f"\n[aviso] traducción desactivada: {error}", file=sys.stderr)
        return "", "ninguno"


def archivo(ruta: str, glosario: str, modelo: str, motor_traducir: str) -> int:
    """Transcribe un archivo ya grabado. Sirve de prueba y para el hito 5."""
    motor.cargar(modelo)  # fuera del cronómetro: cargar no es transcribir
    motor_traducir = _preparar_traduccion(motor_traducir)
    inicio = time.monotonic()
    segmentos, info = motor.transcribir_archivo(ruta, glosario, modelo)
    total = time.monotonic() - inicio

    for segmento in segmentos:
        texto = segmento.text.strip()
        print(f"[{segmento.start:6.1f}] {texto}")
        espanol, motor_traducir = _traducir(texto, motor_traducir)
        if espanol:
            print(f"           es: {espanol}")

    print()
    print(f"{len(segmentos)} segmentos · {info.duration:.1f} s de audio "
          f"en {total:.1f} s de proceso")
    print(f"RTF: {total / info.duration:.2f}  (< 1 significa más rápido que el habla)")
    return 0


def vivo(fuente: str, glosario: str, modelo: str, bloque_seg: float, medir: bool,
         motor_traducir: str, seguir: bool) -> int:
    # Cargar antes de capturar: si tarda, no se acumula audio viejo en el tubo.
    motor.cargar(modelo)
    motor_traducir = _preparar_traduccion(motor_traducir)
    captura = audio.Captura(fuente, seguir=seguir)
    cola: queue.Queue[bytes | None] = queue.Queue(maxsize=3)
    parar = threading.Event()

    def lector() -> None:
        paso = audio.BYTES_POR_SEGUNDO // 8  # 125 ms
        tope = int(audio.BYTES_POR_SEGUNDO * bloque_seg)
        minimo = int(audio.BYTES_POR_SEGUNDO * MIN_BLOQUE)
        pausa = int(audio.BYTES_POR_SEGUNDO * PAUSA_CORTE)
        acumulado = bytearray()
        silencio = 0  # bytes seguidos por debajo del umbral, al final del bloque
        actual = captura.fuente
        while not parar.is_set():
            datos = captura.leer(paso)
            if captura.fuente != actual:
                actual = captura.fuente
                sys.stdout.write("\r" + " " * 60 + "\r")
                print(f"[audio] salida cambiada: {actual}", flush=True)
            if not datos:
                if not parar.is_set():
                    print("\n[audio] la captura se cerró. ¿Se desconectó el dispositivo?",
                          flush=True)
                break
            if audio.rms(datos) >= UMBRAL_SILENCIO:
                acumulado += datos
                silencio = 0
            elif acumulado:
                acumulado += datos  # pausa dentro de una frase ya empezada
                silencio += len(datos)
            else:
                continue  # pausa inicial: el bloque empieza cuando suena algo
            acumulado_sin_pausa = len(acumulado) - silencio
            # Se cierra en una pausa lo bastante larga (frase entera) o al llegar
            # al tope (nadie habla sin pausas mucho rato; mejor no bloquear).
            cerrar = len(acumulado) >= tope or (
                silencio >= pausa and acumulado_sin_pausa >= minimo
            )
            if not cerrar:
                continue
            bloque = bytes(acumulado[:acumulado_sin_pausa])  # sin la pausa final
            acumulado.clear()
            silencio = 0
            try:
                cola.put(bloque, timeout=1)
            except queue.Full:
                pass  # preferible perder un bloque a acumular retraso
        # Si la captura termina sola, el último trozo no se pierde.
        if not parar.is_set() and len(acumulado) - silencio >= minimo:
            cola.put(bytes(acumulado[: len(acumulado) - silencio]))
        parar.set()
        cola.put(None)

    def trabajador() -> None:
        nonlocal motor_traducir
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
            espanol, motor_traducir = _traducir(texto, motor_traducir)
            if espanol:
                print(f"           es: {espanol}", flush=True)

    hilo_lector = threading.Thread(target=lector, daemon=True)
    hilo_trabajador = threading.Thread(target=trabajador, daemon=True)
    hilo_lector.start()
    hilo_trabajador.start()

    print(f"Fuente: {captura.fuente}")
    print(f"Modelo: {modelo} · bloques de hasta {bloque_seg:.0f} s, "
          f"cortados en pausas de {PAUSA_CORTE:.1f} s")
    print("Ctrl+C para salir.\n")

    try:
        while hilo_trabajador.is_alive():
            hilo_trabajador.join(timeout=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        parar.set()
        captura.cerrar()
        hilo_lector.join(timeout=2)

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
                        help="duración máxima de un bloque (se corta antes en las pausas)")
    parser.add_argument("--duracion", type=float, help="parar tras N segundos")
    parser.add_argument("--medir", action="store_true", help="mostrar el RTF")
    parser.add_argument("--traductor", default="auto",
                        choices=["auto", "argos", "deepl", "mentira", "ninguno"],
                        help="motor de traducción (auto: DeepL si hay clave, si no Argos)")
    args = parser.parse_args()

    if args.listar:
        return listar()

    rutas = Path(args.glosario)
    glosario = motor.leer_glosario(rutas) if rutas.exists() else ""

    if args.archivo:
        return archivo(args.archivo, glosario, args.modelo, args.traductor)

    fuente = args.fuente or audio.mejor_monitor()
    if not fuente:
        print("No hay ningún monitor de audio disponible.")
        print("Prueba `python3 subtitulos.py --listar` y elige uno con --fuente.")
        return 1

    if args.medidor:
        return medidor(fuente, args.duracion, seguir=args.fuente is None)
    return vivo(fuente, glosario, args.modelo, args.chunk, args.medir, args.traductor,
                seguir=args.fuente is None)


if __name__ == "__main__":
    sys.exit(main())
