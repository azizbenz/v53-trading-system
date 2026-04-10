"""CLI entrypoint for the bounded sealed-secrets slice."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from secrets_manager.loader import SecretManagerLoadError, load_secret_text, write_unsealed_text
from secrets_manager.sealer import generate_master_key, seal_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m secrets_manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen_key = subparsers.add_parser("gen-key", help="Generate a master key file")
    gen_key.add_argument("path", help="Destination master key path")
    gen_key.add_argument("--force", action="store_true", help="Overwrite an existing master key")

    seal = subparsers.add_parser("seal", help="Seal a plaintext secret file")
    seal.add_argument("path", help="Plaintext file to seal")
    seal.add_argument("--key-path", required=True, help="Master key path")
    seal.add_argument("--output", help="Optional output path for the sealed envelope")
    seal.add_argument(
        "--delete-source",
        action="store_true",
        help="Delete the plaintext source after a successful seal",
    )

    unseal = subparsers.add_parser("unseal", help="Unseal a sealed secret file")
    unseal.add_argument("path", help="Sealed envelope to unseal")
    unseal.add_argument("--key-path", required=True, help="Master key path")
    unseal.add_argument("--output", required=True, help="Destination plaintext path")
    unseal.add_argument("--force", action="store_true", help="Overwrite output if it exists")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "gen-key":
            path = generate_master_key(args.path, force=args.force)
            print(path)
            return 0
        if args.command == "seal":
            path = seal_file(
                args.path,
                key_path=args.key_path,
                output_path=args.output,
                remove_source=args.delete_source,
            )
            print(path)
            return 0
        if args.command == "unseal":
            text = load_secret_text(args.path, key_path=args.key_path)
            path = write_unsealed_text(args.output, text=text, force=args.force)
            print(path)
            return 0
    except SecretManagerLoadError as exc:
        parser.exit(1, f"{exc}\n")
    parser.exit(2, "Unknown command\n")


__all__ = ["build_parser", "main"]
