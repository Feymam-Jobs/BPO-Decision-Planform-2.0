"""Uso:  python -m bpo_automation [--dry-run] [--no-email] [--dataset RUTA.xlsx]"""
from __future__ import annotations

import argparse
import logging
import sys

from . import __version__
from .config import load_config
from .data import DatasetError
from .mailer import MailError
from .pipeline import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bpo_automation",
        description="Calcula prioridades y TMO por agente desde un Excel, genera el dashboard y envía el correo.",
    )
    parser.add_argument("--config", default="config.toml", help="ruta del config.toml (por defecto: ./config.toml)")
    parser.add_argument("--dataset", help="Excel de entrada (sustituye input.dataset del config)")
    parser.add_argument("--output-dir", help="carpeta de salida (sustituye output.dir del config)")
    parser.add_argument("--no-email", action="store_true", help="solo genera los archivos; no arma ni envía el correo")
    parser.add_argument("--dry-run", action="store_true",
                        help="arma el correo completo y lo guarda como correo.eml, sin enviarlo")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    try:
        cfg = load_config(args.config)
        run(cfg, dataset=args.dataset, send=not args.no_email, dry_run=args.dry_run, output_dir=args.output_dir)
    except (DatasetError, MailError, ValueError) as exc:
        logging.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
