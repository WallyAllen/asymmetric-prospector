"""Punto de entrada único:  python -m prospector <comando>"""
from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import AUDITED_FILE, COMPOSED_FILE, RAW_FILE, ensure_dirs, settings
from .logging_setup import setup_logging
from .storage import load_leads

BANNER = r"""
  ┌─────────────────────────────────────────────┐
  │  PROSPECTOR  ·  prospección asimétrica      │
  └─────────────────────────────────────────────┘"""


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="prospector",
        description="Encuentra negocios con webs malas (o sin web) y escríbeles con pruebas.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  python -m prospector mine \"clinicas dentales valencia\"\n"
            "  python -m prospector audit --limite 10\n"
            "  python -m prospector compose\n"
            "  python -m prospector send                # simulación\n"
            "  python -m prospector send --enviar-de-verdad --limite 5\n"
            "  python -m prospector run \"fisioterapia sevilla\"\n"
        ),
    )
    p.add_argument("--verbose", "-v", action="store_true", help="traza detallada")
    p.add_argument("--version", action="version", version=f"prospector {__version__}")
    sub = p.add_subparsers(dest="comando", required=True)

    m = sub.add_parser("mine", help="minar prospectos de un nicho")
    m.add_argument("query", nargs="+", help='p. ej. "clinicas dentales valencia"')
    m.add_argument("--fuente", choices=["maps", "buscador"], default="maps")
    m.add_argument("--max", type=int, help="tope de leads a extraer")
    m.add_argument("--sin-contactos", action="store_true", help="no visitar las webs a por el email")
    m.add_argument("--visible", action="store_true", help="mostrar el navegador")

    e = sub.add_parser("enrich", help="segunda pasada buscando emails en lo ya minado")
    e.add_argument("--visible", action="store_true")

    a = sub.add_parser("audit", help="auditar las webs y calificar la oportunidad")
    a.add_argument("--limite", type=int, help="auditar solo los primeros N leads")
    a.add_argument("--forzar", action="store_true", help="reauditar incluso lo ya auditado")
    a.add_argument("--sin-ia", action="store_true", help="solo señales objetivas, sin jurado visual")
    a.add_argument("--umbral", type=int, help="score mínimo para no descartar (por defecto 35)")
    a.add_argument("--concurrencia", type=int, help="webs auditadas en paralelo")
    a.add_argument("--visible", action="store_true")

    c = sub.add_parser("compose", help="redactar los primeros mensajes")
    c.add_argument("--forzar", action="store_true", help="reescribir los que ya tienen borrador")
    c.add_argument("--sin-ia", action="store_true", help="usar solo el motor de plantillas")

    s = sub.add_parser("send", help="enviar la cola (simula por defecto)")
    s.add_argument("--enviar-de-verdad", action="store_true", help="enviar realmente los correos")
    s.add_argument("--limite", type=int, help="máximo de correos en esta tanda")

    r = sub.add_parser("run", help="pipeline completo de una tirada")
    r.add_argument("query", nargs="+")
    r.add_argument("--fuente", choices=["maps", "buscador"], default="maps")
    r.add_argument("--enviar-de-verdad", action="store_true")
    r.add_argument("--limite", type=int)

    sub.add_parser("status", help="estado actual del embudo")
    i = sub.add_parser("report", help="generar el informe HTML")
    i.add_argument("--minimo", type=int, default=0, help="score mínimo a incluir")
    return p


def _estado() -> None:
    etapas = (
        ("1 · minados", RAW_FILE),
        ("2 · auditados", AUDITED_FILE),
        ("3 · redactados", COMPOSED_FILE),
    )
    print(BANNER)
    for titulo, ruta in etapas:
        leads = load_leads(ruta)
        conteo: dict[str, int] = {}
        for lead in leads:
            conteo[lead.estado] = conteo.get(lead.estado, 0) + 1
        detalle = ", ".join(f"{v} {k}" for k, v in sorted(conteo.items())) or "vacío"
        print(f"  {titulo:<16} {len(leads):>4} leads   ({detalle})")

    auditados = load_leads(AUDITED_FILE)
    calificados = [l for l in auditados if l.audit and l.estado != "descartado"]
    if calificados:
        calificados.sort(key=lambda l: -l.audit.score)
        print("\n  Mejores oportunidades:")
        for lead in calificados[:5]:
            marca = "✉" if lead.contactable else "·"
            print(f"    {marca} {lead.audit.score:>3}/100  {lead.etiqueta[:52]:<52} {lead.audit.veredicto}")
    print()


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    log = setup_logging(verbose=args.verbose)
    ensure_dirs()

    from . import pipeline, report

    cfg = settings
    if getattr(args, "visible", False):
        cfg.mining.headless = False
        cfg.audit.headless = False
    if getattr(args, "max", None):
        cfg.mining.max_leads = args.max
    if getattr(args, "umbral", None) is not None:
        cfg.audit.min_score = args.umbral
    if getattr(args, "concurrencia", None):
        cfg.audit.concurrency = args.concurrencia
    if getattr(args, "sin_ia", False):
        cfg.audit.use_vision = False
        cfg.compose.use_ai = False

    try:
        if args.comando == "mine":
            pipeline.minar(" ".join(args.query), cfg, fuente=args.fuente,
                           enriquecer=not args.sin_contactos)
        elif args.comando == "enrich":
            pipeline.enriquecer_contactos(cfg)
        elif args.comando == "audit":
            pipeline.auditar_leads(cfg, forzar=args.forzar, limite=args.limite)
        elif args.comando == "compose":
            pipeline.redactar_correos(cfg, forzar=args.forzar)
        elif args.comando == "send":
            pipeline.enviar_correos(cfg, simular=not args.enviar_de_verdad, limite=args.limite)
        elif args.comando == "run":
            pipeline.ejecutar_todo(" ".join(args.query), cfg, fuente=args.fuente,
                                   simular=not args.enviar_de_verdad, limite_envio=args.limite)
        elif args.comando == "status":
            _estado()
        elif args.comando == "report":
            report.generar(minimo=args.minimo)
    except KeyboardInterrupt:
        log.warning("Interrumpido. El progreso quedó guardado; puedes retomar donde ibas.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
