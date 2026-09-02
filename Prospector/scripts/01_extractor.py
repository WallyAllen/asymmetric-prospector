#!/usr/bin/env python3
"""Compatibilidad: este script ahora delega en el paquete `prospector`.

Equivale a:  python -m prospector mine [args]
Toda la lógica vive en prospector/ para poder probarla y reutilizarla.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prospector.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["mine", *sys.argv[1:]]))
