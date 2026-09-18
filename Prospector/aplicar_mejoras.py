"""Deja el corpus limpio y al día con el motor nuevo. Cinco pasos, retomables.

    py aplicar_mejoras.py --fecha 2026-09-14

Cada paso es idempotente: si ya se hizo, avisa y sigue. Si cortás con Ctrl+C,
volvés a correr lo mismo y retoma donde iba — incluida la auditoría, que ahora
guarda cada 10 sitios medidos (antes guardaba recién al final, así que un corte
a los cuarenta minutos tiraba los cuarenta minutos).

Los pasos, y por qué está cada uno:

  1 · recuperar-whatsapp   los mensajes mandados a mano no quedaban registrados
  2 · audit --forzar       los hallazgos viejos vienen sin partir en tres, y es
                           el paso que captura el WhatsApp publicado en cada web
  3 · audit --solo …       re-mide los "inaccesible": casi la mitad eran webs
                           vivas que fallaron por un tropiezo de DNS
  4 · compose --forzar     reescribe los borradores de los dos canales
  5 · lint                 mide duplicación, repetición y validación

Opciones:
    --fecha D       día real de los WhatsApp mandados sin registrar (AAAA-MM-DD)
    --sin-auditar   saltea los pasos 2 y 3 (son los que tardan)
    --si            no pregunta nada
    --paso N        corre solo ese paso (1 a 5)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

try:
    from prospector.config import ensure_dirs, settings
    from prospector.logging_setup import setup_logging
except ModuleNotFoundError:
    print("No encuentro el paquete `prospector`.")
    print(f"Este archivo tiene que estar en la raíz del proyecto: {RAIZ}")
    raise SystemExit(1)


def titulo(n: int, texto: str, detalle: str) -> None:
    print()
    print("═" * 70)
    print(f"  PASO {n} · {texto}")
    print(f"  {detalle}")
    print("═" * 70)


def confirmar(pregunta: str, automatico: bool) -> bool:
    if automatico:
        return True
    return input(f"{pregunta} (ENTER sí / 'n' no): ").strip().lower() != "n"


# ─────────────────────────────── Los cinco pasos ───────────────────────────────

def paso_1_recuperar(automatico: bool, fecha: str | None = None) -> None:
    """Da de alta en el registro los WhatsApp que se mandaron sin dejar rastro."""
    titulo(1, "Registrar los WhatsApp mandados a mano",
           "Los que quedaron con estado='enviado' y nada más: ni fecha, ni canal.")
    from prospector import migrate

    cuantos = migrate.recuperar_whatsapp(simular=True, fecha=fecha)
    if not cuantos:
        print("  Nada pendiente: ya están todos registrados.")
        return
    if not fecha:
        print("  Sin --fecha quedan sin día. Si sabés cuándo los mandaste, cortá y corré:")
        print("      py aplicar_mejoras.py --fecha AAAA-MM-DD")
    if confirmar(f"  ¿Doy de alta esos {cuantos}?", automatico):
        migrate.recuperar_whatsapp(simular=False, fecha=fecha)


def paso_2_auditar(automatico: bool) -> None:
    """Re-mide todos los sitios. Es el paso largo y el más importante.

    Trae dos cosas que no se pueden conseguir de otra forma: los hallazgos
    partidos en observación / consecuencia / puente (sin eso el mensaje repite
    la consecuencia y cierra con un puente que no viene a cuento), y el número
    de WhatsApp que cada negocio publica en su propia web — el único número
    del que se sabe con certeza que está en WhatsApp.
    """
    titulo(2, "Re-auditar los sitios (el paso largo)",
           "Un navegador por sitio, concurrencia 3. Puede ser una hora o más.")
    print("  Guarda cada 10 sitios: si cortás, retomás con --reanudar y no perdés nada.")
    if not confirmar("  ¿Lo corro ahora?", automatico):
        print("  Salteado. Después: py -m prospector audit --forzar")
        return
    from prospector import pipeline

    arranque = time.time()
    try:
        pipeline.auditar_leads(settings, forzar=True)
    except KeyboardInterrupt:
        print("\n  Cortado. Lo medido quedó guardado.")
        print("  Para seguir: py -m prospector audit --reanudar")
        raise
    print(f"  Listo en {(time.time() - arranque) / 60:.0f} min.")


def paso_3_reverificar(automatico: bool) -> None:
    """Segunda mirada sobre los que no cargaron.

    De los 36 que la tanda anterior marcó "inaccesible", 17 tenían el dominio
    perfectamente vivo: fallaron por un tropiezo de DNS y el sistema les iba a
    escribir "intenté entrar y tu web no cargó", que el dueño desmiente
    abriendo su propia web. Ahora se consulta el DNS por fuera del navegador y
    los que resuelven quedan como `no_medido` en vez de como caídos.
    """
    titulo(3, "Volver sobre los que no cargaron",
           "Son decenas de sitios, no cientos: cinco minutos.")
    from prospector import pipeline

    for veredicto in ("inaccesible", "no_medido"):
        pipeline.auditar_leads(settings, solo_veredicto=veredicto)


def paso_4_redactar(automatico: bool) -> None:
    """Reescribe los borradores de los dos canales con el motor de fragmentos."""
    titulo(4, "Reescribir todos los borradores",
           "Correo con el ensamblador nuevo y WhatsApp con su redactor propio.")
    from prospector import pipeline

    pipeline.redactar_correos(settings, forzar=True)


def paso_5_lint(automatico: bool) -> None:
    """Mide el corpus resultante: duplicación, repetición y validación."""
    titulo(5, "Medir el resultado",
           "Duplicación, apertura más repetida y mensajes que no pasan la validación.")
    from prospector import lint

    lint.imprimir()


PASOS = (paso_1_recuperar, paso_2_auditar, paso_3_reverificar, paso_4_redactar, paso_5_lint)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deja el corpus limpio y al día con el motor de redacción nuevo.")
    parser.add_argument("--sin-auditar", action="store_true",
                        help="saltear los pasos 2 y 3, que son los que tardan")
    parser.add_argument("--si", action="store_true", help="no preguntar nada")
    parser.add_argument("--paso", type=int, choices=[1, 2, 3, 4, 5], help="correr solo ese paso")
    parser.add_argument("--fecha", metavar="AAAA-MM-DD",
                        help="día en que se mandaron los WhatsApp sin registrar")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)
    ensure_dirs()

    try:
        if args.paso:
            if args.paso == 1:
                paso_1_recuperar(args.si, args.fecha)
            else:
                PASOS[args.paso - 1](args.si)
            return 0

        paso_1_recuperar(args.si, args.fecha)
        if args.sin_auditar:
            print("\n  (pasos 2 y 3 salteados por --sin-auditar: los mensajes van a salir")
            print("   con los hallazgos viejos y sin los WhatsApp de cada web)")
        else:
            paso_2_auditar(args.si)
            paso_3_reverificar(args.si)
        paso_4_redactar(args.si)
        paso_5_lint(args.si)
    except KeyboardInterrupt:
        print("\n  Interrumpido. Volvé a correr lo mismo y retoma donde iba.")
        return 130

    print()
    print("  Los .txt de WhatsApp están en data/05_whatsapp/ (mirá _INDICE.txt).")
    print("  Para mandar:  py scripts\\send_whatsapp.py")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
