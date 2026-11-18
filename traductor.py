"""Traducción inglés → español, con motores intercambiables.

Una sola función pública:

    traducir("hello world")                       # elige solo
    traducir("hello world", motor="argos")        # obliga a Argos
    traducir("hello world", motor="deepl")        # obliga a DeepL
    traducir("hello world", motor="mentira")      # no traduce: para probar el flujo

Regla de elección con `motor="auto"`: si hay clave de DeepL se usa DeepL y, si
falla, se cae a Argos. Sin clave, se usa Argos directamente.

Nada de Argos ni de DeepL se importa hasta que se usa ese motor. Así el programa
arranca aunque falten dependencias, y el motor de mentira permite probar el resto
del proyecto sin descargar nada.

Los paquetes de Argos se guardan dentro del proyecto (`modelos/argos/`), no en el
home, y el modelo local se instala solo la primera vez que hace falta.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).parent
CARPETA_ARGOS = RAIZ / "modelos" / "argos"
IDIOMA_ORIGEN = "en"
IDIOMA_DESTINO = "es"
VARIABLE_CLAVE = "DEEPL_API_KEY"
TIEMPO_MAXIMO_DEEPL = 10  # segundos; un subtítulo no puede esperar más

_traduccion_argos = None  # se carga una vez y se reutiliza


class ErrorTraduccion(Exception):
    """Fallo del motor de traducción, con un mensaje que se puede leer."""


def _preparar_entorno_argos() -> None:
    """Deja los datos de Argos dentro del proyecto antes de importarlo.

    Argos crea carpetas en el home al importarse. Con estas variables usa
    `modelos/argos/` y el proyecto sigue siendo autónomo.
    """
    destinos = {
        "ARGOS_PACKAGES_DIR": CARPETA_ARGOS / "paquetes",
        "XDG_DATA_HOME": CARPETA_ARGOS / "xdg",
        "XDG_CONFIG_HOME": CARPETA_ARGOS / "xdg",
        "XDG_CACHE_HOME": CARPETA_ARGOS / "xdg",
    }
    for variable, destino in destinos.items():
        destino.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault(variable, str(destino))

    # Ajustes medidos en este equipo (ver ESTADO.md). `setdefault` deja que se
    # cambien desde fuera sin tocar el código.
    os.environ.setdefault("ARGOS_DEVICE_TYPE", "cpu")
    os.environ.setdefault("ARGOS_CHUNK_TYPE", "MINISBD")   # no cargar Stanza/SpaCy
    os.environ.setdefault("ARGOS_COMPUTE_TYPE", "int8")    # mitad de RAM, el doble de rápido
    os.environ.setdefault("ARGOS_BEAM_SIZE", "1")
    os.environ.setdefault("ARGOS_INTRA_THREADS", "2")      # 2 núcleos reales


def _instalar_modelo_local(paquetes) -> None:
    """Instala el .argosmodel que ya está en disco, sin usar la red."""
    archivos = sorted(CARPETA_ARGOS.glob("*.argosmodel"))
    if not archivos:
        raise ErrorTraduccion(
            "No hay modelo en→es de Argos en "
            f"{CARPETA_ARGOS}. Descárgalo con curl (ver ESTADO.md)."
        )
    for archivo in archivos:
        print(f"Instalando modelo de Argos: {archivo.name}…", file=sys.stderr)
        paquetes.install_from_path(archivo)


def _cargar_argos():
    """Carga Argos la primera vez y devuelve el traductor en→es."""
    global _traduccion_argos
    if _traduccion_argos is not None:
        return _traduccion_argos

    _preparar_entorno_argos()
    try:
        from argostranslate import package as paquetes
        from argostranslate import translate as argos
    except ImportError as error:
        raise ErrorTraduccion(
            "Falta argostranslate. Instálalo con:\n"
            "  .venv/bin/python -m pip install argostranslate"
        ) from error

    origen = argos.get_language_from_code(IDIOMA_ORIGEN)
    destino = argos.get_language_from_code(IDIOMA_DESTINO)
    if origen is None or destino is None:
        _instalar_modelo_local(paquetes)
        origen = argos.get_language_from_code(IDIOMA_ORIGEN)
        destino = argos.get_language_from_code(IDIOMA_DESTINO)

    if origen is None or destino is None:
        raise ErrorTraduccion(
            "Argos está instalado, pero no encuentra el modelo en→es. "
            f"Revisa {CARPETA_ARGOS}."
        )

    _traduccion_argos = origen.get_translation(destino)
    return _traduccion_argos


def _argos(texto: str) -> str:
    return _cargar_argos().translate(texto).strip()


def _deepl(texto: str, clave: str | None = None) -> str:
    """Traduce con la API de DeepL. Solo se envía el texto, nada más."""
    clave = (clave or os.environ.get(VARIABLE_CLAVE, "")).strip()
    if not clave:
        raise ErrorTraduccion(
            f"Falta la clave de DeepL: pásala con --clave o en la variable {VARIABLE_CLAVE}."
        )

    # Las claves gratuitas terminan en «:fx» y usan otro servidor.
    servidor = "https://api-free.deepl.com" if clave.endswith(":fx") else "https://api.deepl.com"
    cuerpo = json.dumps(
        {"text": [texto], "source_lang": "EN", "target_lang": "ES"}
    ).encode("utf-8")
    peticion = urllib.request.Request(
        servidor + "/v2/translate",
        data=cuerpo,
        headers={
            "Authorization": f"DeepL-Auth-Key {clave}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(peticion, timeout=TIEMPO_MAXIMO_DEEPL) as respuesta:
            datos = json.load(respuesta)
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise ErrorTraduccion(f"DeepL no respondió: {error}") from error

    return datos["translations"][0]["text"].strip()


def _mentira(texto: str) -> str:
    """Traductor falso: no traduce, solo marca el texto.

    Sirve para probar el flujo completo (captura → inglés → español) sin instalar
    Argos ni tener clave de DeepL. Si algo falla con este motor, el fallo no es
    de la traducción.
    """
    return f"[mentira] {texto}"


def _elegir(motor: str, clave: str | None) -> str:
    """Resuelve "auto" al motor concreto que se va a usar."""
    motor = (motor or "auto").lower()
    if motor == "auto":
        return "deepl" if (clave or os.environ.get(VARIABLE_CLAVE)) else "argos"
    return motor


def preparar(motor: str = "auto", clave: str | None = None) -> str:
    """Carga el motor al arrancar y devuelve el que se usará.

    Cargar Argos tarda ~5 s. Hacerlo antes de capturar evita que el primer
    subtítulo llegue tarde. Si el motor no está listo, lanza ErrorTraduccion.
    """
    motor = _elegir(motor, clave)
    if motor in ("ninguno", "mentira"):
        return motor
    if motor == "argos":
        _cargar_argos()
        return motor
    if motor == "deepl":
        if not (clave or os.environ.get(VARIABLE_CLAVE)):
            raise ErrorTraduccion(
                f"Falta la clave de DeepL: pásala en la variable {VARIABLE_CLAVE}."
            )
        return motor
    raise ErrorTraduccion(f"Motor desconocido: {motor!r}")


def traducir(texto: str, motor: str = "auto", clave: str | None = None) -> str:
    """Traduce una frase al español y devuelve el texto.

    `motor`: "auto", "argos", "deepl", "mentira" o "ninguno".
    Con "auto", DeepL manda si hay clave; si falla, se usa Argos.
    """
    texto = (texto or "").strip()
    if not texto:
        return ""

    motor = _elegir(motor, clave)

    if motor == "ninguno":
        return ""
    if motor == "mentira":
        return _mentira(texto)
    if motor == "argos":
        return _argos(texto)
    if motor == "deepl":
        try:
            return _deepl(texto, clave)
        except ErrorTraduccion as error:
            print(f"[aviso] DeepL falló ({error}); se usa Argos.", file=sys.stderr)
            try:
                return _argos(texto)
            except ErrorTraduccion as error_argos:
                raise ErrorTraduccion(
                    f"DeepL falló ({error}) y Argos tampoco está listo ({error_argos})."
                ) from error_argos

    raise ErrorTraduccion(
        f"Motor desconocido: {motor!r} (usa auto, argos, deepl, mentira o ninguno)"
    )


def comprobar() -> int:
    """Dice qué motores están listos, sin traducir nada."""
    print("Mentira:  listo (no traduce, solo para probar).")

    _preparar_entorno_argos()
    try:
        from argostranslate import translate as argos
    except ImportError:
        print("Argos:    NO instalado (falta argostranslate).")
    else:
        hay = (
            argos.get_language_from_code(IDIOMA_ORIGEN) is not None
            and argos.get_language_from_code(IDIOMA_DESTINO) is not None
        )
        print("Argos:    instalado;", "modelo en→es listo." if hay else "falta el modelo en→es.")
        if not hay:
            archivos = sorted(CARPETA_ARGOS.glob("*.argosmodel"))
            print(f"          modelos en disco: {len(archivos)}")

    print("DeepL:    " + ("clave configurada." if os.environ.get(VARIABLE_CLAVE) else
                          f"sin clave (variable {VARIABLE_CLAVE})."))
    return 0


def main() -> int:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Traducir una frase inglés → español.")
    parser.add_argument("texto", nargs="*", help="frase a traducir")
    parser.add_argument("--motor", default="auto", choices=["auto", "argos", "deepl", "mentira"])
    parser.add_argument("--clave", help="clave de DeepL (o variable DEEPL_API_KEY)")
    parser.add_argument("--comprobar", action="store_true", help="decir qué motores están listos")
    args = parser.parse_args()

    if args.comprobar:
        return comprobar()

    texto = " ".join(args.texto).strip()
    if not texto:
        parser.error("falta el texto a traducir")

    try:
        print(traducir(texto, args.motor, args.clave))
    except ErrorTraduccion as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
